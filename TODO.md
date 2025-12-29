# TODO - Future Improvements

This document tracks potential improvements identified during code review. Items are prioritized by impact and effort. The codebase is production-ready; these are enhancements rather than bugs.

**Last updated:** 2025-12-29

---

## High Priority

_No high priority items remaining._

---

## Medium Priority

### 2. Verbose Debug Logging Mode (was #3)

**Category:** Features
**Impact:** Medium | **Effort:** Medium
**Codex Review:** VALID

**Problem:**
Users reporting Modbus issues have no way to see raw register values. Current logging only shows operation metadata (register address, count) but not the actual values returned. No config/option exists to toggle verbose Modbus logging.

**Affected Files:**
- `modbus_controller.py:366-432` - Read paths log only metadata
- `modbus_controller.py:228-283` - Write paths log register and value but not raw frames
- `data_retrieval.py:330-391` - Logs durations and filtered spikes but no raw values

**Suggested Implementation:**
```python
# In options flow, add toggle:
CONF_VERBOSE_MODBUS_LOGGING = "verbose_modbus_logging"

# In modbus_controller.py
if self._verbose_logging:
    _LOGGER.debug(
        "READ %s registers %d-%d: %s",
        "holding" if holding else "input",
        address,
        address + count - 1,
        [hex(v) for v in result.registers]
    )

# For writes
if self._verbose_logging:
    _LOGGER.debug(
        "WRITE register %d = %s (0x%04X)",
        register,
        value,
        value
    )
```

**UI Integration:**
- Add toggle in integration options: "Enable verbose Modbus logging"
- Default: Off (to avoid log bloat)
- When enabled, logs at DEBUG level (user must also set logger level)

**Benefits:**
- Helps users diagnose inverter communication issues
- Enables remote debugging without code changes
- Useful for identifying firmware-specific quirks

---

### 4. Review Log Level Strategy

**Category:** Maintainability
**Impact:** Low | **Effort:** Low
**Codex Review:** PARTIALLY VALID - Current levels may be intentional

**Problem:**
Logging levels vary across the codebase:
- `modbus_controller.py:473-482` logs connection failures at DEBUG
- `data_retrieval.py:140-144` logs exceeding retry limits at WARNING
- `data_retrieval.py:133-135` logs connection exceptions at ERROR
- `data_retrieval.py:353-354` logs polling exceptions at WARNING with stack traces

**Analysis:**
Codex review suggests this may be **intentional** rather than inconsistent:
- DEBUG for transient connection attempts avoids log spam
- WARNING after retry exhaustion escalates appropriately
- ERROR for unexpected exceptions is correct

**Recommendation:**
Before changing, audit the current log levels and document the rationale. If current levels are intentional, add comments explaining why. If changes are needed, follow this standard:

| Event Type | Level | Example |
|------------|-------|---------|
| Successful operations | DEBUG | "Read 10 registers from 5000" |
| Configuration changes | INFO | "Polling interval changed to 30s" |
| Transient errors (will retry) | DEBUG or WARNING | "Connection attempt failed" |
| Persistent errors | ERROR | "Failed after 5 retries" |
| Startup/shutdown | INFO | "Integration loaded successfully" |

---

## Low Priority

### 5. Pre-compute Spike-Filtered Register Set

**Category:** Performance
**Impact:** Low | **Effort:** Low

**Problem:**
`data_retrieval.py:359-391` checks `if register not in SPIKE_FILTERED_REGISTERS` for every register value during polling. With 100+ registers per cycle, this adds minor overhead.

**Suggested Fix:**
```python
# At init time, pre-compute set of registers needing filtering
self._spike_filtered_set = frozenset(SPIKE_FILTERED_REGISTERS)

# In hot path
if register in self._spike_filtered_set:  # frozenset lookup is O(1)
    value = self._apply_spike_filter(register, value)
```

**Benefits:**
- Marginal performance improvement
- frozenset is immutable, safe for concurrent access

---

### 6. Expand Spike Filtering Tests

**Category:** Testing
**Impact:** Low | **Effort:** Medium

**Problem:**
Spike filtering logic has edge cases that may not be fully covered:
- Alternating spikes (0, 1, 0, 1, 0)
- Cached value is None
- Exactly 3 consecutive spikes (threshold boundary)

**Suggested Tests:**
```python
@pytest.mark.parametrize("values,expected", [
    ([100, 0, 100, 100], [100, 100, 100, 100]),  # Single spike filtered
    ([100, 0, 0, 0, 100], [100, 100, 100, 100, 100]),  # 3 spikes then real change
    ([100, 0, 0, 0, 0, 100], [100, 100, 100, 100, 0, 100]),  # 4 spikes = real
    ([None, 100, 0, 100], [None, 100, 100, 100]),  # None handling
])
def test_spike_filtering_patterns(values, expected):
    ...
```

---

### 7. Add Multi-Battery Integration Tests

**Category:** Testing
**Impact:** Low | **Effort:** Medium

**Problem:**
Battery controller has unit tests, but integration with main polling loop for multi-battery scenarios (4 stacks) isn't covered.

**Suggested Test:**
```python
async def test_four_battery_stack_polling():
    """Test polling loop correctly handles 4 battery stacks."""
    # Setup mock with 4 batteries responding
    # Verify all 4 sets of sensors created
    # Verify polling reads from all 4 address ranges
```

---

### 8. Strict Register Validation Mode

**Category:** Security
**Impact:** Low | **Effort:** Low

**Problem:**
Write service (`__init__.py:81-142`) validates value range (0-65535) but allows writing to any register. A misconfigured automation could write to dangerous registers.

