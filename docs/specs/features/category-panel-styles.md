# Category Panel Style Specification

**Version:** 1.0
**Last Updated:** 2026-03-15
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** READY

---

## §1 Overview

### §1.1 Purpose

This specification defines the complete visual style for the Category Panel component, including typography, color tokens, spatial characteristics, geometry, and all interactive states. It serves as the authoritative reference for refactoring and implementation.

### §1.2 Scope

- Category Panel container and layout
- Tab widget (Categories, Filters, Highlights tabs)
- Search input with icon
- Tree view with checkboxes
- Button bar (Check All, Uncheck All)
- All interactive states (default, hover, active, focus, disabled)
- Adaptive layout considerations

### §1.3 References

- **UI Components:** [ui-components.md](ui-components.md) §5
- **UI Design System:** [ui-design-system.md](ui-design-system.md)
- **Color Palette:** [color-palette.md](../global/color-palette.md) - Comprehensive color system
- **Typography System:** [typography-system.md](typography-system.md)
- **Checkbox Behavior:** [category-checkbox-behavior.md](category-checkbox-behavior.md)
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py)
- **Stylesheet:** [`src/styles/stylesheet.py`](../../src/styles/stylesheet.py)

---

## §2 Component Structure

### §2.1 Visual Hierarchy

```
CategoryPanel (QWidget)
├── QTabWidget
│   ├── Categories Tab (QWidget)
│   │   ├── Search Container (QHBoxLayout)
│   │   │   ├── Search Icon (QLabel, 20px fixed width)
│   │   │   └── Search Input (QLineEdit)
│   │   ├── Tree View (QTreeView)
│   │   │   └── QStandardItemModel
│   │   └── Button Bar (QWidget)
│   │       └── QHBoxLayout
│   │           ├── Check All Button (QPushButton)
│   │           └── Uncheck All Button (QPushButton)
│   ├── Filters Tab (QWidget)
│   │   └── FiltersTabContent
│   └── Highlights Tab (QWidget)
│       └── QLabel (placeholder)
```

### §2.2 Layout Parameters

| Element | Property | Value | Source |
|---------|----------|-------|--------|
| CategoryPanel | Margins | 0px (all sides) | Implementation |
| CategoryPanel | Spacing | 0px | Implementation |
| TabWidget | Document Mode | `True` | Implementation |
| Categories Tab | Margins | 4px (all sides) | Implementation |
| Categories Tab | Spacing | 4px | Implementation |
| Search Container | Margins | 0px (all sides) | Implementation |
| Search Container | Spacing | 4px | Implementation |
| Button Bar | Margins | 4px (all sides) | Implementation |
| Button Bar | Spacing | 4px | Implementation |
| Filters Tab | Margins | 4px (all sides) | Implementation |

---

## §3 Typography

### §3.1 Font Families

| Element | Font Family | Source |
|---------|-------------|--------|
| Tab Labels | System UI Font | `Typography.PRIMARY` |
| Search Input | System UI Font | `Typography.PRIMARY` |
| Search Placeholder | System UI Font | `Typography.PRIMARY` |
| Tree Items | System UI Font | `Typography.PRIMARY` |
| Button Labels | System UI Font | `Typography.PRIMARY` |

**Implementation:**
```python
from src.constants.typography import Typography

font_family = Typography.PRIMARY  # '"SF Pro Text"' on macOS, '"Segoe UI"' on Windows
```

### §3.2 Font Sizes

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Tab Labels | System Default | Normal (400) | Inherit from application |
| Search Input | System Default | Normal (400) | Inherit from application |
| Tree Items | System Default | Normal (400) | Inherit from application |
| Button Labels | System Default | Normal (400) | Inherit from application |
| Search Icon | 14pt (emoji) | N/A | Unicode magnifying glass |

**Note:** All font sizes use Qt's system default. See [typography-system.md](typography-system.md) for details.

### §3.3 Text Colors

| Element | State | Color | Token |
|---------|-------|-------|-------|
| Tab Labels | Default | `#333333` | Primary Text |
| Tab Labels | Selected | `#333333` | Primary Text |
| Tab Labels | Disabled | `#999999` | Disabled Text |
| Search Input | Default | `#333333` | Primary Text |
| Search Placeholder | Default | `#666666` | Secondary Text |
| Tree Items | Default | `#333333` | Primary Text |
| Tree Items | Selected | `#000000` | Selection Text |
| Tree Items | Disabled | `#999999` | Disabled Text |
| Button Labels | Default | `#333333` | Primary Text |
| Button Labels | Disabled | `#999999` | Disabled Text |

