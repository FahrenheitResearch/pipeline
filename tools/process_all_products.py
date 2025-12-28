#!/usr/bin/env python3
"""
Process All HRRR Products (legacy wrapper)

This script now routes through the unified pipeline. For new usage, prefer
processor_cli.py.
"""

import sys
from pathlib import Path
from datetime import datetime

from field_registry import FieldRegistry
from smart_hrrr.availability import get_latest_cycle
from smart_hrrr.io import create_output_structure
from smart_hrrr.orchestrator import process_model_run


def process_all_products(cycle=None, forecast_hours=[1], output_dir=None,
                        by_category=False, include_categories=None,
                        exclude_categories=None, grib_dir=None, use_local_grib=True,
                        model='hrrr'):
    if output_dir:
        print("⚠️  output_dir is deprecated; pipeline uses standard outputs/ paths")
    if grib_dir or use_local_grib:
        print("⚠️  grib_dir/use_local_grib are deprecated; pipeline manages GRIB staging")
    if by_category:
        print("ℹ️  by_category is now implied by the output structure")

    if cycle is None:
        cycle, dt = get_latest_cycle(model)
        if not cycle:
            raise RuntimeError("No available cycle found")
        date = dt.strftime("%Y%m%d")
        hour = dt.hour
    else:
        date = cycle[:8]
        hour = int(cycle[8:10])

    categories = None
    if include_categories or exclude_categories:
        registry = FieldRegistry()
        categories = registry.get_available_categories()
        if include_categories:
            categories = [c for c in categories if c in include_categories]
        if exclude_categories:
            categories = [c for c in categories if c not in exclude_categories]
        if not categories:
            print("⚠️ No categories matched filters")
            categories = []

    print("🚀 PROCESSING ALL PRODUCTS (Unified Pipeline)")
    print("=" * 60)
    print(f"Categories: {categories if categories else 'all'}")
    print(f"Forecast hours: {forecast_hours}")
    print(f"Model: {model}")
    print("=" * 60)

    results = process_model_run(
        model=model,
        date=date,
        hour=hour,
        forecast_hours=forecast_hours,
        categories=categories if categories else None,
    )

    output_dirs = create_output_structure(model, date, hour)
    create_product_index(output_dirs["run"], categories or [], forecast_hours)

    return results


def create_product_index(output_dir, categories, forecast_hours):
    """Create an index of all generated products"""
    index_file = Path(output_dir) / "product_index.txt"

    with open(index_file, "w") as f:
        f.write("HRRR Product Index\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        if categories:
            f.write(f"Categories: {', '.join(categories)}\n")
        f.write(f"Forecast Hours: {', '.join([f'F{h:02d}' for h in forecast_hours])}\n\n")

        for fhr_dir in sorted(Path(output_dir).glob("F*")):
            if fhr_dir.is_dir():
                f.write(f"\n{fhr_dir.name}:\n")
                category_dirs = [d for d in fhr_dir.iterdir() if d.is_dir()]
                if category_dirs:
                    for cat_dir in sorted(category_dirs):
                        png_files = list(cat_dir.glob("*.png"))
                        f.write(f"  {cat_dir.name}: {len(png_files)} maps\n")
                        for png_file in sorted(png_files):
                            f.write(f"    {png_file.name}\n")
                else:
                    png_files = list(fhr_dir.glob("*.png"))
                    f.write(f"  {len(png_files)} maps\n")
                    for png_file in sorted(png_files):
                        f.write(f"    {png_file.name}\n")

    print(f"📋 Product index created: {index_file}")


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "all":
            process_all_products(by_category=True)
        elif command == "instability":
            process_all_products(include_categories=["instability"], by_category=True)
        elif command == "severe":
            process_all_products(include_categories=["severe", "reflectivity"], by_category=True)
        elif command == "surface":
            process_all_products(include_categories=["surface", "precipitation"], by_category=True)
        elif command == "smoke":
            process_all_products(include_categories=["smoke"], by_category=True)
        elif command == "forecast":
            if len(sys.argv) > 2:
                try:
                    max_fhr = int(sys.argv[2])
                    forecast_hours = list(range(0, max_fhr + 1, 3))
                    process_all_products(forecast_hours=forecast_hours, by_category=True)
                except ValueError:
                    print("Invalid forecast hour. Use: python process_all_products.py forecast 12")
            else:
                print("Usage: python process_all_products.py forecast <max_hour>")
        else:
            print("Unknown command. Use: all|instability|severe|surface|smoke|forecast")
    else:
        process_all_products(by_category=True)


if __name__ == "__main__":
    raise SystemExit(main())
