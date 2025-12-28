# Known Issues & Technical Debt

This document tracks remaining issues identified during code review that have not yet been addressed. Each issue includes the symptom, root cause, affected files, and suggested fix with code snippets.

**Important:** Before fixing any issue, check CHANGELOG.md to ensure a similar fix hasn't already been applied.

---

## Critical Issues

*No critical issues at this time.*

---

## Important Issues

*No important issues at this time.*

---

## Minor Issues

### 1. Missing async_write_ha_state for Register 90005

**Severity:** Minor
**File:** `custom_components/sungrow_modbus/sensors/sungrow_binary_sensor.py`
**Lines:** 74-77

**Symptom:** The connection toggle entity (register 90005) updates its internal state but never pushes the update to Home Assistant, so the UI doesn't reflect the actual enabled/disabled status.

**Current Code:**
```python
if self._register == 90005:
    self._attr_is_on = self._modbus_controller.enabled
    self._attr_available = True
    return self._attr_is_on  # Early return without async_write_ha_state()
```

**Root Cause:** The early `return` bypasses the `self.async_write_ha_state()` call that other code paths use (line 92).

**Suggested Fix:**
```python
if self._register == 90005:
    self._attr_is_on = self._modbus_controller.enabled
    self._attr_available = True
    self.async_write_ha_state()
    return self._attr_is_on
```

**Impact:** Low - UI state for connection toggle may be stale until next poll.

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
| Missing async_write_ha_state for 90005 | Minor | Low | Low |

**Recommendation:** The remaining issue is minor and cosmetic - the connection toggle UI may be slightly stale until the next poll.
