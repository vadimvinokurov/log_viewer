# Category Tree Row Style Unification Specification

**Version:** 1.2
**Last Updated:** 2026-03-16
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** READY

---

## §1 Overview

### §1.1 Purpose

This specification defines the unification of category tree row styles with log table row styles, ensuring visual consistency across the application. The category panel tree rows will use the same typography, spacing, and visual density as the log table rows.

### §1.2 Motivation

Currently, category tree rows and log table rows have different styling:
- **Category Tree**: `padding: 2px 4px` (top/bottom, left/right)
- **Log Table**: `padding: 0` (zero padding for maximum density)

This creates visual inconsistency when viewing both panels side by side. Unifying the styles provides:
1. **Visual Cohesion**: Consistent appearance across all data rows
2. **Information Density**: Maximum visible content in both panels
3. **Simplified Maintenance**: Single source of truth for row styling

### §1.3 Scope

- Tree item padding and spacing
- Tree item height calculation
- Typography for tree items
- Background colors and states
- Checkbox positioning

### §1.4 Cross-References

- **Table Unified Styles:** [table-unified-styles.md](table-unified-styles.md)
- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md)
- **Typography System:** [typography-system.md](typography-system.md)
- **UI Design System:** [ui-design-system.md](ui-design-system.md)
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py)
- **Delegate:** [`src/views/delegates/category_item_delegate.py`](../../src/views/delegates/category_item_delegate.py)

---

## §2 Current State Analysis

### §2.1 Log Table Row Styles (Reference)

From [table-unified-styles.md](table-unified-styles.md):

| Property | Value | Notes |
|----------|-------|-------|
| Padding | `0` | Zero padding for maximum density |
| Height | `Typography.TABLE_CELL_HEIGHT` | Font metrics + 2px |
| Font | System default | No hardcoding |
| Background | `#B6B6B6` | Gray background |
| Selected | `#DCEBF7` | Light blue selection |
| Text Color | `#333333` | Primary text color |

### §2.2 Category Tree Row Styles (Current)

From [category-panel-styles.md](category-panel-styles.md):

| Property | Value | Notes |
|----------|-------|-------|
| Padding | `2px 4px` | Top/bottom, left/right |
| Height | Qt default | Not explicitly set |
| Font | System default | No hardcoding |
| Background | Transparent | Default items |
| Hover | `#E8E8E8` | Hover background |
| Selected | `#DCEBF7` | Selection highlight |
| Text Color | `#333333` | Primary text color |

### §2.3 Key Differences

| Property | Log Table | Category Tree | Action |
|----------|-----------|---------------|--------|
| Padding | `0` | `2px 4px` | **Change to 0** |
| Height | `TABLE_CELL_HEIGHT` | Qt default | **Set explicitly** |
| Background | `#B6B6B6` | Transparent | **Keep transparent** (different context) |
| Hover | `#B6B6B6` | `#E8E8E8` | **Keep `#E8E8E8`** (tree hover feedback) |
| Selected | `#DCEBF7` | `#DCEBF7` | ✅ Already matches |

---

## §3 Unified Row Styles

### §3.1 Typography

Tree items use the same typography as log table rows:

| Property | Value | Source |
|----------|-------|--------|
| Font Family | System UI Font | `Typography.PRIMARY` |
| Font Size | System default | No hardcoding |
| Font Weight | Normal (400) | Default |
| Line Height | `1.0` | Compact for tree |

**Implementation:**
```python
from src.constants.typography import Typography

# Use system default font
font = Typography.UI_FONT
```

### §3.2 Spacing and Dimensions

#### §3.2.1 Cell Padding

**Change:** Tree item padding changes from `2px 4px` to `0`.

| Side | Before | After | Rationale |
|------|--------|-------|-----------|
| `padding-top` | `2px` | `0` | Match table density |
| `padding-right` | `4px` | `0` | Match table density |
| `padding-bottom` | `2px` | `0` | Match table density |
| `padding-left` | `0` | `0` | No change (indentation handled by Qt) |

