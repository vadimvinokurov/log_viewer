# Custom Categories Removal Specification

**Version:** 1.0  
**Last Updated:** 2026-03-14  
**Project Context:** Python Tooling (Desktop Application)  
**Status:** [DRAFT]

---

## §1 Overview

This specification documents the complete removal of the Custom Categories feature from the Log Viewer application. Custom Categories allowed users to create user-defined categories that filter by message content (substring match) rather than log category path.

### §1.1 Rationale for Removal

- Feature adds complexity to the filtering system
- Limited usage in practice
- Maintenance overhead outweighs benefits
- Simplifies the codebase and user experience

### §1.2 Scope

This removal affects:
- Specification documents
- Core data structures ([`CategoryNode`](../../src/core/category_tree.py:12), [`FilterState`](../../src/models/filter_state.py:19))
- Filter logic ([`FilterEngine`](../../src/core/filter_engine.py:1))
- UI components ([`CategoryPanel`](../../src/views/category_panel.py:1), [`CustomCategoryDialog`](../../src/views/widgets/custom_category_dialog.py:1))
- Settings management ([`SettingsManager`](../../src/utils/settings_manager.py:1))
- Tests

---

## §2 Files to Modify

### §2.1 Specification Documents

| File | Changes |
|------|---------|
| [`category-tree.md`](category-tree.md) | Remove §4 (Custom Categories), update examples |
| [`filter-engine.md`](filter-engine.md) | Remove §3.2 (Custom Category Filter), update §4 (Filter Combination) |
| [`ui-components.md`](ui-components.md) | Remove custom categories from CategoryPanel API |
| [`category-checkbox-behavior.md`](category-checkbox-behavior.md) | Remove §4.3 (Custom Categories) |
| [`memory-model.md`](../global/memory-model.md) | Remove `_custom_categories` from CategoryPanel |
| [`SPEC.md`](../../SPEC.md) | Remove `custom_category_dialog.py` from file tree |
| [`SPEC-INDEX.md`](../../SPEC-INDEX.md) | No changes needed (feature not separately indexed) |

### §2.2 Implementation Files

| File | Action | Changes |
|------|--------|---------|
| [`src/core/category_tree.py`](../../src/core/category_tree.py:1) | Modify | Remove `is_custom`, `pattern` from [`CategoryNode`](../../src/core/category_tree.py:12), remove [`add_custom_category()`](../../src/core/category_tree.py:182), remove [`get_custom_categories()`](../../src/core/category_tree.py:281) |
| [`src/core/filter_engine.py`](../../src/core/filter_engine.py:1) | Modify | Remove [`_compile_custom_category_filter()`](../../src/core/filter_engine.py:203), remove custom filter logic from [`compile_filter()`](../../src/core/filter_engine.py:40) |
| [`src/models/filter_state.py`](../../src/models/filter_state.py:1) | Modify | Remove `custom_categories` field from [`FilterState`](../../src/models/filter_state.py:19) |
| [`src/utils/settings_manager.py`](../../src/utils/settings_manager.py:1) | Modify | Remove [`CustomCategory`](../../src/utils/settings_manager.py:16) dataclass, remove `custom_categories` from [`AppSettings`](../../src/utils/settings_manager.py:76), remove related methods |
| [`src/views/category_panel.py`](../../src/views/category_panel.py:1) | Modify | Remove `_custom_categories` field, remove custom category UI methods, remove `custom_categories_changed` signal |
| [`src/views/widgets/custom_category_dialog.py`](../../src/views/widgets/custom_category_dialog.py:1) | **DELETE** | Entire file |
| [`src/controllers/filter_controller.py`](../../src/controllers/filter_controller.py:1) | Modify | Remove [`set_custom_categories()`](../../src/controllers/filter_controller.py:316), remove [`get_custom_categories()`](../../src/controllers/filter_controller.py:327), remove [`set_custom_category_enabled()`](../../src/controllers/filter_controller.py:337), remove `_custom_categories` field |
| [`src/controllers/main_controller.py`](../../src/controllers/main_controller.py:1) | Modify | Remove custom category signal connections and handlers |
| [`src/views/main_window.py`](../../src/views/main_window.py:1) | Modify | Remove custom category button connections |

### §2.3 Test Files

| File | Action | Changes |
|------|--------|---------|
| [`tests/test_category_tree.py`](../../tests/test_category_tree.py:1) | Modify | Remove custom category test cases |
| [`tests/test_filter_engine.py`](../../tests/test_filter_engine.py:1) | Modify | Remove custom category filter tests |
| [`tests/test_integration.py`](../../tests/test_integration.py:1) | Modify | Remove custom category integration tests |
| [`tests/test_settings_manager.py`](../../tests/test_settings_manager.py:1) | Modify | Remove custom category settings tests |

---

## §3 Detailed Changes

### §3.1 CategoryNode Data Structure

**Before:**
```python
@dataclass
class CategoryNode:
    name: str
    full_path: str
    parent: CategoryNode | None = None
    children: dict[str, CategoryNode] = field(default_factory=dict)
    is_enabled: bool = True
    is_custom: bool = False          # REMOVE
    pattern: str | None = None        # REMOVE
```

