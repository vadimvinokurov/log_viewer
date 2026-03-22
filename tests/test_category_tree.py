"""Tests for category tree management."""
from __future__ import annotations

import pytest

from src.core.category_tree import (
    CategoryTree,
    CategoryNode,
    build_category_display_nodes,
)


class TestCategoryNode:
    """Tests for CategoryNode class."""
    
    def test_node_creation(self) -> None:
        """Test creating a category node."""
        node = CategoryNode(
            name="test",
            full_path="parent/test"
        )
        
        assert node.name == "test"
        assert node.full_path == "parent/test"
        assert node.parent is None
        assert node.children == {}
        assert node.is_enabled is True
    
    def test_node_with_parent(self) -> None:
        """Test creating a node with parent."""
        parent = CategoryNode(name="parent", full_path="parent")
        child = CategoryNode(
            name="child",
            full_path="parent/child",
            parent=parent
        )
        
        assert child.parent == parent
        assert child.full_path == "parent/child"


class TestCategoryTree:
    """Tests for CategoryTree class."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tree = CategoryTree()
    
    def test_add_single_category(self) -> None:
        """Test adding a single category."""
        self.tree.add_category("HordeMode")
        
        assert "HordeMode" in self.tree
        assert len(self.tree) == 1
        
        node = self.tree.get_node("HordeMode")
        assert node is not None
        assert node.name == "HordeMode"
        assert node.full_path == "HordeMode"
    
    def test_add_hierarchical_category(self) -> None:
        """Test adding hierarchical categories."""
        self.tree.add_category("HordeMode/scripts/app")
        
        # All parent nodes should be created
        assert "HordeMode" in self.tree
        assert "HordeMode/scripts" in self.tree
        assert "HordeMode/scripts/app" in self.tree
        assert len(self.tree) == 3
        
        # Check parent-child relationships
        root = self.tree.get_node("HordeMode")
        assert root is not None
        assert "scripts" in root.children
        
        scripts = self.tree.get_node("HordeMode/scripts")
        assert scripts is not None
        assert scripts.parent == root
        assert "app" in scripts.children
        
        app = self.tree.get_node("HordeMode/scripts/app")
        assert app is not None
        assert app.parent == scripts
    
    def test_add_empty_category(self) -> None:
        """Test adding empty category does nothing."""
        self.tree.add_category("")
        
        assert len(self.tree) == 0
    
    def test_add_category_with_empty_parts(self) -> None:
        """Test adding category with empty parts."""
        self.tree.add_category("app//models")
        
        # Empty parts should be skipped
        assert "app" in self.tree
        assert "app/models" in self.tree
    
    def test_toggle_parent_affects_children(self) -> None:
        """Test that toggling parent affects all children."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        self.tree.add_category("app/views")
        
        # Disable parent
        self.tree.toggle("app", False)
        
        assert not self.tree.is_enabled("app")
        assert not self.tree.is_enabled("app/controllers")
        assert not self.tree.is_enabled("app/models")
        assert not self.tree.is_enabled("app/views")
        
        # Enable parent
        self.tree.toggle("app", True)
        
        assert self.tree.is_enabled("app")
        assert self.tree.is_enabled("app/controllers")
        assert self.tree.is_enabled("app/models")
        assert self.tree.is_enabled("app/views")
    
    def test_toggle_child_does_not_affect_parent(self) -> None:
        """Test that toggling child does not affect parent."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        
        # Disable one child
        self.tree.toggle("app/controllers", False)
        
        assert self.tree.is_enabled("app")
        assert not self.tree.is_enabled("app/controllers")
        assert self.tree.is_enabled("app/models")
    
    def test_toggle_nonexistent_category(self) -> None:
        """Test toggling a category that doesn't exist."""
        # Should not raise an error
        self.tree.toggle("nonexistent", False)
        assert True
    
    def test_is_enabled_nonexistent(self) -> None:
        """Test is_enabled for nonexistent category returns True."""
        assert self.tree.is_enabled("nonexistent") is True
    
    def test_get_enabled_categories(self) -> None:
        """Test getting enabled categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        self.tree.add_category("lib/utils")
        
        # All enabled by default
        enabled = self.tree.get_enabled_categories()
        assert len(enabled) == 5  # app, app/controllers, app/models, lib, lib/utils
        assert "app" in enabled
        assert "app/controllers" in enabled
        
        # Disable some
        self.tree.toggle("app", False)
        
        enabled = self.tree.get_enabled_categories()
        assert "app" not in enabled
        assert "app/controllers" not in enabled
        assert "lib" in enabled
    
    def test_get_all_categories(self) -> None:
        """Test getting all categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        
        all_cats = self.tree.get_all_categories()
        assert len(all_cats) == 4  # app, app/controllers, lib, lib/utils
        assert "app" in all_cats
        assert "app/controllers" in all_cats
        assert "lib" in all_cats
        assert "lib/utils" in all_cats
    
    def test_clear(self) -> None:
        """Test clearing all categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        
        self.tree.clear()
        
        assert len(self.tree) == 0
        assert self.tree.get_root_categories() == []
    
    def test_get_node(self) -> None:
        """Test getting node by path."""
        self.tree.add_category("app/controllers")
        
        node = self.tree.get_node("app/controllers")
        assert node is not None
        assert node.name == "controllers"
        
        nonexistent = self.tree.get_node("nonexistent")
        assert nonexistent is None
    
    def test_get_children(self) -> None:
        """Test getting children of a category."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        self.tree.add_category("lib/utils")
        
        # Get children of app
        children = self.tree.get_children("app")
        assert len(children) == 2
        names = {c.name for c in children}
        assert "controllers" in names
        assert "models" in names
        
        # Get children of root
        root_children = self.tree.get_children()
        assert len(root_children) == 2
        names = {c.name for c in root_children}
        assert "app" in names
        assert "lib" in names
        
        # Get children of nonexistent
        nonexistent_children = self.tree.get_children("nonexistent")
        assert nonexistent_children == []
    
    def test_get_root_categories(self) -> None:
        """Test getting root categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        
        roots = self.tree.get_root_categories()
        assert len(roots) == 2
        names = {r.name for r in roots}
        assert "app" in names
        assert "lib" in names
    
    def test_has_category(self) -> None:
        """Test checking if category exists."""
        self.tree.add_category("app/controllers")
        
        assert self.tree.has_category("app") is True
        assert self.tree.has_category("app/controllers") is True
        assert self.tree.has_category("nonexistent") is False
    
    def test_enable_all(self) -> None:
        """Test enabling all categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        
        self.tree.disable_all()
        self.tree.enable_all()
        
        assert self.tree.is_enabled("app")
        assert self.tree.is_enabled("app/controllers")
        assert self.tree.is_enabled("lib")
        assert self.tree.is_enabled("lib/utils")
    
    def test_disable_all(self) -> None:
        """Test disabling all categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        
        self.tree.disable_all()
        
        assert not self.tree.is_enabled("app")
        assert not self.tree.is_enabled("app/controllers")
        assert not self.tree.is_enabled("lib")
        assert not self.tree.is_enabled("lib/utils")
    
    def test_len(self) -> None:
        """Test __len__ method."""
        assert len(self.tree) == 0
        
        self.tree.add_category("app/controllers")
        assert len(self.tree) == 2  # app and app/controllers
        
        self.tree.add_category("app/models")
        assert len(self.tree) == 3  # app, app/controllers, app/models
    
    def test_contains(self) -> None:
        """Test __contains__ method."""
        self.tree.add_category("app/controllers")
        
        assert "app" in self.tree
        assert "app/controllers" in self.tree
        assert "nonexistent" not in self.tree
    
    def test_deeply_nested_categories(self) -> None:
        """Test deeply nested category paths."""
        self.tree.add_category("a/b/c/d/e/f")
        
        assert "a" in self.tree
        assert "a/b" in self.tree
        assert "a/b/c" in self.tree
        assert "a/b/c/d" in self.tree
        assert "a/b/c/d/e" in self.tree
        assert "a/b/c/d/e/f" in self.tree
        
        # Test toggle propagation
        self.tree.toggle("a", False)
        assert not self.tree.is_enabled("a/b/c/d/e/f")
        
        self.tree.toggle("a/b/c/d/e/f", True)
        assert self.tree.is_enabled("a/b/c/d/e/f")
        assert not self.tree.is_enabled("a/b/c/d/e")  # Parent still disabled
    
    def test_multiple_roots(self) -> None:
        """Test multiple root categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        self.tree.add_category("test/fixtures")
        
        roots = self.tree.get_root_categories()
        assert len(roots) == 3
        
        root_names = {r.name for r in roots}
        assert "app" in root_names
        assert "lib" in root_names
        assert "test" in root_names