**Note:** Left padding remains `0` because tree indentation is handled by Qt's `indentation` property (10px per level, reduced from Qt default 16px for compact layout).

#### §3.2.2 Row Height

Tree rows use the same height calculation as table rows:

| Element | Height Calculation | Source |
|---------|-------------------|--------|
| Tree Row | `Typography.TABLE_CELL_HEIGHT` | Same as table |

**Implementation:**
```python
from src.constants.dimensions import TABLE_CELL_HEIGHT

# Set uniform row heights for performance
self._tree_view.setUniformRowHeights(True)
# Note: Row height is determined by font metrics + 2px padding
# This matches the table row height calculation
```

### §3.3 Background Colors

Background colors remain unchanged for tree-specific behavior:

| State | Color | Token | Notes |
|-------|-------|-------|-------|
| Default | Transparent | - | Tree background shows through |
| Hover | `#E8E8E8` | Background Hover | Visual feedback for hover |
| Selected | `#DCEBF7` | Selection Highlight | Same as table selection |

**Rationale:** Unlike table rows which have a uniform gray background (`#B6B6B6`), tree items use transparent backgrounds to show the tree's background color (`#F5F5F5`). Hover state uses `#E8E8E8` to provide visual feedback when navigating the tree.

### §3.4 Text Colors

Text colors match the log table:

| State | Color | Token | Notes |
|-------|-------|-------|-------|
| Default | `#333333` | Primary Text | Same as table |
| Selected | `#000000` | Selection Text | Same as table |
| Disabled | `#999999` | Disabled Text | Same as table |

---

## §4 Checkbox Rendering

### §4.1 Custom Drawn Checkboxes

Checkboxes are custom drawn with a dark gray, minimalist, flat design that provides clear visual feedback without distracting from the content.

| State | Border | Background | Checkmark | Size |
|-------|--------|------------|-----------|------|
| Unchecked | `#666666` | `#FFFFFF` | N/A | 12×12px |
| Checked | `#666666` | `#666666` | White ✓ | 12×12px |
| Partially Checked | `#666666` | `#E0E0E0` | `#666666` (─) | 12×12px |
| Hover (Unchecked) | `#555555` | `#FFFFFF` | N/A | 12×12px |
| Hover (Checked) | `#555555` | `#555555` | White ✓ | 12×12px |
| Disabled | `#B0B0B0` | `#F5F5F5` | N/A | 12×12px |

