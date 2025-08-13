#!/usr/bin/env python3

from pathlib import Path
from typing import List, Optional

from smart_hrrr.parallel_engine import process_hrrr_parallel as _impl


def process_hrrr_parallel(cycle: str, forecast_hour: int = 0, output_dir: Optional[Path] = None,
                         categories: Optional[List[str]] = None, model: str = 'hrrr'):
    """Process HRRR data in parallel - wrapper for backward compatibility"""
    return _impl(cycle=cycle, forecast_hour=forecast_hour, output_dir=output_dir, categories=categories, model=model)


if __name__ == "__main__":
    import sys
    cyc = sys.argv[1] if len(sys.argv) > 1 else '20250710_19Z'
    fhr = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    cats = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    process_hrrr_parallel(cyc, fhr, categories=cats)