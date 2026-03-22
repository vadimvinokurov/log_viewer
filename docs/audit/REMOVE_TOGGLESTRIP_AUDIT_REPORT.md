# Audit Report: Remove ToggleStrip from SearchToolbar

**Date:** 2026-03-18T23:21:07Z  
**Spec Reference:**  
- docs/specs/features/ui-components.md §6 (SearchToolbar)  
- docs/specs/features/panel-toggle-button.md §5.1/§6.1 (Implementation Details)  
- docs/specs/features/ui-design-system.md §3.4 (Layout Structure)  
**Master Spec:** docs/SPEC.md  
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)

---

## Summary

- **Files audited:**
  - src/views/main_window.py
  - src/views/widgets/__init__.py
  - src/views/widgets/main_status_bar.py
  - src/views/widgets/search_toolbar.py
  - src/styles/stylesheet.py
  - tests/test_main_window_panel_toggle.py
- **Spec sections verified:** §6 (ui-components), §5.1/§6.1 (panel-toggle-button), §3.4 (ui-design-system)
- **Verdict:** ❌ **FAIL**

---

## Findings

### ❌ Critical Deviations

#### 1. SearchToolbar Visibility Not Working

**File:** [`src/views/main_window.py`](src/views/main_window.py:123-137)

**Issue:** The `_search_toolbar` widget is added to a `QToolBar` container (line 135), but `set_panels_visible()` calls `setVisible()` on the widget, not the toolbar container.

**Expected per spec §6.1:**
```python
# Hide search toolbar
self._search_toolbar.setVisible(False)
```

**Actual implementation:**
```python
# Line 129-137: Creates QToolBar container
toolbar = QToolBar("Main Toolbar")
toolbar.setMovable(False)
toolbar.setFloatable(False)
toolbar.addWidget(self._search_toolbar)  # Widget added to toolbar
return toolbar

# Line 508: Tries to hide widget inside toolbar
self._search_toolbar.setVisible(False)  # WRONG: toolbar remains visible
```

**Impact:** The QToolBar container remains visible even when the widget inside is hidden. Users see an empty toolbar area instead of the toolbar being completely hidden.

**Recommendation:** Store a reference to the QToolBar and call `setVisible()` on the toolbar itself:

```python
# In _create_components():
self._main_toolbar: QToolBar  # Store reference

# In _create_toolbar():
self._main_toolbar = QToolBar("Main Toolbar")
self._main_toolbar.setMovable(False)
self._main_toolbar.setFloatable(False)
self._main_toolbar.addWidget(self._search_toolbar)
return self._main_toolbar

# In set_panels_visible():
if visible:
    self._main_toolbar.setVisible(True)  # Show toolbar container
else:
    self._main_toolbar.setVisible(False)  # Hide toolbar container
```

---

### ✅ Compliant Items

#### 2. MainWindow Panel Toggle Implementation (Except Toolbar Visibility)

**File:** [`src/views/main_window.py`](src/views/main_window.py)

- ✅ **Line 74:** `panels_toggled = Signal(bool)` signal declared per spec §4.2
- ✅ **Lines 100-103:** State variables `_panels_visible` and `_stored_splitter_sizes` properly declared
- ✅ **Lines 447-452:** `_on_toggle_panels()` keyboard shortcut handler implemented per spec §5.3
- ✅ **Lines 454-462:** `_on_status_bar_panels_toggled()` signal handler correctly delegates to `set_panels_visible()`
- ✅ **Lines 464-473:** `toggle_panels()` method toggles visibility correctly per spec §4.2
- ✅ **Lines 490-500:** Category panel splitter logic is correct
- ✅ **Lines 523-531:** `is_panels_visible()` returns current state per spec §4.2
- ❌ **Lines 488, 508:** Search toolbar visibility uses wrong target (widget vs toolbar container)

#### 3. MainStatusBar Panel Toggle Button

