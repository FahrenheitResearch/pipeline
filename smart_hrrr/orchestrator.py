import logging
import time
from pathlib import Path
from typing import List, Optional, Dict

from .availability import check_forecast_hour_availability, get_latest_cycle, get_expected_max_forecast_hour
from .io import create_output_structure
from .pipeline import PipelineConfig, PipelineRunner


def process_forecast_hour_smart(
    cycle: str,
    forecast_hour: int,
    output_dirs: Dict[str, Path],
    categories: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    force_reprocess: bool = False,
    model: str = "hrrr",
    map_workers: Optional[int] = None,
    compute_only: bool = False,
):
    """Process a single forecast hour using the unified pipeline."""
    cfg = PipelineConfig(
        model=model,
        categories=categories,
        fields=fields,
        force_reprocess=force_reprocess,
        compute_only=compute_only,
        map_workers=map_workers,
        download_workers=1,
        prefetch=0,
    )
    runner = PipelineRunner(cfg)
    return runner.process_hour(cycle, forecast_hour, output_dirs)


def process_model_run(
    model: str,
    date: str,
    hour: int,
    forecast_hours: List[int],
    categories: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    max_workers: Optional[int] = None,
    force_reprocess: bool = False,
    profiler=None,
    map_workers: Optional[int] = None,
    download_workers: int = 2,
    prefetch: int = 2,
    compute_only: bool = False,
):
    """Process an entire model run with a single unified pipeline."""
    if map_workers is None:
        map_workers = max_workers
    if map_workers is not None and map_workers < 1:
        map_workers = None

    cfg = PipelineConfig(
        model=model,
        categories=categories,
        fields=fields,
        force_reprocess=force_reprocess,
        compute_only=compute_only,
        map_workers=map_workers,
        download_workers=download_workers,
        prefetch=prefetch,
    )
    runner = PipelineRunner(cfg)
    return runner.process_run(date, hour, forecast_hours)


def monitor_and_process_latest(
    categories: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    workers: Optional[int] = None,
    check_interval: int = 30,
    force_reprocess: bool = False,
    hour_range: Optional[List[int]] = None,
    max_hours: Optional[int] = None,
    model: str = "hrrr",
):
    """Monitor for new forecast hours and process them as they become available."""
    logger = logging.getLogger(__name__)

    cycle, cycle_time = get_latest_cycle(model)
    if cycle is None:
        logger.error(f"No available cycles for {model}")
        return [], None, None, 0

    date_str = cycle_time.strftime("%Y%m%d")
    hour = cycle_time.hour

    output_dirs = create_output_structure(model, date_str, hour)

    expected_max_fhr = get_expected_max_forecast_hour(cycle)

    if hour_range is not None:
        forecast_hours = [h for h in hour_range if h <= expected_max_fhr]
    elif max_hours is not None:
        forecast_hours = list(range(0, min(max_hours, expected_max_fhr) + 1))
    else:
        forecast_hours = list(range(0, expected_max_fhr + 1))

    map_workers = workers if workers is not None and workers > 0 else None
    cfg = PipelineConfig(
        model=model,
        categories=categories,
        fields=fields,
        force_reprocess=force_reprocess,
        map_workers=map_workers,
        download_workers=1,
        prefetch=0,
    )
    runner = PipelineRunner(cfg)

    processed_hours = set()
    available_hours = set()
    consecutive_no_new = 0
    max_consec = 10

    try:
        while True:
            logger.info("Checking for new forecast hours...")

            new_found = False
            for fhr in forecast_hours:
                if fhr in processed_hours:
                    continue

                available_files = check_forecast_hour_availability(cycle, fhr)
                if available_files:
                    if fhr not in available_hours:
                        logger.info(f"New forecast hour: F{fhr:02d} ({', '.join(available_files)})")
                        available_hours.add(fhr)
                        new_found = True

                    res = runner.process_hour(cycle, fhr, output_dirs)
                    if res["success"]:
                        processed_hours.add(fhr)
                    else:
                        logger.error(f"F{fhr:02d} failed: {res.get('error')}")

            consecutive_no_new = 0 if new_found else consecutive_no_new + 1

            if len(processed_hours) >= len(forecast_hours):
                break

            if consecutive_no_new >= max_consec:
                break

            time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")

    return list(processed_hours), date_str, hour, forecast_hours
