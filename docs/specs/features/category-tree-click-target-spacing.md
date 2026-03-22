# Category Tree Click Target Spacing Specification

**Version:** 2.0
**Last Updated:** 2026-03-18
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** PROPOSED

---

## §1 Overview

### §1.1 Purpose

This specification defines proper spacing between the branch indicator (expand/collapse arrow) and the checkbox in the category tree view, following UI best practices for click target separation using **dynamic Qt style metrics** instead of hardcoded values.

### §1.2 Motivation

**Current Issue:**
- Indentation: 10px (hardcoded, below Qt default)
- Branch-to-checkbox gap: 1px (too small)
- Users may accidentally click the wrong element
- Poor visual separation between interactive elements
- **Hardcoded values don't adapt to platform/theme changes**

**Industry Standards:**

| Platform/Framework | Indentation | Branch Area | Gap to Content |
|-------------------|-------------|-------------|----------------|
| Qt Default | Style-dependent (16-20px) | ~16px | ~4px |
| Qt Documentation Example | 20px | ~16px | ~4px |
| macOS Finder | ~20px | ~16px | ~4-8px |
| Windows Explorer | ~19px | ~16px | ~4px |
| VS Code | 16px (configurable) | ~12-16px | ~4-8px |
| Material Design | 16-24dp | ~16dp | 8dp minimum |
| Apple HIG | ~20pt | 16×16pt | 8pt minimum |

**Key Findings:**
- Qt provides style-dependent metrics via `QStyle.pixelMetric()`
- Desktop platforms (macOS/Windows) use 16-20px indentation
- 4-8px gap between interactive elements is standard
- **Dynamic values adapt to platform theme automatically**

### §1.3 Scope

- Branch indicator (expand/collapse arrow) dimensions
- Checkbox dimensions and positioning
- Spacing between branch indicator and checkbox
- Click target sizing for both elements

### §1.4 Cross-References

- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md)
- **Category Tree Row Unification:** [category-tree-row-unification.md](category-tree-row-unification.md)
- **UI Design System:** [ui-design-system.md](ui-design-system.md)
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py)

---

## §2 Current State Analysis

### §2.1 Current Dimensions

| Element | Property | Current Value | Issue |
|---------|----------|---------------|-------|
| Tree Indentation | `setIndentation()` | 10px | Controls branch + child offset |
| Branch Indicator | Width | ~10px (Qt default) | Part of indentation |
| Branch-to-Checkbox Gap | Spacing | 1px | **Too small** |
| Checkbox | Size | 12×12px | Adequate |
| Checkbox-to-Text | Padding | 4px | Adequate |

### §2.2 Visual Representation (Current)

```
Current Layout (1px gap):
┌─────────────────────────────────────────────────────┐
│ ▶☐ Category Name                                    │
│   ↑↑                                                │
│   │└─ Checkbox (12×12px)                            │
│   └─ Branch indicator (~10px)                       │
│                                                     │
│ Gap between arrow and checkbox: 1px (TOO SMALL)     │
└─────────────────────────────────────────────────────┘
```

### §2.3 Problems

1. **Click Target Overlap Risk**: 1px gap makes it easy to misclick
2. **Visual Confusion**: Hard to distinguish where arrow ends and checkbox begins
3. **Accessibility**: Poor separation for users with motor impairments
4. **Inconsistent with Best Practices**: Most UI frameworks recommend 8px minimum

---

## §3 Proposed Solution

### §3.1 Dynamic Spacing from Qt Style Metrics

**Key Principle:** Use Qt's style metrics instead of hardcoded values to ensure platform-native appearance and automatic adaptation to theme changes.

**Qt Style Metrics Available:**

| Metric | Qt Constant | Description | Typical Value |
|--------|-------------|-------------|---------------|
| Indicator Width | `QStyle.PM_IndicatorWidth` | Checkbox/indicator width | 12-16px |
| Indicator Height | `QStyle.PM_IndicatorHeight` | Checkbox/indicator height | 12-16px |
| Default Indentation | `QTreeView.indentation()` | Tree indentation (style-dependent) | 16-20px |

**Implementation Approach:**

