# Category Tree Expand/Collapse Toggle - Implementation Plan

**Version:** v1.0
**Created:** 2026-03-21
**Status:** READY FOR IMPLEMENTATION
**Spec Reference:** [category-tree-expand-collapse.md](category-tree-expand-collapse.md)

---

## Overview

This plan breaks down the implementation of the expand/collapse toggle button for the Category Tree panel into discrete, testable tasks that can be delegated to spec-coder agents.

---

## Task Breakdown

### T-001: Add ExpandCollapseState Enum and State Management

**Priority:** P1 (Foundation)
**Complexity:** Simple
**Estimated Time:** 30 minutes

#### Scope
- Add `ExpandCollapseState` enum to `src/views/category_panel.py`
- Add private members `_expand_state` and `_expand_button` to `CategoryPanel`
- Initialize state in `__init__`

#### Files to Modify
- `src/views/category_panel.py`

#### Spec Reference
- [category-tree-expand-collapse.md](category-tree-expand-collapse.md) §4.1, §4.3

#### Implementation Details

```python
from enum import Enum

class ExpandCollapseState(Enum):
    """Expand/collapse button state.
    
    The state represents the current expansion state of the tree,
    not the button action. When state is EXPANDED, the button shows
    a collapse icon (indicating "click to collapse").
    """
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"
```

#### In `CategoryPanel.__init__`
```python
# Add after existing members
self._expand_state: ExpandCollapseState = ExpandCollapseState.EXPANDED
self._expand_button: QPushButton | None = None
```

#### Acceptance Criteria
- [ ] `ExpandCollapseState` enum defined with `EXPANDED` and `COLLAPSED` values
- [ ] `_expand_state` member initialized to `EXPANDED`
- [ ] `_expand_button` member initialized to `None`
- [ ] Type hints correct (`ExpandCollapseState`, `QPushButton | None`)

---

### T-002: Create Expand/Collapse Public API Methods

**Priority:** P1 (Core Functionality)
**Complexity:** Simple
**Estimated Time:** 45 minutes
**Dependencies:** T-001

#### Scope
- Implement `expand_all()` method
- Implement `collapse_all()` method
- Implement `is_all_expanded()` method
- Implement `is_all_collapsed()` method
- Implement `_update_expand_button_icon()` private method

#### Files to Modify
- `src/views/category_panel.py`

#### Spec Reference
- [category-tree-expand-collapse.md](category-tree-expand-collapse.md) §5.1, §7.1, §7.2, §7.4

#### Implementation Details

```python
@beartype
def expand_all(self) -> None:
    """Expand all category nodes in the tree.
    
    Sets all nodes to expanded state and updates button icon.
    Emits no signals - this is a view-only operation.
    
    Performance:
        O(n) where n = total number of nodes
        Target: <100ms for 10,000 nodes
    """
    # Update state first
    self._expand_state = ExpandCollapseState.EXPANDED
    
    # Use Qt's built-in expandAll for efficiency
    self._tree_view.expandAll()
    
    # Update button icon
    self._update_expand_button_icon()

@beartype
def collapse_all(self) -> None:
    """Collapse all category nodes in the tree.
    
    Sets all nodes to collapsed state and updates button icon.
    Emits no signals - this is a view-only operation.
    
    Performance:
        O(n) where n = total number of nodes
        Target: <100ms for 10,000 nodes
    """
    # Update state first
    self._expand_state = ExpandCollapseState.COLLAPSED
    
    # Use Qt's built-in collapseAll for efficiency
    self._tree_view.collapseAll()
    
    # Update button icon
    self._update_expand_button_icon()

@beartype
def is_all_expanded(self) -> bool:
    """Check if all nodes are expanded.
    
    Returns:
        True if all nodes are expanded, False otherwise.
    """
    return self._expand_state == ExpandCollapseState.EXPANDED

@beartype
def is_all_collapsed(self) -> bool:
    """Check if all nodes are collapsed.
    
    Returns:
        True if all nodes are collapsed, False otherwise.
    """
    return self._expand_state == ExpandCollapseState.COLLAPSED

def _update_expand_button_icon(self) -> None:
    """Update button icon based on current state."""
    if self._expand_button is None:
        return
    
    if self._expand_state == ExpandCollapseState.EXPANDED:
        # Show collapse icon (▼) - indicates "click to collapse"
        self._expand_button.setText("▼")
        self._expand_button.setToolTip("Collapse all categories")
    else:
        # Show expand icon (▶) - indicates "click to expand"
        self._expand_button.setText("▶")
        self._expand_button.setToolTip("Expand all categories")
```

