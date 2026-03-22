# Unified Table Styles Specification

**Version:** 1.0
**Last Updated:** 2026-03-15
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** DRAFT

---

## §1 Overview

This specification defines a unified styling system for the log table, ensuring visual consistency between the header and data rows. The design emphasizes a clean, professional appearance with clear visual hierarchy and optimal readability.

### §1.1 Design Philosophy

1. **Visual Unity**: Header and rows share the same fundamental styling language
2. **Clear Hierarchy**: Subtle differentiation through background shades, not dramatic contrast
3. **Readability**: Optimal typography, spacing, and contrast for log viewing
4. **Simplicity**: Clean, uniform white background for all rows
5. **Accessibility**: WCAG 2.1 AA compliant color contrast ratios
6. **Performance**: Efficient QSS selectors, minimal repaint operations

### §1.2 Scope

This specification covers:
- Table header styling
- Table row styling (normal, selected, hover states)
- Typography for all table cells
- Spacing and padding conventions
- Border and grid line styling

### §1.3 Cross-References

- **UI Design System (Typography):** [ui-design-system.md](ui-design-system.md) §2.2
- **UI Design System (Colors):** [ui-design-system.md](ui-design-system.md) §2.1
- **UI Design System (Layout):** [ui-design-system.md](ui-design-system.md) §3
- **Color Palette:** [color-palette.md](../global/color-palette.md) - Comprehensive color system
- **Table Column Alignment:** [table-column-alignment.md](table-column-alignment.md)
- **Table Text Overflow:** [table-cell-text-overflow.md](table-cell-text-overflow.md)
- **Colors Implementation:** [src/constants/colors.py](../../src/constants/colors.py)
- **Dimensions Implementation:** [src/constants/dimensions.py](../../src/constants/dimensions.py)

---

## §2 Typography

### §2.1 Font System

The table uses the unified typography system defined in [ui-design-system.md](ui-design-system.md) §2.2.

| Element | Font Family | Source |
|---------|-------------|--------|
| Header Text | System UI Font | `Typography.PRIMARY` |
| Row Text (Time, Category, Type) | System UI Font | `Typography.PRIMARY` |
| Row Text (Message) | System Monospace | `Typography.MONOSPACE` |

**Font Family Values:**

| Platform | UI Font | Monospace Font |
|----------|---------|----------------|
| macOS | SF Pro Text | Menlo |
| Windows | Segoe UI | Consolas |
| Linux | Sans Serif | Monospace |

### §2.2 Font Properties

#### §2.2.1 Header Typography

| Property | Value | Notes |
|----------|-------|-------|
| `font-family` | `Typography.PRIMARY` | System UI font |
| `font-size` | System default | No hardcoding |
| `font-weight` | `normal` (400) | Regular weight |
| `font-style` | `normal` | No italics |
| `line-height` | `1.0` | Compact for table |
| `text-align` | `center` | Centered column headers |

#### §2.2.2 Row Typography

| Property | Value | Notes |
|----------|-------|-------|
| `font-family` | `Typography.PRIMARY` (Time, Category, Type) | System UI font |
| `font-family` | `Typography.MONOSPACE` (Message) | Monospace for logs |
| `font-size` | System default | No hardcoding |
| `font-weight` | `normal` (400) | Regular weight |
| `font-style` | `normal` | No italics |
| `line-height` | `1.0` | Compact for table |

### §2.3 Text Colors

| Element | State | Color | Hex | Contrast Ratio |
|---------|-------|-------|-----|----------------|
| Header Text | Default | Primary Text | #333333 | 10.2:1 (on #F5F5F5) |
| Row Text | Default | Primary Text | #333333 | 8.6:1 (on #B6B6B6) |
| Row Text | Selected | Selection Text | #000000 | 21:1 (on #DCEBF7) |
| Row Text | Hover | Primary Text | #333333 | 8.6:1 (on #B6B6B6) |
| Row Text | Disabled | Disabled Text | #999999 | 3.5:1 (on #B6B6B6) |

