#!/usr/bin/env python3
"""
Experimental Custom Colormaps for HRRR
Artistic and unique color schemes
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

def create_experimental_colormaps():
    """Create experimental custom colormaps"""
    
    custom_cmaps = {}
    
    # Vaporwave colormap
    vaporwave_colors = ['#FF006E', '#FB5607', '#FFBE0B', '#8338EC', '#3A86FF']
    custom_cmaps['vaporwave'] = LinearSegmentedColormap.from_list('vaporwave', vaporwave_colors)
    
    # Miami Vice colormap
    miami_colors = ['#0B0B0B', '#1A1A2E', '#16213E', '#0F3460', '#E94560', '#FFD93D']
    custom_cmaps['miami'] = LinearSegmentedColormap.from_list('miami', miami_colors)
    
    # Northern Lights colormap
    aurora_colors = ['#000428', '#004E92', '#00A896', '#02C39A', '#F0F3BD', '#FFE66D']
    custom_cmaps['aurora'] = LinearSegmentedColormap.from_list('aurora', aurora_colors)
    
    # Thermal camera colormap
    thermal_colors = ['#000000', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF0000', '#FFFFFF']
    custom_cmaps['thermal'] = LinearSegmentedColormap.from_list('thermal', thermal_colors)
    
    # Vintage weather map colormap
    vintage_colors = ['#F4E8C1', '#D4A574', '#BB8C5F', '#96705B', '#70524D', '#4A3C3B']
    custom_cmaps['vintage_weather'] = LinearSegmentedColormap.from_list('vintage_weather', vintage_colors)
    
    # Electric colormap
    electric_colors = ['#0D0221', '#1A0B3E', '#420A68', '#721F81', '#B63679', '#F7667E', '#FFB6C1']
    custom_cmaps['electric'] = LinearSegmentedColormap.from_list('electric', electric_colors)
    
    # Matrix green colormap
    matrix_colors = ['#000000', '#003300', '#006600', '#009900', '#00CC00', '#00FF00', '#66FF66']
    custom_cmaps['matrix'] = LinearSegmentedColormap.from_list('matrix', matrix_colors)
    
    # Infrared colormap
    infrared_colors = ['#000033', '#000055', '#0000BB', '#0E4C92', '#5899DA', '#F5B800', '#FFE74C', '#FFFFFF']
    custom_cmaps['infrared'] = LinearSegmentedColormap.from_list('infrared', infrared_colors)
    
    return custom_cmaps


def add_experimental_to_colormaps():
    """Add experimental colormaps to matplotlib"""
    exp_cmaps = create_experimental_colormaps()
    
    for name, cmap in exp_cmaps.items():
        # Register with matplotlib
        plt.register_cmap(name=name, cmap=cmap)
        
        # Also make available through plt.cm
        setattr(plt.cm, name, cmap)
    
    print(f"✨ Registered {len(exp_cmaps)} experimental colormaps")
    return exp_cmaps


if __name__ == "__main__":
    # Register colormaps when module is imported
    add_experimental_to_colormaps()
