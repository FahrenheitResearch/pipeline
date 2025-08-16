from .common import *

def wbgt_shade(wet_bulb_temp: np.ndarray, dry_bulb_temp: np.ndarray) -> np.ndarray:
    """
    Compute WBGT Approximation for shaded conditions (no solar load)
    
    WBGT_approx = 0.7 × Tw + 0.3 × Tdb
    
    NOTE: This is a simplified approximation. True WBGT requires:
    - Natural wet-bulb temperature (Tnwb) vs psychrometric wet-bulb (Tw)
    - Black globe temperature (Tg) vs dry-bulb temperature (Tdb)
    True formula: WBGT = 0.7×Tnwb + 0.3×Tg
    
    This approximation is acceptable for heat stress screening but may
    underestimate true WBGT by 1-2°C. For precise occupational health 
    assessments, use actual Tnwb and Tg measurements.
    
    Args:
        wet_bulb_temp: Psychrometric wet bulb temperature (°C) - proxy for Tnwb
        dry_bulb_temp: Dry bulb (air) temperature (°C) - proxy for Tg in shade
        
    Returns:
        WBGT approximation for shade (°C)
        
    Heat stress thresholds (for acclimatized workers, light clothing):
        > 32°C: Stop activity
        28-32°C: Extreme caution (15 min work/45 min rest)
        25-28°C: High caution (30 min work/30 min rest)
        < 25°C: Generally safe for continuous work
        
    Reference:
        ACGIH TLVs and BEIs, 2024
        ISO 7243:2017 - Ergonomics of the thermal environment
    """
    # Input validation
    if wet_bulb_temp is None or dry_bulb_temp is None:
        raise ValueError("Temperature inputs cannot be None")
    
    # WBGT calculation for shaded conditions
    wbgt = 0.7 * wet_bulb_temp + 0.3 * dry_bulb_temp
    
    # Mask invalid data
    wbgt = np.where(
        (np.isnan(wet_bulb_temp)) | (np.isnan(dry_bulb_temp)),
        np.nan, wbgt
    )
    
    return wbgt