```python
from PySide6.QtWidgets import QStyle

# Get checkbox size from Qt style
checkbox_size = tree_view.style().pixelMetric(QStyle.PM_IndicatorWidth)

# Get default indentation from Qt style
# Option 1: Use Qt's default (reset to style default)
tree_view.resetIndentation()  # Restores style-dependent default

# Option 2: Calculate based on checkbox size + gap
# Gap should be at least 4px (desktop standard)
gap = 4  # Minimum gap for desktop
indentation = checkbox_size + gap
tree_view.setIndentation(indentation)
```

### §3.2 Recommended Dynamic Calculation

| Element | Source | Calculation | Rationale |
|---------|--------|-------------|-----------|
| Checkbox Size | `QStyle.PM_IndicatorWidth` | Dynamic (12-16px) | Platform-native size |
| Branch Area | Same as checkbox | `checkbox_size` | Visual symmetry |
| Gap | Fixed minimum | 4px | Desktop standard (macOS/Windows) |
| Indentation | Calculated | `checkbox_size + gap` | Adapts to platform |

### §3.3 Visual Representation (Dynamic)

```
Dynamic Layout (adapts to platform):
┌─────────────────────────────────────────────────────┐
│ ▶ ☐ Category Name                                   │
│ │ │                                                 │
│ │ └─ Checkbox (QStyle.PM_IndicatorWidth)           │
│ │ ↑                                                 │
│ │ └─ 4px gap (fixed minimum)                       │
│ └─ Branch indicator (same as checkbox)            │
│                                                     │
│ Indentation = checkbox_size + 4px gap              │
│ Example: 12px + 4px = 16px (typical)              │
│ Example: 16px + 4px = 20px (high DPI)             │
└─────────────────────────────────────────────────────┘
```

### §3.4 Benefits of Dynamic Approach

| Benefit | Description |
|---------|-------------|
| **Platform Native** | Adapts to macOS, Windows, Linux automatically |
| **Theme Aware** | Changes with Qt theme (Fusion, macOS, Windows) |
| **High DPI Ready** | Scales correctly on high-DPI displays |
| **Maintainable** | No hardcoded values to update |
| **Consistent** | Matches other Qt applications on same platform |

---

## §4 Implementation Options

### §4.1 Option A: Use Qt Default Indentation (Recommended)

**Approach:** Reset to Qt's style-dependent default indentation.

**Implementation:**
```python
# In category_panel.py _setup_ui()
# Current:
self._tree_view.setIndentation(10)

# Proposed:
self._tree_view.resetIndentation()  # Use Qt style default (16-20px)
```

**Pros:**
- **Platform Native**: Automatically adapts to macOS, Windows, Linux
- **Theme Aware**: Changes with Qt theme
- **Zero Maintenance**: No hardcoded values
- **Simple**: One-line change

**Cons:**
- Less control over exact spacing
- May vary across platforms (16-20px)

### §4.2 Option B: Calculate Indentation from Style Metrics

**Approach:** Calculate indentation based on Qt's checkbox size + gap.

**Implementation:**
```python
# In category_panel.py _setup_ui()
from PySide6.QtWidgets import QStyle

# Get checkbox size from Qt style
checkbox_size = self._tree_view.style().pixelMetric(QStyle.PM_IndicatorWidth)

# Calculate indentation: checkbox size + gap
# Gap is fixed at 4px (desktop standard minimum)
gap = 4
indentation = checkbox_size + gap

self._tree_view.setIndentation(indentation)
```

**Pros:**
- **Visual Symmetry**: Branch area = checkbox size
- **Platform Native**: Uses Qt's checkbox size
- **Consistent Gap**: Fixed 4px gap for desktop standard
- **High DPI Ready**: Scales with DPI

**Cons:**
- Slightly more complex than Option A
- Requires style() call

### §4.3 Option C: Hybrid Approach (Best of Both)

**Approach:** Use Qt default, but ensure minimum gap by calculating if needed.