class TestCategoryTreeEdgeCases:
    """Edge case tests for CategoryTree."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tree = CategoryTree()
    
    def test_duplicate_add(self) -> None:
        """Test adding same category twice."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/controllers")
        
        # Should only have one instance
        assert len(self.tree) == 2  # app and app/controllers
    
    def test_partial_path_add(self) -> None:
        """Test adding partial path then full path."""
        self.tree.add_category("app")
        self.tree.add_category("app/controllers")
        
        assert len(self.tree) == 2
        assert "app" in self.tree
        assert "app/controllers" in self.tree
    
    def test_toggle_leaf_then_parent(self) -> None:
        """Test toggling leaf then parent."""
        self.tree.add_category("app/controllers/main")
        
        # Disable leaf
        self.tree.toggle("app/controllers/main", False)
        assert not self.tree.is_enabled("app/controllers/main")
        assert self.tree.is_enabled("app/controllers")
        
        # Disable parent
        self.tree.toggle("app/controllers", False)
        assert not self.tree.is_enabled("app/controllers")
        assert not self.tree.is_enabled("app/controllers/main")
        
        # Enable parent
        self.tree.toggle("app/controllers", True)
        assert self.tree.is_enabled("app/controllers")
        assert self.tree.is_enabled("app/controllers/main")
    
    def test_special_characters_in_category(self) -> None:
        """Test categories with special characters."""
        # Categories can have various characters
        self.tree.add_category("app/controllers-v1")
        self.tree.add_category("lib/module.sub")
        
        assert "app/controllers-v1" in self.tree
        assert "lib/module.sub" in self.tree
    
    def test_unicode_category(self) -> None:
        """Test categories with unicode characters."""
        self.tree.add_category("приложение/модели")
        
        assert "приложение" in self.tree
        assert "приложение/модели" in self.tree