---

## §4 Color Tokens

### §4.1 Background Colors

| Element | State | Color | Token | Usage |
|---------|-------|-------|-------|-------|
| CategoryPanel | Default | `#F0F0F0` | Background Tertiary | Inherited from parent |
| TabWidget Pane | Default | `#FFFFFF` | Background Primary | Content area |
| Tab Bar | Default | `#E8E8E8` | Background Hover | Inactive tabs |
| Tab Bar | Selected | `#F0F0F0` | Background Tertiary | Active tab |
| Tab Bar | Hover | `#F0F0F0` | Background Tertiary | Hover on inactive |
| Search Input | Default | `#FFFFFF` | Background Primary | Input field |
| Search Input | Focus | `#FFFFFF` | Background Primary | Focused state |
| Search Input | Disabled | `#F5F5F5` | Background Secondary | Disabled state |
| Tree View | Default | `#F5F5F5` | Background Secondary | Tree background |
| Tree Item | Default | Transparent | - | Default items |
| Tree Item | Hover | `#E8E8E8` | Background Hover | Hovered items |
| Tree Item | Selected | `#DCEBF7` | Selection Highlight | Selected items |
| Button | Default | `#F5F5F5` | Background Secondary | Normal state |
| Button | Hover | `#E8E8E8` | Background Hover | Hovered state |
| Button | Active | `#D0D0D0` | Background Active | Pressed state |
| Button | Disabled | `#F5F5F5` | Background Secondary | Disabled state |

### §4.2 Border Colors

| Element | State | Color | Token | Width |
|---------|-------|-------|-------|-------|
| TabWidget Pane | Default | `#C0C0C0` | Border Default | 1px |
| Tab (inactive) | Default | None | - | - |
| Tab (selected) | Bottom | `#0066CC` | Primary Blue | 2px |
| Search Input | Default | `#C0C0C0` | Border Default | 1px |
| Search Input | Focus | `#0066CC` | Primary Blue | 1px |
| Search Input | Disabled | `#C0C0C0` | Border Default | 1px |
| Tree View | Default | None | - | - |
| Tree Item | Default | None | - | - |
| Button | Default | `#C0C0C0` | Border Default | 1px |
| Button | Hover | `#A0A0A0` | Border Hover | 1px |
| Button | Active | `#A0A0A0` | Border Hover | 1px |
| Button | Disabled | `#D0D0D0` | Border Disabled | 1px |

### §4.3 Checkbox Colors

| State | Border | Background | Checkmark | Source |
|-------|--------|------------|-----------|--------|
| Unchecked | `#A0A0A0` | `#FFFFFF` | N/A | ui-design-system.md §4.4 |
| Checked | `#0066CC` | `#0066CC` | White | ui-design-system.md §4.4 |
| Partially Checked | `#0066CC` | `#DCEBF7` | Partial indicator | ui-design-system.md §4.4 |

**Note:** Partially checked state is not currently used in the implementation but is defined for future use.

---

## §5 Spatial Characteristics

### §5.1 Padding

| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| TabWidget Pane | Padding | 0px | Content area padding |
| Tab Label | Padding | 6px 16px | Top/bottom, left/right |
| Search Input | Padding | 4px 6px | Top/bottom, left/right |
| Tree Item | Padding | 0px | **Zero padding** - unified with table rows (see [category-tree-row-unification.md](category-tree-row-unification.md)) |
| Button | Padding | 4px 12px | Top/bottom, left/right |
| Categories Tab | Padding | 4px | Container padding |

### §5.2 Margins

| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| Tab Bar | Margin Right | 2px | Between tabs |
| Search Icon | Margin Right | 4px | Gap before input |
| Button Bar | Margin | 4px | Container margins |

### §5.3 Gap/Spacing

| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| Categories Tab | Spacing | 4px | Between children |
| Search Container | Spacing | 4px | Between icon and input |
| Button Bar | Spacing | 4px | Between buttons |
| Tab Bar | Spacing | 2px | Between tabs (margin-right) |
| Tree Branch to Checkbox | Spacing | 1px | Gap via QTreeView::indicator margin-left |