#### Acceptance Criteria
- [ ] `expand_all()` sets state to `EXPANDED`, calls `expandAll()`, updates icon
- [ ] `collapse_all()` sets state to `COLLAPSED`, calls `collapseAll()`, updates icon
- [ ] `is_all_expanded()` returns `True` when state is `EXPANDED`
- [ ] `is_all_collapsed()` returns `True` when state is `COLLAPSED`
- [ ] `_update_expand_button_icon()` updates button text and tooltip
- [ ] All methods have proper type hints and docstrings

---

### T-003: Integrate State Management with Existing Methods

**Priority:** P1 (Integration)
**Complexity:** Simple
**Estimated Time:** 30 minutes
**Dependencies:** T-001, T-002

#### Scope
- Modify `set_categories()` to set initial state
- Modify `_filter_tree()` to set state on search
- Modify `clear()` to reset state

#### Files to Modify
- `src/views/category_panel.py`

#### Spec Reference
- [category-tree-expand-collapse.md](category-tree-expand-collapse.md) §8.1, §8.2, §8.3

#### Implementation Details

**In `set_categories()` (after `expandAll()` call):**
```python
# Expand all items (existing behavior)
self._tree_view.expandAll()

# NEW: Set state to EXPANDED
self._expand_state = ExpandCollapseState.EXPANDED
self._update_expand_button_icon()
```

**In `_filter_tree()` (both branches):**
```python
if not text:
    self._show_all_items(self._model.invisibleRootItem())
    self._tree_view.expandAll()
    # NEW: Set state to EXPANDED
    self._expand_state = ExpandCollapseState.EXPANDED
    self._update_expand_button_icon()
    return

# ... existing implementation ...

self._tree_view.expandAll()
# NEW: Set state to EXPANDED
self._expand_state = ExpandCollapseState.EXPANDED
self._update_expand_button_icon()
```

**In `clear()`:**
```python
def clear(self) -> None:
    """Clear all categories."""
    self._model.blockSignals(True)
    self._model.clear()
    self._category_items.clear()
    self._all_categories.clear()
    self._model.blockSignals(False)
    
    # NEW: Reset state to EXPANDED
    self._expand_state = ExpandCollapseState.EXPANDED
    self._update_expand_button_icon()
```

#### Acceptance Criteria
- [ ] `set_categories()` sets state to `EXPANDED` after populating
- [ ] `_filter_tree()` sets state to `EXPANDED` when filtering
- [ ] `clear()` resets state to `EXPANDED`
- [ ] All integration points call `_update_expand_button_icon()`

---

### T-004: Add Button to UI and Connect Signals

**Priority:** P1 (UI Implementation)
**Complexity:** Simple
**Estimated Time:** 45 minutes
**Dependencies:** T-001, T-002

#### Scope
- Create `_setup_expand_button()` method
- Add button to button bar layout
- Connect click signal to handler
- Implement `_on_expand_collapse_clicked()` handler

#### Files to Modify
- `src/views/category_panel.py`

#### Spec Reference
- [category-tree-expand-collapse.md](category-tree-expand-collapse.md) §3.1, §3.2, §7.3, §9.2

#### Implementation Details

**New method `_setup_expand_button()`:**
```python
def _setup_expand_button(self) -> None:
    """Set up the expand/collapse button.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §9.2
    """
    self._expand_button = QPushButton()
    self._expand_button.setObjectName("expandCollapseButton")
    self._expand_button.setFixedWidth(32)
    self._expand_button.setAccessibleName("Expand/Collapse Categories")
    self._expand_button.clicked.connect(self._on_expand_collapse_clicked)
    
    # Set initial state
    self._expand_state = ExpandCollapseState.EXPANDED
    self._update_expand_button_icon()
```

**New handler `_on_expand_collapse_clicked()`:**
```python
def _on_expand_collapse_clicked(self) -> None:
    """Handle expand/collapse button click.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §7.3
    """
    if self._expand_state == ExpandCollapseState.EXPANDED:
        self.collapse_all()
    else:
        self.expand_all()
```

**Modify `_setup_ui()` to add button to button bar:**
```python
# Button bar for categories
button_bar = QWidget()
button_layout = QHBoxLayout(button_bar)
button_layout.setContentsMargins(4, 4, 4, 4)
button_layout.setSpacing(4)

# Check all button
check_all_btn = QPushButton("Check All")
check_all_btn.clicked.connect(lambda: self.check_all(True))
button_layout.addWidget(check_all_btn)

# Uncheck all button
uncheck_all_btn = QPushButton("Uncheck All")
uncheck_all_btn.clicked.connect(lambda: self.check_all(False))
button_layout.addWidget(uncheck_all_btn)

# NEW: Expand/collapse button
self._setup_expand_button()
button_layout.addWidget(self._expand_button)

categories_layout.addWidget(button_bar)
```