class TestCategoryVisibility:
    """Tests for is_category_visible method.
    
    // Ref: docs/specs/features/category-checkbox-behavior.md §6.1.3
    // Visibility Rule: log_visible(category) = category.checked (simple checkbox state)
    // Performance: O(1) lookup instead of O(h) ancestor traversal
    """
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tree = CategoryTree()
    
    def test_visibility_with_enabled_parent_disabled_child(self) -> None:
        """Test visibility when parent is enabled, child is disabled.
        
        NEW BEHAVIOR: Parent enabled, child disabled → child logs HIDDEN
        (Each checkbox independently controls its own logs)
        """
        self.tree.add_category("parent/child")
        
        # Enable parent (cascade enables children)
        self.tree.toggle("parent", True)
        # Then disable child independently
        self.tree.set_enabled("parent/child", False)
        
        assert self.tree.is_enabled("parent") is True
        assert self.tree.is_enabled("parent/child") is False
        # Child is NOT visible - only its own checkbox state matters
        assert self.tree.is_category_visible("parent/child") is False
    
    def test_visibility_with_disabled_parent_enabled_child(self) -> None:
        """Test visibility when parent is disabled, child is enabled.
        
        Child enabled → child logs visible (independent of parent state)
        """
        self.tree.add_category("parent/child")
        
        # Disable parent (cascade disables children)
        self.tree.toggle("parent", False)
        # Then enable child independently
        self.tree.set_enabled("parent/child", True)
        
        assert self.tree.is_enabled("parent") is False
        assert self.tree.is_enabled("parent/child") is True
        # Child is visible - its own checkbox is checked
        assert self.tree.is_category_visible("parent/child") is True
    
    def test_visibility_with_all_disabled(self) -> None:
        """Test visibility when parent and child are both disabled."""
        self.tree.add_category("parent/child")
        
        # Disable parent (cascades to children)
        self.tree.toggle("parent", False)
        
        assert self.tree.is_enabled("parent") is False
        assert self.tree.is_enabled("parent/child") is False
        assert self.tree.is_category_visible("parent/child") is False
    
    def test_visibility_with_all_enabled(self) -> None:
        """Test visibility when all categories are enabled."""
        self.tree.add_category("parent/child")
        
        # All enabled by default
        assert self.tree.is_enabled("parent") is True
        assert self.tree.is_enabled("parent/child") is True
        assert self.tree.is_category_visible("parent/child") is True
        assert self.tree.is_category_visible("parent") is True
    
    def test_visibility_with_invalid_path(self) -> None:
        """Test visibility with invalid path returns True (default enabled)."""
        # Invalid path should return True (default enabled) per spec §7.1
        assert self.tree.is_category_visible("nonexistent") is True
        assert self.tree.is_category_visible("also/nonexistent/path") is True
    
    def test_visibility_with_enabled_self(self) -> None:
        """Test visibility when category itself is enabled."""
        self.tree.add_category("parent/child")
        
        # Child enabled by default
        assert self.tree.is_category_visible("parent/child") is True
        
        # Explicitly enable
        self.tree.set_enabled("parent/child", True)
        assert self.tree.is_category_visible("parent/child") is True
    
    def test_visibility_root_category(self) -> None:
        """Test visibility for root-level category."""
        self.tree.add_category("root")
        
        # Enabled by default
        assert self.tree.is_category_visible("root") is True
        
        # Disabled
        self.tree.toggle("root", False)
        assert self.tree.is_category_visible("root") is False
    
    def test_visibility_multiple_branches(self) -> None:
        """Test visibility with multiple sibling branches.
        
        Each category's visibility is independent - based only on its own state.
        """
        self.tree.add_category("parent/child1")
        self.tree.add_category("parent/child2")
        self.tree.add_category("parent/child3")
        
        # Disable parent (cascades to all children)
        self.tree.toggle("parent", False)
        
        # Enable only child2
        self.tree.set_enabled("parent/child2", True)
        
        # Each category's visibility depends only on its own state
        assert self.tree.is_category_visible("parent/child1") is False
        assert self.tree.is_category_visible("parent/child2") is True
        assert self.tree.is_category_visible("parent/child3") is False
    
    def test_visibility_deep_hierarchy_independent(self) -> None:
        """Test visibility with deep hierarchy - each category independent.
        
        With the new simple checkbox logic, each category's visibility
        depends only on its own checkbox state, not ancestors.
        """
        self.tree.add_category("a/b/c/d/e/f")
        
        # All enabled by default
        assert self.tree.is_category_visible("a/b/c/d/e/f") is True
        
        # Disable root - all should be invisible (cascade disabled them)
        self.tree.toggle("a", False)
        assert self.tree.is_category_visible("a/b/c/d/e/f") is False
        
        # Enable just the leaf - only that category should be visible
        self.tree.set_enabled("a/b/c/d/e/f", True)
        assert self.tree.is_category_visible("a/b/c/d/e/f") is True
        assert self.tree.is_category_visible("a/b/c/d/e") is False
        assert self.tree.is_category_visible("a/b/c/d") is False
        assert self.tree.is_category_visible("a/b/c") is False
        assert self.tree.is_category_visible("a/b") is False
        assert self.tree.is_category_visible("a") is False


