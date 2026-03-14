# Category Tree Specification

**Version:** 1.1  
**Last Updated:** 2026-03-14  
**Project Context:** Python Tooling (Desktop Application)  
**Related:** [category-checkbox-behavior.md](category-checkbox-behavior.md)

---

## §1 Overview

The Category Tree provides hierarchical category management with efficient lookup and visibility-based filtering. Categories are derived from log file parsing.

---

## §2 Architecture

### §2.1 Tree Structure

```
CategoryTree
├── _root: CategoryNode (empty name, empty path)
└── _nodes: dict[str, CategoryNode]  # Flat lookup by path

CategoryNode
├── name: str              # Node name (e.g., "app")
├── full_path: str         # Full path (e.g., "HordeMode/scripts/app")
├── parent: CategoryNode | None
├── children: dict[str, CategoryNode]
└── is_enabled: bool
```

### §2.2 Example Tree

```
_root
├── HordeMode/
│   ├── scripts/
│   │   ├── app (enabled=True)
│   │   └── core (enabled=True)
│   └── config (enabled=False)
└── Game/
    └── network (enabled=True)
```

---

## §3 Core Operations

### §3.1 Adding Categories

```python
def add_category(self, path: str) -> None:
    """
    Add a category path to the tree.
    
    Creates all intermediate nodes as needed.
    
    Args:
        path: Category path like "HordeMode/scripts/app"
    
    Example:
        tree.add_category("HordeMode/scripts/app")
        # Creates: HordeMode -> scripts -> app
    """
```

**Algorithm:**
1. Split path by `/`
2. Traverse from root, creating nodes as needed
3. Store each node in `_nodes` dict for O(1) lookup

### §3.2 Toggle (Cascade to Children)

```python
def toggle(self, path: str, enabled: bool) -> None:
    """
    Toggle category and all children.
    
    When a parent is toggled, all children are toggled to the same state.
    Child toggles do NOT affect parent.
    
    Ref: docs/specs/features/category-checkbox-behavior.md §3.1, §3.2
    """
```

**Behavior:**
- Parent checked → All children checked
- Parent unchecked → All children unchecked
- Child checked/uncheck → Parent unchanged

### §3.3 Set Enabled (No Cascade)

```python
def set_enabled(self, path: str, enabled: bool) -> None:
    """
    Set category enabled state WITHOUT cascading to children.
    
    Use this when syncing exact checkbox states from UI.
    """
```

### §3.4 Visibility Check

```python
def is_category_visible(self, path: str) -> bool:
    """
    Check if a category's logs should be visible.
    
    A category is visible if it OR any ancestor is enabled.
    
    Ref: docs/specs/features/category-checkbox-behavior.md §6.1.3
    
    Returns:
        True if visible, False otherwise.
        Returns True (default enabled) for invalid paths.
    """
```

**Algorithm:**
1. Check if category itself is enabled → return True
2. Walk up tree checking ancestors
3. If any ancestor is enabled → return True
4. Return False

---

## §4 API Reference

### §4.1 CategoryTree

```python
class CategoryTree:
    def __init__(self) -> None:
        """Initialize empty tree."""
    
    @beartype
    def add_category(self, path: str) -> None:
        """Add a category path to the tree."""
    
    @beartype
    def toggle(self, path: str, enabled: bool) -> None:
        """Toggle category and cascade to children."""
    
    @beartype
    def set_enabled(self, path: str, enabled: bool) -> None:
        """Set category enabled state without cascade."""
    
    @beartype
    def is_enabled(self, path: str) -> bool:
        """Check if category is enabled."""
    
    @beartype
    def is_category_visible(self, path: str) -> bool:
        """Check if category is visible (self or ancestor enabled)."""
    
    @beartype
    def get_enabled_categories(self) -> set[str]:
        """Get all enabled category paths."""
    
    @beartype
    def get_all_categories(self) -> set[str]:
        """Get all category paths."""
    
    def clear(self) -> None:
        """Clear all categories."""
    
    @beartype
    def get_node(self, path: str) -> CategoryNode | None:
        """Get node by path."""
    
    @beartype
    def get_children(self, path: str | None = None) -> list[CategoryNode]:
        """Get direct children of a category."""
    
    @beartype
    def get_root_categories(self) -> list[CategoryNode]:
        """Get all root-level categories."""
    
    @beartype
    def has_category(self, path: str) -> bool:
        """Check if category exists."""
    
    @beartype
    def enable_all(self) -> None:
        """Enable all categories."""
    
    @beartype
    def disable_all(self) -> None:
        """Disable all categories."""
    
    def __len__(self) -> int:
        """Return number of categories."""
    
    def __contains__(self, path: str) -> bool:
        """Check if category path exists."""
```