**Implementation:**
```python
# In category_panel.py _setup_ui()
from PySide6.QtWidgets import QStyle

# Get Qt's default indentation
self._tree_view.resetIndentation()
default_indent = self._tree_view.indentation()

# Get checkbox size from style
checkbox_size = self._tree_view.style().pixelMetric(QStyle.PM_IndicatorWidth)

# Ensure minimum gap of 4px
min_gap = 4
min_required_indent = checkbox_size + min_gap

# If default is too small, increase it
if default_indent < min_required_indent:
    self._tree_view.setIndentation(min_required_indent)
```

**Pros:**
- **Best of Both Worlds**: Uses Qt default when adequate
- **Fallback Safety**: Ensures minimum gap if default is too small
- **Platform Native**: Respects platform defaults
- **Accessible**: Guarantees minimum spacing for usability

**Cons:**
- Most complex implementation
- Requires conditional logic

---

## §5 Recommended Implementation

### §5.1 Chosen Approach: Option B (Calculate from Style Metrics)

**Rationale:**
1. **Visual Symmetry**: Branch area = checkbox size from Qt style
2. **Platform Native**: Uses Qt's actual checkbox size
3. **Desktop Standard**: Fixed 4px gap matches macOS/Windows
4. **High DPI Ready**: Scales correctly on high-DPI displays
5. **Maintainable**: No hardcoded values to update

### §5.2 Implementation Details

**File:** [`src/views/category_panel.py`](../../src/views/category_panel.py)

**Change:**
```python
# Line 152 (in _setup_ui method)
# Current:
self._tree_view.setIndentation(10)

# Proposed:
from PySide6.QtWidgets import QStyle

# Get checkbox size from Qt style (platform-native)
checkbox_size = self._tree_view.style().pixelMetric(QStyle.PM_IndicatorWidth)

# Calculate indentation: checkbox size + gap
# Gap is fixed at 4px (desktop standard minimum)
gap = 4
indentation = checkbox_size + gap

self._tree_view.setIndentation(indentation)
```

**Alternative (Simpler):**
```python
# If Qt's default indentation is adequate on all platforms:
self._tree_view.resetIndentation()  # Use Qt style default
```

### §5.3 Constants File Update

**File:** [`src/constants/dimensions.py`](../../src/constants/dimensions.py)

Add dynamic tree indentation constant:
```python
def get_tree_indentation() -> int:
    """Get tree indentation based on Qt style metrics.
    
    Calculates indentation as checkbox size + gap for proper
    spacing between branch indicator and checkbox.
    
    Returns:
        Indentation in pixels (checkbox_size + 4px gap).
    
    Ref: docs/specs/features/category-tree-click-target-spacing.md §5.3
    """
    from PySide6.QtWidgets import QApplication, QStyle
    
    # Get checkbox size from Qt style
    # Note: QApplication must be initialized before calling this
    style = QApplication.style()
    if style is None:
        return 16  # Fallback: 12px checkbox + 4px gap
    
    checkbox_size = style.pixelMetric(QStyle.PM_IndicatorWidth)
    gap = 4  # Desktop standard minimum
    return checkbox_size + gap


class _LazyTreeIndentation:
    """Lazy descriptor for TREE_INDENTATION.
    
    QStyle requires QApplication to be initialized.
    This descriptor computes the value on first access.
    
    Ref: docs/specs/features/category-tree-click-target-spacing.md §5.3
    """
    
    def __init__(self):
        self._value: int | None = None
    
    def __get__(self, obj, objtype=None) -> int:
        if self._value is None:
            self._value = get_tree_indentation()
        return self._value


TREE_INDENTATION: int = _LazyTreeIndentation()  # type: ignore[assignment]
"""Tree indentation in pixels.
Computed dynamically from QStyle.PM_IndicatorWidth + 4px gap.
"""
```

### §5.4 Usage in CategoryPanel

**File:** [`src/views/category_panel.py`](../../src/views/category_panel.py)

```python
from src.constants.dimensions import TREE_INDENTATION

# In _setup_ui():
self._tree_view.setIndentation(TREE_INDENTATION)
```

### §5.5 Visual Comparison

**Before (10px hardcoded indentation, ~1px gap):**
```
▶☐ Category
  ↑↑
  │└─ ~1px gap (too small)
  └─ Branch area (~10px, different from checkbox)
```

