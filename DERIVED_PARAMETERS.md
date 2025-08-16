# HRRR Derived Parameters Documentation

This document provides a comprehensive overview of all derived meteorological parameters calculated in the HRRR map project, including their formulas, inputs, and operational interpretations.

## Overview

The HRRR map project implements **70+ derived parameters** across multiple meteorological categories:
- **Severe Weather Indices** (SCP, STP, EHI, SHIP, etc.)
- **Wind Shear Calculations** (0-1km, 0-6km bulk shear)
- **Thermodynamic Parameters** (CAPE/CIN variants, stability indices)
- **Heat Stress Indices** (WBGT variants, wet bulb temperature)
- **Fire Weather Parameters** (Haines Index, ventilation rate)
- **Specialized Research Parameters** (VTP, MSP, etc.)

---

## Core Severe Weather Parameters

### Supercell Composite Parameter (SCP)
**Formula:** `SCP = (muCAPE/1000) × (ESRH/50) × shear_term × CIN_weight`

**Inputs:**
- `mucape`: Most-Unstable CAPE (J/kg) - HRRR field MUCAPE
- `effective_srh`: Effective Storm Relative Helicity (m²/s²) - HRRR field ESRHL  
- `effective_shear`: Effective Bulk Wind Difference (m/s) - derived parameter
- `mucin`: Most-Unstable CIN (J/kg, negative) - HRRR field MUCIN [optional]

**Implementation Details:**
- **Shear Term:** SPC-compliant piecewise scaling
  - 0 when EBWD < 10 m/s
  - Linear (EBWD-10)/10 for 10-20 m/s
  - 1.0 when EBWD ≥ 20 m/s
- **CIN Weight:** Official SPC two-part gate
  - 1.0 when muCIN > -40 J/kg (weak inhibition)
  - -40/muCIN otherwise (proportional penalty)

**File:** `derived_params/supercell_composite_parameter.py:3`

**Interpretation:** SCP > 1 indicates supercell potential. Values > 10 indicate extreme overlap conditions.

---

### Significant Tornado Parameter (STP)
**Formula:** `STP = (MLCAPE/1500) × (ESRH/150) × (EBWD/12) × ((2000-MLLCL)/1000) × ((MLCIN+200)/150)`

**Inputs:**
- `mlcape`: Mixed Layer CAPE (J/kg)
- `mlcin`: Mixed Layer CIN (J/kg, negative values)
- `srh_01km`: 0-1 km Storm Relative Helicity (m²/s²)
- `shear_06km`: 0-6 km bulk wind shear magnitude (m/s)
- `lcl_height`: Mixed Layer LCL height (m AGL)

**Implementation Details:**
- **LCL Term:** (2000-LCL)/1000 with clipping
  - LCL < 1000m → 1.0 (extremely favorable)
  - LCL > 2000m → 0.0 (unfavorable, high cloud base)
- **Shear Term:** < 12.5 m/s → 0, > 30 m/s → cap at 1.5
- **CIN Term:** MLCIN > -50 → 1.0, MLCIN < -200 → 0.0

**File:** `derived_params/significant_tornado_parameter.py:3`

**Interpretation:** STP > 1 indicates heightened EF2+ tornado risk. Values 4-8+ indicate extreme outbreak potential.

---

### Energy-Helicity Index (EHI)
**Formula:** `EHI = (CAPE/1600) × (SRH/50) × damping_factor`

**Inputs:**
- `cape`: CAPE (J/kg) - surface-based or mixed-layer
- `srh_03km`: 0-3 km Storm Relative Helicity (m²/s²) - preserves sign

**Implementation Details:**
- **Anti-saturation damping:** Prevents "red sea" oversaturation
- **Damping threshold:** 5.0
- **Exponential compression:** `threshold + log(ehi_abs/threshold)` for extreme values
- **Sign preservation:** Positive = right-moving, negative = left-moving

**File:** `derived_params/energy_helicity_index.py:3`

