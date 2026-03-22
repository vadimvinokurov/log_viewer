# Panel Content Unified Styles Specification

**Version:** 1.0
**Last Updated:** 2026-03-17
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** PROPOSED

---

## §1 Overview

### §1.1 Purpose

This specification defines unified visual styles for all tab content panels within the CategoryPanel (Categories, Filters, Highlights). The goal is to ensure consistent look and feel across all tabs using the application's light theme.

### §1.2 Scope

- Categories tab (Tree view with checkboxes)
- Filters tab (Saved filters list)
- Highlights tab (Highlight patterns list)
- Common UI elements: lists, buttons, inputs, labels

### §1.3 References

- **UI Design System:** [ui-design-system.md](ui-design-system.md)
- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md)
- **UI Components:** [ui-components.md](ui-components.md)
- **Implementation:** 
  - [`src/views/category_panel.py`](../../src/views/category_panel.py)
  - [`src/views/components/filters_tab.py`](../../src/views/components/filters_tab.py)
  - [`src/views/components/highlights_tab.py`](../../src/views/components/highlights_tab.py)

---

## §2 Current State Analysis

### §2.1 Categories Tab (Reference Implementation)

The Categories tab uses the application's light theme consistently:

| Element | Property | Value | Source |
|---------|----------|-------|--------|
| Tree Background | Background | `#F5F5F5` | `get_tree_stylesheet()` |
| Tree Item (default) | Background | Transparent | `get_tree_stylesheet()` |
| Tree Item (hover) | Background | `#E8E8E8` | `get_tree_stylesheet()` |
| Tree Item (selected) | Background | `#DCEBF7` | `get_tree_stylesheet()` |
| Container Margins | Margins | 4px all sides | Implementation |
| Container Spacing | Spacing | 4px | Implementation |
| Button Bar | Margins | 4px all sides | Implementation |
| Button Bar | Spacing | 4px | Implementation |

### §2.2 Filters Tab (Current Issues)

The Filters tab lacks custom styling and relies on Qt defaults:

| Element | Current State | Issue |
|---------|---------------|-------|
| List Background | Qt default | Inconsistent with tree |
| List Item (hover) | Qt default | May not match tree hover |
| List Item (selected) | Qt default | May not match tree selection |
| Container Margins | 4px all sides | ✅ Correct |
| Container Spacing | 4px | ✅ Correct |
| Buttons | Qt default | ✅ Uses application stylesheet |

### §2.3 Highlights Tab (Current Issues)

The Highlights tab uses **dark theme colors** that are inconsistent with the light theme:

| Element | Current Value | Should Be | Issue |
|---------|---------------|-----------|-------|
| List Background | Qt default | `#F5F5F5` | Inconsistent |
| List Item Border | `#3c3c3c` | None or `#E0E0E0` | Dark theme color |
| List Item (selected) | `#094771` | `#DCEBF7` | Dark theme color |
| List Item (hover) | `#2a2d2e` | `#E8E8E8` | Dark theme color |
| Type Label Color | `#888888` | `#666666` | Slightly off |
| Container Margins | 4px all sides | - | ✅ Correct |
| Container Spacing | 4px | - | ✅ Correct |

**Current Dark Theme Styles (to be removed):**
```css
/* HIGHLIGHT_ITEM_STYLE - DARK THEME */
QListWidget::item {
    padding: 4px;
    border-bottom: 1px solid #3c3c3c;  /* Dark theme! */
}
QListWidget::item:selected {
    background-color: #094771;  /* Dark theme! */
}
QListWidget::item:hover {
    background-color: #2a2d2e;  /* Dark theme! */
}
```

---

## §3 Unified Style Specification

### §3.1 Design Principles

1. **Consistency**: All tabs should use the same visual language
2. **Light Theme**: Use the application's light color palette
3. **Reusability**: Create shared stylesheet functions
4. **Maintainability**: Centralize style definitions

### §3.2 Color Palette (from UI Design System)

| Token | Value | Usage |
|-------|-------|-------|
| Background Primary | `#FFFFFF` | Input fields, content areas |
| Background Secondary | `#F5F5F5` | Panel backgrounds, lists |
| Background Hover | `#E8E8E8` | Hover states |
| Selection Highlight | `#DCEBF7` | Selection background |
| Border Default | `#C0C0C0` | Default borders |
| Border Light | `#E0E0E0` | Subtle separators |
| Text Primary | `#333333` | Primary text |
| Text Secondary | `#666666` | Secondary text, hints |
| Text Disabled | `#999999` | Disabled text |
| Primary Blue | `#0066CC` | Focus states, accents |

**Shared Constants (Implementation):**
```python
# src/styles/stylesheet.py
PANEL_CONTENT_BG = "#f5f5f5"        # Background Secondary
PANEL_CONTENT_HOVER = "#e8e8e8"     # Background Hover
PANEL_CONTENT_SELECTION = "#dcebf7"  # Selection Highlight
PANEL_CONTENT_TEXT = "#000000"      # Selected text color
```

