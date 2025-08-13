# Slim HRRRProcessor; delegates heavy pieces into smart_hrrr.derived

import time
from pathlib import Path
from typing import Dict, Any, Optional
import xarray as xr

from field_registry import FieldRegistry
from model_config import get_model_registry
from config.colormaps import create_all_colormaps
from core import downloader, grib_loader, plotting
from . import derived as derived_mod


class HRRRProcessor:
    """Weather data processor with extensible field configurations
    
    Supports multiple weather models including HRRR and RRFS
    """
    
    def __init__(self, config_dir: Path = None, model: str = 'hrrr'):
        """Initialize weather processor
        
        Args:
            config_dir: Directory containing parameter configuration files
            model: Weather model to use ('hrrr' or 'rrfs')
        """
        self.registry = FieldRegistry(config_dir)
        self.colormaps = create_all_colormaps()
        # Hardcoded CONUS region since regional processing is removed
        self.regions = {
            'conus': {
                'name': 'CONUS',
                'extent': [-130, -65, 20, 50],
                'barb_thinning': 60
            }
        }
        self.current_region = 'conus'  # Fixed region
        # NEW: simple in-memory cache for the current cycle/FHR
        self._data_cache: Dict[tuple[str, str, int], xr.DataArray] = {}
        
        # Model configuration
        self.model_registry = get_model_registry()
        self.model_name = model.lower()
        self.model_config = self.model_registry.get_model(self.model_name)
        
        if not self.model_config:
            raise ValueError(f"Unknown model: {model}. Available models: {self.model_registry.list_models()}")

    def set_region(self, region_name: str) -> bool:
        """Set the current region for plotting (only conus supported now)"""
        self.current_region = 'conus'
        return True

    def download_model_file(self, cycle, forecast_hour, output_dir, file_type='pressure'):
        """Download weather model file with appropriate source fallbacks"""
        return downloader.download_model_file(cycle, forecast_hour, output_dir, file_type, self.model_config)
    
    def download_hrrr_file(self, cycle, forecast_hour, output_dir, file_type='wrfprs'):
        """Legacy method for backward compatibility - redirects to download_model_file"""
        return downloader.download_hrrr_file(cycle, forecast_hour, output_dir, file_type, self.model_config)

    def load_field_data(self, grib_file, field_name, field_config):
        """Load specific field data - now uses robust multi-dataset approach when needed"""
        return grib_loader.load_field(grib_file, field_name, field_config, self.model_name)
    
    def load_uh_layer(self, path, top, bottom):
        """Return max-1h UH for a given AG layer (m AGL) from a HRRR wrfsfc file."""
        return grib_loader.load_uh_layer(path, top, bottom)

    # Delegate heavy methods to smart_hrrr.derived
    def load_derived_parameter(self, field_name, field_config, grib_file, wrfsfc_file=None):
        """Load and compute derived parameter from input fields"""
        return derived_mod.load_derived_parameter(self, field_name, field_config, grib_file, wrfsfc_file)

    def _load_composite_data(self, field_name, field_config, grib_file, wrfsfc_file=None):
        """Load data for composite plots that need multiple input fields"""
        return derived_mod.load_composite_data(self, field_name, field_config, grib_file, wrfsfc_file)

    def create_spc_plot(self, data, field_name, field_config, cycle, forecast_hour, output_dir: Path):
        """Create enhanced SPC-style plot with comprehensive metadata"""
        return plotting.create_plot(data, field_name, field_config, cycle, forecast_hour, output_dir,
                                   self.regions, self.current_region, self.colormaps, self.registry)