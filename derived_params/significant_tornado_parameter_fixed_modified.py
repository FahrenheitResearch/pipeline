from .common import *

def significant_tornado_parameter_fixed_modified(mlcape: np.ndarray, mlcin: np.ndarray,
                                                srh_01km: np.ndarray, shear_06km: np.ndarray,
                                                lcl_height: np.ndarray) -> np.ndarray:
    """
    Compute Significant Tornado Parameter (STP) - Fixed Layer Version with CIN (MODIFIED)
    
    STP_fixed_modified = (MLCAPE/1500) × (SRH_01km/150) × (BWD_06km/12) × ((2000-MLLCL)/1000) × ((MLCIN+200)/150)
    
    Status: 🟡 Modified (not SPC canonical)
    
    This is a PROJECT-SPECIFIC VARIANT that mixes fixed layers with CIN term.
    Pure SPC implementations use either:
    - Fixed layers WITHOUT CIN term (see significant_tornado_parameter_fixed)
    - Effective layers WITH CIN term (see significant_tornado_parameter_effective)
    
    This variant adds the CIN term to the fixed-layer approach, which may be
    useful for operational applications but is not the canonical SPC definition.
    
    Args:
        mlcape: Mixed Layer CAPE (J/kg)
        mlcin: Mixed Layer CIN (J/kg, negative values)
        srh_01km: 0-1 km Storm Relative Helicity (m²/s²) - FIXED LAYER
        shear_06km: 0-6 km bulk wind shear magnitude (m/s) - FIXED LAYER
        lcl_height: Mixed Layer LCL height (m AGL)
        
    Returns:
        STP values (dimensionless, always ≥ 0)
        
    References:
        Based on Thompson et al. (2003) fixed layers + Thompson et al. (2012) CIN term
        Note: This specific combination is a project modification
    """
    # 1. CAPE term: MLCAPE/1500 (no arbitrary cap - let physics decide)
    cape_term = np.maximum(mlcape / 1500.0, 0)
    
    # 2. LCL term: (2000-LCL)/1000 with proper clipping
    # LCL < 1000m → 1.0 (extremely favorable)
    # LCL > 2000m → 0.0 (unfavorable, high cloud base)
    lcl_term = np.where(lcl_height < 1000, 1.0,
                       np.where(lcl_height > 2000, 0.0,
                               (2000 - lcl_height) / 1000.0))
    
    # 3. SRH term: 0-1km SRH/150 (preserve sign for left-moving detection)
    srh_term = np.maximum(srh_01km / 150.0, 0)
    
    # 4. Shear term: EBWD/12 m/s with SPC clipping
    # < 12.5 m/s (25 kt) → 0 (insufficient shear)
    # > 30 m/s (60 kt) → cap at 1.5 (diminishing returns)
    shear_term = np.where(shear_06km < 12.5, 0,
                         np.where(shear_06km > 30, 1.5, shear_06km / 12.0))
    
    # 5. CIN term: (MLCIN + 200)/150 - Official SPC formula
    # MLCIN > -50 J/kg → 1.0 (weak/no cap)
    # MLCIN = -200 J/kg → 0.0 (strong cap kills tornado potential)
    # MLCIN < -200 J/kg → 0.0 (very strong cap)
    cin_term = np.where(mlcin > -50, 1.0,
                       np.where(mlcin < -200, 0.0,
                               np.maximum((mlcin + 200) / 150.0, 0.0)))
    
    # STP calculation (multiplicative - any weak ingredient reduces total)
    stp = cape_term * lcl_term * srh_term * shear_term * cin_term
    
    # Zero out where CAPE is too low for convection
    stp = np.where(mlcape < 100, 0, stp)
    
    # Ensure STP is never negative (should not happen with proper clipping)
    stp = np.maximum(stp, 0.0)
    
    # Mask invalid input data
    stp = np.where((mlcape < 0) | (np.isnan(mlcape)) | (np.isnan(mlcin)) |
                  (np.isnan(srh_01km)) | (shear_06km < 0) | (np.isnan(shear_06km)) |
                  (lcl_height < 0) | (np.isnan(lcl_height)), 
                  np.nan, stp)
    
    return stp
