# Implementation Plan: Category Tree Click Target Spacing

**Specification:** [category-tree-click-target-spacing.md](category-tree-click-target-spacing.md)
**Status:** READY FOR IMPLEMENTATION
**Created:** 2026-03-18

---

## Overview

Implement dynamic tree indentation based on Qt style metrics to ensure proper spacing between branch indicator (expand/collapse arrow) and checkbox in the category tree view.

## Problem

- Current indentation: 10px (hardcoded, too small)
- Branch-to-checkbox gap: ~1px (too small, causes misclicks)
- Hardcoded values don't adapt to platform/theme changes

## Solution

Use Qt's `QStyle.PM_IndicatorWidth` to get checkbox size dynamically, then calculate indentation as `checkbox_size + 4px_gap`.

---

## Implementation Tasks

### Task 1: Add Dynamic Indentation Constant

**File:** `src/constants/dimensions.py`

**Add the following:**

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

**Location:** Add after `TABLE_CELL_HEIGHT` definition (around line 133)

---

### Task 2: Update CategoryPanel to Use Dynamic Indentation

**File:** `src/views/category_panel.py`

**Change line 152:**

```python
# Current (line 152):
self._tree_view.setIndentation(10)

# Replace with:
from src.constants.dimensions import TREE_INDENTATION

# In _setup_ui() method:
self._tree_view.setIndentation(TREE_INDENTATION)
```

**Complete change:**

```python
# At top of file, add import (around line 41):
from src.constants.dimensions import TREE_INDENTATION

# In _setup_ui() method (line 152):
# Ref: docs/specs/features/category-panel-styles.md §5.4
# Indentation controls branch indicator width + child offset
# Ref: docs/specs/features/category-tree-click-target-spacing.md §5.4
self._tree_view.setIndentation(TREE_INDENTATION)
```

---

### Task 3: Update Documentation

**File:** `docs/specs/features/category-panel-styles.md`

**Update §5.4 Indentation:**

```markdown
| Element | Property | Value | Notes |
|---------|----------|-------|-------|
| Tree View | Indentation | Dynamic | Per level depth (QStyle.PM_IndicatorWidth + 4px gap) |
| Tree Branch | Indentation | Dynamic | Controlled via `TREE_INDENTATION` constant |
```

**File:** `docs/specs/features/category-tree-row-unification.md`

**Update §4.3 Checkbox Positioning:**

```markdown
| Property | Value | Notes |
|----------|-------|-------|
| Branch Area Width | Dynamic | Same as checkbox (QStyle.PM_IndicatorWidth) |
| Branch-to-Checkbox Gap | 4px | Desktop standard (macOS/Windows) |
| Text-to-Checkbox Padding | 4px | Space between checkbox and text |
| Vertical Alignment | Center | Vertically centered in row |
```

---

## Testing Checklist

- [ ] Visual: Branch-checkbox gap is 4px
- [ ] Visual: Indentation looks correct at multiple nesting levels
- [ ] Platform: Test on macOS, Windows, Linux
- [ ] High DPI: Test on 2x display scaling
- [ ] Theme: Verify indentation updates when Qt theme changes
- [ ] Fallback: Verify 16px fallback when style unavailable

---

## Files to Modify

1. `src/constants/dimensions.py` - Add `TREE_INDENTATION` constant
2. `src/views/category_panel.py` - Use `TREE_INDENTATION` instead of hardcoded 10
3. `docs/specs/features/category-panel-styles.md` - Update §5.4
4. `docs/specs/features/category-tree-row-unification.md` - Update §4.3

---

## Verification

After implementation, verify:

1. **Dynamic Calculation:**
   ```python
   from src.constants.dimensions import TREE_INDENTATION
   print(f"Tree indentation: {TREE_INDENTATION}px")
   # Expected: 16px on standard displays (12px checkbox + 4px gap)
   # Expected: 32px on 2x high-DPI displays
   ```

2. **Visual Check:**
   - Branch indicator and checkbox should have 4px gap
   - Both should be same size (visual symmetry)
   - Indentation should look native on each platform

---

## References

- **Specification:** [category-tree-click-target-spacing.md](category-tree-click-target-spacing.md)
- **Qt Documentation:** [QStyle.PM_IndicatorWidth](https://doc.qt.io/qt-6/qstyle.html)
- **Implementation:** `src/views/category_panel.py:152`