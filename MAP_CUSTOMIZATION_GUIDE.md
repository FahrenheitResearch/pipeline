# 🗺️ Map Customization Guide for HRRR Weather Processor

This guide explains how to customize the appearance of weather maps in this HRRR processing system. The maps are generated using matplotlib, cartopy, and custom styling configurations.

## 📁 Key Files for Map Customization

### Core Files:
- **`core/plotting.py`** - Main plotting logic, map features, styling
- **`map_enhancer.py`** - Automatic style enhancements and custom colormaps
- **`config/colormaps.py`** - Custom colormap definitions
- **`parameters/*.json`** - Field configurations including colors, levels, styles

### Current Map Pipeline:
1. Data is loaded from GRIB files
2. Field configuration is read from JSON (colormap, levels, style)
3. `core/plotting.py` creates the map with cartopy
4. `map_enhancer.py` applies style overrides
5. Output saved as PNG at 150 DPI

## 🎨 Quick Customization Options

### 1. **Changing Colors (Easiest)**

Edit any parameter file in `parameters/` folder:
```json
{
  "sbcape": {
    "var": "CAPE",
    "level": "surface",
    "cmap": "viridis",  // ← CHANGE THIS
    "title": "Surface-Based CAPE",
    "units": "J/kg",
    "levels": [100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000]
  }
}
```

**Available colormaps:**
- Scientific: `viridis`, `plasma`, `inferno`, `magma`, `cividis`
- Temperature: `RdBu_r`, `coolwarm`, `bwr`, `seismic`
- Precipitation: `Blues`, `BuGn`, `YlGnBu`, `PuBu`
- Intensity: `hot`, `afmhot`, `gist_heat`, `YlOrRd`
- Rainbow: `turbo`, `jet`, `rainbow`, `gist_rainbow`
- Custom: `CAPE`, `NWSReflectivity`, `WBGT` (defined in project)

### 2. **Adjusting Contour Levels**

Controls the smoothness and breaks in color transitions:
```json
{
  "levels": [0, 500, 1000, 1500, 2000, 3000, 4000, 5000],  // Fewer = smoother
  "levels": [0, 100, 200, 300, 400, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 4000, 5000]  // More = detailed
}
```

### 3. **Plot Styles**

```json
{
  "plot_style": "filled",      // Default: smooth filled contours
  "plot_style": "contour",     // Just contour lines, no fill
  "plot_style": "pcolormesh",  // Pixelated/gridded appearance
  "plot_style": "lines"        // For overlays only
}
```

### 4. **Colorbar Extensions**

```json
{
  "extend": "neither",  // No arrows on colorbar
  "extend": "both",     // Arrows on both ends (values exceed range)
  "extend": "min",      // Arrow on low end only
  "extend": "max"       // Arrow on high end only
}
```

## 🛠️ Advanced Customization

### Map Features (`core/plotting.py` lines 49-64)

Current settings:
```python
# State boundaries
ax_map.add_feature(cfeature.STATES.with_scale('50m'), linewidth=0.6, edgecolor='#444444', facecolor='none', zorder=2)

# Coastlines
ax_map.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.8, edgecolor='#222222', facecolor='none', zorder=2)

# International borders
ax_map.add_feature(cfeature.BORDERS, linewidth=1.0, edgecolor='#222222', facecolor='none', zorder=2)

# Land/Ocean shading
ax_map.add_feature(cfeature.LAND, facecolor='#fafafa', alpha=0.3, zorder=0)
ax_map.add_feature(cfeature.OCEAN, facecolor='#e6f2ff', alpha=0.2, zorder=0)
```

**Customization options:**
- `linewidth`: Thickness of lines (0.1 to 2.0)
- `edgecolor`: Color of lines (hex colors like '#000000' for black)
- `alpha`: Transparency (0.0 = invisible, 1.0 = opaque)
- `facecolor`: Fill color for areas
- Resolution: `'50m'`, `'10m'` (higher detail), `'110m'` (lower detail)

### Figure Size and Quality (`core/plotting.py` lines 34-35)

```python
fig_width = 12  # Width in inches
fig_height = fig_width / aspect_ratio  # Height maintains data aspect ratio
```

Output quality (line 651):
```python
plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
```

### Custom Colormaps (`config/colormaps.py`)

To add a new colormap:
```python
def create_my_custom_colormap():
    colors = ['#ffffff', '#ffe6e6', '#ffcccc', '#ff9999', '#ff6666', '#ff3333', '#cc0000']
    return LinearSegmentedColormap.from_list('MyCustom', colors)

# In create_all_colormaps():
custom_colormaps['MyCustom'] = create_my_custom_colormap()
```

### Map Enhancements (`map_enhancer.py`)

The enhancer automatically improves maps. To disable or modify:
- Comment out `from map_enhancer import auto_enhance_maps` in `processor_base.py`
- Or edit the color definitions in `map_enhancer.py` lines 17-72

## 🧪 Testing Workflow

### 1. Create Test Variations

Add to any parameter JSON file:
```json
{
  "temperature_2m_original": {
    "var": "TMP",
    "level": "2 m above ground",
    "cmap": "RdBu_r",
    "title": "Temperature (Original)"
  },
  "temperature_2m_modern": {
    "var": "TMP", 
    "level": "2 m above ground",
    "cmap": "turbo",
    "levels": [-30, -20, -10, 0, 10, 20, 30, 40],
    "title": "Temperature (Modern)"
  }
}
```

### 2. Process Only Test Fields

```bash
# Test single forecast hour with specific fields
python processor_cli.py 20250716 12 --hours 0 --fields temperature_2m_original,temperature_2m_modern
```

### 3. Output Location

Maps are saved to:
```
outputs/hrrr/[date]/[hour]z/F[fcst_hr]/conus/F[fcst_hr]/[category]/[field]_f[fcst_hr]_REFACTORED.png
```

## 📝 Common Customization Tasks

### Make maps more colorful:
- Change `cmap` to `turbo`, `jet`, or `rainbow`
- Increase color `levels` for more gradations

### Make maps more professional/muted:
- Use `viridis`, `cividis`, or `plasma` colormaps
- Reduce `alpha` values for overlays
- Use grayscale borders: `edgecolor='#666666'`

### Improve readability:
- Increase `linewidth` for borders
- Add white or black halos to text
- Reduce number of `levels` for cleaner appearance

### Match SPC/NWS style:
- Use their colormaps (already included)
- Set borders to black with 0.5-0.8 linewidth
- Remove land/ocean shading

## 🐛 Debugging Tips

1. **Color ranges wrong?** Check `levels` array - must go from low to high
2. **Map features missing?** Check `zorder` - higher numbers plot on top
3. **Colors look different?** `map_enhancer.py` may be overriding - check line 60-72
4. **Changes not showing?** The system caches field configs - restart processing

## 💡 Performance Notes

- Higher resolution features (`'10m'`) slow down plotting
- More contour `levels` increase processing time
- `pcolormesh` is faster than `contourf` for large grids
- Higher DPI increases file size significantly

## 🔧 System Architecture

The plotting system loads configurations from JSON files at runtime, making it easy to experiment without changing code. The basic flow:

1. **Field Registry** reads all parameter JSON files
2. **Processor** loads the GRIB data
3. **Plotting** module receives data + config
4. **Map Enhancer** applies style overrides
5. **Output** saved as PNG

This modular design means you can:
- Add new fields by creating JSON entries
- Test variations by duplicating and modifying entries
- Switch styles without reprocessing data
- Compare different visualizations side-by-side