### §5.4 Indentation

| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| Tree View | Indentation | Dynamic | Per level depth (QStyle.PM_IndicatorWidth + 4px gap) |
| Tree Branch | Indentation | Dynamic | Controlled via `TREE_INDENTATION` constant |

---

## §6 Geometry

### §6.1 Dimensions

| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| CategoryPanel | Min Width | None | Determined by splitter |
| CategoryPanel | Default Width | 25% | Splitter ratio (SPLITTER_RIGHT_RATIO) |
| Search Icon | Fixed Width | 20px | Implementation |
| Search Icon | Fixed Height | Auto | Text height |
| Search Input | Min Width | None | Expands to fill |
| Search Input | Height | Auto | Text height + padding |
| Tree View | Min Height | None | Expands to fill |
| Button | Min Width | 60px | ui-design-system.md §4.1.1 |
| Button | Height | Auto | Text height + padding |
| Checkbox | Width | Auto | Unicode character (font size) |
| Checkbox | Height | Auto | Unicode character (font size) |

**Note:** Checkboxes are rendered as Unicode characters (U+2610 ☐, U+2612 ☒), so their size is determined by the font size rather than fixed pixel dimensions. See [category-tree-row-unification.md](category-tree-row-unification.md) §4 for details.

### §6.2 Border Radius

| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| TabWidget Pane | Border Radius | 0px | Rectangular |
| Tab Labels | Border Radius | 0px | Rectangular (bottom border only) |
| Search Input | Border Radius | 3px | Rounded corners |
| Tree View | Border Radius | 0px | Rectangular |
| Button | Border Radius | 3px | Rounded corners |
| Checkbox | Border Radius | 0px | Square |

### §6.3 Tree View Properties

| Property | Value | Notes |
|----------|-------|-------|
| Header Hidden | `True` | No header row |
| Root Is Decorated | `True` | Show expand/collapse indicators |
| Animated | `True` | Smooth expand/collapse |
| Uniform Row Heights | `True` | Performance optimization |
| Selection Mode | `SingleSelection` | One item at a time |
| Edit Triggers | `NoEditTriggers` | Read-only |
| Horizontal Scroll Bar | `ScrollBarAlwaysOff` | No horizontal scroll |

---

## §7 States

### §7.1 Tab States

| State | Background | Border | Text Color | Notes |
|-------|-------------|--------|------------|-------|
| Default | `#E8E8E8` | None | `#333333` | Inactive tab |
| Selected | `#F0F0F0` | Bottom: 2px `#0066CC` | `#333333` | Active tab |
| Hover (inactive) | `#F0F0F0` | None | `#333333` | Hover on inactive |
| Disabled | `#E8E8E8` | None | `#999999` | Disabled tab |

**QSS Implementation:**
```css
QTabBar::tab {
    background-color: #E8E8E8;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 16px;
    margin-right: 2px;
    color: #333333;
}

QTabBar::tab:selected {
    background-color: #F0F0F0;
    border-bottom: 2px solid #0066CC;
}

QTabBar::tab:hover:!selected {
    background-color: #F0F0F0;
}

QTabBar::tab:disabled {
    color: #999999;
}
```

### §7.2 Search Input States

| State | Background | Border | Text Color | Notes |
|-------|-------------|--------|------------|-------|
| Default | `#FFFFFF` | 1px `#C0C0C0` | `#333333` | Normal state |
| Focus | `#FFFFFF` | 1px `#0066CC` | `#333333` | Focused for input |
| Disabled | `#F5F5F5` | 1px `#C0C0C0` | `#999999` | Disabled state |
| Error | `#FFFFFF` | 1px `#CC0000` | `#333333` | Validation error (future) |

**QSS Implementation:**
```css
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #C0C0C0;
    border-radius: 3px;
    padding: 4px 6px;
    color: #333333;
}

QLineEdit:focus {
    border: 1px solid #0066CC;
}

QLineEdit:disabled {
    background-color: #F5F5F5;
    color: #999999;
}
```

### §7.3 Tree Item States

Tree item styling is unified with log table row styling. See [category-tree-row-unification.md](category-tree-row-unification.md) for complete specification.

