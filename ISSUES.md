# Known Issues & Technical Debt

This document tracks remaining issues identified during code review that have not yet been addressed. Each issue includes the symptom, root cause, affected files, and suggested fix with code snippets.

---

## Minor Issues

### 1. Invalid Type Annotation Syntax

**Severity:** Minor (static analysis warning)
**File:** `custom_components/sungrow_modbus/data/sungrow_config.py`
**Line:** 33

**Symptom:** Static type checkers (mypy, pyright) flag this as an error.

**Current Code:**
```python
self.features: [InverterFeature] = features  # Invalid syntax
```

**Root Cause:** `[InverterFeature]` is not valid Python type annotation syntax. This creates a list literal containing the class, not a type hint.

**Suggested Fix:**
```python
self.features: list[InverterFeature] = features
```

**Impact:** Low - code runs correctly, but IDE/type checker warnings appear.

---

### 2. Magic Register Numbers Without Constants

**Severity:** Minor (maintainability)
**File:** `custom_components/sungrow_modbus/sensors/sungrow_derived_sensor.py`
**Lines:** 74, 80, 94, 106, 110, 115

**Symptom:** Code uses magic numbers that are hard to understand without context.

**Current Code:**
```python
# Line 74
filtered_registers = {reg for reg in self._register if reg not in (0, 1, 90007)}

# Line 80
if 90007 in self._register:

# Line 94
if 90006 in self._register:

# Line 106
if 33095 in self._register:

# Line 110
if any(r in self._register for r in [33049, 33051, 33053, 33055]) and len(self._register) >= 2:

# Line 115
if any(r in self._register for r in [33079, 33080, 33081, 33082]) and len(self._register) >= 4:
```

**Root Cause:** Virtual/derived register numbers and special register addresses are hardcoded without explanation.

**Suggested Fix:** Define named constants at the top of the file:
```python
# Virtual registers (not real Modbus addresses)
REGISTER_CLOCK_DRIFT = 90007      # Triggers clock drift check
REGISTER_LAST_SUCCESS = 90006     # Last successful Modbus timestamp
REGISTER_PLACEHOLDER_0 = 0        # Placeholder for derived sensors
REGISTER_PLACEHOLDER_1 = 1        # Placeholder for derived sensors

# Real register addresses
REGISTER_RUNNING_STATUS = 33095   # System running status code

# Phase voltage/current registers for power calculation
REGISTERS_PHASE_POWER = [33049, 33051, 33053, 33055]

# Active/reactive power registers for power factor calculation
REGISTERS_POWER_FACTOR = [33079, 33080, 33081, 33082]
```

Then use:
```python
filtered_registers = {reg for reg in self._register if reg not in (REGISTER_PLACEHOLDER_0, REGISTER_PLACEHOLDER_1, REGISTER_CLOCK_DRIFT)}

if REGISTER_CLOCK_DRIFT in self._register:
    ...
```

**Impact:** Medium - code is harder to understand and maintain.

---

### 3. Empty Callback Function (Dead Code)

**Severity:** Minor (dead code)
**File:** `custom_components/sungrow_modbus/sensor.py`
**Lines:** 67-70

**Symptom:** A callback function is defined but has an empty body and is never used.

**Current Code:**
```python
@callback
def update(now):
    """Update Modbus data periodically."""

return True
```

**Root Cause:** This appears to be leftover code from a previous implementation where periodic updates were done differently. The actual update mechanism now uses event listeners.

**Suggested Fix:** Remove the dead code entirely:
```python
# Remove lines 67-70, just keep:
return True
```

Or if periodic updates are needed in the future, implement the function:
```python
@callback
def update(now):
    """Update Modbus data periodically."""
    for entity in sensor_entities:
        entity.async_schedule_update_ha_state(True)
```

**Impact:** Low - dead code adds confusion but doesn't affect functionality.

---

### 4. Defensive Code with Unclear Purpose

**Severity:** Minor (code clarity)
**File:** `custom_components/sungrow_modbus/sensors/sungrow_derived_sensor.py`
**Lines:** 18-19

