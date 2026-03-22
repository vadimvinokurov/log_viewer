"""Tests for CategoryPanel expand/collapse functionality.

// Ref: docs/specs/features/category-tree-expand-collapse.md §11
"""
from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.views.category_panel import CategoryPanel, ExpandCollapseState
from src.models import CategoryDisplayNode


# === Fixtures ===

@pytest.fixture
def category_panel(qapp: QApplication) -> CategoryPanel:
    """Create a CategoryPanel for testing.
    
    Args:
        qapp: QApplication fixture from conftest.
    
    Returns:
        CategoryPanel instance with test categories.
    """
    panel = CategoryPanel()
    panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True, children=[
            CategoryDisplayNode(name="B", path="A/B", checked=True)
        ])
    ])
    return panel


# === Unit Tests (§11.1) ===

def test_expand_all(category_panel: CategoryPanel) -> None:
    """Test expand_all expands all nodes.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.1
    """
    # Collapse all first
    category_panel.collapse_all()
    assert category_panel.is_all_collapsed()
    
    # Expand
    category_panel.expand_all()
    
    # Verify all expanded
    assert category_panel.is_all_expanded()
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED


def test_collapse_all(category_panel: CategoryPanel) -> None:
    """Test collapse_all collapses all nodes.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.1
    """
    # Initial state is collapsed
    assert category_panel.is_all_collapsed()
    
    # Expand first
    category_panel.expand_all()
    assert category_panel.is_all_expanded()
    
    # Collapse
    category_panel.collapse_all()
    
    # Verify all collapsed
    assert category_panel.is_all_collapsed()
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED


def test_toggle_button(category_panel: CategoryPanel) -> None:
    """Test toggle button switches states.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.1
    """
    # Initial state: collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    
    # Click button
    category_panel._expand_button.click()
    
    # Should be expanded
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED
    
    # Click again
    category_panel._expand_button.click()
    
    # Should be collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED


def test_search_triggers_expand(category_panel: CategoryPanel) -> None:
    """Test that search triggers expand all.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.1
    """
    # Collapse all
    category_panel.collapse_all()
    assert category_panel.is_all_collapsed()
    
    # Trigger search
    category_panel.set_search_text("B")
    
    # Should be expanded
    assert category_panel.is_all_expanded()


def test_initial_state(category_panel: CategoryPanel) -> None:
    """Test initial state is collapsed.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.1
    """
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    assert category_panel._expand_button.text() == "▶"


def test_clear_resets_state(category_panel: CategoryPanel) -> None:
    """Test that clear resets state to collapsed.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.1
    """
    # Expand
    category_panel.expand_all()
    assert category_panel.is_all_expanded()
    
    # Clear
    category_panel.clear()
    
    # Should reset to collapsed
    assert category_panel.is_all_collapsed()


# === Integration Tests (§11.2) ===

def test_expand_collapse_with_nested_categories(qapp: QApplication) -> None:
    """Test expand/collapse with deeply nested categories.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.2
    """
    panel = CategoryPanel()
    panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True, children=[
            CategoryDisplayNode(name="B", path="A/B", checked=True, children=[
                CategoryDisplayNode(name="C", path="A/B/C", checked=True, children=[
                    CategoryDisplayNode(name="D", path="A/B/C/D", checked=True)
                ])
            ])
        ])
    ])
    
    # Collapse all
    panel.collapse_all()
    
    # Verify root is collapsed
    assert panel.is_all_collapsed()
    
    # Expand all
    panel.expand_all()
    
    # Verify all expanded
    assert panel.is_all_expanded()


def test_expand_collapse_performance(qapp: QApplication) -> None:
    """Test expand/collapse performance with many nodes.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.2
    """
    panel = CategoryPanel()
    
    # Create 1000 categories
    categories = [
        CategoryDisplayNode(name=f"Cat{i}", path=f"Cat{i}", checked=True)
        for i in range(1000)
    ]
    panel.set_categories(categories)
    
    # Measure collapse
    start = time.time()
    panel.collapse_all()
    collapse_time = time.time() - start
    
    # Measure expand
    start = time.time()
    panel.expand_all()
    expand_time = time.time() - start
    
    # Should be fast
    assert collapse_time < 0.1  # 100ms
    assert expand_time < 0.1  # 100ms


