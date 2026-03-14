# Terminology Cleanup: SystemNode → CategoryDisplayNode

**Version:** 1.0  
**Last Updated:** 2026-03-14  
**Project Context:** Python Tooling (Desktop Application)  
**Status:** [DRAFT] Pending Approval  
**Related:** [category-tree.md](category-tree.md), [ui-components.md](ui-components.md)

---

## §1 Overview

This specification defines a terminology cleanup to rename legacy `SystemNode` and related terms to more accurate names that reflect their actual purpose in the codebase.

### §1.1 Problem Statement

The current naming uses confusing terminology:
- **`SystemNode`** - Actually represents a category display node for the UI tree
- **"systems panel"** - Actually refers to the CategoryPanel
- **`build_system_nodes()`** - Actually builds category display nodes

This is legacy naming from an earlier design iteration and causes confusion for developers.

### §1.2 Proposed Changes

| Current Name | New Name | Location |
|--------------|----------|----------|
| `SystemNode` | `CategoryDisplayNode` | `src/models/system_node.py` |
| `system_node.py` | `category_display_node.py` | `src/models/` |
| `build_system_nodes()` | `build_category_display_nodes()` | `src/core/category_tree.py` |
| "systems panel" | "CategoryPanel" | Documentation only |
| "system tree" | "category tree view" | Documentation only |

---

## §2 Affected Files

### §2.1 Source Code Files

| File | Changes Required |
|------|------------------|
| `src/models/system_node.py` | Rename file, rename class |
| `src/models/__init__.py` | Update import/export |
| `src/core/category_tree.py` | Rename function, update imports |
| `src/core/__init__.py` | Update exports |
| `src/views/category_panel.py` | Update imports |
| `src/controllers/main_controller.py` | Update imports and function call |

### §2.2 Specification Files

| File | Changes Required |
|------|------------------|
| `docs/specs/features/category-tree.md` | Update §4.3, terminology |
| `docs/specs/features/ui-components.md` | Update SystemNode references |
| `docs/specs/features/main-controller.md` | Update imports |
| `docs/specs/features/category-checkbox-behavior.md` | Update references |
| `docs/specs/api/engine-api.yaml` | Update §2.4, all references |
| `docs/SPEC-INDEX.md` | Update SystemNode reference |
| `docs/audit/AUDIT_REPORT.md` | Update references (if needed) |

### §2.3 Test Files

| File | Changes Required |
|------|------------------|
| `tests/test_category_tree.py` | Update imports, function calls |
| `tests/test_integration.py` | Update imports |

### §2.4 Documentation Files

| File | Changes Required |
|------|------------------|
| `plans/ui_refactoring_plan.md` | Update references |
| `src/views/main_window.py` | Update docstring (line 5) |

---

## §3 Detailed Changes

### §3.1 Class Rename: SystemNode → CategoryDisplayNode

**File:** `src/models/system_node.py` → `src/models/category_display_node.py`

**Before:**
```python
@beartype
@dataclass
class SystemNode:
    """System node for tree view."""
    
    name: str
    path: str
    checked: bool = False
    children: list[SystemNode] = field(default_factory=list)
```

**After:**
```python
@beartype
@dataclass
class CategoryDisplayNode:
    """Display node for category tree view in UI.
    
    This is a data transfer object (DTO) that transforms the internal
    CategoryTree/CategoryNode structure into a format suitable for
    display in the CategoryPanel's tree view.
    
    Attributes:
        name: Display name (e.g., "app" from "HordeMode/scripts/app")
        path: Full category path (e.g., "HordeMode/scripts/app")
        checked: Checkbox state for UI display
        children: Child nodes for hierarchical display
    """
    
    name: str
    path: str
    checked: bool = False
    children: list[CategoryDisplayNode] = field(default_factory=list)
```

### §3.2 Function Rename: build_system_nodes → build_category_display_nodes

**File:** `src/core/category_tree.py`

**Before:**
```python
@beartype
def build_system_nodes(tree: CategoryTree) -> list[SystemNode]:
    """Build system nodes from a category tree.
    
    Transforms a CategoryTree into a list of SystemNode instances
    for display in the systems panel.
    ...
    """
```

**After:**
```python
@beartype
def build_category_display_nodes(tree: CategoryTree) -> list[CategoryDisplayNode]:
    """Build display nodes from a category tree for CategoryPanel.
    
    Transforms a CategoryTree into a list of CategoryDisplayNode instances
    for display in the CategoryPanel's tree view.
    ...
    """
```

### §3.3 Import Updates

**File:** `src/models/__init__.py`

**Before:**
```python
from src.models.system_node import SystemNode

__all__ = ["LogEntry", "LogLevel", "LogDocument", "FilterState", "FilterMode", "SystemNode"]
```

**After:**
```python
from src.models.category_display_node import CategoryDisplayNode

__all__ = ["LogEntry", "LogLevel", "LogDocument", "FilterState", "FilterMode", "CategoryDisplayNode"]
```

### §3.4 Export Updates

**File:** `src/core/__init__.py`

**Before:**
```python
from src.core.category_tree import CategoryTree, CategoryNode, build_system_nodes

__all__ = [
    ...
    "build_system_nodes",
    ...
]
```

**After:**
```python
from src.core.category_tree import CategoryTree, CategoryNode, build_category_display_nodes

__all__ = [
    ...
    "build_category_display_nodes",
    ...
]
```

---

## §4 Migration Guide

### §4.1 For Developers

**Before:**
```python
from src.models import SystemNode
from src.core import build_system_nodes

nodes = build_system_nodes(tree)
panel.set_categories(nodes)
```

**After:**
```python
from src.models import CategoryDisplayNode
from src.core import build_category_display_nodes

nodes = build_category_display_nodes(tree)
panel.set_categories(nodes)
```

### §4.2 For Tests

**Before:**
```python
from src.models import SystemNode

def test_category():
    node = SystemNode(name="test", path="test", checked=True)
```

**After:**
```python
from src.models import CategoryDisplayNode

def test_category():
    node = CategoryDisplayNode(name="test", path="test", checked=True)
```

---

## §5 Implementation Order

1. **Phase 1: Create new names**
   - Create `category_display_node.py` with `CategoryDisplayNode` class
   - Add `build_category_display_nodes()` function
   - Update `__init__.py` files with new exports

2. **Phase 2: Update internal code**
   - Update all internal imports to use new names
   - Update all function calls
   - Update all docstrings

3. **Phase 3: Update specifications**
   - Update all spec files with new terminology
   - Update API documentation

4. **Phase 4: Update tests**
   - Update test imports
   - Update test function calls

5. **Phase 5: Remove old file**
   - Delete `system_node.py`
   - Update all references

---

## §6 Testing Requirements

### §6.1 Unit Tests

- Verify `CategoryDisplayNode` class works correctly
- Verify `build_category_display_nodes()` produces correct output

### §6.2 Integration Tests

- Verify CategoryPanel displays correctly with new types
- Verify filter functionality unchanged
- Verify state persistence works

---

## §7 Cross-References

- **Category Tree:** [category-tree.md](category-tree.md)
- **UI Components:** [ui-components.md](ui-components.md)
- **Category Checkbox Behavior:** [category-checkbox-behavior.md](category-checkbox-behavior.md)
- **Main Controller:** [main-controller.md](main-controller.md)
- **API Reference:** [engine-api.yaml](../api/engine-api.yaml)

---

## §8 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-14 | Removed backward compatibility aliases (§4) |
| 1.0 | 2026-03-14 | Initial terminology cleanup specification |