# Data Validation Design

**Date:** 2025-12-28
**Status:** Approved

## Overview

Add data validation for both read (sensor values from inverter) and write (user commands to inverter) operations using existing `min_value` and `max_value` properties in sensor definitions.

## Behavior

### Read Validation
- **When:** After value conversion in `_convert_raw_value()`, before returning
- **Action:** Log warning with sensor name, register, value, and bound exceeded
- **Result:** Return value anyway (debug mode - helps identify hardware issues)

### Write Validation
- **When:** In `async_set_native_value()` before calling controller write
- **Action:** Log error and raise `HomeAssistantError`
- **Result:** Write blocked, UI shows failure to user

## Implementation

### 1. Default Bounds by Unit Type

Add `_get_default_bounds()` method to derive sensible min/max from unit type when not explicitly set:

| Unit | Min | Max | Rationale |
|------|-----|-----|-----------|
| `PERCENTAGE` | 0 | 100 | Percentages can't exceed 100% |
| `UnitOfTemperature.CELSIUS` | -40 | 100 | Inverter operating range |
| `UnitOfElectricPotential.VOLT` | 0 | 1000 | Max grid/PV voltage |
| `UnitOfElectricCurrent.AMPERE` | -100 | 100 | Signed current (charge/discharge) |
| `UnitOfPower.WATT` | -50000 | 50000 | Signed power (import/export) |
| `UnitOfPower.KILO_WATT` | -50 | 50 | Same in kW |
| `UnitOfEnergy.KILO_WATT_HOUR` | 0 | 1000000 | Energy totals (cumulative) |
| `UnitOfFrequency.HERTZ` | 45 | 65 | Grid frequency range |

### 2. Read Validation Method

```python
def _validate_read_value(self, value) -> None:
    """Log warning if converted value is outside expected bounds."""
    if value is None or self.value_mapping is not None:
        return  # Skip validation for None or mapped values (enums)

    if self.min_value is not None and value < self.min_value:
        _LOGGER.warning(
            "Sensor '%s' (register %s) value %s below minimum %s",
            self.name, self.registrars, value, self.min_value
        )
    elif self.max_value is not None and value > self.max_value:
        _LOGGER.warning(
            "Sensor '%s' (register %s) value %s above maximum %s",
            self.name, self.registrars, value, self.max_value
        )
```

### 3. Write Validation

```python
from homeassistant.exceptions import HomeAssistantError

async def async_set_native_value(self, value: float) -> None:
    """Set new value with validation."""
    if self._sensor.min_value is not None and value < self._sensor.min_value:
        _LOGGER.error(
            "Rejecting write to '%s': value %s below minimum %s",
            self._sensor.name, value, self._sensor.min_value
        )
        raise HomeAssistantError(
            f"Value {value} is below minimum {self._sensor.min_value}"
        )

    if self._sensor.max_value is not None and value > self._sensor.max_value:
        _LOGGER.error(
            "Rejecting write to '%s': value %s above maximum %s",
            self._sensor.name, value, self._sensor.max_value
        )
        raise HomeAssistantError(
            f"Value {value} is above maximum {self._sensor.max_value}"
        )

    # ... existing write logic ...
```

## Files to Modify

| File | Changes |
|------|---------|
| `sensors/sungrow_base_sensor.py` | Add `_validate_read_value()`, `_get_default_bounds()`, update `__init__` |
| `sensors/sungrow_number_sensor.py` | Add write validation in `async_set_native_value()` |
| `sensors/sungrow_select_entity.py` | Add write validation for select options |
| `tests/test_validation.py` | New file with ~15 test cases |
| `CHANGELOG.md` | Document the feature addition |

## Test Coverage

### Read Validation Tests
- Value within bounds - no warning logged
- Value below minimum - warning logged, value returned
- Value above maximum - warning logged, value returned
- None value - validation skipped
- Mapped value (enum) - validation skipped

### Write Validation Tests
- Valid write - succeeds
- Write below minimum - raises HomeAssistantError
- Write above maximum - raises HomeAssistantError
- Write at boundary - succeeds

### Default Bounds Tests
- Percentage defaults to 0-100
- Temperature has reasonable range
- Explicit override wins over defaults

## Risk Assessment

- **Low risk** - validation is additive, doesn't change existing behavior
- Read validation only logs, doesn't filter values
- Write validation uses `HomeAssistantError` which is HA-standard for rejecting operations