These constants are used by both `get_tree_stylesheet()` and `get_panel_list_stylesheet()` to ensure consistent styling across Categories (QTreeView), Filters (QListWidget), and Highlights (QListWidget) tabs.

### §3.3 Panel Content Container

All tab content containers should use:

| Property | Value | Notes |
|----------|-------|-------|
| Margins | 4px (all sides) | Consistent with Categories tab |
| Spacing | 4px | Between children |
| Background | `#FFFFFF` | Content area background |

**Implementation:**
```python
layout = QVBoxLayout(self)
layout.setContentsMargins(4, 4, 4, 4)
layout.setSpacing(4)
```

### §3.4 List Widget Styles (Unified)

All list widgets in Filters and Highlights tabs should use:

| Element | Property | Value |
|---------|----------|-------|
| List Background | Background | `#F5F5F5` |
| List Item (default) | Background | Transparent |
| List Item (default) | Padding | 0px |
| List Item (default) | Border | None |
| List Item (hover) | Background | `#E8E8E8` |
| List Item (selected) | Background | `#DCEBF7` |
| List Item (selected) | Text Color | `#000000` |

**QSS Implementation:**
```css
QListWidget {
    background-color: #F5F5F5;
    border: none;
}

QListWidget::item {
    padding: 0;
    border: none;
}

QListWidget::item:hover {
    background-color: #E8E8E8;
}

QListWidget::item:selected {
    background-color: #DCEBF7;
    color: #000000;
}
```

### §3.5 Button Bar Styles

Button bars in all tabs should use:

| Property | Value |
|----------|-------|
| Margins | 4px (all sides) |
| Spacing | 4px |
| Button Min Width | 60px |
| Button Padding | 4px 12px |
| Button Border Radius | 3px |

Buttons use the application-wide stylesheet from `get_application_stylesheet()`.

### §3.6 Color Swatch Styles (Highlights Tab)

The color swatch in Highlights tab should use:

| Property | Value |
|----------|-------|
| Min/Max Width | 20px |
| Min/Max Height | 14px |
| Border | 1px solid `#888888` |
| Border Radius | 3px |

**QSS Implementation:**
```css
QLabel {
    border: 1px solid #888888;
    border-radius: 3px;
    min-width: 20px;
    max-width: 20px;
    min-height: 14px;
    max-height: 14px;
}
```

### §3.7 Type Label Styles (Highlights Tab)

The type indicator label (regex/text) should use:

| Property | Value |
|----------|-------|
| Color | `#666666` (Text Secondary) |
| Font Style | Italic |

**QSS Implementation:**
```css
QLabel {
    color: #666666;
    font-style: italic;
}
```

---

## §4 Implementation Plan

### §4.1 Stylesheet Changes

Created shared constants and functions in [`src/styles/stylesheet.py`](../../src/styles/stylesheet.py):

**Shared Constants:**
```python
# Panel content colors - used by both tree and list views
PANEL_CONTENT_BG = "#f5f5f5"        # Background Secondary
PANEL_CONTENT_HOVER = "#e8e8e8"     # Background Hover
PANEL_CONTENT_SELECTION = "#dcebf7"  # Selection Highlight
PANEL_CONTENT_TEXT = "#000000"      # Selected text color
```

**Tree Stylesheet Function (updated to use constants):**
```python
def get_tree_stylesheet() -> str:
    """Get the stylesheet for tree views.
    
    Uses shared panel content colors for consistency with list widgets.
    """
    return f"""
        QTreeView {{
            background-color: {PANEL_CONTENT_BG};
            border: none;
            selection-background-color: {PANEL_CONTENT_SELECTION};
            selection-color: {PANEL_CONTENT_TEXT};
        }}
        QTreeView::item {{
            padding: 0;
            border: none;
        }}
        QTreeView::item:selected {{
            background-color: {PANEL_CONTENT_SELECTION};
            color: {PANEL_CONTENT_TEXT};
        }}
        QTreeView::item:hover {{
            background-color: {PANEL_CONTENT_HOVER};
        }}
    """
```

**List Stylesheet Function:**
```python
def get_panel_list_stylesheet() -> str:
    """Get the stylesheet for panel content list widgets.
    
    Uses shared panel content colors for consistency with tree views.
    """
    return f"""
        QListWidget {{
            background-color: {PANEL_CONTENT_BG};
            border: none;
        }}
        QListWidget::item {{
            padding: 0;
            border: none;
        }}
        QListWidget::item:hover {{
            background-color: {PANEL_CONTENT_HOVER};
        }}
        QListWidget::item:selected {{
            background-color: {PANEL_CONTENT_SELECTION};
            color: {PANEL_CONTENT_TEXT};
        }}
    """
```

### §4.2 Filters Tab Changes

Update [`src/views/components/filters_tab.py`](../../src/views/components/filters_tab.py):

1. Apply `get_panel_list_stylesheet()` to `_filter_list`
2. No other changes needed (margins and spacing already correct)

