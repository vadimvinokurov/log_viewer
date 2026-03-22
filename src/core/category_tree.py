"""Category tree management."""
from __future__ import annotations

from dataclasses import dataclass, field

from beartype import beartype

from src.models import CategoryDisplayNode


@dataclass
class CategoryNode:
    """Node in category tree."""
    name: str
    full_path: str
    parent: CategoryNode | None = None
    children: dict[str, CategoryNode] = field(default_factory=dict)
    is_enabled: bool = True


class CategoryTree:
    """Tree structure for category management."""
    
    @beartype
    def __init__(self):
        self._root = CategoryNode(name="", full_path="")
        self._nodes: dict[str, CategoryNode] = {}
    
    @beartype
    def add_category(self, path: str) -> None:
        """
        Add a category path to the tree.
        
        Args:
            path: Category path like "HordeMode/scripts/app"
        """
        if not path:
            return
        
        parts = path.split('/')
        current = self._root
        current_path = ""
        
        for part in parts:
            if not part:
                continue
            
            current_path = f"{current_path}/{part}" if current_path else part
            
            if part not in current.children:
                node = CategoryNode(
                    name=part,
                    full_path=current_path,
                    parent=current
                )
                current.children[part] = node
                self._nodes[current_path] = node
            
            current = current.children[part]
    
    @beartype
    def toggle(self, path: str, enabled: bool) -> None:
        """
        Toggle category and all children.
        
        When a parent is toggled, all children are toggled to the same state.
        Child toggles do NOT affect parent.
        
        Args:
            path: Category path
            enabled: New enabled state
        """
        node = self._nodes.get(path)
        if node is None:
            return
        
        node.is_enabled = enabled
        self._set_children_enabled(node, enabled)
    
    @beartype
    def set_enabled(self, path: str, enabled: bool) -> None:
        """
        Set category enabled state WITHOUT cascading to children.
        
        Use this when you want to set the exact state of each category
        individually, without affecting children.
        
        Args:
            path: Category path
            enabled: New enabled state
        """
        node = self._nodes.get(path)
        if node is None:
            return
        
        node.is_enabled = enabled
    
    def _set_children_enabled(self, node: CategoryNode, enabled: bool) -> None:
        """Recursively set enabled state for all children."""
        for child in node.children.values():
            child.is_enabled = enabled
            self._set_children_enabled(child, enabled)
    
    @beartype
    def is_enabled(self, path: str) -> bool:
        """
        Check if category is enabled.
        
        Args:
            path: Category path
            
        Returns:
            True if enabled, False otherwise
        """
        node = self._nodes.get(path)
        if node is None:
            return True
        return node.is_enabled
    
    @beartype
    def is_category_visible(self, path: str) -> bool:
        """Check if a category's logs should be visible.
        
        A category is visible if it is enabled (checked).
        This is a simple checkbox-based visibility - each category's
        checkbox independently controls its own logs.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §6.1.3
        // Logic: Simple checkbox state check (no ancestor traversal)
        // Performance: O(1) lookup instead of O(h) ancestor traversal
        // Error: Returns True (default enabled) for invalid paths
        
        Args:
            path: Category path
            
        Returns:
            True if visible (enabled), False otherwise
        """
        return self.is_enabled(path)
    
    @beartype
    def get_enabled_categories(self) -> set[str]:
        """
        Get all enabled category paths.
        
        Returns:
            Set of enabled category paths
        """
        return {
            path for path, node in self._nodes.items()
            if node.is_enabled
        }
    
    @beartype
    def get_all_categories(self) -> set[str]:
        """
        Get all category paths.
        
        Returns:
            Set of all category paths
        """
        return set(self._nodes.keys())
    
    def clear(self) -> None:
        """Clear all categories."""
        self._root = CategoryNode(name="", full_path="")
        self._nodes.clear()
    
    @beartype
    def get_node(self, path: str) -> CategoryNode | None:
        """
        Get node by path.
        
        Args:
            path: Category path
            
        Returns:
            CategoryNode if found, None otherwise
        """
        return self._nodes.get(path)
    
    @beartype
    def get_children(self, path: str | None = None) -> list[CategoryNode]:
        """
        Get direct children of a category.
        
        Args:
            path: Category path, or None for root children
            
        Returns:
            List of child nodes
        """
        if path is None or path == "":
            return list(self._root.children.values())
        
        node = self._nodes.get(path)
        if node is None:
            return []
        
        return list(node.children.values())
    
    @beartype
    def get_root_categories(self) -> list[CategoryNode]:
        """
        Get all root-level categories.
        
        Returns:
            List of root category nodes
        """
        return list(self._root.children.values())
    
    @beartype
    def has_category(self, path: str) -> bool:
        """
        Check if category exists.
        
        Args:
            path: Category path
            
        Returns:
            True if category exists
        """
        return path in self._nodes
    
    @beartype
    def enable_all(self) -> None:
        """Enable all categories."""
        for node in self._nodes.values():
            node.is_enabled = True
    
    @beartype
    def disable_all(self) -> None:
        """Disable all categories."""
        for node in self._nodes.values():
            node.is_enabled = False
    
    def __len__(self) -> int:
        """Return number of categories."""
        return len(self._nodes)
    
    def __contains__(self, path: str) -> bool:
        """Check if category path exists."""
        return path in self._nodes


@beartype
def build_category_display_nodes(tree: CategoryTree) -> list[CategoryDisplayNode]:
    """Build display nodes from a category tree for CategoryPanel.

    Transforms a CategoryTree into a list of CategoryDisplayNode instances
    for display in the CategoryPanel's tree view.
    
    Categories are sorted alphabetically at each nesting level (case-insensitive).

    // Ref: docs/specs/features/category-alphabetical-sorting.md §3.1
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    // Performance: O(n log n) acceptable for <5000 categories
    // Memory: In-place sort on temporary lists, no additional allocation

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
    # Ref: docs/specs/features/category-alphabetical-sorting.md §2.1
    root_categories.sort(key=lambda node: node.name.lower())

    for root_cat in root_categories:
        node = _build_category_display_node_from_category(tree, root_cat)
        if node:
            nodes.append(node)

    return nodes


@beartype
def _build_category_display_node_from_category(
    tree: CategoryTree,
    category: CategoryNode | str
) -> CategoryDisplayNode | None:
    """Build a category display node from a category.

    // Ref: docs/specs/features/category-alphabetical-sorting.md §4.2
    // Sorting: Children sorted alphabetically (case-insensitive) at each level

    Args:
        tree: The CategoryTree to use.
        category: CategoryNode or category path string.

    Returns:
        CategoryDisplayNode or None.
    """
    # Handle both CategoryNode and string path
    if isinstance(category, CategoryNode):
        category_node = category
        category_path = category.full_path
    else:
        category_path = category
        category_node = tree.get_node(category_path)

    if category_node is None:
        return None

    # Get children for this category
    children = tree.get_children(category_path)
    
    # Sort children alphabetically (case-insensitive)
    # Ref: docs/specs/features/category-alphabetical-sorting.md §2.1
    children.sort(key=lambda node: node.name.lower())

    # Build child nodes
    child_nodes: list[CategoryDisplayNode] = []
    for child in children:
        child_node = _build_category_display_node_from_category(tree, child)
        if child_node:
            child_nodes.append(child_node)

    # Create node
    # Extract the last part of the category path for display
    display_name = category_path.split("/")[-1] if "/" in category_path else category_path

    return CategoryDisplayNode(
        name=display_name,
        path=category_path,
        checked=True,
        children=child_nodes
    )