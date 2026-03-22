# Category Tree Expand/Collapse Toggle Specification

**Version:** v1.0  
**Last Updated:** 2026-03-21  
**Project Context:** Python Tooling (Desktop Application)  
**Related:** [category-tree.md](category-tree.md), [category-panel-styles.md](category-panel-styles.md)

---

## §1 Overview

### §1.1 Purpose

This specification defines the expand/collapse toggle button for the Category Tree panel, allowing users to expand or collapse all category nodes with a single click.

### §1.2 Scope

- Toggle button placement in button bar
- State management (expanded/collapsed)
- Recursive tree traversal algorithm
- Visual feedback with chevron icons
- Accessibility support
- Integration with search functionality

### §1.3 References

- **Category Tree:** [category-tree.md](category-tree.md)
- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md)
- **UI Components:** [ui-components.md](ui-components.md) §5
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py)

---

## §2 Requirements

### §2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | User can expand all categories with a single click | Must |
| FR-2 | User can collapse all categories with a single click | Must |
| FR-3 | Button toggles between expand/collapse states | Must |
| FR-4 | State persists during session (not across sessions) | Must |
| FR-5 | Search triggers expand-all to show matching items | Must |
| FR-6 | Visual feedback shows current state via icon | Must |
| FR-7 | Keyboard accessible (Tab focus, Space/Enter activation) | Must |
| FR-8 | Screen reader announces state changes | Should |

### §2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Expand/collapse operation completes in <100ms for 10,000 nodes | Performance |
| NFR-2 | No UI freeze during operation | Responsiveness |
| NFR-3 | Consistent with existing button bar styling | UX |
| NFR-4 | Works with nested categories at any depth | Robustness |

---

## §3 Architecture

### §3.1 Component Location

```
CategoryPanel (QWidget)
├── QTabWidget
│   └── Categories Tab (QWidget)
│       ├── Search Container (QHBoxLayout)
│       │   ├── Search Icon (QLabel)
│       │   ├── Search Input (QLineEdit)
│       │   └── Expand/Collapse Toggle Button (QPushButton) ← NEW
│       ├── Tree View (QTreeView)
│       └── Button Bar (QWidget)
│           └── QHBoxLayout
│               ├── Check All Button (QPushButton)
│               └── Uncheck All Button (QPushButton)
```

### §3.2 Search Bar Layout

| Component | Order | Width | Purpose |
|-----------|-------|-------|---------|
| Search Icon | 1 | Fixed (20px) | Visual search indicator |
| Search Input | 2 | Stretch | Category search/filter |
| Expand/Collapse | 3 | Fixed (32px) | Toggle tree expansion |

**Layout Parameters:**
- Search bar spacing: 4px (per [category-panel-styles.md](category-panel-styles.md) §5.3)
- Search bar margins: 0px (per [category-panel-styles.md](category-panel-styles.md) §5.1)

---

## §4 State Management

### §4.1 State Definition

```python
class ExpandCollapseState(Enum):
    """Expand/collapse button state."""
    EXPANDED = "expanded"    # All nodes expanded, button shows collapse icon
    COLLAPSED = "collapsed"  # All nodes collapsed, button shows expand icon
```

### §4.2 State Transitions

```
┌─────────────────────────────────────────────────────────────┐
│                     State Machine                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐                    ┌───────────┐              │
│  │ EXPANDED │ ──click──────────▶ │ COLLAPSED │              │
│  └──────────┘                    └───────────┘              │
│       ▲                                │                     │
│       │                                │                     │
│       └────────click──────────────────┘                     │
│                                                              │
│  External Triggers:                                          │
│  ─ set_categories() ──▶ COLLAPSED (initial load)            │
│  ─ search_changed()  ──▶ EXPANDED (show matching items)     │
│  ─ clear()           ──▶ COLLAPSED (reset state)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### §4.3 State Properties

| Property | Type | Initial Value | Description |
|----------|------|---------------|-------------|
| `_expand_state` | `ExpandCollapseState` | `COLLAPSED` | Current button state |
| `_expand_button` | `QPushButton` | - | Button widget reference |

### §4.4 State Invariants

1. **Initial State:** When categories are loaded, state is `COLLAPSED` (all nodes collapsed)
2. **Search Trigger:** When search text changes, state becomes `EXPANDED`
3. **User Toggle:** Click toggles between `EXPANDED` ↔ `COLLAPSED`
4. **Clear Reset:** When categories cleared, state resets to `COLLAPSED`

---

## §5 API Reference

### §5.1 CategoryPanel Additions

```python
class CategoryPanel(QWidget):
    """Panel for category filtering with tabs and tree view."""
    
    # === New Private Members ===
    _expand_state: ExpandCollapseState
    _expand_button: QPushButton
    
    # === New Public Methods ===
    
    @beartype
    def expand_all(self) -> None:
        """Expand all category nodes in the tree.
        
        Sets all nodes to expanded state and updates button icon.
        Emits no signals - this is a view-only operation.
        
        Performance:
            O(n) where n = total number of nodes
            Target: <100ms for 10,000 nodes
        """
    
    @beartype
    def collapse_all(self) -> None:
        """Collapse all category nodes in the tree.
        
        Sets all nodes to collapsed state and updates button icon.
        Emits no signals - this is a view-only operation.
        
        Performance:
            O(n) where n = total number of nodes
            Target: <100ms for 10,000 nodes
        """
    
    @beartype
    def is_all_expanded(self) -> bool:
        """Check if all nodes are expanded.
        
        Returns:
            True if all nodes are expanded, False otherwise.
        """
    
    @beartype
    def is_all_collapsed(self) -> bool:
        """Check if all nodes are collapsed.
        
        Returns:
            True if all nodes are collapsed, False otherwise.
        """
    
    # === Modified Methods ===
    
    def set_categories(self, categories: list[CategoryDisplayNode]) -> None:
        """Populate tree with categories.
        
        MODIFIED: Now sets expand state to EXPANDED after populating.
        """
    
    def _filter_tree(self, text: str) -> None:
        """Filter tree items based on search text.
        
        MODIFIED: Now sets expand state to EXPANDED when filtering.
        """
