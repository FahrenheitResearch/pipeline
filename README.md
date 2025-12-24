# HRRR Weather Model Processing System

High-performance pipeline for downloading, processing, and visualizing HRRR, RRFS, and GFS weather model data. Pure NumPy calculations with SPC-compliant severe weather parameters.

## Quick Start

```bash
# Setup
conda create -n hrrr_maps python=3.11
conda activate hrrr_maps
conda install -c conda-forge cartopy cfgrib matplotlib xarray numpy pandas
pip install psutil requests rich typer questionary

# Process latest severe weather
python processor_cli.py --latest --categories severe --workers 8

# Interactive mode
python hrrr_cli.py interactive
```

## Features

- **108 weather parameters** across severe, instability, smoke, surface, reflectivity, and more
- **SPC-compliant** tornado/supercell parameters (STP, SCP, SHIP, EHI)
- **Parallel processing** with configurable workers
- **Multi-model support**: HRRR, RRFS, GFS
- **Diurnal analysis** with rolling 24h windows
- **Animated GIFs** from forecast sequences

## Usage

### Basic Processing

```bash
# Latest model run, specific categories
python processor_cli.py --latest --categories severe,instability --hours 0-12

# Specific date/cycle
python processor_cli.py 20251224 12 --categories smoke --workers 8

# Single fields
python processor_cli.py --latest --fields stp_fixed,sbcape,srh_01km
```

### Diurnal Temperature Analysis

```bash
# Rolling 24h temperature range across 48h forecast
python tools/process_diurnal.py --latest --synoptic --end-fhr 48 --rolling --workers 12 --gif
```

### Animations

```bash
cd tools
python create_gifs.py 20251224 12z --categories severe --max-hours 24
```

### Continuous Monitoring

```bash
python monitor_continuous.py &
```

## Project Structure

```
├── processor_cli.py          # Main CLI
├── hrrr_cli.py               # Interactive CLI (Rich/Typer)
├── smart_hrrr/               # Core processing modules
├── derived_params/           # 80+ derived parameter calculations
├── parameters/               # JSON configs by category
├── config/colormaps.py       # Custom colormaps
├── core/                     # GRIB loading, plotting
├── tools/                    # GIF creation, diurnal processing
└── outputs/                  # Generated maps
```

## Parameters

### Severe Weather (SPC-Aligned)
| Parameter | Description |
|-----------|-------------|
| `stp_fixed` | Significant Tornado Parameter (fixed layer) |
| `stp_effective` | STP with effective inflow layer |
| `scp` | Supercell Composite Parameter |
| `ship` | Significant Hail Parameter |
| `ehi_spc` | Energy-Helicity Index |

### Other Categories
- **Instability**: CAPE/CIN variants, lifted index, LCL height
- **Surface**: Temperature, dewpoint, winds, pressure
- **Smoke/Fire**: Near-surface smoke, visibility, ventilation rate
- **Reflectivity**: Composite, 1km/4km AGL
- **Heat Stress**: Wet bulb, WBGT variants
- **Diurnal**: Temperature range, heating/cooling rates

Run `python processor_cli.py --list-fields` for the full list.

## Adding Parameters

### Base GRIB Field
Add to `parameters/<category>.json`:
```json
{
  "my_field": {
    "var": "TMP",
    "level": "2 m above ground",
    "title": "2m Temperature",
    "units": "K",
    "cmap": "RdYlBu_r"
  }
}
```

### Derived Parameter
Create `derived_params/my_calc.py`:
```python
import numpy as np

def my_calculation(temp, dewpoint):
    return temp - dewpoint
```

Add to `parameters/derived.json`:
```json
{
  "my_derived": {
    "derived": true,
    "function": "my_calculation",
    "inputs": ["t2m", "d2m"],
    "title": "Temp-Dewpoint Spread",
    "units": "K"
  }
}
```

## Output Structure

```
outputs/hrrr/20251224/12z/
├── F00/conus/F00/severe/      # Maps by category
├── F01/conus/F01/instability/
├── diurnal/                    # Diurnal products
└── animations/                 # GIFs
```

## Environment Variables

```bash
HRRR_USE_PARALLEL=false    # Disable parallel processing
HRRR_MAX_WORKERS=4         # Limit workers
HRRR_DEBUG=1               # Verbose logging
```

## Data Sources

- **NOMADS** (primary): ~2 days retention
- **AWS S3** (backup): Historical archive
- **Utah Pando** (fallback): Research archive

HRRR data typically available 45-75 min after model run time. Synoptic cycles (00/06/12/18Z) have 48h forecasts; others have 18h.

## Docs

- [Diurnal Temperature Analysis](docs/DIURNAL_TEMPERATURE.md)
- [Setup Guide](SETUP.md)