### §4.2 CategoryNode

```python
@dataclass
class CategoryNode:
    """Node in category tree."""
    name: str
    full_path: str
    parent: CategoryNode | None = None
    children: dict[str, CategoryNode] = field(default_factory=dict)
    is_enabled: bool = True
```

### §4.3 Helper Functions

```python
@beartype
def build_system_nodes(tree: CategoryTree) -> list[SystemNode]:
    """
    Build system nodes from a category tree.
    
    Transforms CategoryTree into list of SystemNode instances
    for display in the systems panel.
    
    Args:
        tree: The CategoryTree to transform.
    
    Returns:
        List of SystemNode instances representing the system tree.
    """
```

---

## §5 Performance

### §5.1 Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `add_category` | O(d) | d = path depth |
| `toggle` | O(n) | n = descendants count |
| `set_enabled` | O(1) | Direct dict lookup |
| `is_enabled` | O(1) | Direct dict lookup |
| `is_category_visible` | O(d) | d = path depth |
| `get_enabled_categories` | O(n) | n = total nodes |
| `get_node` | O(1) | Dict lookup |

### §5.2 Memory

| Component | Size | Notes |
|-----------|------|-------|
| CategoryNode | ~80 bytes | Name + path + pointers |
| Tree (1000 categories) | ~80 KB | Nodes + dict overhead |
| Tree (10000 categories) | ~800 KB | Linear scaling |

---

## §6 Thread Safety

### §6.1 Guarantees

- **Not thread-safe** - Owned by single thread (FilterController)
- **Read-only after compilation** - Compiled filter is thread-safe
- **No concurrent modification** - Modify only on main thread

### §6.2 Usage Pattern

```python
# Main thread: Modify tree
tree.toggle("HordeMode", False)

# Main thread: Compile filter (creates snapshot)
filter_func = engine.compile_filter(state, tree)

# Background thread: Apply filter (safe, read-only)
filtered = [e for e in entries if filter_func(e)]
```

---

## §7 State Persistence

### §7.1 Saving State

```python
# Get checkbox states
states = window.get_category_panel().get_category_states()
settings_manager.set_category_states(states)
settings_manager.save()
```

### §7.2 Restoring State

```python
# Load saved states
saved_states = settings_manager.get_category_states()

# Apply to tree
for path, checked in saved_states.items():
    tree.set_enabled(path, checked)  # No cascade
```

---

## §8 Testing

### §8.1 Unit Tests

```python
def test_add_category():
    """Test adding categories creates hierarchy."""
    tree = CategoryTree()
    tree.add_category("HordeMode/scripts/app")
    
    assert tree.has_category("HordeMode")
    assert tree.has_category("HordeMode/scripts")
    assert tree.has_category("HordeMode/scripts/app")

def test_toggle_cascade():
    """Test toggle cascades to children."""
    tree = CategoryTree()
    tree.add_category("HordeMode/scripts/app")
    tree.toggle("HordeMode", False)
    
    assert tree.is_enabled("HordeMode") == False
    assert tree.is_enabled("HordeMode/scripts") == False
    assert tree.is_enabled("HordeMode/scripts/app") == False

def test_visibility():
    """Test visibility with ancestor checking."""
    tree = CategoryTree()
    tree.add_category("HordeMode/scripts/app")
    tree.set_enabled("HordeMode/scripts/app", False)
    tree.set_enabled("HordeMode/scripts", True)  # Ancestor enabled
    
    # Child visible via ancestor
    assert tree.is_category_visible("HordeMode/scripts/app") == True
```

### §8.2 Integration Tests

See [test_category_tree.py](../../tests/test_category_tree.py)

---

## §9 Cross-References

- **Checkbox Behavior:** [category-checkbox-behavior.md](category-checkbox-behavior.md)
- **Filter Engine:** [filter-engine.md](filter-engine.md)
- **Filter Controller:** [filter-controller.md](filter-controller.md)
- **Category Panel:** [category-panel.md](category-panel.md)

---

## §10 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-14 | Removed custom categories feature |
| 1.0 | 2026-03-13 | Initial category tree specification |