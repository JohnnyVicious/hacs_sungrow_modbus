# Known Issues & Technical Debt

This document tracks remaining issues identified during code review that have not yet been addressed. Each issue includes the symptom, root cause, affected files, and suggested fix with code snippets.

**Important:** Before fixing any issue, check CHANGELOG.md to ensure a similar fix hasn't already been applied.

---

## Critical Issues

*No critical issues at this time.*

---

## Important Issues

### 1. Derived Sensor Mutates Controller Private Attributes

**Severity:** Important
**File:** `custom_components/sungrow_modbus/sensors/sungrow_derived_sensor.py`
**Lines:** 206-207

**Symptom:** Derived sensor directly mutates private attributes (`_sw_version` and `_model`) on the controller object.

**Current Code:**
```python
if REGISTER_PROTOCOL_VERSION in self._register:
    protocol_version, model_description = decode_inverter_model(new_value)
    self.base_sensor.controller._sw_version = protocol_version  # Direct mutation!
    self.base_sensor.controller._model = model_description      # Direct mutation!
```

**Root Cause:** Violates encapsulation by directly accessing controller internals. Creates tight coupling that will break silently if controller implementation changes.

**Suggested Fix:**
```python
# Add setter methods to ModbusController:
def set_sw_version(self, version: str) -> None:
    self._sw_version = version

def set_model(self, model: str) -> None:
    self._model = model

# Then in derived sensor:
self.base_sensor.controller.set_sw_version(protocol_version)
self.base_sensor.controller.set_model(model_description)
```

**Impact:** Medium - code smell that complicates maintenance and debugging.

**Note:** v0.2.0 fixed the same pattern for `_data_received`/`_sensor_groups` in DataRetrieval. This is the same issue with different attributes (`_sw_version`/`_model`).

---

### 2. Service Handler Write Result Discarded

**Severity:** Important
**File:** `custom_components/sungrow_modbus/__init__.py`
**Lines:** 123, 135

**Symptom:** Service calls report success even when underlying writes fail.

**Current Code:**
```python
if host:
    controller = get_controller(hass, host, slave)
    if controller is None:
        _LOGGER.error("No controller found for host %s, slave %s", host, slave)
        return
    await write_with_logging(controller, address, value)  # Result discarded!
else:
    for controller in targets:
        await write_with_logging(controller, address, value)  # Result discarded!
```

**Root Cause:** `write_with_logging()` returns success/failure but callers don't use the return value. Service always "succeeds" from HA's perspective.

**Suggested Fix:**
```python
if host:
    result = await write_with_logging(controller, address, value)
    if not result:
        raise ServiceValidationError(f"Failed to write to {host}:{slave}")
else:
    failed = []
    for controller in targets:
        if not await write_with_logging(controller, address, value):
            failed.append(controller.connection_id)
    if failed:
        raise ServiceValidationError(f"Write failed on: {', '.join(failed)}")
```

**Impact:** Medium - users can't reliably know if service calls succeeded.

---

## Minor Issues

### 6. Duplicate Step Attribute Assignment

**Severity:** Minor
**File:** `custom_components/sungrow_modbus/sensors/sungrow_number_sensor.py`
**Lines:** 53-54

**What's wrong:** Both `_attr_native_step` and `_attr_step` are set to the same value. One is likely redundant.

**Current Code:**
```python
self._attr_native_step = sensor.step
self._attr_step = sensor.step
```

**How to fix:** Verify which attribute `NumberEntity` base class uses and remove the redundant one.

---

### 7. Inconsistent State Update Methods

**Severity:** Minor
**File:** Multiple files

**What's wrong:** Codebase mixes `schedule_update_ha_state()` and `async_write_ha_state()` inconsistently:
- `sungrow_derived_sensor.py:125,134,215` uses `schedule_update_ha_state()`
- `sungrow_binary_sensor.py:77,93` uses `async_write_ha_state()`

**How to fix:** Standardize on `async_write_ha_state()` in `@callback` decorated methods for immediate state updates.

---

### 8. Magic Numbers in Retry Logic

**Severity:** Minor
**File:** `custom_components/sungrow_modbus/data_retrieval.py`
**Lines:** 110-111, 369

**What's wrong:** Retry delays (0.5s initial, 30s max, 20 retries) and spike filter threshold (3) are hardcoded without documentation.

**Current Code:**
```python
retry_delay = 0.5
max_retries = 20
# ...
retry_delay = min(retry_delay * 2, 30)
# ...
if self._spike_counter[register] < 3:  # Magic number
```

**How to fix:** Extract to named constants with comments explaining rationale.

---

### 9. Hardcoded Timeout Values

**Severity:** Minor
**File:** `custom_components/sungrow_modbus/modbus_controller.py`
**Lines:** 147, 151, 318-319

**What's wrong:** Various timeouts are hardcoded:
- `await asyncio.sleep(5)` when not connected
- `await asyncio.sleep(0.2)` between queue checks
- `delay_ms = 100 if is_write else 50` for inter-frame delays

**How to fix:** Extract to named constants or make configurable via constructor.

---

### Theoretical Issues (Low Risk)

These issues were identified but have low practical risk:

- **Division by zero in number sensor** (`sungrow_number_sensor.py:153`): Divides by `self._multiplier` without guard. However, no editable sensors currently use `multiplier: 0` (only string-type read-only sensors do).

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

---

### 3. AsyncModbus Client close() Not Awaited (False Positive)

**File:** `custom_components/sungrow_modbus/client_manager.py`
**Line:** 116

**What was found:** Initial code review suggested `client.close()` should be awaited.

**Why it was ignored:**
- False positive - In pymodbus 3.x (version 3.11.4 in use), `close()` is synchronous, not a coroutine
- Verified with `inspect.iscoroutinefunction(AsyncModbusTcpClient.close)` returns `False`
- The current code correctly calls `client.close()` synchronously
- No resource leaks occur with the current implementation

**Revisit if:** pymodbus changes `close()` to be async in a future version.

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

**2 Important issues** remaining (2025-12-29):

1. Derived sensor mutates controller privates - encapsulation violation
2. Service handler discards write results - no failure feedback

**4 Minor issues** remaining:

1. Duplicate step attribute assignment
2. Inconsistent state update methods
3. Magic numbers in retry logic
4. Hardcoded timeout values

**Resolved issues (see CHANGELOG.md):**
- Clock drift counters not namespaced - FIXED in [Unreleased]
- Connect return value ignored - FIXED in [Unreleased]
- Number entity fire-and-forget writes - FIXED in [Unreleased]
- Switch entity fire-and-forget writes - FIXED in [Unreleased]

**Moved to Ignored/Deferred:**
- AsyncModbus close() not awaited - FALSE POSITIVE (close() is synchronous in pymodbus 3.x)

**Assessment:** Production ready with caveats. All 410 tests pass. Issues primarily affect edge cases (offline behavior, frequent reloads, multi-inverter).

See the Ignored/Deferred Issues section above for items that were reviewed but intentionally not fixed.
