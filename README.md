# Weather Model Processing System

A high-performance, extensible system for downloading, processing, and visualizing weather model data from NOAA's HRRR (High-Resolution Rapid Refresh), RRFS (Rapid Refresh Forecast System), and GFS (Global Forecast System) models. Generates publication-quality meteorological maps with support for 98+ weather parameters.

## 🚀 Key Features

- **Multi-Model Support**: HRRR, RRFS, and GFS models
- **98+ Weather Parameters**: Including severe weather indices, instability parameters, smoke/fire products
- **Parallel Processing**: 8x faster map generation using multiprocessing
- **Smart Caching**: Avoids reprocessing completed products
- **Continuous Monitoring**: Automatically process new model runs as they become available
- **Extensible Architecture**: Easy to add new parameters, models, or visualization styles
- **Professional Visualizations**: SPC-style plots with customizable colormaps

## 📁 Project Structure

```
hrrr-dr-4/
├── processor_base.py          # Base processor class with core functionality
├── processor_batch.py         # Batch processing with parallel map generation
├── processor_cli.py           # Main command-line interface
├── monitor_continuous.py      # Continuous monitoring for new model runs
├── field_registry.py          # Dynamic field configuration system
├── field_templates.py         # Reusable parameter templates
├── model_config.py           # Model-specific configurations (URLs, patterns)
├── map_enhancer.py           # Modern map styling enhancements
├── config/
│   ├── colormaps.py          # Custom colormaps for weather parameters
├── core/
│   ├── downloader.py         # GRIB file download management
│   ├── grib_loader.py        # GRIB data extraction with cfgrib
│   ├── metadata.py           # Metadata generation for products
│   └── plotting.py           # Map generation with Cartopy
├── derived_params/           # 70+ derived parameter calculations
├── parameters/               # JSON configuration files by category
│   ├── severe.json          # Severe weather parameters
│   ├── instability.json     # CAPE, CIN, stability indices
│   ├── smoke.json           # Fire and smoke products
│   └── ...                  # Additional categories
├── tools/
│   ├── process_all_products.py    # Batch processing utilities
│   ├── process_single_hour.py     # Single forecast hour processing
│   └── create_gifs.py            # Animation generation
└── outputs/                      # Generated products (organized by date/model/hour)
```

## 🛠️ Installation

```bash
# Clone the repository
git clone <repository-url> hrrr-dr-4
cd hrrr-dr-4

# Create conda environment
conda create -n hrrr_maps python=3.11
conda activate hrrr_maps

# Install dependencies
conda install -c conda-forge cartopy cfgrib matplotlib xarray numpy pandas
pip install psutil requests

# Optional: Install MetPy for additional derived parameters
conda install -c conda-forge metpy
```

## 📊 Available Weather Parameters

### Categories:
- **Severe Weather** (27 params): STP, SCP, SHIP, EHI, bulk shear, effective layer parameters
- **Instability** (9 params): CAPE/CIN (surface-based, mixed-layer, most-unstable), LCL, LI
- **Surface** (10 params): Temperature, dewpoint, pressure, winds, relative humidity
- **Upper Air** (10 params): Heights, temperatures, winds at standard levels
- **Precipitation** (2 params): Instantaneous rate, accumulated total
- **Reflectivity** (3 params): Composite, 1km AGL, 4km AGL
- **Smoke/Fire** (6 params): Near-surface smoke, visibility, fire weather indices
- **Composites** (9 params): Multi-parameter visualizations with overlays
- **Heat Stress** (5 params): Wet bulb temperature, WBGT, heat indices
- **Updraft Helicity** (5 params): Various layer calculations for tornado potential

## 🎯 Command Examples

### Basic Processing

```bash
# Process latest available HRRR run (all products)
python processor_cli.py --latest

# Process specific date/hour
python processor_cli.py 20250715 12

# Process only specific categories
python processor_cli.py 20250715 12 --categories severe,instability

# Process specific parameters
python processor_cli.py 20250715 12 --fields sbcape,sbcin,stp,reflectivity_comp

# Process specific forecast hours (default is F00-F18)
python processor_cli.py 20250715 12 --hours 0-6

# Process extended forecast (for 00z, 06z, 12z, 18z runs)
python processor_cli.py 20250715 12 --hours 0-48
```


