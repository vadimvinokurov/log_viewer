# Native Checkbox Unification Specification

**Version:** 1.0
**Last Updated:** 2026-03-17
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** PROPOSED

---

## §1 Overview

### §1.1 Purpose

This specification defines the removal of custom checkbox delegates and the adoption of native Qt checkboxes across all panel content tabs (Categories, Filters, Highlights) to ensure visual consistency and reduce maintenance burden.

### §1.2 Motivation

| Tab | Widget | Current State | Issue |
|-----|--------|---------------|-------|
| Categories | QTreeView | Custom delegate (CategoryItemDelegate) | Unnecessary complexity |
| Filters | QListWidget | Native Qt checkboxes (via setCheckState) | ✅ Reference implementation |
| Highlights | QListWidget | Native Qt checkboxes (via setCheckState) | ✅ Reference implementation |

**Problems with current state:**
1. **Unnecessary Complexity**: Custom delegate adds ~300 lines of code for checkbox rendering
2. **Maintenance Burden**: Custom drawing code needs updates for Qt changes
3. **Platform Inconsistency**: Custom checkboxes don't adapt to platform themes
4. **Over-Engineering**: Native Qt checkboxes work perfectly fine

### §1.3 Solution

Remove custom checkbox delegates and use Qt's built-in checkbox rendering:
- **Categories Tab**: Remove `CategoryItemDelegate`, use default Qt rendering
- **Filters Tab**: Already using native checkboxes ✅
- **Highlights Tab**: Already using native checkboxes ✅

### §1.4 Cross-References

- **Category Panel:** [category-panel-styles.md](category-panel-styles.md)
- **Implementation:**
  - [`src/views/category_panel.py`](../../src/views/category_panel.py)
  - [`src/views/delegates/category_item_delegate.py`](../../src/views/delegates/category_item_delegate.py)

---

## §2 Current State Analysis

### §2.1 Categories Tab - Custom Delegate (REMOVE)

Currently uses `CategoryItemDelegate` with custom QPainter drawing:

```python
# In category_panel.py line 161-162:
self._delegate = CategoryItemDelegate(self._tree_view)
self._tree_view.setItemDelegate(self._delegate)
```

**Problems:**
- Custom drawing code for checkboxes
- Manual handling of hover states
- Manual text positioning
- ~300 lines of unnecessary code

### §2.2 Filters/Highlights Tabs - Native Checkboxes (KEEP)

Both use Qt's built-in checkboxes via `QListWidgetItem.setCheckState()`:

```python
# In filters_tab.py:
item.setCheckState(Qt.Checked if filter.enabled else Qt.Unchecked)

# In highlights_tab.py:
item.setCheckState(Qt.CheckState.Checked if pattern.enabled else Qt.CheckState.Unchecked)
```

**Benefits:**
- Native platform appearance
- Automatic hover/selection states
- No custom drawing code
- Less code to maintain

---

## §3 Implementation Changes

### §3.1 Files to Modify

| File | Changes |
|------|---------|
| `src/views/category_panel.py` | Remove CategoryItemDelegate import and usage |
| `src/views/delegates/__init__.py` | Remove CategoryItemDelegate export (or deprecate) |

### §3.2 Files to Deprecate

| File | Action |
|------|--------|
| `src/views/delegates/category_item_delegate.py` | Deprecate or delete |
| `src/views/delegates/panel_checkbox_delegate.py` | Delete (was created in error) |
| `src/views/delegates/list_checkbox_delegate.py` | Delete (was created in error) |

### §3.3 Category Panel Changes

**File:** [`src/views/category_panel.py`](../../src/views/category_panel.py)

**Remove:**
```python
# Line 45: Remove import
from src.views.delegates.category_item_delegate import CategoryItemDelegate

# Lines 161-162: Remove delegate creation
self._delegate = CategoryItemDelegate(self._tree_view)
self._tree_view.setItemDelegate(self._delegate)
```

**Result:**
- QTreeView will use default item rendering
- Checkboxes will be rendered by Qt automatically
- Appearance will match Filters/Highlights tabs

### §3.4 Filters/Highlights Tabs

**No changes needed** - these already use native Qt checkboxes.

---

## §4 Visual Comparison

### §4.1 Before (Inconsistent)

```
┌─────────────────────────────────────────────────────┐
│ [Categories] [Filters] [Highlights]                  │
├─────────────────────────────────────────────────────┤
│ Categories Tab:                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ▶ [■] Category Name     ← Custom delegate       │ │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│ Filters Tab:                                         │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ☑ Filter Name           ← Native Qt            │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### §4.2 After (Unified - Native Qt)

```
┌─────────────────────────────────────────────────────┐
│ [Categories] [Filters] [Highlights]                  │
├─────────────────────────────────────────────────────┤
│ Categories Tab:                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ▶ ☑ Category Name       ← Native Qt            │ │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│ Filters Tab:                                         │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ☑ Filter Name           ← Native Qt            │ │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│ Highlights Tab:                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ☑ Pattern Name          ← Native Qt            │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## §5 Benefits

### §5.1 Code Reduction

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Delegate files | 3 | 0 | -3 files |
| Lines of code | ~450 | 0 | -450 lines |
| Complexity | High | Low | Significant |

### §5.2 Maintenance

- **Before**: Custom drawing code needs updates for Qt changes, platform quirks
- **After**: Qt handles all checkbox rendering automatically

### §5.3 Platform Consistency

- **Before**: Custom checkboxes look the same on all platforms (may not match platform style)
- **After**: Native checkboxes adapt to platform theme (macOS, Windows, Linux)

---

## §6 Testing Requirements

### §6.1 Visual Tests

| Test | Description |
|------|-------------|
| Checkbox rendering | Verify checkboxes appear in Categories tab |
| Check/uncheck | Verify clicking toggles state |
| Parent/child | Verify parent checkbox affects children |
| Partially checked | Verify tri-state checkbox for partial selections |

### §6.2 Functional Tests

| Test | Description |
|------|-------------|
| Click toggle | Click checkbox toggles state |
| Row click | Click row toggles checkbox |
| Keyboard Space | Space key toggles checkbox |
| Batch operations | Check All/Uncheck All works correctly |

### §6.3 Cross-Platform Tests

| Platform | Test |
|----------|------|
| macOS | Verify native checkbox appearance |
| Windows | Verify native checkbox appearance |
| Linux | Verify native checkbox appearance |

---

## §7 Migration Notes

### §7.1 Breaking Changes

None. This is a visual change only with no API impact.

### §7.2 Compatibility

- **Qt Version:** Compatible with PySide6 6.0+
- **Platform:** Compatible with all platforms (macOS, Windows, Linux)
- **High DPI:** Compatible with high DPI displays (Qt handles automatically)

---

## §8 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-17 | Initial specification for native checkbox unification |

---

## §9 Implementation Checklist

- [ ] Remove `CategoryItemDelegate` import from `category_panel.py`
- [ ] Remove delegate creation in `category_panel.py`
- [ ] Remove `CategoryItemDelegate` from `delegates/__init__.py`
- [ ] Delete `category_item_delegate.py` (or deprecate)
- [ ] Delete `panel_checkbox_delegate.py` (created in error)
- [ ] Delete `list_checkbox_delegate.py` (created in error)
- [ ] Remove `ListCheckboxDelegate` imports from `filters_tab.py` and `highlights_tab.py`
- [ ] Remove delegate usage from `filters_tab.py` and `highlights_tab.py`
- [ ] Visual verification: Categories tab shows native checkboxes
- [ ] Visual verification: All tabs have consistent checkbox appearance
- [ ] Functional tests: All checkbox operations work correctly