**After:**
```python
@dataclass
class CategoryNode:
    name: str
    full_path: str
    parent: CategoryNode | None = None
    children: dict[str, CategoryNode] = field(default_factory=dict)
    is_enabled: bool = True
```

### §3.2 FilterState Data Structure

**Before:**
```python
@dataclass
class FilterState:
    enabled_categories: Set[str] = field(default_factory=set)
    filter_text: str = ""
    filter_mode: FilterMode = FilterMode.PLAIN
    custom_categories: List[CustomCategory] = field(default_factory=list)  # REMOVE
    all_categories: Set[str] = field(default_factory=set)
    enabled_levels: Set[str] = field(default_factory=lambda: {...})
```

**After:**
```python
@dataclass
class FilterState:
    enabled_categories: Set[str] = field(default_factory=set)
    filter_text: str = ""
    filter_mode: FilterMode = FilterMode.PLAIN
    all_categories: Set[str] = field(default_factory=set)
    enabled_levels: Set[str] = field(default_factory=lambda: {...})
```

### §3.3 FilterEngine.compile_filter()

**Before:**
```python
def compile_filter(self, state: FilterState, category_tree: CategoryTree | None = None) -> Callable[[LogEntry], bool]:
    category_filter = self._compile_category_filter(...)
    custom_filter = self._compile_custom_category_filter(...)  # REMOVE
    
    # Combine: (Category OR Custom) AND Text AND Level
    if category_filter and custom_filter:
        category_or_custom = lambda e: category_filter(e) or custom_filter(e)
    elif category_filter:
        category_or_custom = category_filter
    else:
        category_or_custom = custom_filter
    ...
```

**After:**
```python
def compile_filter(self, state: FilterState, category_tree: CategoryTree | None = None) -> Callable[[LogEntry], bool]:
    category_filter = self._compile_category_filter(...)
    
    # Combine: Category AND Text AND Level
    ...
```

### §3.4 CategoryPanel API

**Removed Methods:**
- `set_custom_categories(categories: list[CustomCategory]) -> None`
- `get_custom_categories() -> list[CustomCategory]`
- `_add_custom_category() -> None`
- `_edit_custom_category() -> None`
- `_remove_custom_category() -> None`
- `_add_custom_category_to_tree(custom: CustomCategory) -> None`
- `_update_custom_categories_in_tree() -> None`

**Removed Signals:**
- `custom_categories_changed = Signal(list)`

### §3.5 SettingsManager Changes

**Removed Dataclass:**
```python
@dataclass
class CustomCategory:  # ENTIRE CLASS REMOVE
    name: str
    pattern: str
    parent: Optional[str] = None
    enabled: bool = True
```

**Removed from AppSettings:**
```python
custom_categories: List[CustomCategory] = field(default_factory=list)  # REMOVE
```

**Removed Methods:**
- `add_custom_category(category: CustomCategory) -> None`
- `get_custom_categories() -> List[CustomCategory]`

---

## §4 Filter Logic Changes

### §4.1 Filter Combination (Before)

```
Final Filter = (Category OR Custom) AND Text AND Level
```

### §4.2 Filter Combination (After)

```
Final Filter = Category AND Text AND Level
```

### §4.3 Special Cases (Removed)

| Category | Custom | Text | Level | Result |
|----------|--------|------|-------|--------|
| None enabled | Active | None | All | Match custom only | ← REMOVE
| All enabled | Active | None | All | Match all (category OR custom) | ← REMOVE

---

## §5 UI Changes

### §5.1 CategoryPanel Buttons

**Before:**
```
[Check All] [Uncheck All] [Add Custom] [Edit Custom] [Remove Custom]
```

**After:**
```
[Check All] [Uncheck All]
```

### §5.2 Category Tree Display

**Before:**
- Regular categories displayed normally
- Custom categories displayed with 🔍 prefix

**After:**
- Only regular categories (from log parsing)

---

## §6 Migration Considerations

### §6.1 Settings File

**Action:** Remove `custom_categories` array from settings JSON.

**Migration:** On load, ignore unknown `custom_categories` field (backward compatible).

### §6.2 Existing User Data

Users with saved custom categories will lose them on upgrade. This is acceptable because:
- Feature is being removed intentionally
- No migration path needed (user-defined patterns can be recreated as text filters)

---

## §7 Testing Updates

### §7.1 Tests to Remove

- `test_add_custom_category()` in [`test_category_tree.py`](../../tests/test_category_tree.py:1)
- `test_custom_category_filter()` in [`test_filter_engine.py`](../../tests/test_filter_engine.py:1)
- `test_custom_category_visibility()` in [`test_category_tree.py`](../../tests/test_category_tree.py:1)
- Custom category integration tests in [`test_integration.py`](../../tests/test_integration.py:1)

### §7.2 Tests to Update

- Filter combination tests (remove custom category cases)
- Category panel tests (remove custom category methods)
- Settings tests (remove custom category persistence)

---

## §8 Cross-References

- **Category Tree:** [category-tree.md](category-tree.md)
- **Filter Engine:** [filter-engine.md](filter-engine.md)
- **UI Components:** [ui-components.md](ui-components.md)
- **Settings:** [settings-manager.md](settings-manager.md)

---

## §9 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-14 | Initial removal specification |