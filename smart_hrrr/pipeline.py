from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Dict
import logging
import time

from core import downloader
from model_config import get_model_registry
from processor_batch import process_hrrr_parallel
from .io import create_output_structure, get_forecast_hour_dir, get_grib_download_dir, stage_gribs_for_hour
from .products import get_available_products, get_missing_products, check_existing_products
from .utils import check_system_memory


@dataclass
class PipelineConfig:
    model: str = "hrrr"
    categories: Optional[List[str]] = None
    fields: Optional[List[str]] = None
    force_reprocess: bool = False
    compute_only: bool = False
    map_workers: Optional[int] = None
    download_workers: int = 2
    prefetch: int = 2


class GribManager:
    def __init__(self, model: str):
        reg = get_model_registry()
        self.model = model.lower()
        self.model_cfg = reg.get_model(self.model)
        if not self.model_cfg:
            raise ValueError(f"Unknown model: {model}")

    def download_hour(self, cycle: str, forecast_hour: int, central_dir: Path) -> bool:
        logger = logging.getLogger(__name__)

        ok = False
        for file_type in ("pressure", "surface"):
            try:
                path = downloader.download_model_file(
                    cycle=cycle,
                    forecast_hour=forecast_hour,
                    output_dir=central_dir,
                    file_type=file_type,
                    model_config=self.model_cfg,
                )
                if path and path.exists():
                    ok = True
            except Exception as e:
                logger.warning(f"Failed to download {file_type} for F{forecast_hour:02d}: {e}")

        return ok


def _resolve_requested_products(categories: Optional[List[str]], fields: Optional[List[str]]) -> List[str]:
    all_products = get_available_products()

    if fields:
        return fields
    if categories:
        from field_registry import FieldRegistry
        reg = FieldRegistry()
        filtered = []
        for cat in categories:
            filtered.extend(reg.get_fields_by_category(cat).keys())
        return filtered

    return all_products


class PipelineRunner:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.grib = GribManager(config.model)

    def process_hour(self, cycle: str, forecast_hour: int, output_dirs: Dict[str, Path],
                     download_ok: Optional[bool] = None, central_dir: Optional[Path] = None) -> Dict[str, object]:
        logger = logging.getLogger(__name__)
        fhr_dir = get_forecast_hour_dir(output_dirs["run"], forecast_hour)

        if not self.config.force_reprocess and not self.config.compute_only:
            requested = _resolve_requested_products(self.config.categories, self.config.fields)
            missing, existing = get_missing_products(fhr_dir, requested)
            if not missing:
                logger.info(f"✓ F{forecast_hour:02d} already complete ({len(existing)} products)")
                return {"success": True, "forecast_hour": forecast_hour, "skipped": True, "existing_count": len(existing)}

            logger.info(f"F{forecast_hour:02d}: {len(existing)} existing, {len(missing)} missing")

        central_dir = central_dir or get_grib_download_dir(cycle, self.config.model)
        if download_ok is None:
            download_ok = self.grib.download_hour(cycle, forecast_hour, central_dir)

        if not download_ok:
            return {"success": False, "forecast_hour": forecast_hour, "error": "GRIB download failed"}

        try:
            stage_gribs_for_hour(
                cycle=cycle,
                fhr=forecast_hour,
                model=self.config.model,
                central_dir=central_dir,
                fhr_dir=fhr_dir,
            )
        except Exception as e:
            return {"success": False, "forecast_hour": forecast_hour, "error": f"GRIB staging failed: {e}"}

        start = time.time()
        try:
            output_files = process_hrrr_parallel(
                cycle=cycle,
                forecast_hour=forecast_hour,
                output_dir=fhr_dir,
                categories=self.config.categories,
                fields=self.config.fields,
                model=self.config.model,
                map_workers=self.config.map_workers,
                compute_only=self.config.compute_only,
            )
        except Exception as e:
            return {"success": False, "forecast_hour": forecast_hour, "error": str(e)}

        dur = time.time() - start
        if self.config.compute_only:
            computed = len(output_files) if isinstance(output_files, list) else 0
            return {"success": True, "forecast_hour": forecast_hour, "duration": dur,
                    "computed_count": computed, "skipped": False}
        final_products = check_existing_products(fhr_dir)
        if final_products:
            return {"success": True, "forecast_hour": forecast_hour, "duration": dur,
                    "product_count": len(final_products), "skipped": False}

        return {"success": False, "forecast_hour": forecast_hour, "error": "No outputs produced"}

    def process_run(self, date: str, hour: int, forecast_hours: List[int]) -> List[Dict[str, object]]:
        import multiprocessing as mp
        logger = logging.getLogger(__name__)

        output_dirs = create_output_structure(self.config.model, date, hour)
        cycle = f"{date}{hour:02d}"

        logger.info(f"Processing {self.config.model.upper()} run {date} {hour:02d}Z "
                    f"F{min(forecast_hours):02d}-F{max(forecast_hours):02d}")
        logger.info(f"Output directory: {output_dirs['run']}")
        logger.info(f"Categories: {self.config.categories if self.config.categories else 'all'}")
        if self.config.fields:
            logger.info(f"Fields: {self.config.fields}")

        sysmem = check_system_memory()
        if sysmem:
            logger.info(f"System memory: {sysmem['used_mb']:.0f}MB/{sysmem['total_mb']:.0f}MB "
                        f"({sysmem['percent']:.1f}%)")

        cpu_count = mp.cpu_count()
        logger.info(f"Available CPUs: {cpu_count}")

        central_dir = get_grib_download_dir(cycle, self.config.model)
        download_workers = max(1, int(self.config.download_workers))
        prefetch = max(0, int(self.config.prefetch))

        results = []
        futures: Dict[int, object] = {}
        next_idx = 0

        def schedule(fhr: int, executor: ThreadPoolExecutor):
            if fhr in futures:
                return
            futures[fhr] = executor.submit(self.grib.download_hour, cycle, fhr, central_dir)

        with ThreadPoolExecutor(max_workers=download_workers) as ex:
            while next_idx < len(forecast_hours) and len(futures) < prefetch + 1:
                schedule(forecast_hours[next_idx], ex)
                next_idx += 1

            for fhr in forecast_hours:
                if fhr not in futures:
                    schedule(fhr, ex)

                download_ok = futures[fhr].result()
                futures.pop(fhr, None)

                res = self.process_hour(cycle, fhr, output_dirs,
                                        download_ok=download_ok, central_dir=central_dir)
                results.append(res)

                while next_idx < len(forecast_hours) and len(futures) < prefetch + 1:
                    schedule(forecast_hours[next_idx], ex)
                    next_idx += 1

        successful = sum(1 for r in results if r["success"])
        skipped = sum(1 for r in results if r.get("skipped", False))
        failed = len(results) - successful
        logger.info(f"Complete. Total: {len(forecast_hours)}, Successful: {successful}, "
                    f"Skipped: {skipped}, Failed: {failed}")

        return results