**File:** [`src/views/widgets/main_status_bar.py`](src/views/widgets/main_status_bar.py)

- ✅ **Line 38:** `panels_toggled = Signal(bool)` signal declared per spec §4.1
- ✅ **Lines 50-51:** State variables `_panels_visible` and `_toggle_button` properly declared
- ✅ **Lines 56-81:** `_setup_ui()` matches spec §6.2
- ✅ **Lines 162-172:** `_on_toggle_clicked()` emits opposite state for toggle per spec §6.2
- ✅ **Lines 174-190:** `set_panels_visible()` updates button icon/tooltip per spec §4.1
- ✅ **Lines 192-200:** `is_panels_visible()` returns current state per spec §4.1

#### 4. SearchToolbar Structure

**File:** [`src/views/widgets/search_toolbar.py`](src/views/widgets/search_toolbar.py)

- ✅ **Lines 39-216:** `SearchToolbar` class is a standard QWidget with no CollapsiblePanel wrapper
- ✅ No ToggleStrip references found (removed as per task)

#### 5. Widget Exports Cleanup

**File:** [`src/views/widgets/__init__.py`](src/views/widgets/__init__.py)

- ✅ **Lines 1-10:** CollapsiblePanel removed from exports
- ✅ Only exports: HighlightDialog, ErrorDialog, MainStatusBar
- ✅ No ToggleStrip references

#### 6. Stylesheet Cleanup

**File:** [`src/styles/stylesheet.py`](src/styles/stylesheet.py)

- ✅ No `get_collapsible_panel_stylesheet()` function found
- ✅ All stylesheet functions are for active components only

#### 7. File Deletion Verification

- ✅ `src/views/widgets/collapsible_panel.py` does NOT exist (verified via ls command)
- ✅ CollapsiblePanel completely removed from codebase

#### 8. Test Coverage

**File:** [`tests/test_main_window_panel_toggle.py`](tests/test_main_window_panel_toggle.py)

- ✅ Tests verify `_search_toolbar.isVisible()` state
- ⚠️ **Tests may pass but actual UI behavior is broken** - tests check widget visibility, not toolbar container visibility
- ⚠️ Tests should verify the toolbar container visibility, not the widget inside

---

## Coverage

- **Spec requirements implemented:** 12/13 (92%)
- **Critical issues:** 1 (toolbar visibility broken)
- **Test coverage:** Tests exist but may not catch the actual UI bug

---

## Project Convention Compliance

### Pattern Consistency

- ✅ Uses Qt parent-child ownership (not raw new/delete)
- ✅ Uses project's signal/slot pattern consistently
- ❌ Visibility control pattern incorrect (widget vs container)

### API Consistency

- ✅ Method naming follows existing patterns (`set_*`, `is_*`, `toggle_*`)
- ✅ Signal naming follows existing patterns (`*_toggled`, `*_clicked`)
- ✅ Method signatures match spec exactly

### Code Style

- ✅ Type hints on all public methods
- ✅ `from __future__ import annotations` at top of files
- ✅ `@beartype` decorator on public API methods
- ✅ Docstrings with `// Ref:` spec cross-references

---

## Spec Amendment Requests

None. Implementation should match spec exactly.

---

## Conclusion

❌ **AUDIT FAIL**: Critical bug in toolbar visibility implementation.

**Issue:** `set_panels_visible()` calls `setVisible()` on the widget inside the QToolBar, not the QToolBar itself. This leaves an empty toolbar visible when panels are "hidden".

**Fix Required:** Store reference to QToolBar and call `setVisible()` on the toolbar container, not the widget inside it.

**Files to Fix:**
- `src/views/main_window.py` - Lines 93, 123-137, 488, 508

---

## Revision History

| Version | Date | Auditor | Result |
|---------|------|---------|--------|
| 1.0 | 2026-03-18 | spec-auditor | FAIL - Toolbar visibility bug |
