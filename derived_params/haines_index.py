from .common import *

def haines_index(temp_850: np.ndarray, temp_700: np.ndarray,
                dewpoint_850: np.ndarray, dewpoint_700: np.ndarray) -> np.ndarray:
    """
    Compute Haines Index for fire weather (MID-LEVEL VARIANT)
    
    ⚠️ DEPRECATION NOTICE: The National Weather Service discontinued the use of
    Haines Index in operational fire weather forecasts as of December 20, 2024
    (Service Change Notice 24-107). Consider using modern alternatives:
    - Hot-Dry-Windy Index (HDW)
    - Vapor Pressure Deficit (VPD)
    - Fire Weather Index (FWI) System
    
    This implementation provides the mid-level variant (850-700mb) suitable for
    elevations 1000-4000 ft. Other variants exist:
    - Low-level (950-850mb): Below 1000 ft elevation
    - High-level (700-500mb): Above 4000 ft elevation
    
    Args:
        temp_850: 850mb temperature (°C)
        temp_700: 700mb temperature (°C)
        dewpoint_850: 850mb dewpoint (°C)
        dewpoint_700: 700mb dewpoint (°C)
        
    Returns:
        Haines Index (2-6 scale) - MID-LEVEL VARIANT ONLY
        
    Reference:
        Haines, D.A., 1988: A lower atmosphere severity index for wildland fires.
        NWS SCN 24-107 (Dec 2024): Discontinuation of Haines Index
    """
    # Stability term (A)
    stability = temp_850 - temp_700
    A = np.where(stability < 4, 1,
                np.where(stability < 8, 2, 3))
    
    # Moisture term (B)  
    moisture = temp_850 - dewpoint_850
    B = np.where(moisture < 6, 1,
                np.where(moisture < 10, 2, 3))
    
    haines = A + B
    
    return np.clip(haines, 2, 6)