```

### §5.2 ExpandCollapseState Enum

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

---

## §6 Visual Design

### §6.1 Button Appearance

| Property | Value | Source |
|----------|-------|--------|
| Fixed Width | 32px | Compact for icon-only |
| Height | Auto | Matches other buttons |
| Border Radius | 3px | [category-panel-styles.md](category-panel-styles.md) §6.2 |
| Background | `#F5F5F5` | [category-panel-styles.md](category-panel-styles.md) §4.1 |
| Border | 1px `#C0C0C0` | [category-panel-styles.md](category-panel-styles.md) §4.2 |
| Padding | 4px | Icon padding |

### §6.2 Icon Specification

| State | Icon | Unicode | Description |
|-------|------|---------|-------------|
| EXPANDED | ▼ | U+25BC | Filled down triangle (collapse action) |
| COLLAPSED | ▶ | U+25B6 | Filled right triangle (expand action) |

**Icon Styling:**
```css
QPushButton {
    font-size: 12pt;
    color: #333333;
    padding: 4px;
}
```

### §6.3 Button States

| State | Background | Border | Icon Color | Notes |
|-------|-------------|--------|------------|-------|
| Default | `#F5F5F5` | 1px `#C0C0C0` | `#333333` | Normal state |
| Hover | `#E8E8E8` | 1px `#A0A0A0` | `#333333` | Mouse over |
| Active/Pressed | `#D0D0D0` | 1px `#A0A0A0` | `#333333` | Mouse down |
| Focus | `#F5F5F5` | 1px `#0066CC` | `#333333` | Keyboard focus |
| Disabled | `#F5F5F5` | 1px `#D0D0D0` | `#999999` | Disabled (not used) |

**QSS Implementation:**
```css
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
```

---

## §7 Algorithm

### §7.1 Expand All

```python
def expand_all(self) -> None:
    """Expand all category nodes."""
    # Update state first
    self._expand_state = ExpandCollapseState.EXPANDED
    
    # Use Qt's built-in expandAll for efficiency
    # Ref: QTreeView::expandAll() - O(n) traversal
    self._tree_view.expandAll()
    
    # Update button icon
    self._update_expand_button_icon()
```

**Complexity:** O(n) where n = total nodes  
**Qt Implementation:** Uses `QTreeView::expandAll()` which internally traverses the model and expands all indices.

### §7.2 Collapse All

```python
def collapse_all(self) -> None:
    """Collapse all category nodes."""
    # Update state first
    self._expand_state = ExpandCollapseState.COLLAPSED
    
    # Use Qt's built-in collapseAll for efficiency
    # Ref: QTreeView::collapseAll() - O(n) traversal
    self._tree_view.collapseAll()
    
    # Update button icon
    self._update_expand_button_icon()
```

**Complexity:** O(n) where n = total nodes  
**Qt Implementation:** Uses `QTreeView::collapseAll()` which internally traverses the model and collapses all indices.

### §7.3 Toggle Handler

```python
def _on_expand_collapse_clicked(self) -> None:
    """Handle expand/collapse button click."""
    if self._expand_state == ExpandCollapseState.EXPANDED:
        self.collapse_all()
    else:
        self.expand_all()
```

### §7.4 Icon Update

```python
def _update_expand_button_icon(self) -> None:
    """Update button icon based on current state."""
    if self._expand_state == ExpandCollapseState.EXPANDED:
        # Show collapse icon (▼) - indicates "click to collapse"
        self._expand_button.setText("▼")
        self._expand_button.setToolTip("Collapse all categories")
    else:
        # Show expand icon (▶) - indicates "click to expand"
        self._expand_button.setText("▶")
        self._expand_button.setToolTip("Expand all categories")
```