**Interpretation:** EHI > 2 = significant tornado potential, > 5 = extreme. Sign indicates storm motion preference.

---

### Significant Hail Parameter (SHIP)
**Formula:** `SHIP = (muCAPE/1500) × (MU_mr/13.6) × (lapse_700_500/7) × (shear_06km/20) × ((frz_lvl-T500_hgt)/8)`

**Inputs:**
- `mucape`: Most-Unstable CAPE (J/kg) - HRRR field MUCAPE
- `mucin`: Most-Unstable CIN (J/kg, negative) - HRRR field MUCIN
- `lapse_rate_700_500`: 700-500mb lapse rate (°C/km) - derived parameter
- `wind_shear_06km`: 0-6km bulk shear magnitude (m/s) - derived parameter
- `freezing_level`: Freezing level height (m AGL) - HRRR field HGTFZLV
- `temp_500`: 500mb temperature (°C) - HRRR field T at 500mb
- `mixing_ratio_2m`: 2m mixing ratio (g/kg) - approximation for MU mixing ratio

**Implementation Details:**
- **All terms capped at 1.0** per SPC guidelines
- **SPC v1.1 specification** compliance
- **2m mixing ratio** used as proxy for MU mixing ratio (operational approximation)

**File:** `derived_params/significant_hail_parameter.py:4`

