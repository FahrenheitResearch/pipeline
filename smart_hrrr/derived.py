# Move the heavy derived/composite logic here, called by HRRRProcessor.
# This keeps processor_core.py under ~300–400 lines.

from typing import Optional
import xarray as xr
from derived_params import compute_derived_parameter


def load_derived_parameter(processor, field_name: str, field_config: dict, grib_file, wrfsfc_file=None) -> Optional[xr.DataArray]:
    """Load and compute derived parameter from input fields"""
    try:
        print(f"🧮 Computing derived parameter: {field_name}")
        
        # Get input field names and function
        input_fields = field_config.get('inputs', [])
        function_name = field_config.get('function')
        
        if not input_fields or not function_name:
            print(f"❌ Missing inputs or function for derived parameter {field_name}")
            return None
        
        # Special handling for composite fields (lines/composite/lines_with_barbs plot styles with identity function)
        plot_style = field_config.get('plot_style', 'filled')
        if plot_style in ['lines', 'composite', 'lines_with_barbs'] and function_name == 'identity':
            return load_composite_data(processor, field_name, field_config, grib_file, wrfsfc_file)
        
        # Load all input fields
        input_data = {}
        for input_field in input_fields:
            print(f"  Loading input field: {input_field}")
            
            # Get configuration for input field
            input_config = processor.registry.get_field(input_field)
            if not input_config:
                print(f"❌ Input field configuration not found: {input_field}")
                return None
            
            # Check if input field is also derived (recursive)
            if input_config.get('derived'):
                data = load_derived_parameter(processor, input_field, input_config, grib_file, wrfsfc_file)
            else:
                # Load regular field data
                if input_config.get('category') == 'smoke' and wrfsfc_file:
                    data = processor.load_field_data(wrfsfc_file, input_field, input_config)
                    if data is None:
                        data = processor.load_field_data(grib_file, input_field, input_config)
                else:
                    data = processor.load_field_data(grib_file, input_field, input_config)
            
            if data is None:
                print(f"❌ Failed to load input field: {input_field}")
                return None
            
            # Convert to numpy array for computation
            input_data[input_field] = data.values
            print(f"  ✅ Loaded {input_field}: {data.shape}")
        
        # Note: SCP will use fallback recipe if mucin is unavailable
        
        # Compute derived parameter
        print(f"  Computing {function_name}...")
        result_array = compute_derived_parameter(field_name, input_data, field_config)
        
        if result_array is None:
            print(f"❌ Failed to compute derived parameter: {field_name}")
            return None
        
        # Create xarray DataArray with coordinates from one of the input fields
        # Use the first successfully loaded input field for coordinates
        reference_field = list(input_data.keys())[0]
        reference_config = processor.registry.get_field(reference_field)
        
        # Load reference field as xarray to get coordinates
        if reference_config.get('derived'):
            # For derived reference fields, we need to find a non-derived input field for coordinates
            # Look for the first non-derived input in the reference field's inputs
            ref_inputs = reference_config.get('inputs', [])
            ref_data = None
            for ref_input in ref_inputs:
                ref_input_config = processor.registry.get_field(ref_input)
                if not ref_input_config.get('derived'):
                    # Found a non-derived input, use it for coordinates
                    if ref_input_config.get('category') == 'smoke' and wrfsfc_file:
                        ref_data = processor.load_field_data(wrfsfc_file, ref_input, ref_input_config)
                        if ref_data is None:
                            ref_data = processor.load_field_data(grib_file, ref_input, ref_input_config)
                    else:
                        ref_data = processor.load_field_data(grib_file, ref_input, ref_input_config)
                    if ref_data is not None:
                        break
            # If still no reference data, use the computed reference field itself
            if ref_data is None:
                # Use one of the already loaded input fields for coordinates
                for inp_name, inp_array in input_data.items():
                    inp_config = processor.registry.get_field(inp_name)
                    if not inp_config.get('derived'):
                        if inp_config.get('category') == 'smoke' and wrfsfc_file:
                            ref_data = processor.load_field_data(wrfsfc_file, inp_name, inp_config)
                            if ref_data is None:
                                ref_data = processor.load_field_data(grib_file, inp_name, inp_config)
                        else:
                            ref_data = processor.load_field_data(grib_file, inp_name, inp_config)
                        if ref_data is not None:
                            break
        else:
            # Regular field, load normally
            if reference_config.get('category') == 'smoke' and wrfsfc_file:
                ref_data = processor.load_field_data(wrfsfc_file, reference_field, reference_config)
                if ref_data is None:
                    ref_data = processor.load_field_data(grib_file, reference_field, reference_config)
            else:
                ref_data = processor.load_field_data(grib_file, reference_field, reference_config)
        
        if ref_data is None:
            print(f"❌ Could not get reference coordinates")
            return None
        
        # Create DataArray with same coordinates as reference
        result_data = xr.DataArray(
            result_array,
            coords=ref_data.coords,
            dims=ref_data.dims,
            name=field_name,
            attrs={
                'long_name': field_config.get('title', field_name),
                'units': field_config.get('units', 'dimensionless'),
                'derived': True
            }
        )
        
        print(f"✅ Successfully computed derived parameter: {field_name}")
        return result_data
        
    except Exception as e:
        print(f"❌ Error computing derived parameter {field_name}: {e}")
        return None


def load_composite_data(processor, field_name: str, field_config: dict, grib_file, wrfsfc_file=None) -> Optional[xr.DataArray]:
    """Load data for composite plots that need multiple input fields"""
    try:
        print(f"🎨 Loading composite data for: {field_name}")
        
        input_fields = field_config.get('inputs', [])
        input_data = {}
        reference_data = None
        
        # Load all input fields as xarray objects
        for input_field in input_fields:
            print(f"  Loading input field: {input_field}")
            
            # Get configuration for input field
            input_config = processor.registry.get_field(input_field)
            if not input_config:
                print(f"❌ Input field configuration not found: {input_field}")
                return None
            
            # Load the field data (keeping as xarray for coordinates)
            if input_config.get('category') == 'smoke' and wrfsfc_file:
                data = processor.load_field_data(wrfsfc_file, input_field, input_config)
                if data is None:
                    data = processor.load_field_data(grib_file, input_field, input_config)
            else:
                data = processor.load_field_data(grib_file, input_field, input_config)
            
            if data is None:
                print(f"❌ Failed to load input field: {input_field}")
                return None
            
            # Store the xarray object
            input_data[input_field] = data
            print(f"  ✅ Loaded {input_field}: {data.shape}")
            
            # Use first field as reference for coordinates
            if reference_data is None:
                reference_data = data
        
        # Create a composite data object that contains all inputs
        # We'll return the reference data but with a special attribute containing all inputs
        composite_data = reference_data.copy()
        composite_data.name = field_name
        composite_data.attrs.update({
            'composite_inputs': input_data,
            'plot_style': field_config.get('plot_style'),
            'plot_config': field_config.get('plot_config', {}),
            'long_name': field_config.get('title', field_name),
            'units': field_config.get('units', 'composite'),
            'derived': True
        })
        
        print(f"✅ Successfully loaded composite data: {field_name}")
        return composite_data
        
    except Exception as e:
        print(f"❌ Error loading composite data {field_name}: {e}")
        return None