**Suggested Implementation:**
```python
CONF_STRICT_REGISTER_VALIDATION = "strict_register_validation"

# Build set of writable registers from sensor definitions
WRITABLE_REGISTERS = {
    sensor["register"][0]
    for group in SENSOR_GROUPS
    for sensor in group["entities"]
    if sensor.get("editable", False)
}

if strict_mode and register not in WRITABLE_REGISTERS:
    raise HomeAssistantError(
        f"Register {register} is not in the allowed writable set. "
        "Disable strict mode to override."
    )
```

**UI Integration:**
- Add toggle in options: "Strict register validation"
- Default: Off (for power users who know what they're doing)
- When enabled, only allow writes to registers defined as `editable: true`

---

### 9. Rate Limiting on Service Calls

**Category:** Security
**Impact:** Low | **Effort:** Medium

**Problem:**
`sungrow_write_holding_register` service has no rate limiting. A misbehaving automation could flood the write queue.

**Suggested Implementation:**
```python
from homeassistant.helpers.debounce import Debouncer

# Per-register rate limiting
self._write_debouncers: dict[int, Debouncer] = {}

async def _rate_limited_write(self, register: int, value: int):
    if register not in self._write_debouncers:
        self._write_debouncers[register] = Debouncer(
            hass=self.hass,
            cooldown=5.0,  # 5 seconds between writes to same register
            immediate=True,
        )

    await self._write_debouncers[register].async_call(
        self._do_write, register, value
    )
```

---

### 10. ModbusController Usage Documentation

**Category:** Documentation
**Impact:** Low | **Effort:** Medium

**Problem:**
`ModbusController` has 25+ public methods but no high-level usage guide. New contributors must read through code to understand the API.

**Suggested Addition to class docstring:**
```python
class ModbusController:
    """Controls Modbus communication with Sungrow inverters.

    Usage Guide
    -----------

    Reading Registers:
        # Input registers (read-only sensor data)
        values = await controller.async_read_input_registers(5000, 10)

        # Holding registers (read/write settings)
        values = await controller.async_read_holding_registers(13049, 5)

    Writing Registers:
        # Single register
        result = await controller.async_write_holding_register(13049, 100)

        # Multiple registers
        result = await controller.async_write_holding_registers(13049, [100, 200])

        # Writes are queued and processed sequentially to avoid
        # overwhelming the inverter.

    Connection Management:
        # Connection is managed automatically. Check status with:
        is_connected = controller.is_connected

        # Force reconnection:
        await controller.async_reconnect()

    Thread Safety:
        All public methods are thread-safe and can be called from
        any async context. Internal locking ensures serial access
        to the Modbus connection.
    """
```

---

## Removed Items (False Positives)

Items initially proposed but removed after Codex verification:

### ~~Per-Operation Timeout~~ (Removed)

**Codex Review:** FALSE POSITIVE

**Original Claim:** No per-request timeout; if an inverter hangs mid-response, the poll loop blocks indefinitely.

**Actual Behavior:** Both TCP and serial clients are created with `timeout=5` (`client_manager.py:35`, `client_manager.py:52-54`). Pymodbus uses this parameter as the request/response timeout, so `read_*`/`write_*` awaits already time out rather than blocking indefinitely.

---

### ~~Optimize asyncio.Lock Creation~~ (Removed)

**Codex Review:** FALSE POSITIVE

**Original Claim:** `get_client_lock()` acquires a threading.Lock on every call, creating per-poll contention.

**Actual Behavior:** `get_client_lock()` is only called during `ModbusController` initialization (`modbus_controller.py:103`, `modbus_controller.py:118`), not on each poll. After initialization, the shared `poll_lock` is reused, so there is no per-poll contention from this method.

---

## Completed Items

Move items here when done, with date and commit reference:

```
- [x] 2025-12-29 (e7cb90e) - Write queue API returns actual result via Future
- [x] 2025-12-29 (044a0a5) - Circuit breaker pattern for connection management
- [x] 2025-12-29 (8e6743c) - Specific exception handling with pymodbus-specific exceptions
- [x] 2025-12-29 (3a8bb69) - TTL-based register caching for slow-changing values
```

---

## Codex Review Log

**Date:** 2025-12-29
**Tool:** OpenAI Codex CLI v0.77.0 (gpt-5.1-codex-max, reasoning: xhigh)

| Item | Original Title | Status | Action |
|------|---------------|--------|--------|
| 1 | Specific Exception Handling | VALID | Kept, expanded details |
| 2 | Circuit Breaker Pattern | VALID | Kept, expanded details |
| 3 | Per-Operation Timeout | FALSE POSITIVE | Removed (pymodbus handles this) |
| 4 | Verbose Debug Logging Mode | VALID | Kept (now #3) |
| 5 | Optimize asyncio.Lock Creation | FALSE POSITIVE | Removed (only called at init) |
| 6 | Standardize Log Levels | PARTIALLY VALID | Kept as #4, noted may be intentional |

**Key Findings:**
- pymodbus `timeout=5` parameter applies to both connect and per-request operations
- `get_client_lock()` is initialization-only, not per-poll
- Current log level strategy may be intentional to reduce noise

---

## Notes

- This list was generated from comprehensive code review on 2025-12-29
- Verified by Codex CLI on 2025-12-29 (2 false positives removed)
- The codebase is production-ready; all items here are enhancements
- See ISSUES.md for bug tracking and CHANGELOG.md for fix history
- Prioritize High items for reliability improvements
- Low priority items are "nice to have" for future development cycles