**Summary:**

| State | Background | Text Color | Notes |
|-------|-------------|------------|-------|
| Default | Transparent | `#333333` | Normal items |
| Hover | `#E8E8E8` | `#333333` | Mouse over |
| Selected | `#DCEBF7` | `#000000` | Selection |
| Disabled | Transparent | `#999999` | Disabled items |

**Key differences from table:**
- Background is transparent (not `#B6B6B6`) to show tree background
- Hover state uses `#E8E8E8` for visual feedback during navigation

### §7.3.1 Branch Indicators

Branch indicators (expand/collapse arrows) are controlled via `QTreeView.setIndentation()`. The indentation value controls both the branch indicator width and the child item offset.

| Property | Value | Notes |
|----------|-------|-------|
| Indentation | 10px | Set via `setIndentation(10)` - controls branch width + child offset |
| Visual Appearance | ▶ / ▼ | Collapsed / Expanded |
| Color | `#333333` | Primary text color (inherited from QTreeView) |
| Checkbox Spacing | 1px | Handled by CategoryItemDelegate |

**Implementation:**
```python
# In CategoryPanel._setup_ui()
# Ref: docs/specs/features/category-panel-styles.md §5.4
# Indentation controls branch indicator width + child offset
self._tree_view.setIndentation(10)
```

**Note:** Qt's default indentation is 16px. Reducing to 10px makes the branch indicator area more compact while still providing adequate visual separation for nested items.

### §7.4 Checkbox States

Checkboxes are custom drawn by `CategoryItemDelegate` using QPainter. See [category-tree-row-unification.md](category-tree-row-unification.md) §4 for complete specification.

**Summary:**

| State | Border | Background | Checkmark | Size |
|-------|--------|------------|-----------|------|
| Unchecked | `#666666` | `#FFFFFF` | N/A | 12×12px |
| Checked | `#666666` | `#666666` | White ✓ | 12×12px |
| Partially Checked | `#666666` | `#E0E0E0` | `#666666` (─) | 12×12px |
| Hover (Unchecked) | `#555555` | `#FFFFFF` | N/A | 12×12px |
| Hover (Checked) | `#555555` | `#555555` | White ✓ | 12×12px |
| Disabled | `#B0B0B0` | `#F5F5F5` | N/A | 12×12px |