---

## §3 Spacing and Dimensions

### §3.1 Cell Padding

All table cells (header and rows) use zero padding for maximum information density:

| Side | Value | Description |
|------|-------|-------------|
| `padding-top` | `0` | No top padding |
| `padding-right` | `0` | No right padding |
| `padding-bottom` | `0` | No bottom padding |
| `padding-left` | `0` | No left padding |

**Shorthand:** `padding: 0;`

**Rationale:** Zero padding allows maximum rows visible in the viewport, which is critical for log viewing applications where users need to scan many entries quickly.

### §3.2 Unified Cell Height

**Header and rows use the SAME height** for visual consistency. A single constant defines the height for all table cells:

| Element | Height Calculation | Typical Value |
|---------|-------------------|----------------|
| All Cells (Header + Rows) | `QFontMetrics.height() + 2px` | ~18-22px |

**Implementation:**
```python
from src.constants.typography import Typography

# Single height for both header and rows
TABLE_CELL_HEIGHT = Typography.TABLE_CELL_HEIGHT  # font metrics + 2px
```

**Note:** The previous implementation had separate `TABLE_ROW_HEIGHT` and `TABLE_HEADER_HEIGHT` constants. These have been unified into a single `TABLE_CELL_HEIGHT` constant because:
1. Header and rows share the same visual style
2. Same font size is used for both
3. Same padding (zero) is applied to both
4. Reduces code complexity and ensures consistency

**Migration:**
```python
# Before (two separate constants)
TABLE_ROW_HEIGHT = Typography.TABLE_ROW_HEIGHT      # ❌ Remove
TABLE_HEADER_HEIGHT = Typography.TABLE_HEADER_HEIGHT  # ❌ Remove

# After (single unified constant)
TABLE_CELL_HEIGHT = Typography.TABLE_CELL_HEIGHT    # ✅ Use this
```

### §3.3 Column Widths

Column widths are automatically sized based on content on initial file load.
See [table-column-auto-size.md](table-column-auto-size.md) for complete specification.

| Column | Auto-Size | Minimum | Maximum | Behavior |
|--------|-----------|---------|---------|----------|
| Time | Yes | 60px | None | Fixed format "HH:MM:SS.mmm" |
| Category | Yes | 50px | 300px | Sample first 100 entries |
| Type | Yes | 30px | None | Single icon character |
| Message | No | 100px | None | Stretches to fill space |

**Note:** Users can manually resize columns after auto-size. Manual adjustments are
preserved across file loads via SettingsManager.

---

## §4 Background Colors

### §4.1 Header Background

The header does NOT react to mouse interactions. It maintains a static appearance regardless of hover state.

| Visual State | Background | Border | Notes |
|--------------|------------|--------|-------|
| Default (all states) | #F5F5F5 | Bottom: #C0C0C0 | Light gray, static |
| Hover (mouse over) | #F5F5F5 | Bottom: #C0C0C0 | **No change** - header ignores mouse |

**Rationale:** The table header serves as a static label area. Unlike data rows, it should not provide hover feedback because:
1. Header is not selectable or interactive in the same way as data rows
2. Consistent appearance reduces visual noise during scrolling
3. Clear separation between interactive (rows) and non-interactive (header) areas

### §4.2 Row Backgrounds

#### §4.2.1 Normal State

| Row Type | Background | Notes |
|----------|------------|-------|
| All Rows | #B6B6B6 | Gray background |

