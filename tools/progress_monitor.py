#!/usr/bin/env python3
"""
Filesystem-based progress monitor for HRRR processing.

Usage:
  python tools/progress_monitor.py 2025122717
  python tools/progress_monitor.py 2025122717 --hours 0-18 --map-workers 14
  python tools/progress_monitor.py --latest --hours 0-6
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

# Allow running from repo root without installing as a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from field_registry import FieldRegistry
from model_config import get_model_registry
from smart_hrrr.availability import get_expected_max_forecast_hour, get_latest_cycle
from smart_hrrr.utils import parse_hour_range


def _human_size(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}PB"


def _bar(progress: float, width: int = 24) -> str:
    progress = max(0.0, min(1.0, progress))
    filled = int(progress * width)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _resolve_cycle(args) -> str:
    if args.cycle:
        return args.cycle
    if args.latest:
        cycle, _ = get_latest_cycle(args.model)
        if not cycle:
            raise SystemExit("No available cycle found.")
        return cycle
    if args.date and args.hour is not None:
        return f"{args.date}{args.hour:02d}"
    raise SystemExit("Provide a cycle (YYYYMMDDHH), or use --latest, or pass --date/--hour.")


def _resolve_expected_fields(categories: List[str], fields: List[str]) -> List[str]:
    reg = FieldRegistry()
    all_fields = reg.get_all_fields()

    if fields:
        valid = [f for f in fields if f in all_fields]
        missing = sorted(set(fields) - set(valid))
        if missing:
            print(f"⚠️ Unknown fields skipped: {', '.join(missing)}")
        return valid

    if categories:
        names = []
        for cat in categories:
            names.extend(reg.get_fields_by_category(cat).keys())
        return sorted(set(names))

    return list(all_fields.keys())


def _count_maps(out_dir: Path) -> int:
    if not out_dir.exists():
        return 0
    return len(list(out_dir.glob("*/*_REFACTORED.png")))


def _status_row(model_cfg, grib_dir: Path, out_base: Path, fhr: int, cycle_hour: int,
                expected_count: int, show_sizes: bool) -> dict:
    prs_name = model_cfg.get_filename(cycle_hour, "pressure", fhr)
    sfc_name = model_cfg.get_filename(cycle_hour, "surface", fhr)
    prs_path = grib_dir / prs_name
    sfc_path = grib_dir / sfc_name

    prs_ok = prs_path.exists() and prs_path.stat().st_size > 0
    sfc_ok = sfc_path.exists() and sfc_path.stat().st_size > 0

    out_dir = out_base / f"F{fhr:02d}" / "conus" / f"F{fhr:02d}"
    png_count = _count_maps(out_dir)

    if prs_ok and sfc_ok and expected_count > 0 and png_count >= expected_count:
        state = "complete"
    elif prs_ok and sfc_ok and png_count > 0:
        state = "rendering"
    elif prs_ok or sfc_ok:
        state = "grib_partial"
    else:
        state = "waiting_grib"

    sizes = ""
    if show_sizes:
        prs_size = _human_size(prs_path.stat().st_size) if prs_ok else "0B"
        sfc_size = _human_size(sfc_path.stat().st_size) if sfc_ok else "0B"
        sizes = f"{prs_size}/{sfc_size}"

    return {
        "fhr": fhr,
        "prs_ok": prs_ok,
        "sfc_ok": sfc_ok,
        "png_count": png_count,
        "state": state,
        "sizes": sizes,
    }


def main():
    parser = argparse.ArgumentParser(description="Monitor HRRR processing progress")
    parser.add_argument("cycle", nargs="?", help="Cycle in YYYYMMDDHH format")
    parser.add_argument("--latest", action="store_true", help="Use latest available cycle")
    parser.add_argument("--date", help="Date in YYYYMMDD format")
    parser.add_argument("--hour", type=int, help="Cycle hour (0-23)")
    parser.add_argument("--model", default="hrrr", help="Model name (default: hrrr)")
    parser.add_argument("--hours", help="Forecast hour range (e.g. 0-6 or 0,1,2)")
    parser.add_argument("--categories", help="Categories to track (comma-separated)")
    parser.add_argument("--fields", help="Fields to track (comma-separated)")
    parser.add_argument("--interval", type=int, default=10, help="Refresh interval seconds")
    parser.add_argument("--once", action="store_true", help="Print once and exit")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear screen between updates")
    parser.add_argument("--show-sizes", action="store_true", help="Show GRIB file sizes")

    args = parser.parse_args()

    cycle = _resolve_cycle(args)
    date = cycle[:8]
    cycle_hour = int(cycle[8:10])

    hour_list = parse_hour_range(args.hours)
    if hour_list is None:
        max_fhr = get_expected_max_forecast_hour(cycle)
        hour_list = list(range(0, max_fhr + 1))

    categories = [c.strip() for c in args.categories.split(",")] if args.categories else []
    fields = [f.strip() for f in args.fields.split(",")] if args.fields else []
    expected_fields = _resolve_expected_fields(categories, fields)
    expected_count = len(expected_fields)

    model_cfg = get_model_registry().get_model(args.model.lower())
    if not model_cfg:
        raise SystemExit(f"Unknown model: {args.model}")

    out_base = Path("outputs") / args.model.lower() / date / f"{cycle_hour:02d}z"
    grib_dir = Path("grib_files") / args.model.lower() / date / f"{cycle_hour:02d}z"

    while True:
        if not args.no_clear:
            os.system("clear")

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        total_expected = expected_count * len(hour_list)
        total_done = 0

        print(f"Cycle: {date} {cycle_hour:02d}Z | Model: {args.model.upper()} | {now}")
        print(f"Hours: F{hour_list[0]:02d}-F{hour_list[-1]:02d} ({len(hour_list)})")
        print(f"Expected maps per hour: {expected_count}")
        print("-" * 80)
        print("FHR  GRIB(P/S)  MAPS      STATUS        " + ("SIZES" if args.show_sizes else ""))

        for fhr in hour_list:
            row = _status_row(model_cfg, grib_dir, out_base, fhr, cycle_hour,
                              expected_count, args.show_sizes)
            total_done += row["png_count"]
            grib_flag = ("P" if row["prs_ok"] else "-") + ("/" + ("S" if row["sfc_ok"] else "-"))
            maps_str = f"{row['png_count']:>4}/{expected_count:<4}" if expected_count else f"{row['png_count']:>4}/----"
            line = f"F{fhr:02d}  {grib_flag:<8} {maps_str:<9} {row['state']:<12}"
            if args.show_sizes:
                line += f" {row['sizes']}"
            print(line)

        if total_expected:
            progress = total_done / total_expected
        else:
            progress = 0.0
        print("-" * 80)
        print(f"Overall: {_bar(progress)} {total_done}/{total_expected} maps")

        if args.once:
            break

        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
