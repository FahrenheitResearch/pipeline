"""GRIB data loading module with multiple strategies"""

import os
import warnings
import tempfile
import subprocess
import numpy as np
import xarray as xr
import cfgrib
import signal


def load_field(grib_file, field_name, field_config, model_name):
    """Load specific field data - uses robust multi-dataset approach when needed"""
    # Check if this field requires robust loading
    if field_config.get('requires_multi_dataset'):
        return load_field_data_robust(grib_file, field_name, field_config, model_name)
    
    # Use original method for regular fields (keeps smoke working!)
    return load_field_data_original(grib_file, field_name, field_config)


def load_field_data_robust(grib_file, field_name, field_config, model_name):
    """Robust field loading with multiple strategies"""
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Loading operation timed out")
    
    # Strategy 1: wgrib2 extraction FIRST for multi-dataset fields (most reliable)
    if field_config.get('requires_multi_dataset') and field_config.get('wgrib2_pattern'):
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout for wgrib2
            
            result = load_field_with_wgrib2(grib_file, field_config)
            signal.alarm(0)  # Cancel timeout
            
            if result is not None:
                print(f"✅ Loaded {field_name} with wgrib2 approach")
                return _apply_data_transformations(result, field_config)
        except (Exception, TimeoutError) as e:
            signal.alarm(0)  # Cancel timeout
            print(f"⚠️ wgrib2 approach failed for {field_name}: {e}")
    
    # Strategy 2: Try original single-dataset approach for non-multi-dataset fields
    if not field_config.get('requires_multi_dataset'):
        try:
            # Set timeout for single-dataset approach
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            result = load_field_data_original(grib_file, field_name, field_config)
            signal.alarm(0)  # Cancel timeout
            
            if result is not None:
                print(f"✅ Loaded {field_name} with single-dataset approach")
                return _apply_data_transformations(result, field_config)
        except (Exception, TimeoutError) as e:
            signal.alarm(0)  # Cancel timeout
            print(f"⚠️ Single-dataset approach failed for {field_name}: {e}")
    
    # Strategy 3: Multi-dataset search (fallback for problematic cases)
    if field_config.get('requires_multi_dataset'):
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout for multi-dataset
            
            result = load_field_data_multids(grib_file, field_name, field_config, model_name)
            signal.alarm(0)  # Cancel timeout
            
            if result is not None:
                print(f"✅ Loaded {field_name} with multi-dataset approach")
                return _apply_data_transformations(result, field_config)
        except (Exception, TimeoutError) as e:
            signal.alarm(0)  # Cancel timeout
            print(f"⚠️ Multi-dataset approach failed for {field_name}: {e}")
    
    print(f"❌ All strategies failed for {field_name}")
    return None