**Rationale:** Gray background provides subtle visual separation from the white header (#F5F5F5) and improves readability in various lighting conditions.

#### §4.2.2 Selected State

| Row Type | Background | Text Color | Notes |
|----------|------------|------------|-------|
| Selected | #DCEBF7 | #000000 | Light blue selection |

#### §4.2.3 Hover State

| Row Type | Background | Notes |
|----------|------------|-------|
| Hover | #B6B6B6 | Same as default (no visual change) |

#### §4.2.4 Log Level Backgrounds (Optional)

When log level highlighting is enabled, only error-related levels have special backgrounds. Normal log levels (MSG, DEBUG, TRACE) display as regular rows with no visual distinction.

| Level | Background | Text Color | Notes |
|-------|------------|------------|-------|
| CRITICAL | #FF6B6B | #000000 | Red background - critical errors |
| ERROR | #FF8C8C | #000000 | Light red background - errors |
| WARNING | #FFD93D | #000000 | Yellow background - warnings |
| MSG | #B6B6B6 | #333333 | Same as default (no visual change) |
| DEBUG | #B6B6B6 | #333333 | Same as default (no visual change) |
| TRACE | #B6B6B6 | #333333 | Same as default (no visual change) |

**Rationale:** Only error-related levels (CRITICAL, ERROR, WARNING) require visual highlighting to draw attention. Normal operational messages (MSG, DEBUG, TRACE) should not distract from important errors and display as regular rows.

**Implementation:** [`LogColors`](../../src/constants/colors.py)

---

## §5 Borders and Grid Lines

### §5.1 Header Borders

| Border | Style | Color | Width |
|--------|-------|-------|-------|
| Bottom | Solid | #C0C0C0 | 1px |
| Right (between columns) | Solid | #E0E0E0 | 1px |

**QSS:**
```css
QHeaderView::section {
    border: none;
    border-bottom: 1px solid #C0C0C0;
    border-right: 1px solid #E0E0E0;
}
```

### §5.2 Row Borders

| Border | Style | Color | Width |
|--------|-------|-------|-------|
| Bottom | Solid | #E0E0E0 | 1px |

**QSS:**
```css
QTableWidget::item {
    border: none;
    border-bottom: 1px solid #E0E0E0;
}
```

### §5.3 Grid Lines

| Grid Type | Color | Style |
|-----------|-------|-------|
| Vertical | #E0E0E0 | Light gray |
| Horizontal | #E0E0E0 | Light gray |

**QSS:**
```css
QTableWidget {
    gridline-color: #E0E0E0;
}
```

### §5.4 Table Border

| Border | Style | Color | Width |
|--------|-------|-------|-------|
| All sides | Solid | #C0C0C0 | 1px |

**QSS:**
```css
QTableWidget {
    border: 1px solid #C0C0C0;
}
```

---

## §6 Alignment

### §6.1 Horizontal Alignment

| Column | Alignment | Rationale |
|--------|-----------|-----------|
| Time | `center` | Fixed-width timestamps look centered |
| Category | `left` | Text content, left-aligned for readability |
| Type | `center` | Log level icons/short text, centered |
| Message | `left` | Log message text, left-aligned for readability |

### §6.2 Vertical Alignment

All cells use `center` vertical alignment for optimal visual balance.

**Implementation:**
```python
# In LogTableModel.data() or delegate
option.displayAlignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
```

---

## §7 States and Interactions

### §7.1 State Matrix

| Visual State | Background | Border | Text Color | Cursor |
|--------------|------------|--------|------------|--------|
| Default (normal) | #B6B6B6 | #E0E0E0 | #333333 | Default |
| Hover (mouse over) | #B6B6B6 | #E0E0E0 | #333333 | Default |
| Selected (clicked) | #DCEBF7 | #E0E0E0 | #000000 | Default |
| Selected + Hover | #DCEBF7 | #E0E0E0 | #000000 | Default |

### §7.2 Header State Matrix

The header does NOT react to mouse hover. Only the sorted state changes appearance.

| Visual State | Background | Border | Text Color | Notes |
|--------------|------------|--------|------------|-------|
| Default (normal) | #F5F5F5 | #C0C0C0 (bottom) | #333333 | Static appearance |
| Hover (mouse over) | #F5F5F5 | #C0C0C0 (bottom) | #333333 | **No visual change** |
| Sorted (column clicked) | #E8E8E8 | #C0C0C0 (bottom) | #333333 | Visual feedback for sort |

### §7.3 Selection Behavior

- **Single Selection:** Click on a row selects it
- **Multi Selection:** Ctrl+Click adds to selection
- **Range Selection:** Shift+Click selects range
- **Selection Color:** Unified #DCEBF7 regardless of zebra striping

---

## §8 Complete QSS Specification

### §8.1 Header Styles

```css
/* Table Header - Unified with Row Style */
QHeaderView::section {
    /* Typography */
    font-family: {Typography.PRIMARY};
    font-weight: normal;
    font-size: inherit;
    
    /* Spacing */
    padding: 0;
    
    /* Background - Static, no hover effect */
    background-color: #F5F5F5;
    
    /* Borders */
    border: none;
    border-bottom: 1px solid #C0C0C0;
    border-right: 1px solid #E0E0E0;
    
    /* Alignment */
    text-align: center;
}

/* NOTE: No :hover pseudo-class - header does NOT react to mouse */

/* Last column - no right border */
QHeaderView::section:last {
    border-right: none;
}
```

### §8.2 Row Styles

```css
/* Table View Container */
QTableWidget {
    /* Background */
    background-color: #B6B6B6;
    
    /* Borders */
    border: 1px solid #C0C0C0;
    gridline-color: #E0E0E0;
    
    /* Selection */
    selection-background-color: #DCEBF7;
    selection-color: #000000;
}

/* Table Rows */
QTableWidget::item {
    /* Spacing */
    padding: 0;
    
    /* Background */
    background-color: #B6B6B6;
    
    /* Borders */
    border: none;
    border-bottom: 1px solid #E0E0E0;
}

/* Hover State - same as default (no visual change) */
QTableWidget::item:hover {
    background-color: #B6B6B6;
}

/* Selected State */
QTableWidget::item:selected {
    background-color: #DCEBF7;
    color: #000000;
}

/* Selected + Hover */
QTableWidget::item:selected:hover {
    background-color: #DCEBF7;
}
```

---

## §9 Accessibility

### §9.1 Color Contrast Ratios

| Element Pair | Foreground | Background | Ratio | WCAG AA |
|--------------|------------|------------|-------|---------|
| Header Text | #333333 | #F5F5F5 | 10.2:1 | ✅ Pass |
| Row Text | #333333 | #B6B6B6 | 8.6:1 | ✅ Pass |
| Selected Text | #000000 | #DCEBF7 | 21:1 | ✅ Pass |
| Hover Text | #333333 | #B6B6B6 | 8.6:1 | ✅ Pass |

### §9.2 Focus Indicators

- **Keyboard Navigation:** Arrow keys navigate between rows
- **Focus Style:** Selection color (#DCEBF7) indicates focused row
- **Focus Visible:** Clear visual indication of current focus

### §9.3 Screen Reader Support

- All cells have accessible descriptions
- Column headers are announced
- Row numbers are announced
- Selection state is announced

---

## §10 Implementation Notes

### §10.1 Performance Considerations

1. **Avoid Complex Selectors:** Use simple class selectors (`QTableWidget::item`)
2. **Minimize Repaints:** Zebra striping via `alternatingRowColors` is GPU-accelerated
3. **Cache Styles:** Pre-compute color values, don't recalculate on each paint

### §10.2 Platform Differences

| Platform | Font Rendering | Grid Lines |
|----------|----------------|------------|
| macOS | Subpixel antialiasing | Subtle (1px) |
| Windows | ClearType | Standard (1px) |
| Linux | Varies by desktop | Standard (1px) |

### §10.3 Migration from Previous Implementation

**Before (Inconsistent Header/Row Styles):**
```css
/* Header had different styling from rows */
QHeaderView::section {
    background-color: #F5F5F5;
    border: none;
    border-bottom: 1px solid #C0C0C0;
    border-right: 1px solid #E0E0E0;
    padding: 0px;
    text-align: center;
}

/* Rows lacked zebra striping */
QTableWidget::item {
    background-color: #FFFFFF;
    padding: 0px;
}
```

**After (Unified Styles):**
```css
/* Header matches row styling */
QHeaderView::section {
    background-color: #F5F5F5;
    border: none;
    border-bottom: 1px solid #C0C0C0;
    border-right: 1px solid #E0E0E0;
    padding: 0;  /* Zero padding for max density */
    text-align: center;
}

/* Rows with uniform gray background */
QTableWidget::item {
    padding: 0;  /* Zero padding for max density */
    background-color: #B6B6B6;
}
```

---

## §11 Testing Requirements

### §11.1 Visual Regression Tests

- [ ] Header appearance matches row appearance
- [ ] All rows have uniform gray background (#B6B6B6)
- [ ] Selection color displays correctly
- [ ] Hover state works correctly
- [ ] Log level colors display correctly when enabled

### §11.2 Accessibility Tests

- [ ] All text meets WCAG AA contrast requirements
- [ ] Keyboard navigation works correctly
- [ ] Screen reader announces all cells
- [ ] Focus indicators are visible

### §11.3 Performance Tests

- [ ] Table with 10,000 rows scrolls smoothly
- [ ] Style application time < 16ms

---

## §12 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.8 | 2026-03-19 | Added migration guide for new color system, added cross-reference to color-palette.md |
| 1.7 | 2026-03-15 | Updated cross-references to ui-design-system.md, added references to table-column-alignment.md and table-cell-text-overflow.md |
| 1.6 | 2026-03-15 | MSG/DEBUG/TRACE levels now use default row background (no special highlighting) |
| 1.5 | 2026-03-15 | Changed row background from #FFFFFF to #B6B6B6 (gray) for better visual separation |
| 1.4 | 2026-03-15 | Removed header hover state - header no longer reacts to mouse interactions |
| 1.3 | 2026-03-15 | Removed zebra striping - all rows use uniform white background |
| 1.2 | 2026-03-15 | Unified TABLE_ROW_HEIGHT and TABLE_HEADER_HEIGHT into single TABLE_CELL_HEIGHT constant |
| 1.1 | 2026-03-15 | Changed cell padding from 2px 4px to 0 for maximum information density |
| 1.0 | 2026-03-15 | Initial unified table styles specification |

---

## §13 Migration Guide

### §13.1 Color Constants

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

### §13.2 Implementation Example

```python
# Before (legacy constants)
from src.constants.colors import (
    TABLE_ROW_BACKGROUND,
    SELECTION_HIGHLIGHT_COLOR,
    BORDER_COLOR,
)

# After (new layered architecture)
from src.constants.colors import (
    PaletteColors,
    UIColors,
)

# Table row background
background = PaletteColors.GRAY_2  # #B6B6B6

# Selection highlight
selection = UIColors.BACKGROUND_SELECTED  # #DCEBF7

# Default border
border = UIColors.BORDER_DEFAULT  # #C0C0C0
```

---

## §14 Implementation Checklist

- [ ] Update `src/styles/stylesheet.py` with unified table styles
- [ ] Update `src/constants/colors.py` with new color constants
- [ ] Update `src/constants/dimensions.py`:
  - [ ] Remove `TABLE_ROW_HEIGHT` constant
  - [ ] Remove `TABLE_HEADER_HEIGHT` constant
  - [ ] Add `TABLE_CELL_HEIGHT` constant (unified)
- [ ] Update `src/constants/typography.py`:
  - [ ] Remove `TABLE_ROW_HEIGHT` property
  - [ ] Remove `TABLE_HEADER_HEIGHT` property
  - [ ] Add `TABLE_CELL_HEIGHT` property (unified)
- [ ] Update `src/views/log_table_view.py` to use unified cell height
- [ ] Update `docs/specs/features/ui-design-system.md` to reference this spec
- [ ] Update `docs/SPEC-INDEX.md` with new spec entry
- [ ] Write visual regression tests
- [ ] Write accessibility tests