# Category Alphabetical Sorting Specification

**Version:** v1.0  
**Last Updated:** 2026-03-16  
**Project Context:** Python Tooling (Desktop Application)  
**Related:** [category-tree.md](category-tree.md), [ui-components.md](ui-components.md)

---

## §1 Overview

Categories in the Category Panel tree view must be sorted alphabetically at each nesting level. This improves discoverability and consistency for users navigating through hierarchical log categories.

---

## §2 Requirements

### §2.1 Sorting Behavior

| Requirement | Description |
|-------------|-------------|
| **Scope** | Sorting applies at each tree level independently |
| **Order** | Ascending alphabetical (A-Z) |
| **Case** | Case-insensitive comparison using `str.lower()` |
| **Stability** | Sort is stable - equal elements maintain relative order |
| **Locale** | Use simple Unicode code point comparison (no locale-specific sorting) |

### §2.2 Example

Before sorting:
```
HordeMode/
├── scripts/
│   ├── app
│   ├── core
│   └── network
└── config
Game/
└── network
```

After sorting:
```
Game/                    # Sorted at root level
└── network
HordeMode/               # Sorted at root level
├── config               # Sorted under HordeMode
└── scripts/             # Sorted under HordeMode
    ├── app              # Sorted under scripts
    ├── core             # Sorted under scripts
    └── network          # Sorted under scripts
```

---

## §3 Implementation Location

### §3.1 Primary Location: `build_category_display_nodes()`

Sorting shall be implemented in the [`build_category_display_nodes()`](../../src/core/category_tree.py:247) function in [`src/core/category_tree.py`](../../src/core/category_tree.py).

**Rationale:**
- Data transformation concern, not UI concern
- Ensures consistent ordering regardless of insertion order
- Single point of change for all consumers
- Performance: sort once during transformation, not on every UI update

### §3.2 Alternative: `CategoryTree.get_children()`

Sorting could alternatively be implemented in [`CategoryTree.get_children()`](../../src/core/category_tree.py:183).

**Trade-offs:**
- ✅ More reusable - all callers benefit
- ❌ Called multiple times - sort repeated unnecessarily
- ❌ Changes contract of `get_children()` - may affect other callers

**Decision:** Use `build_category_display_nodes()` for sorting.

---

## §4 API Changes

### §4.1 Modified Function

```python
@beartype
def build_category_display_nodes(tree: CategoryTree) -> list[CategoryDisplayNode]:
    """Build display nodes from a category tree for CategoryPanel.

    Transforms a CategoryTree into a list of CategoryDisplayNode instances
    for display in the CategoryPanel's tree view.
    
    Categories are sorted alphabetically at each nesting level (case-insensitive).

    Args:
        tree: The CategoryTree to transform.

    Returns:
        List of CategoryDisplayNode instances representing the category tree,
        sorted alphabetically at each level.
    """
    nodes: list[CategoryDisplayNode] = []

    # Get root categories from the category tree
    root_categories = tree.get_root_categories()
    
    # Sort root categories alphabetically (case-insensitive)
    root_categories.sort(key=lambda node: node.name.lower())

    for root_cat in root_categories:
        node = _build_category_display_node_from_category(tree, root_cat)
        if node:
            nodes.append(node)

    return nodes
```

### §4.2 Modified Helper Function

```python
@beartype
def _build_category_display_node_from_category(
    tree: CategoryTree,
    category: CategoryNode | str
) -> CategoryDisplayNode | None:
    """Build a category display node from a category.

    Args:
        tree: The CategoryTree to use.
        category: CategoryNode or category path string.

    Returns:
        CategoryDisplayNode or None.
    """
    # ... existing code ...

    # Get children for this category
    children = tree.get_children(category_path)
    
    # Sort children alphabetically (case-insensitive)
    children.sort(key=lambda node: node.name.lower())

    # Build child nodes
    child_nodes: list[CategoryDisplayNode] = []
    for child in children:
        child_node = _build_category_display_node_from_category(tree, child)
        if child_node:
            child_nodes.append(child_node)

    # ... rest of existing code ...
```

---

## §5 Performance

### §5.1 Time Complexity

| Operation | Before | After | Notes |
|-----------|--------|-------|-------|
| `build_category_display_nodes` | O(n) | O(n log n) | n = total nodes |
| `get_root_categories` | O(1) | O(1) | Returns list reference |
| `get_children` | O(1) | O(1) | Returns list reference |

### §5.2 Sorting Overhead

For typical category counts:
- 100 categories: ~66 additional comparisons (negligible)
- 1000 categories: ~996 additional comparisons (~1ms)
- 10000 categories: ~13300 additional comparisons (~10ms)

**Conclusion:** Sorting overhead is acceptable for expected category counts (< 5000).

### §5.3 Memory

No additional memory allocation - sorting is in-place on temporary lists.

---

## §6 Thread Safety

### §6.1 Guarantees

- **Main thread only** - `build_category_display_nodes()` called from main thread
- **No concurrent access** - CategoryTree owned by FilterController
- **Read-only during sort** - Tree not modified during display node creation

### §6.2 Thread Safety Analysis

Per [docs/specs/global/threading.md](../global/threading.md) §8.1:
- CategoryTree modifications happen on main thread only
- Display nodes are created on main thread during UI updates
- No cross-thread data sharing

