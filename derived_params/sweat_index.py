from .common import *

def sweat_index(temp_850: np.ndarray, temp_500: np.ndarray, 
               dewpoint_850: np.ndarray, u_850: np.ndarray, v_850: np.ndarray,
               u_500: np.ndarray, v_500: np.ndarray) -> np.ndarray:
    """
    Compute SWEAT (Severe Weather Threat) Index - Full Conditional Formula
    
    SWEAT = 12×Td850 + 20×max(TT-49,0) + 2×WS850 + WS500 + 125×(sin(DD500-DD850)+0.2)
    
    where:
        TT = Total Totals = (T850 + Td850) - 2×T500
        WS terms set to 0 if wind speed < 7.5 m/s
        Directional term set to 0 unless 130° ≤ (DD500-DD850) ≤ 250°
    
    Args:
        temp_850: 850mb temperature (°C)
        temp_500: 500mb temperature (°C)  
        dewpoint_850: 850mb dewpoint (°C)
        u_850: 850mb U wind (m/s)
        v_850: 850mb V wind (m/s)
        u_500: 500mb U wind (m/s)
        v_500: 500mb V wind (m/s)
        
    Returns:
        SWEAT index (dimensionless)
        
    References:
        Miller, R.C., 1972: Notes on analysis and severe storm forecasting 
            procedures of the Air Force Global Weather Central. AWS Tech. Rep. 200.
    """
    # Calculate wind speeds
    wspd_850 = np.sqrt(u_850**2 + v_850**2)
    wspd_500 = np.sqrt(u_500**2 + v_500**2)
    
    # Calculate wind directions (meteorological convention)
    wdir_850 = np.degrees(np.arctan2(-u_850, -v_850)) % 360
    wdir_500 = np.degrees(np.arctan2(-u_500, -v_500)) % 360
    
    # ========================================================================
    # SWEAT TERMS - Full conditional implementation
    # ========================================================================
    
    # 1. Dewpoint term: 12 × Td850
    dewpoint_term = 12.0 * dewpoint_850
    
    # 2. Total Totals term: TT = (T850 + Td850) - 2×T500
    tt = temp_850 + dewpoint_850 - 2.0 * temp_500
    tt_term = 20.0 * np.maximum(tt - 49.0, 0.0)
    
    # 3. Wind speed terms with 7.5 m/s threshold
    ws850_term = np.where(wspd_850 >= 7.5, 2.0 * wspd_850, 0.0)
    ws500_term = np.where(wspd_500 >= 7.5, wspd_500, 0.0)
    
    # 4. Directional shear term with full conditional logic
    # Calculate directional difference (DD500 - DD850)
    dd_diff = (wdir_500 - wdir_850) % 360
    
    # Apply all conditional requirements:
    # - 130° ≤ directional difference ≤ 250°
    # - Both wind speeds ≥ 7.5 m/s
    directional_gate = (
        (dd_diff >= 130.0) & (dd_diff <= 250.0) &
        (wspd_850 >= 7.5) & (wspd_500 >= 7.5)
    )
    
    # Convert to radians for sin calculation
    dd_diff_rad = np.radians(dd_diff)
    wd_term = np.where(
        directional_gate,
        125.0 * (np.sin(dd_diff_rad) + 0.2),
        0.0
    )
    
    # ========================================================================
    # FINAL SWEAT CALCULATION
    # ========================================================================
    sweat = dewpoint_term + tt_term + ws850_term + ws500_term + wd_term
    
    # Ensure SWEAT is never negative
    sweat = np.maximum(sweat, 0.0)
    
    # Mask invalid input data
    sweat = np.where(
        (np.isnan(temp_850)) | (np.isnan(temp_500)) | (np.isnan(dewpoint_850)) |
        (np.isnan(u_850)) | (np.isnan(v_850)) | (np.isnan(u_500)) | (np.isnan(v_500)),
        np.nan, sweat
    )
    
    return sweat