# === Accessibility Tests (§11.3) ===

def test_accessible_name(category_panel: CategoryPanel) -> None:
    """Test button has accessible name.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.3
    """
    assert category_panel._expand_button.accessibleName() == "Expand/Collapse Categories"


def test_tool_tip_updates(category_panel: CategoryPanel) -> None:
    """Test tool tip updates with state.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.3
    """
    category_panel.expand_all()
    assert category_panel._expand_button.toolTip() == "Collapse all categories"
    
    category_panel.collapse_all()
    assert category_panel._expand_button.toolTip() == "Expand all categories"


def test_keyboard_activation(category_panel: CategoryPanel) -> None:
    """Test button can be activated with keyboard.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §11.3
    """
    # Focus button
    category_panel._expand_button.setFocus()
    
    # Initial state is collapsed
    assert category_panel._expand_state == ExpandCollapseState.COLLAPSED
    
    # Simulate click
    category_panel._expand_button.click()
    
    # Should be expanded after click
    assert category_panel._expand_state == ExpandCollapseState.EXPANDED


# === Additional Tests ===

def test_button_icon_state_expanded(category_panel: CategoryPanel) -> None:
    """Test button shows collapse icon when expanded.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §6.2
    """
    category_panel.expand_all()
    assert category_panel._expand_button.text() == "▼"


def test_button_icon_state_collapsed(category_panel: CategoryPanel) -> None:
    """Test button shows expand icon when collapsed.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §6.2
    """
    category_panel.collapse_all()
    assert category_panel._expand_button.text() == "▶"


def test_expand_all_idempotent(category_panel: CategoryPanel) -> None:
    """Test that expand_all is idempotent.
    
    Calling expand_all multiple times should not change state.
    """
    category_panel.expand_all()
    assert category_panel.is_all_expanded()
    
    # Call again
    category_panel.expand_all()
    assert category_panel.is_all_expanded()


def test_collapse_all_idempotent(category_panel: CategoryPanel) -> None:
    """Test that collapse_all is idempotent.
    
    Calling collapse_all multiple times should not change state.
    """
    category_panel.collapse_all()
    assert category_panel.is_all_collapsed()
    
    # Call again
    category_panel.collapse_all()
    assert category_panel.is_all_collapsed()


def test_set_categories_resets_to_collapsed(qapp: QApplication) -> None:
    """Test that set_categories resets state to collapsed.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §8.1
    """
    panel = CategoryPanel()
    panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=True)
    ])
    
    # Expand
    panel.expand_all()
    assert panel.is_all_expanded()
    
    # Set new categories
    panel.set_categories([
        CategoryDisplayNode(name="B", path="B", checked=True)
    ])
    
    # Should be collapsed
    assert panel.is_all_collapsed()


def test_clear_search_text_triggers_expand(category_panel: CategoryPanel) -> None:
    """Test that clearing search text triggers expand.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §8.2
    """
    # Set search text (triggers expand)
    category_panel.set_search_text("B")
    assert category_panel.is_all_expanded()
    
    # Collapse
    category_panel.collapse_all()
    assert category_panel.is_all_collapsed()
    
    # Clear search (should trigger expand)
    category_panel.set_search_text("")
    assert category_panel.is_all_expanded()


def test_expand_collapse_with_empty_panel(qapp: QApplication) -> None:
    """Test expand/collapse works with empty panel.
    
    Edge case: no categories loaded.
    """
    panel = CategoryPanel()
    
    # Should not raise
    panel.expand_all()
    assert panel.is_all_expanded()
    
    panel.collapse_all()
    assert panel.is_all_collapsed()


def test_multiple_toggle_cycles(category_panel: CategoryPanel) -> None:
    """Test multiple toggle cycles work correctly.
    
    Stress test for state machine.
    """
    for _ in range(10):
        # Initial state is collapsed, first click expands
        category_panel._expand_button.click()
        assert category_panel.is_all_expanded()
        
        # Second click collapses
        category_panel._expand_button.click()
        assert category_panel.is_all_collapsed()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])