def load_field_data_original(grib_file, field_name, field_config):
    """Original single-dataset loading method - kept for reliable fields like smoke"""
    try:
        # Open dataset with specific access method
        access_keys = field_config['access'].copy()
        
        # For paramId-based fields, try to be more specific
        if 'paramId' in access_keys:
            # Add surface level specification for common surface fields
            surface_params = {167: 't2m', 168: 'd2m', 165: 'u10', 166: 'v10', 260242: 'r2'}
            if access_keys['paramId'] in surface_params:
                access_keys['typeOfLevel'] = 'heightAboveGround'
                access_keys['level'] = 2 if access_keys['paramId'] in [167, 168, 260242] else 10
        
        # Special handling for COLMD (column-integrated smoke)
        if field_config['var'] == 'COLMD_entireatmosphere_consideredasasinglelayer_':
            # Extract COLMD using wgrib2 and read as NetCDF
            with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp_file:
                temp_nc = tmp_file.name
            
            try:
                # Find COLMD record
                result = subprocess.run(['wgrib2', str(grib_file), '-s'], capture_output=True, text=True)
                colmd_record = None
                for line in result.stdout.strip().split('\n'):
                    if 'COLMD' in line:
                        colmd_record = line.split(':')[0]
                        break
                
                if colmd_record:
                    # Extract to NetCDF
                    subprocess.run(['wgrib2', str(grib_file), '-d', colmd_record, '-netcdf', temp_nc], 
                                 capture_output=True, text=True, check=True)
                    
                    # Load the NetCDF file
                    ds = xr.open_dataset(temp_nc)
                    print(f"🔍 COLMD variables available: {list(ds.data_vars.keys())}")
                else:
                    print("❌ COLMD record not found")
                    return None
                    
            except Exception as e:
                print(f"❌ Failed to extract COLMD: {e}")
                return None
            finally:
                # Clean up temp file
                if os.path.exists(temp_nc):
                    os.unlink(temp_nc)
        else:
            ds = cfgrib.open_dataset(grib_file, filter_by_keys=access_keys)
        
        if field_config['var'] not in ds.data_vars:
            print(f"❌ Variable {field_config['var']} not found")
            return None
        
        data = ds[field_config['var']]
        
        # Handle multi-dimensional data
        if field_config.get('process') == 'select_layer':
            # For SRH, select appropriate layer
            if 'heightAboveGroundLayer' in data.dims:
                if len(data.heightAboveGroundLayer) > 1:
                    if '01km' in field_name:
                        data = data.isel(heightAboveGroundLayer=0)  # First layer
                    else:
                        data = data.isel(heightAboveGroundLayer=-1)  # Last layer
                else:
                    data = data.isel(heightAboveGroundLayer=0)
        
        # Handle height-based reflectivity (select specific level)
        if 'heightAboveGround' in data.dims and len(data.dims) > 2:
            target_level = field_config['access'].get('level')
            if target_level:
                # Find closest level
                levels = data.heightAboveGround.values
                closest_idx = np.argmin(np.abs(levels - target_level))
                data = data.isel(heightAboveGround=closest_idx)
                print(f"Selected height level: {levels[closest_idx]} m (target: {target_level} m)")
            else:
                # Default to first level
                data = data.isel(heightAboveGround=0)
                print(f"Selected first available height level: {data.heightAboveGround.values} m")
        
        # Ensure data is 2D for plotting
        while len(data.dims) > 2:
            # Remove extra dimensions by selecting first index
            extra_dim = [dim for dim in data.dims if dim not in ['latitude', 'longitude', 'y', 'x']][0]
            data = data.isel({extra_dim: 0})
            print(f"Reduced dimension {extra_dim} to 2D")
        
        # Apply transformations
        if field_config.get('transform') == 'abs':
            data = abs(data)
        elif field_config.get('transform') == 'celsius':
            data = data - 273.15  # Kelvin to Celsius
        elif field_config.get('transform') == 'mb':
            data = data / 100  # Pa to mb
        elif field_config.get('transform') == 'smoke_concentration':
            # Convert from kg/m³ to μg/m³ (HRRR changed units in Dec 2021)
            data = data * 1e9  # kg/m³ to μg/m³
        elif field_config.get('transform') == 'smoke_column':
            # Convert column mass to mg/m²
            data = data * 1e6  # kg/m² to mg/m²
        elif field_config.get('transform') == 'dust_concentration':
            # Convert dust concentration from kg/m³ to μg/m³
            data = data * 1e9  # kg/m³ to μg/m³
        elif field_config.get('transform') == 'prate_units':
            # Convert precipitation rate from kg/m²/s to mm/hr
            data = data * 3600  # kg/m²/s to mm/hr
        
        return data
        
    except Exception as e:
        print(f"❌ Failed to load {field_name}: {e}")
        return None