**Rationale:**
1. **Minimalist Design**: Dark gray (#666666) provides subtle, non-distracting visual indicator
2. **Flat Design**: No gradients, shadows, or 3D effects - clean and modern appearance
3. **Clear States**: Distinct visual difference between unchecked, checked, and partially checked
4. **Hover Feedback**: Darker gray (#555555) provides subtle interactive feedback
5. **Accessibility**: High contrast between checked (dark gray) and unchecked (white) states

### §4.2 Checkbox Dimensions

| Property | Value | Notes |
|----------|-------|-------|
| Width | 12px | Compact checkbox size |
| Height | 12px | Compact checkbox size |
| Border Width | 1px | Thin border for clean look |
| Border Radius | 2px | Slightly rounded corners |
| Checkmark Size | 8×8px | Centered within checkbox |

### §4.3 Checkbox Positioning

| Property | Value | Notes |
|----------|-------|-------|
| Branch Area Width | Dynamic | Same as checkbox (QStyle.PM_IndicatorWidth) |
| Branch-to-Checkbox Gap | 4px | Desktop standard (macOS/Windows) |
| Text-to-Checkbox Padding | 4px | Space between checkbox and text |
| Vertical Alignment | Center | Vertically centered in row |

### §4.4 Checkbox Drawing Algorithm

```python
def draw_checkbox(painter, rect, state, hover=False):
    """Draw custom checkbox matching application style.
    
    Args:
        painter: QPainter instance
        rect: QRect for checkbox (14x14 pixels)
        state: Qt.Unchecked, Qt.Checked, or Qt.PartiallyChecked
        hover: Whether mouse is over the checkbox
    """
    if state == Qt.Checked:
        # Filled blue checkbox with white checkmark
        draw_filled_box(painter, rect, fill="#0066CC", border="#0066CC")
        draw_checkmark(painter, rect, color="#FFFFFF")
    elif state == Qt.PartiallyChecked:
        # Light blue background with horizontal line
        draw_filled_box(painter, rect, fill="#DCEBF7", border="#0066CC")
        draw_minus_sign(painter, rect, color="#0066CC")
    else:
        # Empty white checkbox with gray border
        border_color = "#A0A0A0" if hover else "#C0C0C0"
        draw_empty_box(painter, rect, fill="#FFFFFF", border=border_color)
```

### §4.5 Color Reference

| Color | Hex | Usage |
|-------|-----|-------|
| Dark Gray | `#666666` | Checked border and fill, partial indicator |
| Dark Gray Hover | `#555555` | Hover state for checked and unchecked |
| Partially Checked BG | `#E0E0E0` | Partially checked background |
| Border Gray | `#666666` | Unchecked border |
| Border Gray Hover | `#555555` | Unchecked hover border |
| White | `#FFFFFF` | Unchecked background, checkmark color |
| Disabled Gray | `#B0B0B0` | Disabled border |
| Disabled Background | `#F5F5F5` | Disabled background |

---

## §5 Complete QSS Specification

### §5.1 Tree View Styles

```css
/* Tree View Container */
QTreeView {
    /* Background */
    background-color: #F5F5F5;
    
    /* Borders */
    border: none;
    
    /* Selection */
    selection-background-color: #DCEBF7;
    selection-color: #000000;
    
    /* Indentation */
    indentation: 10px;
}

/* Tree Items - Unified with Table Rows */
QTreeView::item {
    /* Spacing - ZERO padding to match table */
    padding: 0;
    
    /* Height - determined by font metrics + 2px */
    /* Note: setUniformRowHeights(True) for performance */
    
    /* Background */
    background-color: transparent;
    
    /* Borders */
    border: none;
    
    /* Text */
    color: #333333;
}

/* Hover State */
QTreeView::item:hover {
    background-color: #E8E8E8;
}

/* Selected State */
QTreeView::item:selected {
    background-color: #DCEBF7;
    color: #000000;
}

/* Disabled State */
QTreeView::item:disabled {
    color: #999999;
}
```

### §5.2 Checkbox Styles (Custom Drawn)

**Note:** Checkboxes are custom drawn by `CategoryItemDelegate` using QPainter, not via QSS. The delegate draws filled rectangles with checkmarks matching the application's primary blue color scheme.

**QSS (not used for checkboxes):**
```css
/* No QTreeView::indicator styles - delegate draws custom checkboxes */
```

**Delegate Implementation:**
```python
# In CategoryItemDelegate._draw_checkbox()
# Draw custom checkbox with:
# - Unchecked: White background, gray border (#C0C0C0)
# - Checked: Blue background (#0066CC), white checkmark
# - Partially: Light blue background (#DCEBF7), blue minus sign
```

---

## §6 Implementation Changes

### §6.1 Files to Modify

| File | Changes |
|------|---------|
| [`src/styles/stylesheet.py`](../../src/styles/stylesheet.py) | Update `get_tree_stylesheet()` to use zero padding, remove `QTreeView::indicator` styles |
| [`src/views/category_panel.py`](../../src/views/category_panel.py) | No changes needed |
| [`src/views/delegates/category_item_delegate.py`](../../src/views/delegates/category_item_delegate.py) | **Major refactor**: Replace custom drawing with Unicode characters |
| [`docs/specs/features/category-panel-styles.md`](category-panel-styles.md) | Update §5.1 padding, §7.4 checkbox states |

### §6.2 Stylesheet Changes

**Before:**
```css
QTreeView::item {
    padding: 2px 4px;
    border: none;
    color: #333333;
}

QTreeView::indicator {
    width: 14px;
    height: 14px;
}
/* ... more indicator styles ... */
```

**After:**
```css
QTreeView::item {
    padding: 0;
    border: none;
    color: #333333;
}
/* No QTreeView::indicator styles - delegate renders Unicode */
```

### §6.3 Delegate Refactor

**CategoryItemDelegate changes:**

| Method | Description |
|--------|-------------|
| `_draw_checkbox()` | Draw custom checkbox with QPainter using application colors |
| `_draw_checkmark()` | Draw white checkmark (✓) for checked state |
| `_draw_minus_sign()` | Draw horizontal line for partially checked state |
| `CHECKBOX_SIZE` | 14px constant for checkbox dimensions |
| `CHECKBOX_BORDER_RADIUS` | 2px for slightly rounded corners |

**Custom drawn delegate:**
```python
class CategoryItemDelegate(QStyledItemDelegate):
    """Delegate for category tree items with custom checkbox rendering."""
    
    # Checkbox dimensions
    CHECKBOX_SIZE = 14
    CHECKBOX_BORDER_RADIUS = 2
    
    # Colors from application palette
    COLOR_PRIMARY_BLUE = "#0066CC"
    COLOR_PRIMARY_BLUE_HOVER = "#0055AA"
    COLOR_SELECTION_LIGHT = "#DCEBF7"
    COLOR_BORDER_GRAY = "#C0C0C0"
    COLOR_BORDER_GRAY_HOVER = "#A0A0A0"
    COLOR_WHITE = "#FFFFFF"
    COLOR_DISABLED_BORDER = "#D0D0D0"
    COLOR_DISABLED_BG = "#F5F5F5"
    
    # Spacing
    BRANCH_TO_CHECKBOX_GAP = 1
    CHECKBOX_TO_TEXT_PADDING = 4
    
    def paint(self, painter, option, index):
        # Draw background (selection, hover)
        # Draw custom checkbox with QPainter
        # Draw text
    
    def _draw_checkbox(self, painter, rect, state, hover=False):
        """Draw custom checkbox matching application style."""
        # Implementation based on §4.1
```

### §6.4 Dimension Constants

No new constants needed. Tree rows use existing `TABLE_CELL_HEIGHT` from [`src/constants/dimensions.py`](../../src/constants/dimensions.py).

---

## §7 Visual Comparison

### §7.1 Before (Unicode Characters)

```
Category Tree Row (Unicode checkbox):
┌─────────────────────────────────────┐
│ ▶ ☐ Category Name                   │
└─────────────────────────────────────┘
  ↑ 0px padding (matches table)

Checkbox: Unicode character ☐ (U+2610) or ☒ (U+2612)
- Not visually consistent with application style
- Gray color doesn't match primary blue
- No hover feedback
```

### §7.2 After (Custom Drawn)

```
Category Tree Row (custom checkbox):
┌─────────────────────────────────────┐
│ ▶ [✓] Category Name                 │
└─────────────────────────────────────┘
  ↑ 0px padding (matches table)

Checkbox: Custom drawn 14×14px box
- Unchecked: White fill, gray border (#C0C0C0)
- Checked: Blue fill (#0066CC), white checkmark
- Partially: Light blue fill (#DCEBF7), blue minus
- Hover: Darker border or darker fill
```

### §7.3 Log Table Row (Reference)

```
Log Table Row:
┌─────────────────────────────────────┐
│ 10:00:00 │ CAT │ MSG │ Message...  │
└─────────────────────────────────────┘
  ↑ 0px padding (reference)
```

---

## §8 Testing Requirements

### §8.1 Visual Regression Tests

- [ ] Tree row height matches table row height
- [ ] Tree row padding is zero (no extra space)
- [ ] Checkbox is vertically centered in row
- [ ] Text is vertically centered in row
- [ ] Hover state displays correctly
- [ ] Selected state displays correctly
- [ ] Branch indicators display correctly
- [ ] Deep nesting displays correctly

### §8.2 Cross-Platform Tests

- [ ] macOS: Font rendering matches table
- [ ] Windows: Font rendering matches table
- [ ] Linux: Font rendering matches table
- [ ] High DPI: Scaling is correct

### §8.3 Accessibility Tests

- [ ] Text contrast meets WCAG AA (8.6:1 minimum)
- [ ] Selected text contrast meets WCAG AA (15:1 minimum)
- [ ] Keyboard navigation works correctly
- [ ] Screen reader announces items correctly

---

## §9 Migration Notes

### §9.1 Breaking Changes

None. This is a visual change only with no API impact.

### §9.2 Compatibility

- **Qt Version:** Compatible with PySide6 6.0+
- **Platform:** Compatible with all platforms (macOS, Windows, Linux)
- **High DPI:** Compatible with high DPI displays

---

## §10 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.7 | 2026-03-16 | Changed checkbox design to dark gray (#666666) minimalist flat style |
| 1.6 | 2026-03-16 | Updated indentation from 14px to 10px for more compact layout |
| 1.5 | 2026-03-16 | Changed checkbox from Unicode characters to custom drawn checkboxes matching application style (primary blue #0066CC) |
| 1.2 | 2026-03-16 | Added U+25A3 (▣) for partially checked state |
| 1.1 | 2026-03-16 | Changed checkbox rendering from custom drawing to Unicode characters (U+2610 ☐, U+2612 ☒) |
| 1.0 | 2026-03-16 | Initial specification for unified tree/table row styles |

---

## §11 Implementation Checklist

- [ ] Update `src/styles/stylesheet.py`:
  - [ ] Change tree item padding to 0
  - [ ] Remove `QTreeView::indicator` styles (no longer needed)
- [ ] Refactor `src/views/delegates/category_item_delegate.py`:
  - [ ] Implement custom checkbox drawing with QPainter
  - [ ] Add `_draw_checkbox()` method with state-based colors
  - [ ] Add `_draw_checkmark()` method for checked state
  - [ ] Add `_draw_minus_sign()` method for partially checked state
  - [ ] Use application colors: `#0066CC` (primary blue), `#C0C0C0` (border gray)
  - [ ] Add hover state support (darker border for unchecked, darker fill for checked)
  - [ ] Add `CHECKBOX_SIZE = 14` and `CHECKBOX_BORDER_RADIUS = 2` constants
- [ ] Update `docs/specs/features/category-panel-styles.md`:
  - [ ] Update §5.1 padding values
  - [ ] Update §7.4 checkbox states (custom drawn)
- [ ] Verify visual appearance:
  - [ ] Tree row height matches table row height
  - [ ] Checkbox is 14×14px with 2px border radius
  - [ ] Checked state: blue fill (#0066CC) with white checkmark
  - [ ] Unchecked state: white fill with gray border (#C0C0C0)
  - [ ] Partially checked: light blue fill (#DCEBF7) with blue minus sign
  - [ ] Hover states work correctly
- [ ] Test on all platforms:
  - [ ] macOS: Custom checkboxes render correctly
  - [ ] Windows: Custom checkboxes render correctly
  - [ ] Linux: Custom checkboxes render correctly
- [ ] Test accessibility:
  - [ ] Screen reader announces checkbox state
  - [ ] Keyboard navigation works correctly

---

## §12 Cross-References

- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md) - Complete panel styling, tabs, buttons
- **Table Unified Styles:** [table-unified-styles.md](table-unified-styles.md) - Reference for table row styles
- **UI Design System:** [ui-design-system.md](ui-design-system.md) - Colors, typography, dimensions
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py)
- **Delegate:** [`src/views/delegates/category_item_delegate.py`](../../src/views/delegates/category_item_delegate.py)
- **Stylesheet:** [`src/styles/stylesheet.py`](../../src/styles/stylesheet.py)