#### Acceptance Criteria
- [ ] Button created with object name `expandCollapseButton`
- [ ] Button fixed width set to 32px
- [ ] Accessible name set to "Expand/Collapse Categories"
- [ ] Click signal connected to handler
- [ ] Button added to button bar after "Uncheck All"
- [ ] Toggle handler switches between expand/collapse states

---

### T-005: Add QSS Styling for Expand/Collapse Button

**Priority:** P2 (Styling)
**Complexity:** Simple
**Estimated Time:** 20 minutes
**Dependencies:** T-004

#### Scope
- Add QSS rules for `#expandCollapseButton` to stylesheet
- Verify icon rendering on all platforms

#### Files to Modify
- `src/styles/stylesheet.py`

#### Spec Reference
- [category-tree-expand-collapse.md](category-tree-expand-collapse.md) §6.1, §6.3

#### Implementation Details

**Add to `get_tree_stylesheet()` or create new function:**
```python
def get_expand_collapse_button_stylesheet() -> str:
    """Get stylesheet for expand/collapse button.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §6.3
    """
    return """
QPushButton#expandCollapseButton {
    background-color: #F5F5F5;
    border: 1px solid #C0C0C0;
    border-radius: 3px;
    padding: 4px;
    min-width: 32px;
    max-width: 32px;
    color: #333333;
}

QPushButton#expandCollapseButton:hover {
    background-color: #E8E8E8;
    border: 1px solid #A0A0A0;
}

QPushButton#expandCollapseButton:pressed {
    background-color: #D0D0D0;
}

QPushButton#expandCollapseButton:focus {
    border: 1px solid #0066CC;
}
"""
```

**Apply in `CategoryPanel._setup_ui()`:**
```python
self._expand_button.setStyleSheet(get_expand_collapse_button_stylesheet())
```

#### Acceptance Criteria
- [ ] QSS rules match spec colors and dimensions
- [ ] Hover state changes background to `#E8E8E8`
- [ ] Pressed state changes background to `#D0D0D0`
- [ ] Focus state shows `#0066CC` border
- [ ] Fixed width enforced (32px)

---

### T-006: Add Unit Tests for Expand/Collapse Functionality

**Priority:** P1 (Testing)
**Complexity:** Medium
**Estimated Time:** 1 hour
**Dependencies:** T-001 through T-005

#### Scope
- Add unit tests for expand/collapse functionality
- Add integration tests for nested categories
- Add performance tests for large trees
- Add accessibility tests

#### Files to Modify
- `tests/test_category_panel.py` (new file) or add to existing test file

#### Spec Reference
- [category-tree-expand-collapse.md](category-tree-expand-collapse.md) §11.1, §11.2, §11.3

#### Test Cases to Implement

**Unit Tests:**
1. `test_expand_all` - Verify expand_all expands all nodes
2. `test_collapse_all` - Verify collapse_all collapses all nodes
3. `test_toggle_button` - Verify toggle button switches states
4. `test_search_triggers_expand` - Verify search triggers expand
5. `test_initial_state` - Verify initial state is expanded
6. `test_clear_resets_state` - Verify clear resets state

**Integration Tests:**
1. `test_expand_collapse_with_nested_categories` - Test with deeply nested categories
2. `test_expand_collapse_performance` - Test performance with 1000+ nodes

**Accessibility Tests:**
1. `test_accessible_name` - Verify button has accessible name
2. `test_tool_tip_updates` - Verify tool tip updates with state
3. `test_keyboard_activation` - Verify button can be activated with keyboard

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All accessibility tests pass
- [ ] Performance test completes in <100ms for 1000 nodes

---

## Dependency Graph

```
T-001 (Enum & State)
    │
    ├── T-002 (Public API Methods)
    │       │
    │       └── T-003 (Integration)
    │
    └── T-004 (UI & Signals)
            │
            └── T-005 (Styling)
                    │
                    └── T-006 (Tests)
```

---

## Execution Order

1. **T-001** - Foundation (no dependencies)
2. **T-002** - Core functionality (depends on T-001)
3. **T-003** - Integration (depends on T-001, T-002)
4. **T-004** - UI implementation (depends on T-001, T-002)
5. **T-005** - Styling (depends on T-004)
6. **T-006** - Testing (depends on all previous)

---

## Verification Checklist

After all tasks complete:

- [ ] All acceptance criteria met
- [ ] All tests pass
- [ ] Code follows project conventions (beartype, type hints)
- [ ] Docstrings reference spec sections
- [ ] No regressions in existing functionality
- [ ] Manual testing confirms UI behavior

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `src/views/category_panel.py` | Add enum, state management, public API, UI integration |
| `src/styles/stylesheet.py` | Add button stylesheet |
| `tests/test_category_panel.py` | Add unit tests |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial implementation plan |