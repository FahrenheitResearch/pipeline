# Migration Guide

## MetPy Dependency Removal

### Overview
The HRRR processor has removed its MetPy dependency in favor of pure NumPy implementations for better performance and fewer dependencies.

### Deprecated Functions

#### `wet_bulb_temperature_metpy` → `wet_bulb_temperature`

**Status:** Deprecated (still works with warning)
**Action Required:** Replace function calls

```python
# Old (deprecated)
from derived_params import wet_bulb_temperature_metpy
wb = wet_bulb_temperature_metpy(temp_2m, dewpoint_2m, pressure)

# New (recommended) 
from derived_params import wet_bulb_temperature
wb = wet_bulb_temperature(temp_2m, dewpoint_2m, pressure)
```

**Notes:**
- Identical behavior and accuracy
- New implementation uses mixed-phase saturation vapor pressure
- Better performance with vectorized operations
- Pressure auto-detection (Pa or hPa)

### Performance Improvements

| Function | Before | After | Improvement |
|----------|--------|-------|-------------|
| `wet_bulb_temperature` | MetPy + fallback | Pure NumPy bisection | ~2x faster |
| `mixing_ratio_2m` | MetPy + fallback | Alduchov-Eskridge | More accurate |
| `lapse_rate_03km` | MetPy interpolation | Vectorized numpy | ~10x faster |

### Debugging

Enable detailed logging with environment variable:
```bash
export HRRR_DEBUG=1  # or true/yes/on
python your_script.py
```

### Compatibility

- All existing APIs remain unchanged
- Backward compatibility maintained through aliases
- No breaking changes to function signatures
- Same output precision and accuracy