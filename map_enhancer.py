#!/usr/bin/env python3
"""
Simple drop-in map enhancement for HRRR plots
No flags, no complex changes - just better looking maps
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# Better colormaps that still work with existing code
def create_better_colormaps():
    """Create modern-looking colormaps that are drop-in replacements"""
    
    # Better temperature colormap (replaces RdBu_r)
    temp_colors = [
        '#2166ac', '#4393c3', '#92c5de', '#d1e5f0',  # Cold blues
        '#fddbc7', '#f4a582', '#d6604d', '#b2182b'   # Warm reds
    ]
    better_temp = LinearSegmentedColormap.from_list('BetterTemp', temp_colors)
    
    # Better precipitation colormap (replaces BrBG)
    precip_colors = [
        '#ffffff', '#e6f5e6', '#a8dba8', '#79bd79',
        '#49a049', '#2d7a2d', '#1a5a1a', '#0d3d0d'
    ]
    better_precip = LinearSegmentedColormap.from_list('BetterPrecip', precip_colors)
    
    # Better CAPE colormap (replaces YlOrRd)
    cape_colors = [
        '#ffffcc', '#ffeda0', '#fed976', '#feb24c',
        '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026'
    ]
    better_cape = LinearSegmentedColormap.from_list('BetterCAPE', cape_colors)
    
    # Better wind colormap (replaces viridis)
    wind_colors = [
        '#440154', '#414487', '#2a788e', '#22a884',
        '#7ad151', '#fde725'
    ]
    better_wind = LinearSegmentedColormap.from_list('BetterWind', wind_colors)
    
    # Better reflectivity colormap
    refl_colors = [
        (0.0, '#00000000'),  # Transparent for low values
        (0.1, '#00ecec'),    # Very light cyan
        (0.25, '#01a0f6'),   # Light blue  
        (0.4, '#0000f6'),    # Blue
        (0.5, '#00ff00'),    # Green
        (0.65, '#ffff00'),   # Yellow
        (0.75, '#ff9500'),   # Orange
        (0.85, '#ff0000'),   # Red
        (0.95, '#d40000'),   # Dark red
        (1.0, '#ff00ff')     # Magenta
    ]
    refl_cmap_data = [(pos, color) for pos, color in refl_colors]
    better_refl = LinearSegmentedColormap.from_list('BetterReflectivity', refl_cmap_data)
    
    return {
        'RdBu_r': better_temp,
        'BrBG': better_precip,
        'YlOrRd': better_cape,
        'viridis': better_wind,
        'NWSReflectivity': better_refl,
        'plasma': better_cape,  # Also use for CAPE
        'hot': better_cape,
        'jet': better_wind,
        'Blues': better_precip,
        'Reds': better_cape,
        'PuBu': better_precip
    }


def enhance_plot_appearance():
    """Simple enhancements to matplotlib defaults"""
    
    # Use a cleaner style as base
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # But override some settings for weather maps
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.titlesize': 13,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'axes.grid': False,  # We don't want grid on maps
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
        'savefig.facecolor': 'white',
        'savefig.edgecolor': 'none'
    })


def auto_enhance_maps():
    """Call this once at startup to automatically enhance all maps"""
    
    # Apply style improvements
    enhance_plot_appearance()
    
    # Replace default colormaps with better ones
    better_cmaps = create_better_colormaps()
    
    # Monkey-patch plt.cm.get_cmap to return our better versions
    original_get_cmap = plt.cm.get_cmap
    
    def enhanced_get_cmap(name=None, lut=None):
        if name in better_cmaps:
            return better_cmaps[name]
        return original_get_cmap(name, lut)
    
    plt.cm.get_cmap = enhanced_get_cmap
    
    # Also patch direct access
    for name, cmap in better_cmaps.items():
        setattr(plt.cm, name, cmap)
    
    print("✨ Map enhancements activated - your maps will look more modern!")


# Additional helper to enhance existing axes if needed
def enhance_map_axes(ax, extent=None):
    """Enhance an existing map axes with better features"""
    
    # Add state borders with better style
    try:
        import cartopy.feature as cfeature
        ax.add_feature(cfeature.STATES.with_scale('50m'), 
                      linewidth=0.5, edgecolor='#666666', alpha=0.7)
    except:
        pass
    
    # Improve coastlines
    try:
        ax.coastlines('50m', linewidth=0.8, color='#333333', alpha=0.9)
    except:
        # Fallback to default resolution
        ax.coastlines(linewidth=0.8, color='#333333', alpha=0.9)
    
    # Better borders
    try:
        ax.add_feature(cfeature.BORDERS.with_scale('50m'), 
                      linewidth=0.8, edgecolor='#333333', alpha=0.7)
    except:
        pass
    
    # Add subtle land/ocean distinction
    try:
        ax.add_feature(cfeature.LAND, facecolor='#fafafa', alpha=0.3)
        ax.add_feature(cfeature.OCEAN, facecolor='#e6f2ff', alpha=0.2)
    except:
        pass
    
    # Clean up spines
    ax.spines['geo'].set_linewidth(0.8)
    ax.spines['geo'].set_edgecolor('#333333')
    
    return ax


if __name__ == '__main__':
    # Demo the enhancements
    print("Map Enhancer - Simple drop-in improvements for weather maps")
    print("\nTo use, just add this line at the top of your script:")
    print("  from map_enhancer import auto_enhance_maps")
    print("  auto_enhance_maps()")
    print("\nNo other changes needed!")