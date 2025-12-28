# HRRR Processing Architecture

## Overview

The processing pipeline is unified and runs in a single direction:

```
processor_cli.py → smart_hrrr/orchestrator.py → smart_hrrr/pipeline.py → smart_hrrr/parallel_engine.py
```

Each forecast hour (Fxx) follows: download → stage GRIBs → load base fields → compute derived fields → plot maps.

## Core Modules

- `processor_cli.py`: CLI entrypoint; parses args and invokes the orchestrator.
- `smart_hrrr/orchestrator.py`: Thin routing layer for runs and monitoring.
- `smart_hrrr/pipeline.py`: Owns GRIB download/staging, prefetch, and per-hour execution.
- `smart_hrrr/parallel_engine.py`: Loads required fields and renders maps in parallel.
- `field_registry.py`: Builds the field registry from JSON configs (skips comments, disabled, and diurnal-only fields by default).
- `core/`: GRIB download (`downloader.py`), GRIB loading (`grib_loader.py`, includes dataset caching), plotting (`plotting.py`).
- `derived_params/`: Derived calculations; `derived_params/__init__.py` is the dispatch table.

## Entry Points

- Standard processing: `processor_cli.py`
- Interactive mode: `hrrr_cli.py`
- Continuous monitoring: `monitor_continuous.py`
- Diurnal products: `tools/process_diurnal.py` (separate path, multi-hour inputs)

## Adding or Modifying Products

1. Base GRIB fields: edit `parameters/<category>.json`.
2. Derived fields:
   - Add a function in `derived_params/`.
   - Register it in `derived_params/__init__.py`.
   - Add a config entry in `parameters/derived.json`.

If a field is experimental or incomplete, set `"disabled": true` in its config to keep it out of the registry.

## Output Layout

```
outputs/<model>/<YYYYMMDD>/<HH>z/
└── FXX/conus/FXX/<category>/*.png
```