def load_field_data_multids(grib_file, field_name, field_config, model_name):
    """Load field data with multi-dataset support - optimized version"""
    var_name = field_config['var']
    
    try:
        # Load all datasets with error suppression to avoid index warnings spam
        # Disable indexing for GFS to prevent conflicts
        backend_kwargs = {}
        if model_name == 'gfs' or os.environ.get('CFGRIB_USE_INDEX_CACHE') == '0':
            backend_kwargs['indexpath'] = ''
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            datasets = cfgrib.open_datasets(grib_file, backend_kwargs=backend_kwargs)
        
        print(f"🔍 Searching {var_name} across {len(datasets)} datasets...")
        
        # Search across all datasets for our variable
        for i, ds in enumerate(datasets):
            try:
                if var_name in ds.data_vars:
                    print(f"✅ Found {var_name} in dataset {i}")
                    data = ds[var_name]
                    
                    # Apply layer selection if needed
                    if 'level_selection' in field_config:
                        data = _select_layer(data, field_config['level_selection'])
                    
                    # Close other datasets to free memory
                    for j, other_ds in enumerate(datasets):
                        if j != i:
                            try:
                                other_ds.close()
                            except:
                                pass
                    
                    return data
                    
                # Handle 'unknown' variables by checking GRIB metadata
                if 'unknown' in ds.data_vars:
                    unknown_var = ds['unknown']
                    if hasattr(unknown_var, 'attrs'):
                        grib_name = unknown_var.attrs.get('GRIB_shortName', '')
                        grib_param_name = unknown_var.attrs.get('GRIB_parameterName', '')
                        
                        # Check both shortName and parameterName for matches
                        var_lower = var_name.lower()
                        grib_shortname_match = field_config.get('grib_shortname_match', '').lower()
                        
                        if (grib_name.lower() == var_lower or 
                            grib_param_name.lower().replace(' ', '_') == var_lower or
                            (grib_shortname_match and grib_name.lower() == grib_shortname_match)):
                            print(f"✅ Found {var_name} as 'unknown' in dataset {i} (GRIB: {grib_name})")
                            data = unknown_var
                            
                            # Apply layer selection if needed
                            if 'level_selection' in field_config:
                                data = _select_layer(data, field_config['level_selection'])
                            
                            # Close other datasets to free memory
                            for j, other_ds in enumerate(datasets):
                                if j != i:
                                    try:
                                        other_ds.close()
                                    except:
                                        pass
                            
                            return data
            except Exception as ds_error:
                # Skip problematic datasets
                continue
        
        # Close all datasets
        for ds in datasets:
            try:
                ds.close()
            except:
                pass
        
        print(f"❌ Variable {var_name} not found in any dataset")
        return None
        
    except Exception as e:
        print(f"❌ Multi-dataset loading error: {e}")
        return None


