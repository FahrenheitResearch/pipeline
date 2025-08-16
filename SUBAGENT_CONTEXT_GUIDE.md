# LLM Subagent Context Guide - HRRR v2.2 Completion

## Project Overview
This is a meteorological parameter calculation project for HRRR (High-Resolution Rapid Refresh) weather model data. The project computes derived severe weather parameters with proper SPC (Storm Prediction Center) alignment.

## Current Status
✅ **Completed v2.2 Critical Fixes:**
- Fixed STP variants to include CIN and use EBWD/20
- Fixed EHI to provide both SPC canonical and display-scaled versions  
- Updated VGP to be dimensionless with configurable K
- Updated SWEAT with proper conditional terms
- Updated configurations to use corrected implementations

## Key File Structure
```
/home/ubuntu2/hrrr-manual-4/
├── derived_params/                    # Core parameter calculations
│   ├── __init__.py                   # Main dispatch and configuration
│   ├── common.py                     # Shared utilities and constants
│   ├── significant_tornado_parameter_*.py  # STP variants
│   ├── energy_helicity_index*.py     # EHI variants  
│   ├── supercell_composite_parameter*.py   # SCP variants
│   ├── surface_richardson_number.py  # Boundary layer physics
│   ├── convective_velocity_scale.py  # w* implementation
│   ├── ventilation_rate*.py         # Fire weather ventilation
│   ├── mixing_ratio_*.py            # Moisture calculations
│   └── bulk_richardson_number.py    # BRN shear definition
├── processor_cli.py                  # Main CLI entry point
├── field_templates.py               # Parameter configuration templates
└── DERIVED_PARAMETERS_CORRECTED.md  # Current documentation (v2.1)
```

## Remaining Tasks for v2.2

### Task D: Implement Effective-Layer Contiguous Method
**Priority: HIGH** - Affects multiple severe weather parameters

**Files to examine:**
- `/home/ubuntu2/hrrr-manual-4/derived_params/effective_srh.py`
- `/home/ubuntu2/hrrr-manual-4/derived_params/effective_shear.py`
- `/home/ubuntu2/hrrr-manual-4/derived_params/significant_tornado_parameter_effective.py`

**Current issue:** Effective layer computation may not use contiguous-layer method per SPC standards.

**Requirements:**
1. Implement contiguous inflow layer search:
   - Start from surface
   - Find contiguous layer where CAPE ≥ 100 J/kg AND CIN ≥ -250 J/kg  
   - If no contiguous layer exists, set ESRH/EBWD = 0
2. Use ML parcel definition explicitly
3. Apply CAPE/CIN thresholds per level
4. Document algorithm in docstrings

**Expected outcome:** ESRH and EBWD computed through proper contiguous effective layer.

### Task G: Fix Boundary Layer Physics (Ri with θᵥ, w* formula)
**Priority: MEDIUM** - Affects stability calculations

**Files to examine:**
- `/home/ubuntu2/hrrr-manual-4/derived_params/surface_richardson_number.py`
- `/home/ubuntu2/hrrr-manual-4/derived_params/convective_velocity_scale.py`

**Current issues:**
1. Richardson number may not use virtual potential temperature consistently
2. w* formula may be missing ρ and cp explicitly

**Requirements:**
1. **Richardson Number:**
   - Use virtual potential temperature (θᵥ) consistently 
   - Derive θᵥ profile and compute its gradient
   - Formula: Ri = (g/θᵥ)(∂θᵥ/∂z)/(∂u/∂z)²

2. **Convective Velocity Scale (w*):**
   - Include ρ and cp explicitly: w* = (gH/(ρcpθᵥ))^(1/3)
   - If ρ unavailable, compute from ideal gas law with moisture correction
   - Document defaults and their effects

**Expected outcome:** Physically consistent boundary layer calculations.

### Task H: Fix Ventilation Rate to Use Transport Wind
**Priority: MEDIUM** - Affects fire weather parameters

**Files to examine:**
- `/home/ubuntu2/hrrr-manual-4/derived_params/ventilation_rate.py`
- `/home/ubuntu2/hrrr-manual-4/derived_params/ventilation_rate_from_components.py`

**Current issue:** May use scalar mean of wind speeds instead of proper transport wind.

**Requirements:**
1. Compute transport wind as vector mean over mixed layer, then take speed
2. Formula: U_transport = |⟨**u**⟩| where ⟨**u**⟩ is vector mean
3. Provide fallback to scalar mean if vectors unavailable
4. Document methodology and fallback behavior

**Expected outcome:** Meteorologically correct ventilation rate calculation.

### Task I: Fix Mixing Ratio Nomenclature and Units
**Priority: MEDIUM** - Affects moisture-dependent parameters

**Files to examine:**
- `/home/ubuntu2/hrrr-manual-4/derived_params/mixing_ratio_2m.py`
- `/home/ubuntu2/hrrr-manual-4/derived_params/_mixing_ratio_approximation.py`

**Current issues:**
1. Inconsistent unit handling (kg/kg vs g/kg)
2. Missing input unit specifications

**Requirements:**
1. **Always state units clearly:**
   - Td in °C, P and e in hPa for 622 factor
   - Return units in docstring (kg/kg or g/kg)
2. **Provide unit conversion flag:**
   - Add parameter to return kg/kg or g/kg
   - Default to g/kg for operational consistency
3. **Input validation:**
   - Check temperature and pressure ranges
   - Document expected input units

**Expected outcome:** Clear, consistent moisture calculations with proper units.

