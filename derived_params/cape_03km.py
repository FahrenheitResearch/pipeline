from .common import *

def cape_03km(mlcape: np.ndarray, cape_profile: np.ndarray = None) -> np.ndarray:
    """
    Compute 0-3 km MLCAPE - APPROXIMATION METHOD
    
    ⚠️ IMPORTANT: This is a HEURISTIC APPROXIMATION, not a true calculation.
    True 0-3km CAPE requires vertical integration of positive buoyancy from 
    surface to 3km AGL. This function uses empirical fractions of total CAPE.
    
    For accurate 0-3km CAPE:
    1. Use HRRR direct output if available (e.g., CAPE:300-0 mb above ground)
    2. Compute from full thermodynamic profile using proper parcel theory
    3. Use tools like MetPy, SHARPpy, or similar for vertical integration
    
    This approximation is based on climatological ratios where 0-3km CAPE
    typically represents 10-30% of total CAPE, with lower fractions for
    higher total CAPE values.
    
    Args:
        mlcape: Mixed-Layer CAPE (J/kg)
        cape_profile: Full CAPE profile (if available) - NOT CURRENTLY USED
        
    Returns:
        0-3 km MLCAPE approximation (J/kg) - EMPIRICAL ESTIMATE ONLY
        
    Warning:
        This approximation can have errors of ±50% or more. Do not use for
        critical applications requiring accurate low-level buoyancy assessment.
    """
    # More realistic approximation based on meteorological studies:
    # 0-3km CAPE is typically 10-30% of total CAPE, with diminishing returns for high CAPE
    
    # Apply scaling with realistic caps
    cape_fraction = np.where(
        mlcape < 1000,     # Low CAPE: higher fraction (surface dominant)
        0.25,
        np.where(
            mlcape < 3000, # Moderate CAPE: decreasing fraction
            0.20,
            0.15           # High CAPE: lower fraction (more aloft)
        )
    )
    
    cape_03km = mlcape * cape_fraction
    
    # Apply realistic caps for 0-3km CAPE based on literature
    cape_03km = np.clip(cape_03km, 0, 600)  # Very rarely exceeds 600 J/kg
    
    # Quality control - warn if high values
    max_cape_03km = np.nanmax(cape_03km) if cape_03km.size > 0 else 0
    if max_cape_03km > 400:
        print(f"🔍 0-3km CAPE max: {max_cape_03km:.0f} J/kg (high for low-level CAPE)")
    
    return cape_03km