def load_field_with_wgrib2(grib_file, field_config):
    """Use wgrib2 to extract specific records then load with cfgrib"""
    var_name = field_config['var']
    pattern = field_config.get('wgrib2_pattern', var_name)
    
    print(f"🔧 Using wgrib2 extraction for {var_name} with pattern: {pattern}")
    
    with tempfile.NamedTemporaryFile(suffix='.grib2', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Extract specific record
        cmd = ['wgrib2', str(grib_file), '-match', pattern, '-grib', tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            print(f"✅ wgrib2 extracted record: {result.stdout.strip()}")
            
            # Load the isolated GRIB record and immediately read data into memory
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ds = cfgrib.open_dataset(tmp_path, backend_kwargs={'indexpath': ''})
            
            print(f"🔍 Available variables in extracted file: {list(ds.data_vars.keys())}")
            
            # Try different variable name mappings
            possible_names = [var_name, var_name.lower(), 'unknown']
            
            for name in possible_names:
                if name in ds.data_vars:
                    print(f"✅ Successfully extracted {var_name} as '{name}' with wgrib2")
                    # Load data into memory immediately
                    data = ds[name].load()
                    ds.close()
                    return data
            
            # If no direct match, return the first variable
            if len(ds.data_vars) > 0:
                first_var = list(ds.data_vars.keys())[0]
                print(f"✅ Using first available variable '{first_var}' for {var_name}")
                # Load data into memory immediately
                data = ds[first_var].load()
                ds.close()
                return data
        else:
            print(f"❌ wgrib2 extraction failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ wgrib2 extraction error: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            
    return None


def load_uh_layer(path, top, bottom):
    """
    Return max-1h UH for a given AG layer (m AGL) from a HRRR wrfsfc file.
    `top` > `bottom`, e.g. top=3000, bottom=0 for 0–3 km.
    
    Args:
        path: Path to HRRR wrfsfc file
        top: Top of layer (m AGL)
        bottom: Bottom of layer (m AGL)
        
    Returns:
        xarray.DataArray of max updraft helicity
    """
    try:
        # Try loading with paramId first (more specific)
        param_ids = {
            (3000, 0): 237137,    # 0-3km MXUPHL 
            (5000, 2000): 237138, # 2-5km MXUPHL
            (2000, 0): 237139     # 0-2km MXUPHL
        }
        
        layer_key = (top, bottom)
        if layer_key in param_ids:
            try:
                ds = xr.open_dataset(
                    path,
                    engine="cfgrib",
                    indexpath="",
                    filter_by_keys={
                        "paramId": param_ids[layer_key]
                    }
                )
                # Get the variable (should be single variable with paramId)
                var_name = list(ds.data_vars)[0]
                uh_data = ds[var_name]
                
                # Check if we loaded the wrong variable (max_vo instead of MXUPHL)
                if var_name == 'max_vo':
                    print(f"⚠️ paramId loaded wrong variable '{var_name}' instead of MXUPHL, falling back to wgrib2...")
                    raise Exception("Wrong variable loaded from paramId, forcing wgrib2 fallback")
                
                # Check if data is all zeros BEFORE dimension processing (indicating wrong field loaded)
                data_max = float(uh_data.max().values)
                if data_max == 0.0:
                    print(f"⚠️ paramId loaded all-zero data (var: {var_name}), falling back to wgrib2...")
                    raise Exception("All-zero data from paramId, forcing wgrib2 fallback")
                
                # Ensure 2D data for plotting (squeeze out extra dims)
                if len(uh_data.dims) > 2:
                    # Keep only spatial dimensions (y/x or latitude/longitude)
                    dims_to_keep = ['latitude', 'longitude', 'y', 'x']
                    for dim in uh_data.dims:
                        if dim not in dims_to_keep and uh_data.sizes[dim] == 1:
                            uh_data = uh_data.squeeze(dim)
                        elif dim not in dims_to_keep:
                            # For non-spatial dimensions with size > 1, take the first slice
                            uh_data = uh_data.isel({dim: 0})
                
                print(f"✅ Loaded UH {bottom}-{top}m layer via paramId from {path}")
                print(f"   Data shape: {uh_data.shape}, dims: {uh_data.dims}")
                print(f"   Data range: {uh_data.min().values:.1f} to {uh_data.max().values:.1f}")
                return uh_data
            except Exception as e:
                print(f"⚠️ paramId approach failed: {e}")
        
        # Fallback: Try using wgrib2 pattern
        wgrib2_patterns = {
            (3000, 0): "MXUPHL:3000-0 m above ground",
            (5000, 2000): "MXUPHL:5000-2000 m above ground", 
            (2000, 0): "MXUPHL:2000-0 m above ground"
        }
        
        if layer_key in wgrib2_patterns:
            try:
                # Extract specific MXUPHL layer using wgrib2
                with tempfile.NamedTemporaryFile(suffix='.grib2', delete=False) as tmp:
                    cmd = [
                        'wgrib2', str(path), 
                        '-match', wgrib2_patterns[layer_key],
                        '-grib', tmp.name
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        # Load the extracted data
                        ds = xr.open_dataset(tmp.name, engine="cfgrib")
                        var_name = list(ds.data_vars)[0]
                        uh_data = ds[var_name]
                        
                        # Ensure 2D data for plotting (squeeze out extra dims)
                        if len(uh_data.dims) > 2:
                            # Keep only spatial dimensions (y/x or latitude/longitude)
                            dims_to_keep = ['latitude', 'longitude', 'y', 'x']
                            for dim in uh_data.dims:
                                if dim not in dims_to_keep and uh_data.sizes[dim] == 1:
                                    uh_data = uh_data.squeeze(dim)
                                elif dim not in dims_to_keep:
                                    # For non-spatial dimensions with size > 1, take the first slice
                                    uh_data = uh_data.isel({dim: 0})
                        
                        print(f"✅ Loaded UH {bottom}-{top}m layer via wgrib2 from {path}")
                        print(f"   Data shape: {uh_data.shape}, dims: {uh_data.dims}")
                        print(f"   Data range: {uh_data.min().values:.1f} to {uh_data.max().values:.1f}")
                        
                        # Clean up temp file
                        os.unlink(tmp.name)
                        return uh_data
                    else:
                        os.unlink(tmp.name)
                        print(f"⚠️ wgrib2 extraction failed: {result.stderr}")
                        
            except Exception as e:
                print(f"⚠️ wgrib2 approach failed: {e}")
        
        # Final fallback - return None
        print(f"❌ All approaches failed for UH layer {bottom}-{top}m")
        return None
        
    except Exception as e:
        print(f"❌ Failed to load UH layer {bottom}-{top}m: {e}")
        return None


def _apply_data_transformations(data, field_config):
    """Apply transformations and ensure data is ready for plotting"""
    # Handle multi-dimensional data
    if field_config.get('process') == 'select_layer':
        # For SRH, select appropriate layer
        if 'heightAboveGroundLayer' in data.dims:
            if len(data.heightAboveGroundLayer) > 1:
                if '01km' in field_config.get('var', ''):
                    data = data.isel(heightAboveGroundLayer=0)  # First layer
                else:
                    data = data.isel(heightAboveGroundLayer=-1)  # Last layer
            else:
                data = data.isel(heightAboveGroundLayer=0)
    
    # Handle height-based reflectivity (select specific level)
    if 'heightAboveGround' in data.dims and len(data.dims) > 2:
        target_level = field_config.get('access', {}).get('level')
        if target_level:
            # Find closest level
            levels = data.heightAboveGround.values
            closest_idx = np.argmin(np.abs(levels - target_level))
            data = data.isel(heightAboveGround=closest_idx)
            print(f"Selected height level: {levels[closest_idx]} m (target: {target_level} m)")
        else:
            # Default to first level
            data = data.isel(heightAboveGround=0)
            print(f"Selected first available height level: {data.heightAboveGround.values} m")
    
    # Ensure data is 2D for plotting
    while len(data.dims) > 2:
        # Remove extra dimensions by selecting first index
        extra_dim = [dim for dim in data.dims if dim not in ['latitude', 'longitude', 'y', 'x']][0]
        data = data.isel({extra_dim: 0})
        print(f"Reduced dimension {extra_dim} to 2D")
    
    # Apply transformations
    if field_config.get('transform') == 'abs':
        data = abs(data)
    elif field_config.get('transform') == 'celsius':
        data = data - 273.15  # Kelvin to Celsius
    elif field_config.get('transform') == 'mb':
        data = data / 100  # Pa to mb
    elif field_config.get('transform') == 'smoke_concentration':
        # Convert from kg/m³ to μg/m³ (HRRR changed units in Dec 2021)
        data = data * 1e9  # kg/m³ to μg/m³
    elif field_config.get('transform') == 'smoke_column':
        # Convert column mass to mg/m²
        data = data * 1e6  # kg/m² to mg/m²
    elif field_config.get('transform') == 'dust_concentration':
        # Convert dust concentration from kg/m³ to μg/m³
        data = data * 1e9  # kg/m³ to μg/m³
    elif field_config.get('transform') == 'prate_units':
        # Convert precipitation rate from kg/m²/s to mm/hr
        data = data * 3600  # kg/m²/s to mm/hr
    elif field_config.get('transform') == 'hail_size':
        # Convert hail diameter from m to mm 
        data = data * 1000  # m to mm
    
    return data


def _select_layer(data, layer_config):
    """Select specific layer from multi-dimensional data"""
    if 'heightAboveGroundLayer' in data.dims:
        layer_values = data.heightAboveGroundLayer.values
        print(f"🔍 Available layers: {layer_values}")
        
        if isinstance(layer_config, dict):
            bottom = layer_config.get('bottom', 0)
            top = layer_config.get('top', 3000)
            
            # Find matching layer - HRRR uses top value as identifier
            for i, layer_val in enumerate(layer_values):
                if layer_val == top:
                    print(f"✅ Selected layer {top}m (index {i})")
                    return data.isel(heightAboveGroundLayer=i)
            
            # If exact match not found, try closest
            closest_idx = np.argmin(np.abs(layer_values - top))
            print(f"⚠️ Exact layer {top}m not found, using closest: {layer_values[closest_idx]}m")
            return data.isel(heightAboveGroundLayer=closest_idx)
                    
        elif isinstance(layer_config, int):
            # Direct layer index
            if layer_config < len(layer_values):
                print(f"✅ Selected layer index {layer_config}: {layer_values[layer_config]}m")
                return data.isel(heightAboveGroundLayer=layer_config)
            else:
                print(f"⚠️ Layer index {layer_config} out of range, using last layer")
                return data.isel(heightAboveGroundLayer=-1)
    
    return data