---

## §7 Testing

### §7.1 Unit Tests

```python
def test_sorting_root_level():
    """Test root categories are sorted alphabetically."""
    tree = CategoryTree()
    tree.add_category("Zebra/app")
    tree.add_category("Alpha/core")
    tree.add_category("Beta/network")
    
    nodes = build_category_display_nodes(tree)
    
    assert len(nodes) == 3
    assert nodes[0].name == "Alpha"
    assert nodes[1].name == "Beta"
    assert nodes[2].name == "Zebra"

def test_sorting_nested_level():
    """Test nested categories are sorted at each level."""
    tree = CategoryTree()
    tree.add_category("Root/Zebra")
    tree.add_category("Root/Alpha")
    tree.add_category("Root/Beta")
    
    nodes = build_category_display_nodes(tree)
    
    assert len(nodes) == 1
    assert nodes[0].name == "Root"
    assert len(nodes[0].children) == 3
    assert nodes[0].children[0].name == "Alpha"
    assert nodes[0].children[1].name == "Beta"
    assert nodes[0].children[2].name == "Zebra"

def test_sorting_case_insensitive():
    """Test sorting is case-insensitive."""
    tree = CategoryTree()
    tree.add_category("Root/zebra")
    tree.add_category("Root/Alpha")
    tree.add_category("Root/beta")
    
    nodes = build_category_display_nodes(tree)
    
    assert nodes[0].children[0].name == "Alpha"
    assert nodes[0].children[1].name == "beta"
    assert nodes[0].children[2].name == "zebra"

def test_sorting_deep_nesting():
    """Test sorting works at multiple nesting levels."""
    tree = CategoryTree()
    tree.add_category("A/Z/Y")
    tree.add_category("A/Z/A")
    tree.add_category("A/A/Z")
    tree.add_category("A/A/A")
    
    nodes = build_category_display_nodes(tree)
    
    # Level A
    assert nodes[0].name == "A"
    
    # Level A/A and A/Z (sorted)
    assert nodes[0].children[0].name == "A"
    assert nodes[0].children[1].name == "Z"
    
    # Level A/A/A and A/A/Z (sorted)
    assert nodes[0].children[0].children[0].name == "A"
    assert nodes[0].children[0].children[1].name == "Z"
    
    # Level A/Z/A and A/Z/Y (sorted)
    assert nodes[0].children[1].children[0].name == "A"
    assert nodes[0].children[1].children[1].name == "Y"
```

### §7.2 Integration Tests

```python
def test_category_panel_displays_sorted():
    """Test CategoryPanel displays categories sorted."""
    # Create tree with unsorted categories
    tree = CategoryTree()
    tree.add_category("Zebra/app")
    tree.add_category("Alpha/core")
    
    # Build display nodes
    nodes = build_category_display_nodes(tree)
    
    # Create panel and set categories
    panel = CategoryPanel()
    panel.set_categories(nodes)
    
    # Verify root items are sorted
    model = panel._model
    root = model.invisibleRootItem()
    
    assert root.rowCount() == 2
    assert root.child(0).text() == "Alpha"
    assert root.child(1).text() == "Zebra"
```

---

## §8 Edge Cases

### §8.1 Empty Categories

```python
def test_empty_tree():
    """Test empty tree returns empty list."""
    tree = CategoryTree()
    nodes = build_category_display_nodes(tree)
    assert nodes == []
```

### §8.2 Single Category

```python
def test_single_category():
    """Test single category returns single node."""
    tree = CategoryTree()
    tree.add_category("Root")
    nodes = build_category_display_nodes(tree)
    assert len(nodes) == 1
    assert nodes[0].name == "Root"
```

### §8.3 Unicode Categories

```python
def test_unicode_sorting():
    """Test Unicode categories sort correctly."""
    tree = CategoryTree()
    tree.add_category("Root/яблоко")  # apple
    tree.add_category("Root/арбуз")    # watermelon
    tree.add_category("Root/банан")    # banana
    
    nodes = build_category_display_nodes(tree)
    
    # Unicode code point order
    assert nodes[0].children[0].name == "арбуз"
    assert nodes[0].children[1].name == "банан"
    assert nodes[0].children[2].name == "яблоко"
```

### §8.4 Numeric Prefixes

```python
def test_numeric_prefix_sorting():
    """Test categories with numeric prefixes sort correctly."""
    tree = CategoryTree()
    tree.add_category("Root/10_app")
    tree.add_category("Root/2_core")
    tree.add_category("Root/1_network")
    
    nodes = build_category_display_nodes(tree)
    
    # String sort (not numeric): "1" < "10" < "2"
    assert nodes[0].children[0].name == "1_network"
    assert nodes[0].children[1].name == "10_app"
    assert nodes[0].children[2].name == "2_core"
```

---

## §9 Cross-References

- **Category Tree:** [category-tree.md](category-tree.md)
- **Category Panel:** [ui-components.md](ui-components.md) §5
- **Threading:** [../global/threading.md](../global/threading.md)
- **Category Display Node:** [../../src/models/category_display_node.py](../../src/models/category_display_node.py)

---

## §10 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-16 | Initial specification for alphabetical category sorting |