---

## §8 Integration Points

### §8.1 set_categories Integration

```python
def set_categories(self, categories: list[CategoryDisplayNode]) -> None:
    """Populate tree with categories."""
    # ... existing implementation ...
    
    # Collapse all items (new behavior)
    self._tree_view.collapseAll()
    
    # NEW: Set state to COLLAPSED
    self._expand_state = ExpandCollapseState.COLLAPSED
    self._update_expand_button_icon()
```

### §8.2 Search Integration

```python
def _filter_tree(self, text: str) -> None:
    """Filter tree items based on search text."""
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

### §8.3 Clear Integration

```python
def clear(self) -> None:
    """Clear all categories."""
    self._model.blockSignals(True)
    self._model.clear()
    self._category_items.clear()
    self._all_categories.clear()
    self._model.blockSignals(False)
    
    # NEW: Reset state to COLLAPSED
    self._expand_state = ExpandCollapseState.COLLAPSED
    self._update_expand_button_icon()
```

---

## §9 Accessibility

### §9.1 Keyboard Navigation

| Shortcut | Action | Context |
|----------|--------|---------|
| `Tab` | Move focus to button | Button bar focus |
| `Shift+Tab` | Move focus from button | Button bar focus |
| `Space` | Activate button | Button focused |
| `Enter` | Activate button | Button focused |

### §9.2 Screen Reader Support

| Property | Value | Notes |
|----------|-------|-------|
| Accessible Name | "Expand/Collapse Categories" | Describes button purpose |
| Accessible Description | Dynamic | "Expand all categories" or "Collapse all categories" |
| Tool Tip | Dynamic | Matches accessible description |

**Implementation:**
```python
def _setup_expand_button(self) -> None:
    """Set up the expand/collapse button."""
    self._expand_button = QPushButton()
    self._expand_button.setObjectName("expandCollapseButton")
    self._expand_button.setFixedWidth(32)
    self._expand_button.setAccessibleName("Expand/Collapse Categories")
    self._expand_button.clicked.connect(self._on_expand_collapse_clicked)
    
    # Set initial state
    self._expand_state = ExpandCollapseState.COLLAPSED
    self._update_expand_button_icon()
```

### §9.3 Focus Indicator

Button uses standard focus indicator per [category-panel-styles.md](category-panel-styles.md) §9.3:
- Focus border: 1px `#0066CC`
- Visible on keyboard focus
- Hidden on mouse click

---

## §10 Performance

### §10.1 Time Complexity

| Operation | Complexity | Qt Method | Notes |
|-----------|------------|-----------|-------|
| `expand_all()` | O(n) | `QTreeView::expandAll()` | Traverses all indices |
| `collapse_all()` | O(n) | `QTreeView::collapseAll()` | Traverses all indices |
| `is_all_expanded()` | O(1) | State check | No traversal needed |
| `is_all_collapsed()` | O(1) | State check | No traversal needed |

### §10.2 Performance Targets

| Nodes | Target Time | Notes |
|-------|-------------|-------|
| 100 | <5ms | Small files |
| 1,000 | <20ms | Medium files |
| 10,000 | <100ms | Large files |
| 100,000 | <500ms | Very large files |

### §10.3 Optimization Notes

1. **Qt Built-in Methods:** Use `expandAll()` and `collapseAll()` instead of manual recursion
2. **State Tracking:** Track state internally to avoid O(n) checks
3. **No Signal Emission:** Expand/collapse is view-only, no model changes
4. **Viewport Update:** Qt handles viewport updates automatically

---

## §11 Testing

### §11.1 Unit Tests

```python
def test_expand_all(category_panel):
    """Test expand_all expands all nodes."""
    # Setup
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True, children=[
            CategoryDisplayNode(name="B", path="A/B", checked=True)
        ])
    ])
    
    # Collapse all first
    category_panel.collapse_all()
    assert not category_panel._tree_view.isExpanded(
        category_panel._model.index(0, 0)
    )
    
    # Expand
    category_panel.expand_all()
    
    # Verify all expanded
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED
    assert category_panel._expand_button.text() == "▼"

def test_collapse_all(category_panel):
    """Test collapse_all collapses all nodes."""
    # Setup
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True, children=[
            CategoryDisplayNode(name="B", path="A/B", checked=True)
        ])
    ])
    
    # Initial state is collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    
    # Expand first
    category_panel.expand_all()
    
    # Verify expanded
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED
    
    # Collapse
    category_panel.collapse_all()
    
    # Verify all collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    assert category_panel._expand_button.text() == "▶"

def test_toggle_button(category_panel):
    """Test toggle button switches states."""
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True)
    ])
    
    # Initial state: collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    
    # Click button
    category_panel._expand_button.click()
    
    # Should be expanded
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED
    
    # Click again
    category_panel._expand_button.click()
    
    # Should be collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED

def test_search_triggers_expand(category_panel):
    """Test that search triggers expand all."""
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True, children=[
            CategoryDisplayNode(name="B", path="A/B", checked=True)
        ])
    ])
    
    # Collapse all
    category_panel.collapse_all()
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    
    # Trigger search
    category_panel.set_search_text("B")
    
    # Should be expanded
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED

def test_initial_state(category_panel):
    """Test initial state is collapsed."""
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True)
    ])
    
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    assert category_panel._expand_button.text() == "▶"

def test_clear_resets_state(category_panel):
    """Test that clear resets state to collapsed."""
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True)
    ])
    
    # Expand
    category_panel.expand_all()
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED
    
    # Clear
    category_panel.clear()
    
    # Should reset to collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
```

