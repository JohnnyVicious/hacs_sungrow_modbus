# Known Issues & Technical Debt

This document tracks remaining issues identified during code review that have not yet been addressed. Each issue includes the symptom, root cause, affected files, and suggested fix with code snippets.

**Important:** Before fixing any issue, check CHANGELOG.md to ensure a similar fix hasn't already been applied.

---

## Critical Issues

_No critical issues at this time._

---

## Important Issues

_No important issues at this time._

---

## Minor Issues

### 1. Hardcoded Register Values for Grid Inverter Offline Handling

**Severity:** Minor
**File:** `custom_components/sungrow_modbus/sensors/sungrow_sensor.py`
**Lines:** 92-95

**Symptom:** Magic numbers used for register addresses instead of named constants.

**Current Code:**
```python
if (
    self.base_sensor.controller.inverter_config.type == InverterType.GRID
    and updated_register == 3014  # Daily energy generation register
    and cache_get(self.hass, 3043, self.base_sensor.controller.controller_key) == 2  # Shutdown state
):
```

**Root Cause:** These register constants were not extracted when other registers were moved to named constants.

**Suggested Fix:**
Add constants at the top of the file (or in a shared constants module):
```python
# Grid inverter registers
REGISTER_DAILY_ENERGY_GENERATION = 3014
REGISTER_GRID_RUNNING_STATE = 3043
GRID_STATE_SHUTDOWN = 2
```

Then use:
```python
if (
    self.base_sensor.controller.inverter_config.type == InverterType.GRID
    and updated_register == REGISTER_DAILY_ENERGY_GENERATION
    and cache_get(self.hass, REGISTER_GRID_RUNNING_STATE, self.base_sensor.controller.controller_key) == GRID_STATE_SHUTDOWN
):
```

**Impact:** Low - Code readability and maintainability. The existing comments document the purpose well.

---

### 2. Magic Numbers in Battery Power Calculations

**Severity:** Minor
**File:** `custom_components/sungrow_modbus/sensors/sungrow_derived_sensor.py`
**Lines:** 173, 186-189

**Symptom:** Magic numbers for power scaling factor and battery direction values.

**Current Code:**
```python
# Line 173:
new_value = round(p_value * 10)

# Lines 186-189:
if str(d_value) == str(0):
    new_value = round(p_value * 10) * -1
else:
    new_value = round(p_value * 10)
```

**Root Cause:** These calculation constants were not extracted when other constants were defined.

**Suggested Fix:**
Add constants:
```python
POWER_SCALE_FACTOR = 10
BATTERY_DIRECTION_CHARGING = 0
BATTERY_DIRECTION_DISCHARGING = 1
```

Then use:
```python
# Line 173:
new_value = round(p_value * POWER_SCALE_FACTOR)

# Lines 186-189:
if d_value == BATTERY_DIRECTION_CHARGING:
    new_value = round(p_value * POWER_SCALE_FACTOR) * -1
else:
    new_value = round(p_value * POWER_SCALE_FACTOR)
```

**Impact:** Low - Code readability. Also note: `str(d_value) == str(0)` could be simplified to `d_value == 0` since both values are integers.

---

## Ignored/Deferred Issues

Issues listed here were identified during code review but intentionally NOT fixed. Each entry includes the reason for deferral. This prevents future reviewers from re-evaluating the same issues.

### 1. Incomplete Type Hints

**File:** Various sensor entity files

**What was found:** Some methods lack return type hints (e.g., `device_info` property returns `DeviceInfo` but this isn't annotated).

**Why it was ignored:**
- Low impact - the code works correctly without explicit return type annotations
- High effort - would require changes across many files
- No mypy/pyright CI enforcement currently in place
- IDE type inference works well enough for most cases

**Revisit if:** A decision is made to add strict type checking (mypy) to the CI pipeline.

---

### 2. String Comparison for Integer Values

**File:** `custom_components/sungrow_modbus/sensors/sungrow_derived_sensor.py`
**Lines:** 172, 186

**What was found:** Uses `str(d_value) == str(d_w_value)` and `str(d_value) == str(0)` instead of direct integer comparison.

**Why it was ignored:**
- The code works correctly as-is
- Changing comparison semantics could introduce subtle bugs if values arrive as different types
- Low impact (minor inefficiency)
- Risk of regression outweighs the benefit

**Revisit if:** Performance profiling identifies this as a bottleneck, or if type guarantees are strengthened elsewhere.

### Ignored Issue Template

```markdown
### N. Issue Title

**File:** `path/to/file.py`
**Line:** XX

**What was found:** Description of the potential issue.

**Why it was ignored:**
- Reason 1 (e.g., "False positive - the code is correct because...")
- Reason 2 (e.g., "Low impact, high effort - not worth the risk of regression")
- Reason 3 (e.g., "By design - this behavior is intentional because...")

**Revisit if:** Conditions under which this should be reconsidered.
```

---

## Issue Template

When adding new issues, use this format:

```markdown
### N. Issue Title

**Severity:** Critical | Important | Minor
**File:** `path/to/file.py`
**Line:** XX

**Symptom:** What the user or developer observes.

**Current Code:**
\`\`\`python
# The problematic code
\`\`\`

**Root Cause:** Why this is happening.

**Suggested Fix:**
\`\`\`python
# The corrected code
\`\`\`

**Impact:** Low | Medium | High - explanation of impact.
```

---

## Summary

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| Hardcoded grid register values | Minor | Low | Low |
| Magic numbers in battery calculations | Minor | Low | Low |

**Recommendation:** Minor issues can be addressed opportunistically when working in those files. Always check CHANGELOG.md for related historical fixes before implementing.
