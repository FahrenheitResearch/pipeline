"""Enhanced SPC-style plotting module"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta
from . import metadata


def create_plot(data, field_name, field_config, cycle, forecast_hour, output_dir, 
                regions, current_region, colormaps, registry):
    """Create enhanced SPC-style plot with comprehensive metadata
    
    Args:
        data: xarray DataArray with the data to plot
        field_name: Name of the field being plotted
        field_config: Configuration dictionary for the field
        cycle: Model cycle string (YYYYMMDDHH)
        forecast_hour: Forecast hour integer
        output_dir: Path object for output directory
        regions: Dictionary of region configurations
        current_region: Current region name
        colormaps: Dictionary of custom colormaps
        registry: FieldRegistry instance for accessing field configurations
    """
    
    # Modern minimal matplotlib settings
    import matplotlib as mpl
    mpl.rcParams['axes.linewidth'] = 0
    mpl.rcParams['axes.edgecolor'] = 'none'
    mpl.rcParams['xtick.major.size'] = 0
    mpl.rcParams['ytick.major.size'] = 0
    # Enable anti-aliasing for smooth lines
    import matplotlib as mpl
    mpl.rcParams['lines.antialiased'] = True
    mpl.rcParams['patch.antialiased'] = True
    mpl.rcParams['text.antialiased'] = True
        
    
    if data is None:
        return None
    
    # Calculate figure size with vertical colorbar in mind
    # With vertical colorbar, we can use more of the figure height
    fig_width = 11  # Slightly wider to accommodate colorbar
    fig_height = 10  # Taller to accommodate extended north view
    
    # Create figure with single axis for map
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor='white', edgecolor='none')
    
    
    # Optional: Use Lambert Conformal Conic (HRRR native projection)
    # Uncomment below to use LCC projection instead of PlateCarree
    # projection = ccrs.LambertConformal(
    #     central_longitude=-97.5,
    #     central_latitude=38.5,
    #     standard_parallels=(38.5, 38.5)
    # )
    # ax_map = plt.axes(projection=projection)
    
    # Create map axes taking full figure
    ax_map = plt.axes(projection=ccrs.PlateCarree())
    ax_map.set_facecolor('white')

    # Remove cartopy attribution for cleaner look
    ax_map._autoscaleXon = False
    ax_map._autoscaleYon = False
        
    # Set extent for CONUS (only supported region now)
    region_config = regions.get('conus', {'extent': [-130, -65, 15, 70], 'barb_thinning': 60})
    # ax_map.set_extent(region_config['extent'], crs=ccrs.PlateCarree())  # Commented - using data bounds instead
    ax_map.patch.set_facecolor('white')
    
    # Add map features with enhanced styling
    try:
        # Try to use higher resolution features if available
        ax_map.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.5, edgecolor='#888888', facecolor='none', zorder=2)
        ax_map.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.6, edgecolor='#666666', facecolor='none', zorder=2)
    except:
        # Fallback to default resolution
        ax_map.add_feature(cfeature.STATES, linewidth=0.6, edgecolor='#444444', facecolor='none', zorder=2)
        ax_map.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='#222222', facecolor='none', zorder=2)
    
    ax_map.add_feature(cfeature.BORDERS, linewidth=0.8, edgecolor='#777777', facecolor='none', zorder=2)
    # Add Great Lakes for geographic reference
    ax_map.add_feature(cfeature.LAKES.with_scale('10m'), facecolor='#f8f8ff', edgecolor='#888888', linewidth=0.3, zorder=1)
    # Add rivers for high-res detail
    ax_map.add_feature(cfeature.RIVERS.with_scale('10m'), facecolor='none', edgecolor='#b8b8ff', linewidth=0.3, alpha=0.5, zorder=1)
    
    # Add very subtle land/ocean distinction for visibility
    ax_map.add_feature(cfeature.LAND, facecolor='#fafafa', alpha=0.5, zorder=0)
    ax_map.add_feature(cfeature.OCEAN, facecolor='#f8f8ff', alpha=0.3, zorder=0)
    
    
    # Get coordinates
    if hasattr(data, 'longitude') and hasattr(data, 'latitude'):
        lons = data.longitude.values
        lats = data.latitude.values
        
        # Debug: Check coordinate dimensions
        # print(f"🔍 Coords for {field_name}: lon shape={lons.shape}, lat shape={lats.shape}, data shape={data.shape}")
    else:
        print(f"❌ No coordinates found for {field_name}")
        return None
    
        # Detect actual data bounds
    data_lat_min, data_lat_max = float(lats.min()), float(lats.max())
    data_lon_min, data_lon_max = float(lons.min()), float(lons.max())
    print(f"📊 Actual HRRR data bounds: Lat {data_lat_min:.1f} to {data_lat_max:.1f}, Lon {data_lon_min:.1f} to {data_lon_max:.1f}")
    
    # Use data bounds with EASTWARD shift to show less Pacific
    # Calculate ranges
    lon_range = data_lon_max - data_lon_min
    lat_range = data_lat_max - data_lat_min
    
    # Slight zoom out (-1% = expand view by 1%)
    zoom_factor = 0  # -0.5% crop = 0.5% expansion on each side
    
    # Adjusted to show full data coverage
    east_shift = 0 # Shifted west to ensure all western data is visible
    
    actual_extent = [
        data_lon_min + (lon_range * zoom_factor) + east_shift,  # West boundary: shift east
        data_lon_max - (lon_range * zoom_factor) + east_shift,  # East boundary: shift east
        data_lat_min + (lat_range * zoom_factor),               # South boundary
        data_lat_max - (lat_range * zoom_factor)                # North boundary
    ]
    
    # Override the configured extent with actual data extent
    ax_map.set_extent(actual_extent, crs=ccrs.PlateCarree())
    print(f"📍 Map extent set to data bounds: {actual_extent}")
    
    # Handle different grid types
    plot_data = data.values.copy()
    if lons.max() > 180:
        lons = np.where(lons > 180, lons - 360, lons)
    
    # Mask invalid data
    if field_config.get('category') == 'smoke':
        # For smoke fields, don't mask out low values - show everything above 0
        plot_data = np.ma.masked_where(
            (np.isnan(plot_data)) | 
            (plot_data <= -9999) | 
            (plot_data <= 0), 
            plot_data
        )
    else:
        # For other fields, mask below first level as usual
        plot_data = np.ma.masked_where(
            (np.isnan(plot_data)) | 
            (plot_data <= -9999) | 
            (plot_data < field_config['levels'][0]), 
            plot_data
        )
    
    # Get colormap
    cmap_name = field_config['cmap']
    if cmap_name in colormaps:
        cmap = colormaps[cmap_name]
    else:
        cmap = plt.cm.get_cmap(cmap_name)
    
    # Plot data - support filled contours, contour lines, and composite plots
    plot_style = field_config.get('plot_style', 'filled')
    
    if plot_style == 'composite':
        # Enhanced composite plot: base field (filled) + multiple overlay types
        plot_cfg = field_config.get('plot_config', {})
        
        # Handle composite data that contains multiple inputs
        if not (hasattr(data, 'attrs') and 'composite_inputs' in data.attrs):
            print(f"❌ Composite plot requires composite data with multiple inputs")
            return None
        
        composite_inputs = data.attrs['composite_inputs']
        base_field_name = plot_cfg.get('base_field')
        
        # 1. Plot Base Layer (filled contour)
        if base_field_name and base_field_name in composite_inputs:
            print(f"🎨 Plotting base field: {base_field_name}")
            base_data = composite_inputs[base_field_name]
            base_config = registry.get_field(base_field_name)
            
            if base_config:
                # Get base field colormap
                base_cmap_name = base_config.get('cmap', 'viridis')
                if base_cmap_name in colormaps:
                    base_cmap = colormaps[base_cmap_name]
                else:
                    base_cmap = plt.cm.get_cmap(base_cmap_name)
                
                # Mask base data
                base_plot_data = np.ma.masked_where(
                    (np.isnan(base_data.values)) | 
                    (base_data.values <= -9999) |
                    (base_data.values < base_config.get('levels', [0])[0]), 
                    base_data.values
                )
                
                # Plot filled contours for base field
                cs_base = ax_map.contourf(
                    lons, lats, base_plot_data,
                    levels=base_config.get('levels', []),
                    cmap=base_cmap,
                    extend=base_config.get('extend', 'max'),
                    transform=ccrs.PlateCarree(),
                    zorder=1
                )
                
                # Add colorbar for base field
                cbar = plt.colorbar(cs_base, ax=ax_map, orientation='horizontal', 
                                   pad=0.05, shrink=0.8, aspect=30)
                cbar.set_label(f"{base_config.get('title', base_field_name)} ({base_config.get('units', 'units')})", 
                               fontsize=12, fontweight='bold')
                cbar.ax.tick_params(labelsize=10)
            else:
                print(f"⚠️ Could not find configuration for base field: {base_field_name}")
        
        # 2. Plot Overlay Layers
        overlays = plot_cfg.get('overlays', [])
        for overlay in overlays:
            overlay_type = overlay.get('type', 'contour')
            
            if overlay_type == 'barbs':
                # Wind barb overlays
                u_field = overlay.get('u_field')
                v_field = overlay.get('v_field')
                
                if u_field in composite_inputs and v_field in composite_inputs:
                    print(f"🌪️ Adding wind barbs: {u_field}, {v_field}")
                    
                    u_data = composite_inputs[u_field].values
                    v_data = composite_inputs[v_field].values
                    
                    # Calculate adaptive thinning based on map extent
                    extent = region_config.get('extent', [-130, -65, 20, 50])
                    extent_width = extent[1] - extent[0]
                    extent_height = extent[3] - extent[2]
                    extent_area = extent_width * extent_height
                    
                    # Adaptive thinning: larger areas need more thinning
                    if extent_area > 2000:  # CONUS-scale
                        adaptive_thinning = 60
                    elif extent_area > 500:  # Regional scale
                        adaptive_thinning = 30
                    elif extent_area > 100:  # State scale
                        adaptive_thinning = 20
                    else:  # Local scale
                        adaptive_thinning = 15
                    
                    # Use overlay-specific, region-specific, or adaptive thinning
                    default_thinning = region_config.get('barb_thinning', adaptive_thinning)
                    thinning = overlay.get('thinning', default_thinning)
                    barb_length = overlay.get('barb_length', 6)
                    barb_units = overlay.get('barb_units', 'm/s')
                    
                    print(f"🎯 Using adaptive barb thinning: {thinning} (extent area: {extent_area:.0f})")
                    
                    # Convert units if specified
                    if barb_units.lower() == 'kts':
                        u_data = u_data * 1.94384  # m/s to knots
                        v_data = v_data * 1.94384
                    elif barb_units.lower() == 'mph':
                        u_data = u_data * 2.23694  # m/s to mph
                        v_data = v_data * 2.23694
                    
                    # Plot wind barbs with thinning
                    ax_map.barbs(
                        lons[::thinning, ::thinning], lats[::thinning, ::thinning],
                        u_data[::thinning, ::thinning], v_data[::thinning, ::thinning],
                        length=barb_length,
                        linewidth=overlay.get('barb_linewidth', 0.5),
                        pivot='middle',
                        color='black',
                        transform=ccrs.PlateCarree(),
                        zorder=3
                    )
                else:
                    print(f"⚠️ Missing wind components for barbs: {u_field}, {v_field}")
            
            elif overlay_type == 'contour':
                # Contour line overlays
                overlay_field = overlay.get('field')
                if overlay_field and overlay_field in composite_inputs:
                    print(f"📈 Adding contour overlay: {overlay_field}")
                    
                    overlay_data = composite_inputs[overlay_field].values
                    overlay_config = registry.get_field(overlay_field)
                    
                    if overlay_config:
                        cs_overlay = ax_map.contour(
                            lons, lats, overlay_data,
                            levels=overlay.get('levels', overlay_config.get('levels', [])),
                            colors=overlay.get('colors', ['white']),
                            linewidths=overlay.get('linewidths', [1.5]),
                            linestyles=overlay.get('linestyles', ['solid']),
                            transform=ccrs.PlateCarree(),
                            zorder=2
                        )
                        
                        # Add labels if requested
                        if overlay.get('label_contours', False):
                            ax_map.clabel(cs_overlay, inline=True, fontsize=8, fmt='%.1f')
                else:
                    print(f"⚠️ Missing overlay field: {overlay_field}")
            
            elif overlay_type == 'streamlines':
                # Streamline overlays (future enhancement)
                u_field = overlay.get('u_field')
                v_field = overlay.get('v_field')
                
                if u_field in composite_inputs and v_field in composite_inputs:
                    print(f"🌊 Adding streamlines: {u_field}, {v_field}")
                    u_data = composite_inputs[u_field].values
                    v_data = composite_inputs[v_field].values
                    
                    ax_map.streamplot(
                        lons, lats, u_data, v_data,
                        color=overlay.get('color', 'black'),
                        linewidth=overlay.get('linewidth', 1),
                        density=overlay.get('density', 1),
                        transform=ccrs.PlateCarree(),
                        zorder=2
                    )
                else:
                    print(f"⚠️ Missing wind components for streamlines: {u_field}, {v_field}")
        
    elif plot_style == 'spc_vtp':
        # SPC-style VTP panel: MLCIN shading + dashed CIN isolines + VTP contours
        spc_config = field_config.get('spc_config', {})
        
        # Load MLCIN data for base shading
        try:
            from field_registry import FieldRegistry
            local_registry = FieldRegistry()
            local_registry.build_all_configs({})
            
            if 'mlcin' in local_registry.all_fields:
                mlcin_config = local_registry.all_fields['mlcin']
                # Try to load MLCIN from available GRIB files
                mlcin_data = None
                grib_files = [f for f in [pressure_grib_file, surface_grib_file] if f and os.path.exists(f)]
                
                for grib_file in grib_files:
                    try:
                        from . import grib_loader
                        mlcin_data = grib_loader.load_field(grib_file, 'mlcin', mlcin_config, 'hrrr')
                        if mlcin_data is not None:
                            break
                    except:
                        continue
                
                if mlcin_data is not None:
                    # 1. MLCIN shading (cyan with hatching)
                    cin_shade_levels = spc_config.get('cin_shade_levels', [-100, -25, 0])
                    cin_colors = spc_config.get('cin_cmap_colors', ['#00d5ff', '#b0f0ff'])
                    cin_hatches = spc_config.get('cin_hatches', ['////', None])
                    
                    cin_cmap = mcolors.ListedColormap(cin_colors)
                    cin_masked = np.ma.masked_where(mlcin_data > -25, mlcin_data)
                    
                    cf = ax_map.contourf(lons, lats, cin_masked,
                                       levels=cin_shade_levels,
                                       cmap=cin_cmap, extend='min',
                                       transform=ccrs.PlateCarree(),
                                       zorder=1)
                    
                    # Add hatching to collections
                    for i, coll in enumerate(cf.collections):
                        if i < len(cin_hatches) and cin_hatches[i]:
                            coll.set_hatch(cin_hatches[i])
                            coll.set_edgecolor('none')
                    
                    # 2. Dashed CIN isolines
                    cin_line_levels = spc_config.get('cin_line_levels', [-50, -25])
                    cin_line_color = spc_config.get('cin_line_color', '#d67800')
                    
                    ax_map.contour(lons, lats, mlcin_data,
                                 levels=cin_line_levels,
                                 colors=cin_line_color,
                                 linewidths=1.0,
                                 linestyles='--',
                                 transform=ccrs.PlateCarree(),
                                 zorder=3)
                    
                    # Add CIN colorbar (small, lower placement)
                    cbar = plt.colorbar(cf, ax=ax_map, orientation='horizontal',
                                      shrink=0.4, pad=0.03)
                    cbar.set_label('MLCIN (J kg⁻¹)', fontsize=10, fontweight='bold')
                    cbar.ax.tick_params(labelsize=8)
                
        except Exception as e:
            print(f"⚠️ Could not load MLCIN for SPC-style plot: {e}")
        
        # 3. VTP contours (red → purple progression)
        vtp_levels = spc_config.get('vtp_levels', [2, 3, 4, 6, 8, 10, 12])
        vtp_colors = spc_config.get('vtp_colors', ['#ff0000']*4 + ['#9900ff']*3)
        vtp_linewidths = spc_config.get('vtp_linewidths', [1, 1, 1, 1.5, 2, 2.5, 3])
        
        # Mask VTP data to only show >= 2
        vtp_masked = np.ma.masked_where(plot_data < 2, plot_data)
        
        cs_vtp = ax_map.contour(lons, lats, vtp_masked,
                               levels=vtp_levels,
                               colors=vtp_colors,
                               linewidths=vtp_linewidths,
                               transform=ccrs.PlateCarree(),
                               zorder=4)
        
        # Add VTP labels
        ax_map.clabel(cs_vtp, inline=True, fontsize=9, fmt='%.0f')
        
    elif plot_style == 'spc_style':
        # SPC-style filled contours with proper boundary norm (Hampshire et al. 2018 standards)
        levels = field_config['levels']
        cmap = plt.cm.get_cmap('plasma', len(levels)-1)
        norm = mcolors.BoundaryNorm(levels, cmap.N)
        
        # Mask data below threshold
        plot_data = np.ma.masked_where((plot_data < levels[0]) | (np.isnan(plot_data)), plot_data)
        
        cs = ax_map.contourf(lons, lats, plot_data,
                            levels=levels, cmap=cmap, norm=norm,
                            extend=field_config['extend'],
                            transform=ccrs.PlateCarree(),
                            zorder=1)
        
        # Add red contour lines for VTP >= 2 (SPC overlay style)
        high_levels = [l for l in levels if l >= 2]
        if len(high_levels) > 0:
            cs_lines = ax_map.contour(lons, lats, plot_data,
                                     levels=high_levels,
                                     colors='red', linewidths=1.5,
                                     transform=ccrs.PlateCarree(),
                                     zorder=2)
            ax_map.clabel(cs_lines, inline=True, fontsize=9, fmt='%.0f')
        
    elif plot_style == 'multicolor_lines':
        # Multi-colored contour lines (like SPC style)
        colors = field_config.get('line_colors', ['red'])
        widths = field_config.get('line_widths', [1.5])
        
        cs = ax_map.contour(lons, lats, plot_data,
                           levels=field_config['levels'],
                           colors=colors,
                           linewidths=widths,
                           transform=ccrs.PlateCarree(),
                           zorder=2)
        # Add contour labels
        ax_map.clabel(cs, inline=True, fontsize=9, fmt='%.1f')
        
    elif plot_style == 'lines':
        # Enhanced contour lines with professional meteorological styling
        plot_cfg = field_config.get('plot_config', {})
        
        # Handle composite data that contains multiple inputs
        if hasattr(data, 'attrs') and 'composite_inputs' in data.attrs:
            # Get the specific field to plot from composite inputs
            field_to_plot = plot_cfg.get('field')
            if field_to_plot and field_to_plot in data.attrs['composite_inputs']:
                line_data = data.attrs['composite_inputs'][field_to_plot].values
            else:
                # Fallback to the first input field
                first_field = list(data.attrs['composite_inputs'].keys())[0]
                line_data = data.attrs['composite_inputs'][first_field].values
                print(f"⚠️ Field '{plot_cfg.get('field')}' not found, using {first_field}")
        else:
            # Regular single-field data
            line_data = plot_data
        
        # Apply optimal smoothing for perfectly smooth contours
        try:
            from scipy import ndimage
            # Get custom smoothing parameter or use default
            gaussian_sigma = plot_cfg.get('gaussian_sigma', 2.0)
            smoothed_data = ndimage.gaussian_filter(line_data, sigma=gaussian_sigma)
            print(f"🎯 Applied Gaussian smoothing (σ={gaussian_sigma}) to {field_config.get('title', 'field')}")
        except ImportError:
            print("⚠️ SciPy not available for smoothing, using raw data")
            smoothed_data = line_data
        except Exception as e:
            print(f"⚠️ Smoothing failed: {e}, using raw data")
            smoothed_data = line_data
        
        # Check and clean data range first
        print(f"🔍 Data range before cleaning: {np.nanmin(smoothed_data):.1f} to {np.nanmax(smoothed_data):.1f}")
        
        # Mask unrealistic values for surface pressure (should be ~980-1040 hPa)
        field_name_lower = field_config.get('title', '').lower()
        if 'pressure' in field_name_lower or 'hpa' in field_config.get('units', '').lower():
            # Mask unrealistic pressure values
            smoothed_data = np.ma.masked_where((smoothed_data < 900) | (smoothed_data > 1100), smoothed_data)
            print(f"🎯 Masked unrealistic pressure values (keeping 900-1100 hPa)")
            print(f"🔍 Data range after cleaning: {np.nanmin(smoothed_data):.1f} to {np.nanmax(smoothed_data):.1f}")
        
        # Parse levels (support both JSON string and list formats)
        levels_config = plot_cfg.get('levels', field_config.get('levels', []))
        if isinstance(levels_config, str):
            try:
                import json
                levels = json.loads(levels_config)
            except (json.JSONDecodeError, ValueError):
                # Generate meteorologically appropriate levels - FEWER levels for clarity
                data_min, data_max = np.nanmin(smoothed_data), np.nanmax(smoothed_data)
                
                # Use standard meteorological intervals
                if 'pressure' in field_name_lower or 'hpa' in field_config.get('units', '').lower():
                    # For pressure: use 4 hPa intervals (standard meteorological practice)
                    levels = np.arange(980, 1040, 4).tolist()
                    print(f"🎯 Using standard pressure levels (4 hPa intervals): {levels}")
                elif 'temperature' in field_name_lower:
                    # For temperature: use 5°C intervals  
                    start_temp = int(data_min // 5) * 5
                    end_temp = int((data_max // 5) + 1) * 5
                    levels = np.arange(start_temp, end_temp + 5, 5).tolist()
                    print(f"🎯 Using temperature levels (5°C intervals): {levels}")
                else:
                    # For other fields: use wider intervals
                    data_range = data_max - data_min
                    interval = max(data_range / 8, 1)  # Maximum 8 levels
                    start_level = int(data_min // interval) * interval
                    end_level = int((data_max // interval) + 1) * interval
                    levels = np.arange(start_level, end_level + interval, interval).tolist()
                    print(f"🎯 Auto-generated levels (max 8 intervals): {levels}")
        else:
            levels = levels_config
        
        # Apply professional meteorological styling - follow your recommendations exactly
        line_color = plot_cfg.get('line_color', 'black')
        line_width = plot_cfg.get('line_width', 0.7)  # Your recommended 0.7 linewidth
        line_style = plot_cfg.get('line_style', 'solid')
        label_contours = plot_cfg.get('label_contours', True)
        
        # Thin the data grid to reduce density (configurable spacing for cleaner contours)
        skip = plot_cfg.get('grid_thinning', 4)
        lons_thin = lons[::skip, ::skip]
        lats_thin = lats[::skip, ::skip]
        data_thin = smoothed_data[::skip, ::skip]
        print(f"🎯 Applied grid thinning: every {skip}th point for cleaner contours")
        
        # Create contour plot with your exact recommendations
        cs = ax_map.contour(lons_thin, lats_thin, data_thin,
                           levels=levels,
                           colors='black',  # Always black as you recommended
                           linewidths=0.7,  # Your exact specification
                           linestyles=line_style,
                           transform=ccrs.PlateCarree(),
                           zorder=2)
        
        # Add contour labels with configurable spacing
        if label_contours:
            label_spacing = plot_cfg.get('label_spacing', 8)
            labels = ax_map.clabel(cs, 
                                  inline=True, 
                                  fontsize=8,        # Your recommended size
                                  fmt='%1.0f',       # Your exact format specification
                                  inline_spacing=label_spacing)  # Configurable spacing
            
            # No background boxes - cleaner professional appearance
            print(f"🎯 Added {len(labels)} contour labels with {label_spacing}-unit spacing")
                
    elif plot_style == 'lines_with_barbs':
        # Classic meteorological map: contour lines + wind barbs (like NOAA surface analysis)
        plot_cfg = field_config.get('plot_config', {})
        
        # Handle composite data that contains multiple inputs
        if not (hasattr(data, 'attrs') and 'composite_inputs' in data.attrs):
            print(f"❌ lines_with_barbs plot requires composite data with multiple inputs")
            return None
        
        composite_inputs = data.attrs['composite_inputs']
        
        # 1. Plot contour lines (e.g., pressure isobars)
        contour_field = plot_cfg.get('contour_field')
        if contour_field and contour_field in composite_inputs:
            print(f"📈 Plotting contour field: {contour_field}")
            contour_data = composite_inputs[contour_field].values
            
            # Apply optimal smoothing for perfectly smooth contours
            try:
                from scipy import ndimage
                smoothed_contour = ndimage.gaussian_filter(contour_data, sigma=2.0)
                print(f"🎯 Applied Gaussian smoothing (σ=2.0) to {contour_field}")
            except ImportError:
                print("⚠️ SciPy not available for smoothing, using raw data")
                smoothed_contour = contour_data
            except Exception as e:
                print(f"⚠️ Smoothing failed: {e}, using raw data")
                smoothed_contour = contour_data
            
            # Check and clean pressure data range
            print(f"🔍 Pressure data range before cleaning: {np.nanmin(smoothed_contour):.1f} to {np.nanmax(smoothed_contour):.1f}")
            
            # Mask unrealistic pressure values (should be ~980-1040 hPa)
            smoothed_contour = np.ma.masked_where((smoothed_contour < 900) | (smoothed_contour > 1100), smoothed_contour)
            print(f"🎯 Masked unrealistic pressure values (keeping 900-1100 hPa)")
            print(f"🔍 Pressure data range after cleaning: {np.nanmin(smoothed_contour):.1f} to {np.nanmax(smoothed_contour):.1f}")
            
            # Parse contour levels
            contour_levels_config = plot_cfg.get('contour_levels', [])
            if isinstance(contour_levels_config, str):
                try:
                    import json
                    contour_levels = json.loads(contour_levels_config)
                except (json.JSONDecodeError, ValueError):
                    # Use standard 4 hPa intervals for pressure (your recommendation)
                    contour_levels = np.arange(980, 1040, 4).tolist()
                    print(f"🎯 Using standard pressure levels (4 hPa intervals): {contour_levels}")
            else:
                contour_levels = contour_levels_config
            
            # Thin the data grid to reduce density for cleaner contours
            skip = 4
            lons_thin = lons[::skip, ::skip]
            lats_thin = lats[::skip, ::skip]
            contour_thin = smoothed_contour[::skip, ::skip]
            print(f"🎯 Applied grid thinning: every {skip}th point for cleaner contours")
            
            # Plot contour lines with your exact recommendations
            cs = ax_map.contour(lons_thin, lats_thin, contour_thin,
                               levels=contour_levels,
                               colors='black',      # Always black as you recommended
                               linewidths=0.8,      # Professional line weight
                               linestyles='solid',
                               transform=ccrs.PlateCarree(),
                               zorder=2)
            
            # Add contour labels with your exact spacing recommendations
            if plot_cfg.get('label_contours', True):
                labels = ax_map.clabel(cs, 
                                      inline=True, 
                                      fontsize=8,        # Your recommended size
                                      fmt='%1.0f',       # Your exact format
                                      inline_spacing=8)  # Increased spacing for cleaner placement
                
                print(f"🎯 Added {len(labels)} pressure contour labels with 8-unit spacing")
        
        # 2. Plot wind barbs
        wind_config = plot_cfg.get('wind_barbs', {})
        u_field = wind_config.get('u_field')
        v_field = wind_config.get('v_field')
        
        if u_field in composite_inputs and v_field in composite_inputs:
            print(f"🌪️ Adding wind barbs: {u_field}, {v_field}")
            
            u_data = composite_inputs[u_field].values
            v_data = composite_inputs[v_field].values
            
            # Use optimal wind barb density (every 30th point for final clarity)
            barb_skip = 30  # Your final recommendation for cleaner appearance
            barb_length = wind_config.get('barb_length', 4)  # Your final recommended length
            barb_linewidth = wind_config.get('barb_linewidth', 0.5)  # Your recommended width
            barb_units = wind_config.get('barb_units', 'm/s')
            
            # Convert units if specified
            if barb_units.lower() == 'kts':
                u_data = u_data * 1.94384  # m/s to knots
                v_data = v_data * 1.94384
            elif barb_units.lower() == 'mph':
                u_data = u_data * 2.23694  # m/s to mph
                v_data = v_data * 2.23694
            
            # Plot wind barbs with your final polished recommendations
            ax_map.barbs(
                lons[::barb_skip, ::barb_skip], lats[::barb_skip, ::barb_skip],
                u_data[::barb_skip, ::barb_skip], v_data[::barb_skip, ::barb_skip],
                length=4,           # Your final recommended length
                linewidth=0.5,      # Your recommended linewidth  
                pivot='middle',
                color='black',      # Your recommended color
                transform=ccrs.PlateCarree(),
                zorder=3
            )
            print(f"🎯 Added wind barbs with {barb_skip}-point spacing (length=4, linewidth=0.5)")
        else:
            print(f"⚠️ Missing wind components for barbs: {u_field}, {v_field}")
    
    else:
        # Default filled contours
        cs = ax_map.contourf(lons, lats, plot_data,
                             levels=field_config['levels'],
                             cmap=cmap,
                             extend=field_config['extend'],
                             transform=ccrs.PlateCarree(),
                             zorder=1)
    
    # Add colorbar (for filled contours and SPC style, but not spc_vtp which handles its own)
    if plot_style in ['filled', 'spc_style']:
        # Vertical colorbar on the left
        # Create a new axes for the colorbar on the left
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(ax_map)
        cax = divider.append_axes("left", size="1.5%", pad=0.05, axes_class=plt.Axes)
        
        cbar = plt.colorbar(cs, cax=cax, orientation='vertical')
        cbar.ax.tick_params(labelsize=8, length=2, color='#999999')
        cbar.outline.set_linewidth(0.5)
        cbar.outline.set_edgecolor('#cccccc')
        
        # Position colorbar ticks on the left
        cbar.ax.yaxis.set_ticks_position('left')
        cbar.ax.yaxis.set_label_position('left')
        
        # Show a few key values
        n_ticks = min(5, len(field_config['levels']))
        tick_indices = [i * (len(field_config['levels']) - 1) // (n_ticks - 1) for i in range(n_ticks)]
        cbar.set_ticks([field_config['levels'][i] for i in tick_indices])
        
        # No label needed - units are in title
        # cbar.set_label(field_config['units'], fontsize=9, color='#666666', labelpad=10)
    
    # Enhanced title for main map
    cycle_dt = datetime.strptime(cycle, '%Y%m%d%H')
    valid_dt = cycle_dt + timedelta(hours=forecast_hour)
    
    # No region suffix needed since we only support CONUS
    region_suffix = ""
    
    # Clean title with units and model run time
    model_run_time = f"{cycle_dt.hour:02d}z"
    title_text = f"{field_config['title']} ({field_config['units']}) · {model_run_time} run · Valid: {valid_dt.strftime('%Y-%m-%d %H:00 UTC')}"
    ax_map.set_title(title_text, fontsize=11, color='#333333', pad=10, loc='left')
    
    # Save map
    output_file = output_dir / f"{field_name}_f{forecast_hour:02d}_REFACTORED.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none', pad_inches=0.1)
    plt.close()
    
    # Save metadata as JSON
    metadata_file = metadata.save_metadata_json(field_name, field_config, cycle_dt, valid_dt, 
                                               forecast_hour, data, output_dir, current_region)
    
    return output_file