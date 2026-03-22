# Implementation Plan: Remove Window Size Restrictions

**Task ID:** T-WINDOW-SIZE-001
**Spec Reference:** docs/specs/features/ui-design-system.md §3.3.1
**Master Constraints:** docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
**Project Context:** Engine Core / Views
**Created:** 2026-03-19
**Status:** READY FOR IMPLEMENTATION

---

## Overview

Remove minimum window size restrictions to allow users full control over window dimensions. The window should open at system default size and be resizable to any dimension.

## Spec Changes

**Before (v1.11):**
- Minimum Width: 1400px
- Minimum Height: 900px

**After (v1.12):**
- Minimum Width: None (no restriction)
- Minimum Height: None (no restriction)

**Rationale:** Users should have full control over window dimensions to accommodate different screen sizes, multi-monitor setups, and personal preferences. UI components handle small window sizes gracefully through scrolling and responsive layouts.

---

## Task Breakdown

### Task 1: Remove Constants from app_constants.py

**File:** `src/constants/app_constants.py`

**Changes:**
- Remove `WINDOW_MIN_WIDTH` constant (line 9)
- Remove `WINDOW_MIN_HEIGHT` constant (line 13)
- Remove associated docstrings

**Lines to Remove:**
```python
# Window dimensions
WINDOW_MIN_WIDTH: int = 1400
"""Minimum width of the main application window in pixels."""

WINDOW_MIN_HEIGHT: int = 900
"""Minimum height of the main application window in pixels."""
```

**Impact:** Low - constants only used in one location

---

### Task 2: Remove setMinimumSize Call from main_window.py

**File:** `src/views/main_window.py`

**Changes:**
- Remove `setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)` call from `_setup_window()` method (line 88)
- Remove imports of `WINDOW_MIN_WIDTH` and `WINDOW_MIN_HEIGHT` (line 28)

**Lines to Remove:**
```python
# Line 28 - Remove from imports
from src.constants.app_constants import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, APPLICATION_NAME, STATUS_MESSAGE_TIMEOUT
)

# Line 88 - Remove setMinimumSize call
self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
```

**Updated Import:**
```python
from src.constants.app_constants import (
    APPLICATION_NAME, STATUS_MESSAGE_TIMEOUT
)
```

**Updated _setup_window Method:**
```python
def _setup_window(self) -> None:
    """Set up window properties."""
    self.setWindowTitle(APPLICATION_NAME)
    # No minimum size - window can be resized to any dimension
    self.setStyleSheet(get_application_stylesheet())
```

**Impact:** Low - single line removal

---

### Task 3: Update Tests (if any)

**Files:** `tests/test_main_window*.py`

**Check:** Search for any tests that verify minimum window size.

**Expected:** No tests should exist for minimum window size (it was an internal constraint, not a user-facing feature).

**Action:** If tests exist, remove them. Otherwise, no action needed.

---

## Implementation Order

1. **Task 1:** Remove constants from `app_constants.py`
2. **Task 2:** Remove usage from `main_window.py`
3. **Task 3:** Check and update tests if needed

---

## Testing Requirements

### Manual Testing

1. **Window Opens:** Application starts without errors
2. **Window Resizable:** Window can be resized to very small dimensions
3. **Window Restore:** Window can be minimized and restored
4. **Multi-Monitor:** Window works on different screen sizes
5. **UI Components:** All UI components remain functional at small sizes

### Automated Testing

- Run existing test suite: `uv run pytest`
- No new tests required (removing restriction, not adding feature)

---

## Verification Checklist

- [ ] Constants removed from `app_constants.py`
- [ ] Import updated in `main_window.py`
- [ ] `setMinimumSize` call removed from `main_window.py`
- [ ] Application starts without errors
- [ ] Window can be resized to small dimensions
- [ ] All existing tests pass
- [ ] No references to `WINDOW_MIN_WIDTH` or `WINDOW_MIN_HEIGHT` in codebase

---

## Dependencies

None - this is a standalone change.

---

## Risk Assessment

**Risk Level:** LOW

**Reasons:**
- Simple removal of constraints
- No complex logic changes
- No data migration needed
- No API changes
- Backward compatible (users gain flexibility)

**Potential Issues:**
- Users with very small windows may see cramped UI
  - **Mitigation:** UI already has scrolling and responsive layouts
- Existing window state restoration may need testing
  - **Mitigation:** Settings manager stores window geometry, not minimum size

---

## Files Modified

| File | Lines Changed | Type |
|------|---------------|------|
| `src/constants/app_constants.py` | -4 lines | Constant removal |
| `src/views/main_window.py` | -2 lines | Code removal |
| `tests/test_main_window*.py` | TBD | Test removal (if needed) |

---

## Estimated Effort

- **Implementation:** 15 minutes
- **Testing:** 10 minutes
- **Total:** 25 minutes

---

## Delegation Instructions

```
📦 TASK DELEGATION
├─ Task ID: T-WINDOW-SIZE-001
├─ Spec Reference: §3.3.1 in docs/specs/features/ui-design-system.md
├─ Master Constraints: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
├─ Project Context: Views / Constants
├─ Scope: 
│  • src/constants/app_constants.py (remove WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
│  • src/views/main_window.py (remove setMinimumSize call, update imports)
├─ Language: Python 3.12
├─ Input/Output: None (removing constraints)
├─ Constraints:
│  • Thread context: Main thread (GUI)
│  • Memory: No changes
│  • Performance: No impact
├─ Tests Required: Run existing test suite, no new tests needed
└─ Dependencies: None
```

---

## Completion Criteria

1. All constants removed from `app_constants.py`
2. All references removed from `main_window.py`
3. Application starts and runs correctly
4. Window can be resized to any dimension
5. All existing tests pass
6. No regressions in UI behavior

---

## Post-Implementation

After implementation is complete and verified:
1. Mark tasks as complete
2. Trigger spec-auditor for final verification
3. Update SPEC-INDEX.md status if needed

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-19 | Initial implementation plan |