### §11.2 Integration Tests

```python
def test_expand_collapse_with_nested_categories(category_panel):
    """Test expand/collapse with deeply nested categories."""
    # Create nested structure: A -> B -> C -> D
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True, children=[
            CategoryDisplayNode(name="B", path="A/B", checked=True, children=[
                CategoryDisplayNode(name="C", path="A/B/C", checked=True, children=[
                    CategoryDisplayNode(name="D", path="A/B/C/D", checked=True)
                ])
            ])
        ])
    ])
    
    # Collapse all
    category_panel.collapse_all()
    
    # Verify root is collapsed
    root_index = category_panel._model.index(0, 0)
    assert not category_panel._tree_view.isExpanded(root_index)
    
    # Expand all
    category_panel.expand_all()
    
    # Verify all expanded
    assert category_panel._tree_view.isExpanded(root_index)

def test_expand_collapse_performance(category_panel):
    """Test expand/collapse performance with many nodes."""
    # Create 1000 categories
    categories = [
        CategoryDisplayNode(name=f"Cat{i}", path=f"Cat{i}", checked=True)
        for i in range(1000)
    ]
    category_panel.set_categories(categories)
    
    import time
    
    # Measure collapse
    start = time.time()
    category_panel.collapse_all()
    collapse_time = time.time() - start
    
    # Measure expand
    start = time.time()
    category_panel.expand_all()
    expand_time = time.time() - start
    
    # Should be fast
    assert collapse_time < 0.1  # 100ms
    assert expand_time < 0.1  # 100ms
```

### §11.3 Accessibility Tests

```python
def test_accessible_name(category_panel):
    """Test button has accessible name."""
    assert category_panel._expand_button.accessibleName() == "Expand/Collapse Categories"

def test_tool_tip_updates(category_panel):
    """Test tool tip updates with state."""
    category_panel.expand_all()
    assert category_panel._expand_button.toolTip() == "Collapse all categories"
    
    category_panel.collapse_all()
    assert category_panel._expand_button.toolTip() == "Expand all categories"

def test_keyboard_activation(category_panel):
    """Test button can be activated with keyboard."""
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True)
    ])
    
    # Focus button
    category_panel._expand_button.setFocus()
    
    # Simulate Space key
    # Note: In real test, use QTest.keyClick()
    category_panel._expand_button.click()
    
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
```

---

## §12 Implementation Checklist

### §12.1 Code Changes

- [ ] Add `ExpandCollapseState` enum to `src/views/category_panel.py`
- [ ] Add `_expand_state` and `_expand_button` members to `CategoryPanel`
- [ ] Create `_setup_expand_button()` method
- [ ] Create `expand_all()` public method
- [ ] Create `collapse_all()` public method
- [ ] Create `_on_expand_collapse_clicked()` handler
- [ ] Create `_update_expand_button_icon()` method
- [ ] Modify `set_categories()` to set initial state
- [ ] Modify `_filter_tree()` to set state on search
- [ ] Modify `clear()` to reset state
- [ ] Add button to button bar layout

### §12.2 Style Changes

- [ ] Add QSS for `#expandCollapseButton` to stylesheet
- [ ] Verify icon rendering on all platforms

### §12.3 Test Changes

- [ ] Add unit tests for expand/collapse functionality
- [ ] Add integration tests for nested categories
- [ ] Add performance tests for large trees
- [ ] Add accessibility tests

---

## §13 Cross-References

- **Category Tree:** [category-tree.md](category-tree.md) - Core tree structure
- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md) - Visual styling
- **UI Components:** [ui-components.md](ui-components.md) §5 - CategoryPanel API
- **Color Palette:** [../global/color-palette.md](../global/color-palette.md) - Color tokens
- **Typography:** [typography-system.md](typography-system.md) - Font specifications

---

## §14 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial specification |