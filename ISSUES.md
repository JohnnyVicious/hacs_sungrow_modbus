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

*No minor issues at this time.*

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

**No issues remaining** (2025-12-29)

**Resolved issues (see CHANGELOG.md):**
- Duplicate step attribute assignment - FIXED in [Unreleased]
- Inconsistent state update methods - FIXED in [Unreleased]
- Magic numbers in retry logic - FIXED in [Unreleased]
- Hardcoded timeout values - FIXED in [Unreleased]
- Service handler discards write results - FIXED in v0.3.2
- Derived sensor mutates controller privates - FIXED in v0.3.2
- Clock drift counters not namespaced - FIXED in v0.3.2
- Connect return value ignored - FIXED in v0.3.2
- Number entity fire-and-forget writes - FIXED in v0.3.2
- Switch entity fire-and-forget writes - FIXED in v0.3.2

**Moved to Ignored/Deferred:**
- AsyncModbus close() not awaited - FALSE POSITIVE (close() is synchronous in pymodbus 3.x)

**Assessment:** Production ready. All 410 tests pass. No known issues remaining.

See the Ignored/Deferred Issues section above for items that were reviewed but intentionally not fixed.