```python
from src.styles.stylesheet import get_panel_list_stylesheet

# In _setup_ui():
self._filter_list = QListWidget()
self._filter_list.setStyleSheet(get_panel_list_stylesheet())
```

### §4.3 Highlights Tab Changes

Update [`src/views/components/highlights_tab.py`](../../src/views/components/highlights_tab.py):

1. Remove `HIGHLIGHT_ITEM_STYLE` constant (dark theme)
2. Remove `COLOR_SWATCH_STYLE` constant
3. Apply `get_panel_list_stylesheet()` to `_pattern_list`
4. Update `HighlightPatternItem` to use light theme colors

**Before (Dark Theme):**
```python
HIGHLIGHT_ITEM_STYLE = """
    QListWidget::item {
        padding: 4px;
        border-bottom: 1px solid #3c3c3c;
    }
    QListWidget::item:selected {
        background-color: #094771;
    }
    QListWidget::item:hover {
        background-color: #2a2d2e;
    }
"""
```

**After (Light Theme):**
```python
# Use get_panel_list_stylesheet() from stylesheet.py
```

**Color Swatch Update:**
```python
# Before
COLOR_SWATCH_STYLE = """
    QLabel {
        border: 1px solid #888;
        ...
    }
"""

# After - use constants from colors.py
from src.constants.colors import BORDER_COLOR

def _get_color_swatch_style(color: QColor) -> str:
    """Get stylesheet for color swatch with specified background color."""
    return f"""
        QLabel {{
            border: 1px solid #888888;
            border-radius: 3px;
            min-width: 20px;
            max-width: 20px;
            min-height: 14px;
            max-height: 14px;
            background-color: {color.name()};
        }}
    """
```

**Type Label Update:**
```python
# Before
self._type_label.setStyleSheet("color: #888; font-style: italic;")

# After
self._type_label.setStyleSheet("color: #666666; font-style: italic;")
```

### §4.4 HighlightPatternItem Widget Layout

The `HighlightPatternItem` widget should maintain its current layout but with updated colors:

| Element | Margins | Spacing |
|---------|---------|---------|
| Container | 4px left/right, 2px top/bottom | 8px |
| Checkbox | Standard | - |
| Color Swatch | Fixed 20x14px | - |
| Text Label | Stretch | - |
| Type Label | Auto | - |

---

## §5 Visual Comparison

### §5.1 Before (Current State)

```
┌─────────────────────────────────────────┐
│ [Categories] [Filters] [Highlights]     │  ← Tab bar (consistent)
├─────────────────────────────────────────┤
│ Categories Tab:                          │
│ ┌─────────────────────────────────────┐ │
│ │ Tree Background: #F5F5F5            │ │
│ │ Item Hover: #E8E8E8                 │ │
│ │ Item Selected: #DCEBF7              │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Highlights Tab:                          │
│ ┌─────────────────────────────────────┐ │
│ │ List Background: Qt default         │ │
│ │ Item Border: #3c3c3c (dark!)       │ │
│ │ Item Selected: #094771 (dark!)      │ │
│ │ Item Hover: #2a2d2e (dark!)         │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### §5.2 After (Unified Light Theme)

```
┌─────────────────────────────────────────┐
│ [Categories] [Filters] [Highlights]     │  ← Tab bar (consistent)
├─────────────────────────────────────────┤
│ Categories Tab:                          │
│ ┌─────────────────────────────────────┐ │
│ │ Tree Background: #F5F5F5            │ │
│ │ Item Hover: #E8E8E8                 │ │
│ │ Item Selected: #DCEBF7              │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Highlights Tab:                          │
│ ┌─────────────────────────────────────┐ │
│ │ List Background: #F5F5F5            │ │  ← Unified!
│ │ Item Border: None                   │ │  ← Unified!
│ │ Item Selected: #DCEBF7              │ │  ← Unified!
│ │ Item Hover: #E8E8E8                 │ │  ← Unified!
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## §6 Testing Requirements

### §6.1 Visual Regression Tests

| Test | Description |
|------|-------------|
| List Background | Verify all tabs use `#F5F5F5` background |
| List Item Hover | Verify all tabs use `#E8E8E8` hover |
| List Item Selected | Verify all tabs use `#DCEBF7` selection |
| Color Swatch | Verify border is visible on all backgrounds |
| Type Label | Verify text is readable (`#666666`) |

### §6.2 Cross-Platform Tests

| Platform | Test |
|----------|------|
| macOS | Verify native font rendering |
| Windows | Verify native font rendering |
| High DPI | Verify scaling on high DPI displays |

---

## §7 Files to Modify

| File | Changes |
|------|---------|
| `src/styles/stylesheet.py` | Add `get_panel_list_stylesheet()` function |
| `src/views/components/filters_tab.py` | Apply stylesheet to list widget |
| `src/views/components/highlights_tab.py` | Remove dark theme styles, apply light theme |
| `docs/specs/features/category-panel-styles.md` | Add reference to unified styles |

---

## §8 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-17 | Initial specification for unified panel content styles |