**Benefits of custom drawing:**
- Minimalist, flat design with dark gray (#666666) color scheme
- Clear visual difference between all three states
- Hover feedback for better UX
- High contrast for accessibility

### §7.5 Button States

| State | Background | Border | Text Color | Notes |
|-------|-------------|--------|------------|-------|
| Default | `#F5F5F5` | 1px `#C0C0C0` | `#333333` | Normal state |
| Hover | `#E8E8E8` | 1px `#A0A0A0` | `#333333` | Mouse over |
| Active/Pressed | `#D0D0D0` | 1px `#A0A0A0` | `#333333` | Mouse down |
| Focus | `#F5F5F5` | 1px `#0066CC` | `#333333` | Keyboard focus |
| Disabled | `#F5F5F5` | 1px `#D0D0D0` | `#999999` | Disabled state |

**QSS Implementation:**
```css
QPushButton {
    background-color: #F5F5F5;
    border: 1px solid #C0C0C0;
    border-radius: 3px;
    padding: 4px 12px;
    min-width: 60px;
    color: #333333;
}

QPushButton:hover {
    background-color: #E8E8E8;
    border: 1px solid #A0A0A0;
}

QPushButton:pressed {
    background-color: #D0D0D0;
}

QPushButton:focus {
    border: 1px solid #0066CC;
}

QPushButton:disabled {
    background-color: #F5F5F5;
    color: #999999;
    border: 1px solid #D0D0D0;
}
```

---

## §8 Adaptive Layout

### §8.1 Panel Width

The Category Panel width is controlled by the splitter ratio:

| Property | Value | Source |
|----------|-------|--------|
| Default Width | 25% of window | SPLITTER_RIGHT_RATIO |
| Minimum Width | None specified | Implementation |
| Resize Behavior | Proportional | Splitter handles resize |

**Implementation:**
```python
from src.constants.dimensions import SPLITTER_RIGHT_RATIO

# Splitter ratio: 75% log table, 25% category panel
SPLITTER_LEFT_RATIO = 75
SPLITTER_RIGHT_RATIO = 25
```

### §8.2 Responsive Considerations

| Scenario | Behavior | Notes |
|----------|----------|-------|
| Window Resize | Panel resizes proportionally | Maintains 25% ratio |
| Small Window | Panel may collapse | Future: minimum width |
| Large Window | Panel expands proportionally | Maintains ratio |
| High DPI | Fonts scale automatically | Qt handles scaling |

### §8.3 Text Overflow

| Element | Overflow Behavior | Notes |
|---------|-------------------|-------|
| Tab Labels | Ellipsis | Qt default |
| Search Input | Scroll | QLineEdit default |
| Tree Items | Ellipsis | Qt default |
| Button Labels | Ellipsis | Qt default |

### §8.4 Scroll Behavior

| Element | Scroll Policy | Notes |
|---------|---------------|-------|
| Tree View (Vertical) | `ScrollBarAsNeeded` | Default Qt behavior |
| Tree View (Horizontal) | `ScrollBarAlwaysOff` | Disabled in implementation |
| Search Input | No scroll | Single line |

---

## §9 Accessibility

### §9.1 Color Contrast

| Element | Foreground | Background | Ratio | Status |
|---------|------------|------------|-------|--------|
| Tab Label (default) | `#333333` | `#E8E8E8` | 10.5:1 | ✅ Pass |
| Tab Label (selected) | `#333333` | `#F0F0F0` | 11.2:1 | ✅ Pass |
| Search Input | `#333333` | `#FFFFFF` | 12.6:1 | ✅ Pass |
| Tree Item (default) | `#333333` | `#F5F5F5` | 11.0:1 | ✅ Pass |
| Tree Item (selected) | `#000000` | `#DCEBF7` | 15.8:1 | ✅ Pass |
| Button Label | `#333333` | `#F5F5F5` | 11.0:1 | ✅ Pass |
| Disabled Text | `#999999` | `#F5F5F5` | 3.5:1 | ⚠️ Borderline |

### §9.2 Keyboard Navigation

| Shortcut | Action | Context |
|----------|--------|---------|
| `Tab` | Next focusable element | Global |
| `Shift+Tab` | Previous focusable element | Global |
| `Up/Down` | Navigate tree items | Tree focused |
| `Left/Right` | Collapse/Expand | Tree focused |
| `Space` | Toggle checkbox | Tree item focused |
| `Enter` | Apply search | Search input focused |
| `Escape` | Clear search | Search input focused |

### §9.3 Focus Indicators

| Element | Focus Indicator | Color |
|---------|-----------------|-------|
| Tab | Bottom border | `#0066CC` (2px) |
| Search Input | Border | `#0066CC` (1px) |
| Tree Item | Selection background | `#DCEBF7` |
| Button | Border | `#0066CC` (1px) |

---

## §10 Animation

### §10.1 Tree Expand/Collapse

| Property | Value | Notes |
|----------|-------|-------|
| Duration | 200ms | Qt default |
| Easing | Linear | Qt default |
| Property | Height | Animated by QTreeView |

**Implementation:**
```python
self._tree_view.setAnimated(True)
```

### §10.2 Tab Switch

| Property | Value | Notes |
|----------|-------|-------|
| Duration | Immediate | No animation |
| Transition | None | Instant switch |

### §10.3 Hover Transitions

| Element | Duration | Notes |
|---------|----------|-------|
| Tab Hover | Immediate | No animation |
| Tree Item Hover | Immediate | No animation |
| Button Hover | Immediate | No animation |
| Checkbox Hover | Immediate | No animation |

---

## §11 Migration Guide

### §11.1 Color Constants

This specification uses the new layered color architecture defined in [color-palette.md](../global/color-palette.md).

| Legacy Constant | New Constant | Usage |
|-----------------|--------------|-------|
| `TABLE_ROW_BACKGROUND` | `PaletteColors.GRAY_2` | Table row background |
| `SELECTION_HIGHLIGHT_COLOR` | `UIColors.BACKGROUND_SELECTED` | Selection highlight |
| `BORDER_COLOR` | `UIColors.BORDER_DEFAULT` | Default borders |
| `HEADER_BACKGROUND` | `UIColors.BACKGROUND_TERTIARY` | Header background |
| `FIND_HIGHLIGHT_COLOR` | `UIColors.FIND_HIGHLIGHT` | Search highlight |
| `DEFAULT_TEXT_COLOR` | `BaseColors.BLACK` | Default text |
| `SECONDARY_TEXT_COLOR` | `UIColors.TEXT_SECONDARY` | Secondary text |
| `PRIMARY_BLUE` | `UIColors.BORDER_FOCUS` | Primary blue (focus) |
| `BACKGROUND_HOVER` | `UIColors.BACKGROUND_HOVER` | Hover background |

See [color-palette.md](../global/color-palette.md) §8.2.1 for complete migration guide.

### §11.2 Implementation Example

```python
# Before (legacy constants)
from src.constants.colors import (
    SELECTION_HIGHLIGHT_COLOR,
    SECONDARY_TEXT_COLOR,
    BORDER_COLOR,
)

# After (new layered architecture)
from src.constants.colors import (
    UIColors,
    BaseColors,
)

# Selection highlight
selection = UIColors.BACKGROUND_SELECTED  # #DCEBF7

# Secondary text
text = UIColors.TEXT_SECONDARY  # #666666

# Default border
border = UIColors.BORDER_DEFAULT  # #C0C0C0
```

---

## §12 Implementation Reference

### §11.1 Stylesheet Functions

The following functions from [`stylesheet.py`](../../src/styles/stylesheet.py) are used:

```python
from src.styles.stylesheet import get_tab_stylesheet, get_tree_stylesheet

# Tab widget styling
self._tab_widget.setStyleSheet(get_tab_stylesheet())

# Tree view styling
self._tree_view.setStyleSheet(get_tree_stylesheet())
```

### §11.2 Color Constants

Colors are defined in [`colors.py`](../../src/constants/colors.py):

```python
from src.constants.colors import (
    SELECTION_HIGHLIGHT_COLOR,  # #dcebf7
    DEFAULT_TEXT_COLOR,          # #000000
    SECONDARY_TEXT_COLOR,        # #666666
    BORDER_COLOR,                # #CCCCCC
)
```

### §11.3 Typography Constants

Typography is defined in [`typography.py`](../../src/constants/typography.py):

```python
from src.constants.typography import Typography

# Font family for QSS
font_family = Typography.PRIMARY

# System font for QFont
font = Typography.UI_FONT
```

### §11.4 Dimension Constants

Dimensions are defined in [`dimensions.py`](../../src/constants/dimensions.py):

```python
from src.constants.dimensions import (
    SPLITTER_LEFT_RATIO,   # 75
    SPLITTER_RIGHT_RATIO,  # 25
)
```

---

## §12 Consistency Verification

### §12.1 Cross-Reference Check

| Specification | Element | Status | Notes |
|---------------|---------|--------|-------|
| ui-design-system.md §4.4 | Tree View | ✅ Consistent | Colors match |
| ui-design-system.md §4.5 | Tab Widget | ✅ Consistent | Colors match |
| ui-design-system.md §4.1 | Buttons | ✅ Consistent | Colors match |
| ui-design-system.md §4.2 | Input Fields | ✅ Consistent | Colors match |
| typography-system.md | Font Families | ✅ Consistent | Uses system fonts |
| category-checkbox-behavior.md | Checkbox Logic | ✅ Consistent | Visual states match |

### §12.2 Implementation Gap Analysis

| Element | Spec | Implementation | Status |
|---------|------|----------------|--------|
| Tab margins | 4px | 4px | ✅ Match |
| Search icon width | 20px | 20px | ✅ Match |
| Tree indentation | 16px | 16px (Qt default) | ✅ Match |
| Checkbox size | 14×14px | 14×14px | ✅ Match |
| Button min-width | 60px | Not specified | ⚠️ Add to implementation |
| Button padding | 4px 12px | Not specified | ⚠️ Add to implementation |

### §12.3 Missing Values

The following values were not explicitly defined in existing specs and are now specified:

| Element | Property | Value | Source |
|---------|----------|-------|--------|
| Search Icon | Fixed Width | 20px | Implementation analysis |
| Categories Tab | Margins | 4px | Implementation analysis |
| Categories Tab | Spacing | 4px | Implementation analysis |
| Button Bar | Margins | 4px | Implementation analysis |
| Button Bar | Spacing | 4px | Implementation analysis |
| Tree View | Horizontal Scroll | Always Off | Implementation analysis |
| Tree Branch to Checkbox | Spacing | 1px | margin-left on QTreeView::indicator |

---

## §13 Testing Requirements

### §13.1 Visual Regression Tests

| Test | Description |
|------|-------------|
| Tab States | Verify all tab states (default, selected, hover, disabled) |
| Search States | Verify all search input states (default, focus, disabled) |
| Tree States | Verify all tree item states (default, hover, selected) |
| Checkbox States | Verify all checkbox states (checked, unchecked, hover) |
| Button States | Verify all button states (default, hover, active, disabled) |

### §13.2 Accessibility Tests

| Test | Description |
|------|-------------|
| Color Contrast | Verify all text meets WCAG 2.1 AA contrast ratio |
| Keyboard Navigation | Verify all elements are keyboard accessible |
| Focus Indicators | Verify focus indicators are visible |
| Screen Reader | Verify accessible names for all elements |

### §13.3 Cross-Platform Tests

| Platform | Test |
|----------|------|
| macOS | Verify native font rendering |
| Windows | Verify native font rendering |
| High DPI | Verify scaling on high DPI displays |

---

## §14 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.15 | 2026-03-19 | Added migration guide for new color system, added cross-reference to color-palette.md |
| 1.14 | 2026-03-16 | Changed checkbox design to dark gray (#666666) minimalist flat style |
| 1.13 | 2026-03-16 | Updated indentation from 14px to 10px for more compact branch indicator |
| 1.12 | 2026-03-16 | Changed checkbox from Unicode characters to custom drawn checkboxes matching application style (primary blue #0066CC) |
| 1.9 | 2026-03-16 | Added explicit branch indicator width (16px) via QSS to reduce excessive default width (did not work - reverted in 1.10) |
| 1.8 | 2026-03-16 | Consolidated §7.3-7.4: removed duplicated content, now references category-tree-row-unification.md for tree item styles and checkbox implementation |
| 1.7 | 2026-03-16 | Added U+25A3 (▣) for partially checked state |
| 1.6 | 2026-03-16 | Changed checkbox rendering from custom drawing to Unicode characters (U+2610 ☐, U+2612 ☒) |
| 1.5 | 2026-03-16 | Updated tree item padding from 2px 4px to 0 to match table row styles (see category-tree-row-unification.md) |
| 1.4 | 2026-03-15 | Fixed branch-to-checkbox spacing: implemented CategoryItemDelegate for proper 1px gap (QSS margin-left does not work) |
| 1.3 | 2026-03-15 | Fixed branch-to-checkbox spacing: changed from QTreeView::branch margin-right to QTreeView::indicator margin-left (did not work) |
| 1.2 | 2026-03-15 | Updated branch-to-checkbox spacing to use QTreeView::branch margin-right approach (did not work) |
| 1.1 | 2026-03-15 | Added §7.3.1 Branch Indicators documentation |
| 1.0 | 2026-03-15 | Initial comprehensive style specification |

---

## §15 Cross-References

- **UI Design System:** [ui-design-system.md](ui-design-system.md)
- **UI Components:** [ui-components.md](ui-components.md) §5
- **Color Palette:** [color-palette.md](../global/color-palette.md) - Comprehensive color system
- **Typography System:** [typography-system.md](typography-system.md)
- **Checkbox Behavior:** [category-checkbox-behavior.md](category-checkbox-behavior.md)
- **Tree Row Unification:** [category-tree-row-unification.md](category-tree-row-unification.md) - Tree/table row style unification, Unicode checkboxes
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py)
- **Delegate:** [`src/views/delegates/category_item_delegate.py`](../../src/views/delegates/category_item_delegate.py)
- **Stylesheet:** [`src/styles/stylesheet.py`](../../src/styles/stylesheet.py)
- **Colors:** [`src/constants/colors.py`](../../src/constants/colors.py)
- **Dimensions:** [`src/constants/dimensions.py`](../../src/constants/dimensions.py)
- **Typography:** [`src/constants/typography.py`](../../src/constants/typography.py)