**After (dynamic indentation, 4px gap):**
```
▶ ☐ Category
│ │
│ └─ Checkbox (QStyle.PM_IndicatorWidth, e.g., 12px)
│ ↑
│ └─ 4px gap (desktop standard)
└─ Branch indicator (same as checkbox)
```

### §5.6 Platform Adaptation

| Platform | PM_IndicatorWidth | Gap | Indentation |
|----------|-------------------|-----|-------------|
| macOS (Fusion) | 12px | 4px | 16px |
| Windows (Fusion) | 12px | 4px | 16px |
| Linux (Fusion) | 12px | 4px | 16px |
| High DPI (2x) | 24px | 8px | 32px |
| macOS (Native) | ~13px | 4px | ~17px |

---

## §6 Testing Requirements

### §6.1 Visual Tests

| Test | Description |
|------|-------------|
| Branch-Checkbox Gap | Verify 4px gap between arrow and checkbox |
| Click Target Separation | Verify misclicks are reduced |
| Nested Items | Verify indentation looks correct at multiple levels |
| Deep Nesting | Verify text visibility at 3+ levels deep |
| Platform Consistency | Verify appearance on macOS, Windows, Linux |
| High DPI | Verify scaling is correct on 2x displays |

### §6.2 Dynamic Metrics Tests

| Test | Description |
|------|-------------|
| Style Change | Verify indentation updates when Qt theme changes |
| Platform Default | Verify `resetIndentation()` provides adequate spacing |
| Checkbox Size | Verify `PM_IndicatorWidth` returns expected values |
| Fallback | Verify fallback value (16px) when style unavailable |

### §6.3 Usability Tests

| Test | Description |
|------|-------------|
| Click Accuracy | Measure misclick rate before/after |
| User Preference | A/B test with users |
| Motor Impairment | Test with users having motor difficulties |

### §6.4 Cross-Platform Tests

| Platform | Test |
|----------|------|
| macOS (Fusion) | Verify 16px indentation |
| Windows (Fusion) | Verify 16px indentation |
| Linux (Fusion) | Verify 16px indentation |
| macOS (Native) | Verify platform-native appearance |
| High DPI (2x) | Verify 32px indentation (scaled) |

---

## §7 Accessibility Considerations

### §7.1 Click Target Size

| Element | Size | WCAG 2.1 | Status |
|---------|------|----------|--------|
| Branch Indicator | Dynamic (12-16px) | 44×44px recommended | ⚠️ Small but acceptable for desktop |
| Checkbox | Dynamic (12-16px) | 44×44px recommended | ⚠️ Small but acceptable for desktop |
| Gap | 4px (fixed) | 4-8px typical | ✅ Within desktop standards |

**Note:** Desktop applications with mouse input can use smaller click targets than touch interfaces. The 4px gap is consistent with macOS Finder and Windows Explorer.

### §7.2 Visual Separation

- **4px gap** provides adequate visual separation for desktop applications
- Matches native tree views on macOS and Windows
- Users can easily distinguish between branch indicator and checkbox
- Consistent with Qt documentation examples

---

## §8 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-03-18 | **Dynamic approach**: Use Qt style metrics instead of hardcoded values |
| 1.2 | 2026-03-18 | Updated to 16px indentation with 12px branch area (same as checkbox) for visual symmetry |
| 1.1 | 2026-03-18 | Updated recommendation to 20px indentation based on Qt documentation and industry standards (macOS/Windows) |
| 1.0 | 2026-03-18 | Initial specification for branch-to-checkbox spacing |

---

## §9 Cross-References

- **Category Panel Styles:** [category-panel-styles.md](category-panel-styles.md) §5.4, §7.3.1
- **Category Tree Row Unification:** [category-tree-row-unification.md](category-tree-row-unification.md) §4.3
- **UI Design System:** [ui-design-system.md](ui-design-system.md) §3.2 (Spacing Scale)
- **Implementation:** [`src/views/category_panel.py`](../../src/views/category_panel.py) line 152
- **Constants:** [`src/constants/dimensions.py`](../../src/constants/dimensions.py)