### Task J: Clarify BRN Shear Definition  
**Priority: LOW** - Documentation clarity

**Files to examine:**
- `/home/ubuntu2/hrrr-manual-4/derived_params/bulk_richardson_number.py`

**Current issue:** Shear definition may be ambiguous.

**Requirements:**
1. Clarify that "shear" in BRN = 0-6km bulk vector wind difference magnitude (BWD06)
2. Not a mean wind or scalar difference
3. Update docstring to be explicit: BRN = CAPE / (0.5 × BWD06²)
4. Add formula and reference to proper literature

**Expected outcome:** Unambiguous BRN calculation documentation.

### Task K: Centralize Constants in Single Module
**Priority: MEDIUM** - Code organization and consistency

**Files to create/modify:**
- `/home/ubuntu2/hrrr-manual-4/derived_params/constants.py` (create)
- Update all parameter files to import from constants

**Current issue:** Constants scattered across files, risk of drift.

**Requirements:**
1. **Create constants.py with:**
   ```python
   # STP Constants
   STP_CAPE_NORM = 1500.0      # J/kg
   STP_SHEAR_NORM = 20.0       # m/s  
   STP_SRH_NORM = 150.0        # m²/s²
   
   # SHIP Constants  
   SHIP_CAPE_NORM = 1500.0     # J/kg
   SHIP_MR_NORM = 13.6         # g/kg
   SHIP_LAPSE_NORM = 7.0       # °C/km
   SHIP_SHEAR_NORM = 20.0      # m/s
   SHIP_TEMP_REF = -20.0       # °C
   
   # EHI Constants
   EHI_CAPE_NORM = 1000.0      # J/kg
   EHI_SRH_NORM = 100.0        # m²/s²
   
   # VGP Constants
   VGP_K_DEFAULT = 40.0        # Dimensionless normalization
   ```

2. **Update all parameter files** to import and use these constants
3. **Eliminate hardcoded values** scattered throughout codebase

**Expected outcome:** Centralized, consistent constants across all parameters.

### Task L: Add Comprehensive Unit Tests
**Priority: HIGH** - Quality assurance

**Files to create:**
- `/home/ubuntu2/hrrr-manual-4/tests/test_spc_alignment.py` (create)
- `/home/ubuntu2/hrrr-manual-4/tests/test_parameter_variants.py` (create)

**Requirements:**
1. **SPC Alignment Tests:**
   ```python
   def test_ehi_spc_vs_display():
       # EHI_spc with CAPE=2000, SRH=200 → 4.0
       # EHI_display with same inputs → 2.5
   
   def test_stp_fixed_includes_cin():
       # Verify STP_fixed uses 5 terms including CIN
   
   def test_scp_no_negative_values():
       # SCP with negative ESRH should be 0, not negative
   ```

2. **Effective Layer Tests:**
   ```python
   def test_effective_layer_elevated_base():
       # Test with inflow base at 1.2km AGL
       # Ensure ESRH/EBWD compute through correct layer
   ```

3. **VGP Dimensionless Test:**
   ```python
   def test_vgp_scaling():
       # Verify typical sig-tor environment produces ~0.3-0.5
   ```

4. **Constants Tests:**
   ```python
   def test_centralized_constants():
       # Verify all parameters use constants.py values
   ```

**Expected outcome:** Comprehensive test coverage ensuring SPC compliance.

### Task M: Update Documentation to v2.2
**Priority: HIGH** - User guidance and compliance record

**Files to create/modify:**
- `/home/ubuntu2/hrrr-manual-4/DERIVED_PARAMETERS_V2.2.md` (create)
- Update existing documentation

**Requirements:**
1. **Complete parameter registry** with status badges:
   - 🟢 SPC-Operational 
   - 🟡 Modified
   - 🟠 Approximation
   - 🔵 Research  
   - 🔴 Deprecated

2. **SPC vs Modified separation:**
   - Clear sections for canonical vs project-specific implementations
   - Document all normalization differences
   - Include threshold adjustments

3. **v2.2 Changelog:**
   - STP shear normalization correction (EBWD/20)
   - STP CIN restored for SPC variants
   - EHI_spc added alongside display-scaled version
   - SHIP temperature term fixed
   - Effective-layer contiguous method
   - VGP dimensionless with K parameter
   - Centralized constants

4. **Algorithm appendices:**
   - Effective-layer contiguous search algorithm
   - Boundary layer physics with θᵥ
   - Transport wind computation

**Expected outcome:** Complete, accurate v2.2 documentation reflecting all changes.

## Testing Your Work

After completing tasks, verify with:

1. **Run unit tests:** `python -m pytest tests/`
2. **Check CLI integration:** `python processor_cli.py --latest` (dry run)
3. **Validate configurations:** Check `create_derived_config()` includes new parameters
4. **Cross-reference documentation:** Ensure code matches documented formulas

## Important Notes

1. **Maintain SPC compliance** where claimed - use literature formulations exactly
2. **Label modifications clearly** - never claim SPC alignment for modified variants  
3. **Preserve backward compatibility** - keep legacy functions with deprecation warnings
4. **Document fallbacks** - clearly state when approximations are used
5. **Test edge cases** - handle missing data, extreme values, unphysical conditions

## Success Criteria

✅ All remaining tasks completed  
✅ Unit tests pass  
✅ SPC variants match literature exactly  
✅ Modified variants clearly labeled  
✅ Documentation comprehensive and accurate  
✅ Constants centralized  
✅ CLI integrates all new parameters  

This completes the v2.2 revision bringing full SPC alignment and clear separation of canonical vs modified implementations.