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

_No minor issues at this time._

---

## Ignored/Deferred Issues

Issues listed here were identified during code review but intentionally NOT fixed. Each entry includes the reason for deferral. This prevents future reviewers from re-evaluating the same issues.

_No ignored issues at this time._

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

| Issue    | Severity | Effort | Priority |
|----------|----------|--------|----------|
| _None_   | -        | -      | -        |

**Recommendation:** Address Critical and Important issues first, then Minor issues based on effort and impact. Always check CHANGELOG.md for related historical fixes before implementing.
