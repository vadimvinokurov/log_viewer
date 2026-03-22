"""Base panel classes for UI components.

Architecture Decision: QTreeWidget vs QTreeView
===============================================

This module provides base classes for tree-based panels. There are two
fundamentally different Qt architectures for tree widgets:

1. QTreeWidget (TreePanel base class)
   - Convenience widget with built-in item management
   - Uses QTreeWidgetItem for direct item manipulation
   - Simpler API, easier for straightforward tree structures
   - Best for: Simple trees with direct item access

2. QTreeView + QStandardItemModel (Model/View architecture)
   - Separation of data (model) and presentation (view)
   - Uses QStandardItem for model-based items
   - Better performance for large datasets
   - Supports proxy models for sorting/filtering
   - Best for: Complex trees, search/filter features, like CategoryPanel

When to use each:
- Use TreePanel (QTreeWidget) when you need simple tree management
  with direct item access and don't need model features.
- Use QTreeView + QStandardItemModel when you need:
  - Search/filter functionality (via proxy models)
  - Better performance with large datasets
  - Model/view separation
  - Potential for custom model implementations

Key API Differences:
- Child access: QTreeWidgetItem.child(i) vs QStandardItem.child(row)
- Child count: QTreeWidgetItem.childCount() vs QStandardItem.rowCount()
- Check state: item.setCheckState(0, state) vs item.setCheckState(state)
- Signal source: tree.itemChanged vs model.itemChanged

See also:
- CategoryPanel: Example of QTreeView-based panel with tabs, search, and custom categories
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt


class TreePanel(QWidget):
    """Base class for panels with QTreeWidget and checkboxes.
    
    Provides common functionality for:
    - Recursive checkbox state updates
    - Check/uncheck all functionality
    - Signal blocking during batch updates
    
    This class is designed for QTreeWidget-based panels where:
    - Direct item manipulation is preferred
    - Simple tree structures are needed
    - Model/view separation is not required
    
    For panels requiring QTreeView + QStandardItemModel architecture,
    implement a standalone class following the patterns in CategoryPanel.
    
    Example:
        class CategoryPanel(TreePanel):
            def __init__(self, parent=None) -> None:
                super().__init__(parent)
                self._tree = QTreeWidget()
                # ... setup tree
    
    Attributes:
        _tree: The QTreeWidget instance (set by subclass).
        _items: Dictionary mapping paths to QTreeWidgetItems.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the tree panel.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._tree: Optional[QTreeWidget] = None
        self._items: dict[str, QTreeWidgetItem] = {}
    
    def _update_children_recursive(self, item: QTreeWidgetItem, checked: bool) -> None:
        """Update all children of an item to match the checked state.
        
        Args:
            item: Parent item.
            checked: Whether to check or uncheck.
        """
        check_state = Qt.Checked if checked else Qt.Unchecked
        
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, check_state)
            self._update_children_recursive(child, checked)
    
    def _check_all_recursive(self, item: QTreeWidgetItem, checked: bool) -> None:
        """Check or uncheck all items recursively.
        
        Args:
            item: Starting item (can be invisible root).
            checked: Whether to check or uncheck.
        """
        check_state = Qt.Checked if checked else Qt.Unchecked
        
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, check_state)
            self._check_all_recursive(child, checked)
    
    def check_all(self, checked: bool) -> None:
        """Check or uncheck all items in the tree.
        
        Args:
            checked: True to check all, False to uncheck all.
        """
        if self._tree is None:
            return
        
        self._tree.blockSignals(True)
        self._check_all_recursive(self._tree.invisibleRootItem(), checked)
        self._tree.blockSignals(False)
    
    def clear(self) -> None:
        """Clear all items from the tree."""
        if self._tree is None:
            return
        
        self._tree.blockSignals(True)
        self._tree.clear()
        self._items.clear()
        self._tree.blockSignals(False)
    
    def get_checked_items(self) -> set[str]:
        """Return set of checked item paths.
        
        Returns:
            Set of paths that are checked.
        """
        checked: set[str] = set()
        for path, item in self._items.items():
            if item.checkState(0) == Qt.Checked:
                checked.add(path)
        return checked
    
    def get_all_items(self) -> set[str]:
        """Return set of all item paths.
        
        Returns:
            Set of all paths.
        """
        return set(self._items.keys())