**Interpretation:** SHIP > 1 = significant hail potential (≥2"), SHIP > 4 = extremely high potential.

---

## Wind Shear Calculations

### Wind Shear Magnitude
**Formula:** `magnitude = sqrt(u_component² + v_component²)`

**Inputs:**
- `u_component`: U component of bulk shear (m/s)
- `v_component`: V component of bulk shear (m/s)

**File:** `derived_params/wind_shear_magnitude.py:3`

**Applied to:**
- 0-1km bulk shear (low-level shear for tornado potential)
- 0-6km bulk shear (deep-layer shear for supercells)

---

## Thermodynamic Parameters

### Wet Bulb Temperature
**Implementation:** Robust bisection method with fallback approximation

**Inputs:**
- `temp_2m`: 2m temperature
- `dewpoint_2m`: 2m dewpoint temperature  
- `pressure`: Surface pressure (auto-detects Pa/hPa)

**Method:**
1. **Primary:** Iterative bisection via psychrometrics
2. **Fallback:** Fast approximation if bisection fails
3. **Quality control:** Switches to fallback if >20% NaN values

**File:** `derived_params/wet_bulb_temperature.py:7`

---

### CAPE/CIN Backup Calculations
**Purpose:** Provide CAPE/CIN when direct HRRR fields unavailable

**Variants:**
- **Surface-Based CAPE/CIN** (`calculate_surface_based_cape.py`)
- **Mixed-Layer CAPE/CIN** (`calculate_mixed_layer_cape.py`)  
- **Most-Unstable CAPE** (`calculate_most_unstable_cape.py`)

**Common Inputs:**
- `t2m`: 2m temperature
- `d2m`: 2m dewpoint
- `surface_pressure`: Surface pressure

---

## Stability Indices

### Lifted Index (LI)
**Formula:** `LI = T500_environment - T500_parcel`

**Surface-based parcel lifted to 500mb compared to environmental temperature**

**Inputs:**
- `t2m`: 2m temperature (surface parcel)
- `d2m`: 2m dewpoint (surface parcel moisture)
- `temp_500`: 500mb environmental temperature

**File:** `derived_params/lifted_index.py`

**Interpretation:** 
- LI > 0: Stable atmosphere
- LI 0 to -3: Marginal instability
- LI -3 to -6: Moderate instability
- LI < -6: Extremely unstable

---

### Showalter Index (SI)
**Formula:** `SI = T500_environment - T500_parcel_from_850mb`

**Similar to LI but uses 850mb parcel instead of surface parcel**

**Inputs:**
- `temp_850mb`: Temperature at 850mb (K)
- `dewpoint_850mb`: Dewpoint at 850mb (K)
- `temp_500mb`: Environmental temperature at 500mb (K)

**Implementation Details:**
- **Parcel lift:** Simplified adiabatic ascent from 850mb to 500mb
- **Lapse rate:** 6.5°C per 3.5km (approximate)
- **Moisture adjustment:** (T850 - Td850) × 0.1 added to parcel temperature
- **Unit conversion:** K to °C throughout calculation

**File:** `derived_params/showalter_index.py:3`

**Interpretation:**
- SI > 0: Stable
- SI 0 to -3: Moderately unstable
- SI < -6: Extremely unstable

---

### SWEAT Index
**Formula:** `SWEAT = 12×TT + 20×max(TT-49,0) + WS850_term + WS500_term + WD_term`

**Severe Weather Threat Index combining stability, moisture, and wind dynamics**

**Inputs:**
- `temp_850`: 850mb temperature (°C)
- `temp_500`: 500mb temperature (°C)
- `dewpoint_850`: 850mb dewpoint (°C)
- `u_850`, `v_850`: 850mb wind components (m/s)
- `u_500`, `v_500`: 500mb wind components (m/s)

**Implementation Details:**
- **Total Totals (TT):** T850 + Td850 - 2×T500
- **Wind speed terms:**
  - WS850_term = 12.5 × (wspd_850 - 15) if wspd_850 > 15, else 0
  - WS500_term = 2 × (wspd_500 - 15) if wspd_500 > 15, else 0
- **Wind direction term:** Only applies when:
  - 850mb wind from SW quadrant (130°-250°)
  - 500mb wind from SW quadrant (210°-310°)
  - Wind speeds ≥ 15 m/s at both levels
  - Positive directional shear
  - Formula: 125 × (sin(directional_difference) + 0.2)

**File:** `derived_params/sweat_index.py:3`

**Interpretation:** Higher values indicate greater severe weather potential. SWEAT > 300 suggests significant severe weather threat.

---

### Cross Totals
**Formula:** `CT = Td850 - T500`

**Simple moisture-instability index**

**Inputs:**
- `temp_850`: 850mb temperature (°C)
- `dewpoint_850`: 850mb dewpoint (°C)
- `temp_500`: 500mb temperature (°C)

**File:** `derived_params/cross_totals.py:3`

**Interpretation:** Higher values indicate greater instability. CT > 18 suggests thunderstorm potential.

---

### Bulk Richardson Number (BRN)
**Formula:** `BRN = CAPE / (0.5 × ΔV²)`

**Compares instability to vertical wind shear for storm organization assessment**

**Inputs:**
- `cape`: CAPE (J/kg) - instability measure
- `wind_shear`: Bulk wind shear magnitude (m/s) - typically 0-6km layer

**Implementation Details:**
- **Shear term:** 0.5 × max(shear², 1.0²) (minimum 1 m/s to avoid division by zero)
- **Zero CAPE handling:** BRN = 0 when CAPE ≤ 0
- **Display cap:** Maximum BRN = 999 to prevent unrealistic values from near-zero shear

**File:** `derived_params/bulk_richardson_number.py:3`

**Interpretation:**
- BRN < 10: Extreme shear (storms may struggle to organize)
- BRN 10-45: Optimal balance for supercells
- BRN > 50: Weak shear (pulse/multicell storms favored)

---

### Lapse Rate (700-500mb)
**Formula:** `LR = (T700 - T500) / height_difference × 1000`

**Mid-level atmospheric lapse rate for instability assessment**

**Inputs:**
- `temp_700`: 700mb temperature (°C)
- `temp_500`: 500mb temperature (°C)

**Implementation Details:**
- **Height difference:** Approximate 2km between 700mb and 500mb levels
- **Units:** °C/km
- **Typical values:** 5.0-10.0°C/km

**File:** `derived_params/calculate_lapse_rate_700_500.py`

**Usage:** Critical component for SHIP calculation (normalized by 7°C/km)

**Interpretation:** Higher values indicate steeper lapse rates and greater instability potential.

---

## Heat Stress Indices

### WBGT (Wet Bulb Globe Temperature)
**Variants:**
1. **WBGT Shade:** `WBGT = 0.7×WB + 0.3×DB`
2. **WBGT Estimated Outdoor:** Includes solar load and wind cooling effects

**Inputs:**
- `wet_bulb_temp`: Wet bulb temperature (derived)
- `t2m`: 2m dry bulb temperature
- `wind_speed_10m`: 10m wind speed [outdoor variant]

**Files:**
- `derived_params/wbgt_shade.py`
- `derived_params/wbgt_estimated_outdoor.py`

---

## Fire Weather Parameters

### Haines Index
**Formula:** `HI = A + B` where A = stability term, B = moisture term

**Fire weather assessment combining mid-level stability and moisture**

**Inputs:**
- `temp_850`: 850mb temperature (°C)
- `temp_700`: 700mb temperature (°C)
- `dewpoint_850`: 850mb dewpoint (°C)
- `dewpoint_700`: 700mb dewpoint (°C)

**Implementation Details:**
- **Stability term (A):** Based on T850 - T700
  - A = 1 if stability < 4°C
  - A = 2 if 4°C ≤ stability < 8°C
  - A = 3 if stability ≥ 8°C
- **Moisture term (B):** Based on T850 - Td850 (dewpoint depression)
  - B = 1 if moisture < 6°C
  - B = 2 if 6°C ≤ moisture < 10°C  
  - B = 3 if moisture ≥ 10°C
- **Range:** 2-6 scale (minimum HI = 2, maximum HI = 6)

**File:** `derived_params/haines_index.py:3`

**Interpretation:** Higher values indicate greater fire weather potential. HI ≥ 4 suggests increased fire activity potential.

---

### Ventilation Rate
**Formula:** `VR = wind_speed × boundary_layer_height`

**Atmospheric capacity for smoke/pollutant dilution**

**Inputs:**
- `u10`, `v10`: 10m wind components (m/s)
- `pbl_height`: Boundary layer height (m)

**Implementation Details:**
- **Wind speed:** magnitude = sqrt(u10² + v10²)
- **Units:** m²/s (mixing volume rate)
- **Typical values:** 1,000-150,000 m²/s

**File:** `derived_params/ventilation_rate_from_components.py`

**Interpretation:** Higher values indicate better atmospheric mixing and smoke dispersion capacity.

---

### Enhanced Smoke Dispersion Index (ESDI)
**Formula:** `ESDI = shear_factor × stability_factor × bl_factor × wind_factor`

**Comprehensive smoke dispersion assessment incorporating multiple atmospheric factors**

**Inputs:**
- `wind_shear`: Wind shear (s⁻¹ or auto-converted from m/s)
- `stability`: Atmospheric stability parameter
- `boundary_layer_height`: Boundary layer height (m)
- `wind_speed`: Wind speed (m/s)

**Implementation Details:**
- **Shear factor:** min(shear_s × 100, 2.0) with auto unit conversion
- **Stability factor:** 
  - 2.0 for unstable (stability < -0.1)
  - 0.5 for stable (stability > 0.1)
  - 1.0 for neutral conditions
- **Boundary layer factor:** clip(BL_height/1500, 0.1, 2.0)
- **Wind factor:** clip(wind_speed/10, 0.1, 2.0)
- **Minimum dispersion:** 0.1 even in stable conditions
- **Range:** 0.1-10.0

**Variants:**
- **Standard:** `enhanced_smoke_dispersion_index.py:3`
- **Simplified:** Uses temperature as stability proxy (`enhanced_smoke_dispersion_index_simplified.py:3`)
- **From Components:** Calculates from wind/shear components (`enhanced_smoke_dispersion_index_from_components.py:3`)

**Interpretation:** Higher values indicate better smoke dispersion conditions. Values < 1 suggest poor dispersion.

---

## Specialized Research Parameters

### Violent Tornado Parameter (VTP)
**Formula:** `VTP = (MLCAPE/1500) × (EBWD/20) × (ESRH/150) × ((2000-MLLCL)/1000) × ((200+MLCIN)/150) × (0-3km MLCAPE/50) × (0-3km Lapse Rate/6.5)`

**Advanced tornado parameter** following Hampshire et al. (2018) formulation with SPC scaling

**Inputs:**
- `mlcape`: Mixed Layer CAPE (J/kg) - use HRRR 180-0mb or compute 100mb parcel
- `mlcin`: Mixed Layer CIN (J/kg, negative values)
- `lcl_height`: Mixed Layer LCL height (m AGL)
- `storm_relative_helicity_03km`: 0-3km SRH (m²/s²) from HRRR or computed
- `wind_shear_06km`: 0-6km bulk wind shear magnitude (m/s)
- `cape_03km`: 0-3km MLCAPE (J/kg) - prefer proper parcel calculation
- `lapse_rate_03km`: 0-3km environmental lapse rate (°C/km)

**Implementation Details:**
- **Effective-layer gate:** Balanced for realistic environments
  - MLCAPE ≥ 100 J/kg
  - MLCIN ≥ -150 J/kg (allows moderate caps)
  - LCL height ≤ 2000m
- **Term scaling with SPC caps:**
  - CAPE term: MLCAPE/1500, soft cap at 2.0
  - LCL term: (2000-MLLCL)/1000, clipped 0-1
  - Shear term: EBWD/20, zero below 12.5 m/s, cap at 1.5 above 30 m/s
  - CIN term: (MLCIN+200)/150, clipped 0-1
  - 0-3km CAPE term: cape_03km/50, cap at 2.0, zero below 25 J/kg
  - SRH term: ESRH/150, soft cap at 4.0 (600 m²/s²)
  - Lapse term: lapse_03km/6.5, cap at 2.0, override to 2.0 when cape_03km ≥ 200 J/kg
- **Hard ceiling:** VTP clipped to maximum 8.0
- **Quality control:** Zero output for any invalid critical inputs

**File:** `derived_params/violent_tornado_parameter.py:3`

**Interpretation:** VTP > 1 indicates violent tornado potential. Values > 4 suggest extreme tornado environments.

---

### Mesocyclone Strength Parameter (MSP)
**Formula:** `MSP = (UH/100) × enhancement_factors`

**Assesses mesocyclone intensity using updraft helicity and optional enhancement factors**

**Inputs:**
- `updraft_helicity`: Updraft helicity (m²/s²) - primary strength indicator
- `vertical_velocity`: Vertical velocity (m/s) - optional enhancement
- `shear_magnitude`: Wind shear magnitude (m/s) - optional enhancement

**Implementation Details:**
- **Base strength:** UH/100 with cap at 3.0
- **Vertical velocity enhancement:** (1 + 0.5 × w_factor) where w_factor = min(max(w,0)/20, 1.5)
- **Shear enhancement:** shear_factor = min(shear/25, 1.2)
- **Multiplicative enhancement:** strength *= (1 + 0.5 × w_factor) × shear_factor

**File:** `derived_params/mesocyclone_strength_parameter.py:3`

**Interpretation:** Higher values indicate stronger mesocyclone potential. Enhanced when strong updrafts and shear coincide.

---

### Vorticity Generation Parameter (VGP)
**Formula:** `VGP = (CAPE/1000) × (shear_01km/1000) × 0.1`

**Estimates rate of vorticity generation from horizontal vorticity through tilting and stretching**

**Inputs:**
- `cape`: CAPE (J/kg) - provides updraft strength for vorticity stretching
- `wind_shear_01km`: 0-1km wind shear magnitude (m/s) - source of horizontal vorticity

**Implementation Details:**
- **Vorticity approximation:** shear/1000 (shear over 1km depth)
- **Scaling factor:** 0.1 to produce meaningful values in m/s²
- **Physical basis:** VGP ∝ CAPE × low-level vorticity

**File:** `derived_params/vorticity_generation_parameter.py:3`

**Interpretation:** 
- VGP > 0.2 m/s²: Increased tornado potential from vorticity stretching
- VGP > 0.5 m/s²: High tornado potential

---

## Additional Composite Parameters

### Craven Significant Severe Parameter
**Formula:** `Craven SigSvr = MLCAPE × Shear_06km`

**Simple multiplicative parameter for significant severe weather assessment**

**Inputs:**
- `mlcape`: Mixed Layer CAPE (J/kg)
- `wind_shear_06km`: 0-6km bulk wind shear magnitude (m/s)

**File:** `derived_params/craven_significant_severe.py`

**Interpretation:** Values > 20,000 m³/s³ indicate significant severe weather potential.

---

### Craven-Brooks Composite
**Formula:** `CBC = 0.4×(CAPE/1000) + 0.4×(Shear/20) + 0.2×(SRH/200)`

**Weighted composite of CAPE, shear, and helicity**

**Inputs:**
- `cape`: CAPE (J/kg)
- `shear_06km`: 0-6km bulk wind shear (m/s)
- `srh_03km`: 0-3km storm relative helicity (m²/s²)

**Implementation Details:**
- **Normalization factors:** CAPE/1000, Shear/20, SRH/200
- **Weights:** 40% CAPE, 40% shear, 20% helicity
- **Output:** Dimensionless composite index

**File:** `derived_params/craven_brooks_composite.py:3`

**Interpretation:** Higher values indicate better overall severe weather environment.

---

### Composite Severe Index
**Multi-parameter severe weather diagnostic**

**Inputs:**
- `scp`: Supercell Composite Parameter
- `stp`: Significant Tornado Parameter
- `updraft_helicity`: Updraft helicity

**File:** `derived_params/composite_severe_index.py`

**Purpose:** Combines multiple severe weather indices for comprehensive assessment.

---

## Additional Wind Parameters

### Effective Storm Relative Helicity
**Helicity calculated using effective layer depths based on parcel characteristics**

**Inputs:**
- `srh_03km`: 0-3km Storm Relative Helicity
- `mlcape`: Mixed Layer CAPE
- `mlcin`: Mixed Layer CIN
- `lcl_height`: LCL height

**File:** `derived_params/effective_srh.py`

**Purpose:** More precise helicity calculation for capped environments.

---

### Effective Bulk Wind Difference
**Shear calculated using effective layer depths**

**Inputs:**
- `wind_shear_06km`: 0-6km bulk wind shear
- `mlcape`: Mixed Layer CAPE
- `mlcin`: Mixed Layer CIN

**File:** `derived_params/effective_shear.py`

**Purpose:** Adjusts shear calculation for convective environment characteristics.

---

### Wind Shear Vector Components
**Vector-based shear calculations preserving directional information**

**Files:**
- `derived_params/wind_shear_vector_01km.py` - 0-1km vector shear
- `derived_params/wind_shear_vector_06km.py` - 0-6km vector shear

**Purpose:** Maintains full vector information for advanced shear analysis.

---

### Updraft Helicity Threshold
**Binary tornado risk indicator based on updraft helicity**

**Inputs:**
- `updraft_helicity`: Updraft helicity (m²/s²)
- `threshold`: Threshold value (default 75.0)

**File:** `derived_params/updraft_helicity_threshold.py`

**Output:** Binary field (0/1) indicating areas exceeding threshold.

---

## Surface and Boundary Layer Parameters

### Surface Richardson Number
**Near-surface stability assessment**

**File:** `derived_params/surface_richardson_number.py`

### Monin-Obukhov Length
**Boundary layer stability scale**

**File:** `derived_params/monin_obukhov_length.py`

### Convective Velocity Scale
**Boundary layer convective intensity**

**File:** `derived_params/convective_velocity_scale.py`

### Turbulent Kinetic Energy Estimate
**Atmospheric turbulence assessment**

**File:** `derived_params/turbulent_kinetic_energy_estimate.py`

---

## Specialized Variants and Utilities

### STP Variants
- **STP (CIN Version):** `significant_tornado_parameter_cin.py`
- **STP (Effective):** `significant_tornado_parameter_effective.py`
- **STP (Fixed):** `significant_tornado_parameter_fixed.py`

### SCP Variants
- **SCP (Effective):** `supercell_composite_parameter_effective.py`

### Modified Parameters
- **Modified STP Effective:** `modified_stp_effective.py`
- **Right-Mover Supercell Composite:** `right_mover_supercell_composite.py`
- **Supercell Strength Index:** `supercell_strength_index.py`

### Internal Calculation Utilities
- **Saturation Vapor Pressure:** `_calculate_saturation_vapor_pressure.py`
- **Virtual Temperature:** `_calculate_virtual_temperature.py`
- **LCL (Bolton):** `_find_lcl_bolton.py`
- **Moist Adiabatic Temperature:** `_moist_adiabatic_temperature.py`
- **Psychrometrics:** `_psychrometrics.py`
- **Mixing Ratio Approximation:** `_mixing_ratio_approximation.py`
- **Wet Bulb Approximation:** `_wet_bulb_approximation.py`

---

## Implementation Architecture

### Dispatch System
All derived parameters are managed through a centralized dispatch system in `derived_params/__init__.py`:

```python
_DERIVED_FUNCTIONS = {
    'supercell_composite_parameter': supercell_composite_parameter,
    'significant_tornado_parameter': significant_tornado_parameter,
    # ... 70+ functions
}

def compute_derived_parameter(param_name, input_data, config):
    function_name = config['function']
    func = _DERIVED_FUNCTIONS[function_name]
    return func(*args, **kwargs)
```

### Configuration System
Parameter metadata stored in `parameters/derived.json` with:
- **Calculation function** and required inputs
- **Visualization settings** (colormap, levels, units)
- **Operational thresholds** and interpretation guidelines
- **Category classification** (severe, heat, fire, etc.)

### Quality Control
All derived parameters implement:
- **Input validation** and masking of invalid data
- **Extreme value detection** and logging
- **Physical bounds** enforcement
- **Missing data handling** with appropriate fallbacks

---

## File Organization

```
derived_params/
├── __init__.py                 # Central dispatch and configuration
├── common.py                   # Shared utilities and helper functions
│
├── # SEVERE WEATHER CORE
├── supercell_composite_parameter.py
├── significant_tornado_parameter.py  
├── energy_helicity_index.py
├── significant_hail_parameter.py
│
├── # WIND SHEAR
├── wind_shear_magnitude.py
├── effective_shear.py
├── effective_srh.py
│
├── # THERMODYNAMICS  
├── wet_bulb_temperature.py
├── calculate_*_cape.py         # CAPE/CIN backup calculations
├── lifted_index.py
├── calculate_lapse_rate_700_500.py
│
├── # HEAT STRESS
├── wbgt_*.py                   # WBGT variants
├── mixing_ratio_2m.py
│
├── # FIRE WEATHER
├── haines_index.py
├── ventilation_rate*.py
├── enhanced_smoke_dispersion_index*.py
│
├── # RESEARCH PARAMETERS
├── violent_tornado_parameter.py
├── mesocyclone_strength_parameter.py
├── vorticity_generation_parameter.py
│
└── # INTERNAL UTILITIES
    ├── _psychrometrics.py      # Thermodynamic calculations
    ├── _wet_bulb_approximation.py
    ├── _calculate_*.py         # Helper calculation functions
    └── _*.py                   # Internal utilities
```

This comprehensive system enables real-time calculation of advanced meteorological parameters for severe weather analysis, heat stress monitoring, fire weather assessment, and atmospheric research applications.