### Model Selection

```bash
# Process RRFS model (experimental)
python processor_cli.py --latest --model rrfs

# Process GFS model
python processor_cli.py --latest --model gfs
```

### Parallel Processing Control

```bash
# Use 4 worker processes (default: auto-detect)
python processor_cli.py --latest --workers 4

# Force reprocess all products (ignore existing)
python processor_cli.py 20250715 12 --force

# Enable debug logging
python processor_cli.py --latest --debug
```

### Continuous Monitoring

```bash
# Monitor and process new HRRR runs as they arrive
python monitor_continuous.py

# The monitor will:
# - Check for new data every 10 seconds
# - Process only missing forecast hours
# - Show progress for each cycle
# - Continue from previous cycle if new data isn't ready
```

### Advanced Features

```bash
# Generate all products for a full model run (parallel processing)
python processor_cli.py 20250715 12 --workers 8

# Create custom filter for specific use case
# Edit custom_filters.json, then:
python processor_cli.py --latest --filter "Severe Weather Core"

# Process with specific output directory
python processor_cli.py --latest --output-dir /path/to/output
```

## 🔧 Configuration

### Adding New Parameters

1. **For base GRIB fields**, add to appropriate JSON in `parameters/`:
```json
{
  "my_new_field": {
    "var": "GRIB_VARIABLE_NAME",
    "level": "2 m above ground",
    "cmap": "viridis",
    "title": "My New Field",
    "units": "units"
  }
}
```

2. **For derived parameters**, create a file in `derived_params/`:
```python
# derived_params/my_calculation.py
from .common import *

def my_calculation(input1: np.ndarray, input2: np.ndarray) -> np.ndarray:
    """Calculate my custom parameter"""
    return input1 + input2 * 2.5
```

Then add to `parameters/derived.json`:
```json
{
  "my_derived_field": {
    "derived": true,
    "function": "my_calculation",
    "inputs": ["base_field1", "base_field2"],
    "title": "My Derived Field",
    "units": "custom units",
    "cmap": "RdBu_r"
  }
}
```


### Custom Colormaps

Add new colormaps in `config/colormaps.py` for specialized visualizations.

## 📈 Performance Optimization

- **Parallel Processing**: Automatically uses N-1 CPU cores (max 8)
- **Smart Caching**: Skips already-processed products
- **Batch Loading**: Loads all GRIB fields once, then generates all products
- **Memory Efficient**: Processes one forecast hour at a time

## 🗄️ Output Structure

```
outputs/
└── hrrr/
    └── 20250715/           # Date
        └── 12z/            # Model run hour
            └── F00/        # Forecast hour
                └── conus/  # Fixed output region
                    └── F00/
                        ├── severe/       # Category folders
                        ├── instability/
                        ├── surface/
                        └── metadata/     # JSON metadata for each product
```

## 🔍 Troubleshooting

```bash
# Check if data is available for a specific cycle
python processor_cli.py 20250715 12 --check-availability

# View all available parameters
python processor_cli.py --list-fields

# View parameters by category
python processor_cli.py --list-fields --category severe

# Test single parameter processing
python processor_cli.py --latest --fields sbcape --debug
```

## 📝 Notes

- HRRR data is typically available 45-75 minutes after the model run time
- NOMADS (primary source) keeps ~2 days of data
- AWS S3 (backup source) has historical data
- GFS and RRFS have different schedules and forecast lengths
- Some derived parameters require MetPy installation

## 🚦 Environment Variables

```bash
# Disable parallel processing
export HRRR_USE_PARALLEL=false

# Set custom number of workers
export HRRR_MAX_WORKERS=4

# Change default model
export HRRR_DEFAULT_MODEL=rrfs
```

## 📜 License

[Your license here]

## 🤝 Contributing

Contributions welcome! Please ensure new parameters include:
- Proper metadata in JSON configuration
- Documentation of calculations
- Appropriate colormaps and units
- Test coverage for derived parameters