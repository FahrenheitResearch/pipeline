#!/usr/bin/env python3
"""
Single Hour Processor (legacy wrapper)

This script now routes through the unified pipeline. For new usage, prefer
processor_cli.py.
"""

import argparse
import json
from pathlib import Path

from smart_hrrr.orchestrator import process_model_run
from smart_hrrr.utils import setup_logging

FILTER_FILE = Path(__file__).parent.parent / "custom_filters.json"


def main():
    parser = argparse.ArgumentParser(description="Process single forecast hour")
    parser.add_argument("cycle", help="Cycle in YYYYMMDDHH format")
    parser.add_argument("forecast_hour", type=int, help="Forecast hour to process")
    parser.add_argument("--categories", help="Categories to process (comma-separated)")
    parser.add_argument("--fields", help="Specific fields to process (comma-separated)")
    parser.add_argument("--filter", help="Saved filter name")
    parser.add_argument("--output-dir", help="Deprecated: output directory override (ignored)")
    parser.add_argument("--grib-dir", help="Deprecated: GRIB directory override (ignored)")
    parser.add_argument("--use-local-grib", action="store_true",
                        help="Deprecated: local GRIB flag (ignored)")
    parser.add_argument("--model", default="hrrr", help="Weather model to use (hrrr or rrfs)")
    parser.add_argument("--map-workers", type=int, help="Map plot workers (default: auto)")
    parser.add_argument("--debug", action="store_true", help="Debug logging")

    args = parser.parse_args()

    if args.output_dir:
        print("⚠️  --output-dir is deprecated; pipeline uses standard outputs/ paths")
    if args.grib_dir or args.use_local_grib:
        print("⚠️  --grib-dir/--use-local-grib are deprecated; pipeline manages GRIB staging")

    include_categories = [cat.strip() for cat in args.categories.split(",")] if args.categories else None
    fields = [f.strip() for f in args.fields.split(",")] if args.fields else None

    if args.filter:
        if FILTER_FILE.exists():
            with open(FILTER_FILE, "r") as f:
                filters = json.load(f)
            if args.filter in filters:
                filt = filters[args.filter]
                if not fields:
                    fields = filt.get("fields")
                if not include_categories:
                    include_categories = filt.get("categories")
            else:
                print(f"Filter not found: {args.filter}")
        else:
            print("No filter file available")

    setup_logging(debug=args.debug)

    cycle = args.cycle
    date = cycle[:8]
    hour = int(cycle[8:10])
    map_workers = args.map_workers if args.map_workers and args.map_workers > 0 else None

    print(f"Processing {cycle} F{args.forecast_hour:02d}")
    print(f"Categories: {include_categories}")
    print(f"Fields: {fields}")

    results = process_model_run(
        model=args.model,
        date=date,
        hour=hour,
        forecast_hours=[args.forecast_hour],
        categories=include_categories,
        fields=fields,
        max_workers=map_workers,
        map_workers=map_workers,
    )

    print(results)


if __name__ == "__main__":
    raise SystemExit(main())