class TestCategorySorting:
    """Tests for alphabetical category sorting.
    
    // Ref: docs/specs/features/category-alphabetical-sorting.md §7.1, §8.1-8.4
    // Sorting: Case-insensitive alphabetical at each nesting level
    """
    
    def test_sorting_root_level(self) -> None:
        """Test root categories are sorted alphabetically.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §7.1
        """
        tree = CategoryTree()
        tree.add_category("Zebra/app")
        tree.add_category("Alpha/core")
        tree.add_category("Beta/network")
        
        nodes = build_category_display_nodes(tree)
        
        assert len(nodes) == 3
        assert nodes[0].name == "Alpha"
        assert nodes[1].name == "Beta"
        assert nodes[2].name == "Zebra"
    
    def test_sorting_nested_level(self) -> None:
        """Test nested categories are sorted at each level.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §7.1
        """
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
    
    def test_sorting_case_insensitive(self) -> None:
        """Test sorting is case-insensitive.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §7.1
        """
        tree = CategoryTree()
        tree.add_category("Root/zebra")
        tree.add_category("Root/Alpha")
        tree.add_category("Root/beta")
        
        nodes = build_category_display_nodes(tree)
        
        assert nodes[0].children[0].name == "Alpha"
        assert nodes[0].children[1].name == "beta"
        assert nodes[0].children[2].name == "zebra"
    
    def test_sorting_deep_nesting(self) -> None:
        """Test sorting works at multiple nesting levels.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §7.1
        """
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
    
    def test_empty_tree(self) -> None:
        """Test empty tree returns empty list.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §8.1
        """
        tree = CategoryTree()
        nodes = build_category_display_nodes(tree)
        assert nodes == []
    
    def test_single_category(self) -> None:
        """Test single category returns single node.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §8.2
        """
        tree = CategoryTree()
        tree.add_category("Root")
        nodes = build_category_display_nodes(tree)
        assert len(nodes) == 1
        assert nodes[0].name == "Root"
    
    def test_unicode_sorting(self) -> None:
        """Test Unicode categories sort correctly.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §8.3
        """
        tree = CategoryTree()
        tree.add_category("Root/яблоко")  # apple
        tree.add_category("Root/арбуз")    # watermelon
        tree.add_category("Root/банан")    # banana
        
        nodes = build_category_display_nodes(tree)
        
        # Unicode code point order
        assert nodes[0].children[0].name == "арбуз"
        assert nodes[0].children[1].name == "банан"
        assert nodes[0].children[2].name == "яблоко"
    
    def test_numeric_prefix_sorting(self) -> None:
        """Test categories with numeric prefixes sort correctly.
        
        // Ref: docs/specs/features/category-alphabetical-sorting.md §8.4
        // String sort on full name (not numeric prefix extraction):
        // "10_app" < "1_network" < "2_core" (comparing character by character)
        """
        tree = CategoryTree()
        tree.add_category("Root/10_app")
        tree.add_category("Root/2_core")
        tree.add_category("Root/1_network")
        
        nodes = build_category_display_nodes(tree)
        
        # String sort compares full names character by character:
        # "10_app" < "1_network" (because "0" < "_" in second character)
        # "1_network" < "2_core" (because "1" < "2")
        assert nodes[0].children[0].name == "10_app"
        assert nodes[0].children[1].name == "1_network"
        assert nodes[0].children[2].name == "2_core"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])