**Symptom:** Fallback logic exists but the condition should never be true.

**Current Code:**
```python
def __init__(self, hass: HomeAssistant, sensor: SungrowBaseSensor):
    self._hass = hass if hass else sensor.hass  # Why would hass ever be None?
```

**Root Cause:** The `hass` parameter is typed as `HomeAssistant` (not `Optional[HomeAssistant]`), and all call sites pass a valid `hass` instance. The fallback to `sensor.hass` suggests historical usage patterns that may no longer exist.

**Suggested Fix:** Either remove the fallback:
```python
def __init__(self, hass: HomeAssistant, sensor: SungrowBaseSensor):
    self._hass = hass
```

Or document why it's needed:
```python
def __init__(self, hass: HomeAssistant | None, sensor: SungrowBaseSensor):
    # Fallback to sensor.hass for backwards compatibility with legacy instantiation
    self._hass = hass if hass else sensor.hass
```

**Impact:** Low - code works correctly, but the intent is unclear.

---

### 5. Unhelpful Error Message for Unknown Device Type

**Severity:** Minor (user experience)
**File:** `custom_components/sungrow_modbus/config_flow.py`
**Line:** 307

**Symptom:** Users with unknown device type codes see an unhelpful "Unknown (0x...)" message during configuration.

**Current Code:**
```python
model = DEVICE_TYPE_MAP.get(device_type_code, f"Unknown (0x{device_type_code:04X})")
```

**Root Cause:** When `device_type_code` is not in `DEVICE_TYPE_MAP`, the fallback message doesn't guide the user on what to do.

**Suggested Fix:** Provide more helpful guidance:
```python
if device_type_code not in DEVICE_TYPE_MAP:
    _LOGGER.warning(
        "Unknown device type code 0x%04X detected. "
        "Please report this to https://github.com/JohnnyVicious/hacs_sungrow_modbus/issues "
        "with your inverter model.",
        device_type_code
    )
    model = f"Unknown (0x{device_type_code:04X}) - Please report this device type"
else:
    model = DEVICE_TYPE_MAP[device_type_code]
```

Or allow manual model selection when auto-detection fails.

**Impact:** Medium for affected users - they may be confused about whether their inverter is supported.

---

### 6. Inconsistent Emoji Usage in Log Messages

**Severity:** Minor (consistency)
**Files:** Multiple files throughout the codebase

**Symptom:** Some log messages use emojis, others don't. Emojis may not render correctly in all environments.

**Examples:**
```python
# With emojis
_LOGGER.info(f"✅ ({self.host}.{self.device_id}) Connected to Modbus device")
_LOGGER.debug(f"⚠️({self.controller.host}.{self.controller.slave}) Skipping...")
_LOGGER.error("❌ Dynamic UOM set failed...")

# Without emojis
_LOGGER.warning("Error during Modbus polling: %s", e, exc_info=True)
_LOGGER.debug("TCP client ref count for %s is now %d", host, count)
```

**Root Cause:** No consistent logging style guide was followed during development.

**Suggested Fix:** Either:
1. Remove all emojis from log messages for consistency and compatibility
2. Add emojis consistently to all messages (and document this in CLAUDE.md)

For maximum compatibility, recommend removing emojis:
```python
# Instead of:
_LOGGER.info(f"✅ ({self.host}.{self.device_id}) Connected to Modbus device")

# Use:
_LOGGER.info("(%s.%s) Connected to Modbus device", self.host, self.device_id)
```

**Impact:** Low - purely cosmetic, but inconsistency can make logs harder to parse.

---

## Summary

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| Invalid type annotation | Minor | Low | Low |
| Magic register numbers | Minor | Medium | Medium |
| Empty callback function | Minor | Low | Low |
| Defensive code unclear | Minor | Low | Low |
| Unhelpful unknown device message | Minor | Low | Medium |
| Inconsistent emoji usage | Minor | Medium | Low |

**Recommendation:** Address issues #2 (magic numbers) and #5 (unknown device message) first as they have the most impact on maintainability and user experience respectively.
