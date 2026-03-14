"""Category panel with tabs, tree view, and search.

This module provides a panel with tabs (Categories/Filters/Highlights)
and a tree view with checkboxes for filtering log entries.

Architecture Note:
==================
This panel uses QTreeView + QStandardItemModel instead of QTreeWidget
because:

1. **Search/Filter Support**: The search functionality benefits from
   the model/view architecture, allowing for potential use of
   QSortFilterProxyModel in the future.

2. **Performance**: QTreeView performs better with large datasets
   and dynamic updates.

3. **Flexibility**: The model/view separation allows for custom
   model implementations if needed.

This panel does NOT inherit from TreePanel (QTreeWidget-based) because
the two architectures are fundamentally incompatible. See the
documentation in base_panel.py for guidance on when to use each approach.

Common patterns implemented here mirror TreePanel functionality:
- check_all(): Check/uncheck all items
- clear(): Clear all items
- get_checked_categories(): Get checked items
- _update_children_recursive(): Recursive checkbox updates
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTreeView,
    QLineEdit, QLabel, QAbstractItemView, QPushButton
)
from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem

from src.styles.stylesheet import get_tree_stylesheet, get_tab_stylesheet
from src.models import CategoryDisplayNode
from src.views.components.filters_tab import FiltersTabContent


class CategoryPanel(QWidget):
    """Panel for category filtering with tabs and tree view.
    
    Features:
    - Tabs: Categories (active), Filters, Highlights
    - Search input with magnifying glass icon
    - Tree view with checkboxes
    - Hierarchical structure with expand/collapse
    
    // Ref: docs/specs/features/saved-filters.md §4.3
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    // Thread: Main thread only (Qt UI component per docs/specs/global/threading.md §8.1)
    // Memory: FiltersTabContent owned by CategoryPanel (Qt parent-child)
    // Perf: O(1) for signal forwarding
    """
    
    # Signals
    category_toggled = Signal(str, bool)  # category_path, checked
    categories_batch_changed = Signal()  # Emitted when all categories changed at once
    search_changed = Signal(str)
    current_tab_changed = Signal(int)
    
    # New signals for saved filters
    # Ref: docs/specs/features/saved-filters.md §4.3
    saved_filter_enabled_changed = Signal(str, bool)  # filter_id, enabled
    saved_filter_deleted = Signal(str)                 # filter_id
    saved_filter_renamed = Signal(str, str)            # filter_id, new_name
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the category panel.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._model: Optional[QStandardItemModel] = None
        self._category_items: dict[str, QStandardItem] = {}
        self._all_categories: set[str] = set()
        self._batch_updating: bool = False  # Flag to prevent per-item signals during batch updates
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(get_tab_stylesheet())
        self._tab_widget.setDocumentMode(True)
        
        # Add tabs
        self._categories_tab = QWidget()
        self._filters_tab = QWidget()
        self._highlights_tab = QWidget()
        
        self._tab_widget.addTab(self._categories_tab, "Categories")
        self._tab_widget.addTab(self._filters_tab, "Filters")
        self._tab_widget.addTab(self._highlights_tab, "Highlights")
        
        # Set up categories tab content
        categories_layout = QVBoxLayout(self._categories_tab)
        categories_layout.setContentsMargins(4, 4, 4, 4)
        categories_layout.setSpacing(4)
        
        # Search input
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        
        search_icon = QLabel("🔍")
        search_icon.setFixedWidth(20)
        search_icon.setAlignment(Qt.AlignCenter)
        search_layout.addWidget(search_icon)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search categories...")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)
        
        categories_layout.addLayout(search_layout)
        
        # Tree view
        self._tree_view = QTreeView()
        self._tree_view.setStyleSheet(get_tree_stylesheet())
        self._tree_view.setHeaderHidden(True)
        self._tree_view.setRootIsDecorated(True)
        self._tree_view.setAnimated(True)
        self._tree_view.setUniformRowHeights(True)
        self._tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Disable horizontal scrollbar - tree content should fit within panel
        self._tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create model
        self._model = QStandardItemModel()
        self._tree_view.setModel(self._model)
        
        # Connect item changed signal for checkbox handling
        self._model.itemChanged.connect(self._on_item_changed)
        
        categories_layout.addWidget(self._tree_view)
        
        # Button bar for categories
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(4, 4, 4, 4)
        button_layout.setSpacing(4)
        
        # Check all button
        check_all_btn = QPushButton("Check All")
        check_all_btn.clicked.connect(lambda: self.check_all(True))
        button_layout.addWidget(check_all_btn)
        
        # Uncheck all button
        uncheck_all_btn = QPushButton("Uncheck All")
        uncheck_all_btn.clicked.connect(lambda: self.check_all(False))
        button_layout.addWidget(uncheck_all_btn)
        
        categories_layout.addWidget(button_bar)
        
        # Filters tab content
        # Ref: docs/specs/features/saved-filters.md §4.3
        self._filters_content = FiltersTabContent()
        filters_layout = QVBoxLayout(self._filters_tab)
        filters_layout.setContentsMargins(4, 4, 4, 4)
        filters_layout.addWidget(self._filters_content)
        
        # Connect signals from FiltersTabContent
        # Ref: docs/specs/features/saved-filters.md §4.3
        self._filters_content.filter_enabled_changed.connect(
            self.saved_filter_enabled_changed
        )
        self._filters_content.filter_deleted.connect(
            self.saved_filter_deleted
        )
        self._filters_content.filter_renamed.connect(
            self.saved_filter_renamed
        )
        
        highlights_layout = QVBoxLayout(self._highlights_tab)
        highlights_label = QLabel("Highlights\n(Coming soon)")
        highlights_label.setAlignment(Qt.AlignCenter)
        highlights_label.setStyleSheet("color: #999; font-style: italic;")
        highlights_layout.addWidget(highlights_label)
        
        # Connect tab change
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self._tab_widget)
    
    def _on_search_changed(self, text: str) -> None:
        """Handle search text change.
        
        Args:
            text: Search text.
        """
        self.search_changed.emit(text)
        self._filter_tree(text)
    
    def _filter_tree(self, text: str) -> None:
        """Filter tree items based on search text.
        
        Args:
            text: Search text to filter by.
        """
        if not text:
            # Show all items
            self._show_all_items(self._model.invisibleRootItem())
            self._tree_view.expandAll()
            return
        
        # Hide items that don't match
        text_lower = text.lower()
        self._filter_items(self._model.invisibleRootItem(), text_lower)
        self._tree_view.expandAll()
    
    def _filter_items(self, parent: QStandardItem, text: str) -> bool:
        """Recursively filter items.
        
        Args:
            parent: Parent item.
            text: Lowercase search text.
        
        Returns:
            True if any child matches.
        """
        any_visible = False
        
        # For the invisible root, use an invalid QModelIndex
        parent_index = parent.index() if parent != self._model.invisibleRootItem() else QModelIndex()
        
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item is None:
                continue
            
            # Check if this item matches
            item_text = item.text().lower()
            matches = text in item_text
            
            # Check children
            child_visible = self._filter_items(item, text)
            
            # Show if this item or any child matches
            visible = matches or child_visible
            self._tree_view.setRowHidden(row, parent_index, not visible)
            
            if visible:
                any_visible = True
        
        return any_visible
    
    def _show_all_items(self, parent: QStandardItem) -> None:
        """Show all items recursively.
        
        Args:
            parent: Parent item.
        """
        # For the invisible root, use an invalid QModelIndex
        parent_index = parent.index() if parent != self._model.invisibleRootItem() else QModelIndex()
        
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item is None:
                continue
            
            self._tree_view.setRowHidden(row, parent_index, False)
            self._show_all_items(item)
    
    def _on_item_changed(self, item: QStandardItem) -> None:
        """Handle item checkbox change.
        
        Args:
            item: The changed item.
        """
        # Skip signal during batch updates
        if self._batch_updating:
            return
        
        # Block signals to prevent recursion
        self._model.blockSignals(True)
        
        checked = item.checkState() == Qt.Checked
        
        # Update all children recursively
        self._update_children_recursive(item, checked)
        
        # Unblock signals
        self._model.blockSignals(False)
        
        # Force viewport repaint to show updated checkbox states
        # This is needed because setCheckState doesn't trigger immediate repaint
        self._tree_view.viewport().update()
        
        # Emit changed signal
        path = item.data(Qt.UserRole)
        if path:
            self.category_toggled.emit(path, checked)
    
    def _update_children_recursive(self, item: QStandardItem, checked: bool) -> None:
        """Update all children of an item to match the checked state.
        
        Args:
            item: Parent item.
            checked: Whether to check or uncheck.
        """
        check_state = Qt.Checked if checked else Qt.Unchecked
        
        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                child.setCheckState(check_state)
                self._update_children_recursive(child, checked)
    
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change.
        
        Args:
            index: New tab index.
        """
        self.current_tab_changed.emit(index)
    
    # === Public API - Category Management ===
    
    def set_categories(self, categories: list[CategoryDisplayNode]) -> None:
        """Populate tree with categories.
        
        Args:
            categories: List of category nodes.
        """
        # Block signals while building tree
        self._model.blockSignals(True)
        
        # Clear existing items
        self._model.clear()
        self._category_items.clear()
        self._all_categories.clear()
        
        # Build tree structure
        for category in categories:
            self._add_category_node(category, self._model.invisibleRootItem())
        
        # Unblock signals
        self._model.blockSignals(False)
        
        # Clear any active search filter to ensure all items are visible
        # Block signals to prevent triggering search_changed during clear
        self._search_input.blockSignals(True)
        self._search_input.clear()
        self._search_input.blockSignals(False)
        
        # Reset the model to ensure view is updated
        # This is necessary after clear() to properly refresh the view
        self._model.layoutChanged.emit()
        
        # Show all items (in case search filter was active)
        self._show_all_items(self._model.invisibleRootItem())
        
        # Expand all items
        self._tree_view.expandAll()
    
    def _add_category_node(self, node: CategoryDisplayNode, parent: QStandardItem) -> None:
        """Add a category node to the tree.
        
        Args:
            node: Category node to add.
            parent: Parent item.
        """
        # Create item
        item = QStandardItem(node.name)
        item.setCheckable(True)
        item.setCheckState(Qt.Checked if node.checked else Qt.Unchecked)
        item.setData(node.path, Qt.UserRole)
        
        # Store in dictionary
        self._category_items[node.path] = item
        self._all_categories.add(node.path)
        
        # Add to parent
        parent.appendRow(item)
        
        # Add children recursively
        for child in node.children:
            self._add_category_node(child, item)
    
    def get_checked_categories(self) -> set[str]:
        """Return set of checked category paths.
        
        Returns:
            Set of full category paths that are checked.
        """
        checked: set[str] = set()
        
        for path, item in self._category_items.items():
            if item.checkState() == Qt.Checked:
                checked.add(path)
        
        return checked
    
    def get_all_categories(self) -> set[str]:
        """Return set of all category paths.
        
        Returns:
            Set of all category paths.
        """
        return self._all_categories.copy()
    
    def get_category_states(self) -> dict[str, bool]:
        """Get all category checkbox states.
        
        Returns:
            Dictionary mapping category paths to their checked state.
        """
        states: dict[str, bool] = {}
        for path, item in self._category_items.items():
            states[path] = item.checkState() == Qt.Checked
        return states
    
    def set_category_states(self, states: dict[str, bool]) -> None:
        """Restore category checkbox states.
        
        Args:
            states: Dictionary mapping category paths to their checked state.
        """
        # Block signals while updating
        self._model.blockSignals(True)
        
        for path, checked in states.items():
            if path in self._category_items:
                check_state = Qt.Checked if checked else Qt.Unchecked
                self._category_items[path].setCheckState(check_state)
        
        # Unblock signals
        self._model.blockSignals(False)
    
    def check_all(self, checked: bool) -> None:
        """Check or uncheck all categories.
        
        Args:
            checked: True to check all, False to uncheck all.
        
        Performance Note:
            Uses batch update signal instead of per-category signals to avoid
            O(n) filter recompilations. This ensures UI remains responsive
            even with thousands of categories.
        """
        # Set batch updating flag to prevent per-item signals
        self._batch_updating = True
        
        check_state = Qt.Checked if checked else Qt.Unchecked
        
        for item in self._category_items.values():
            item.setCheckState(check_state)
        
        # Clear batch updating flag
        self._batch_updating = False
        
        # Force viewport repaint to show updated checkbox states
        # This is needed because setCheckState doesn't trigger immediate repaint
        self._tree_view.viewport().update()
        
        # Emit single batch signal instead of per-category signals
        # This allows controller to perform a single filter update
        self.categories_batch_changed.emit()
    
    def check_category(self, path: str, checked: bool) -> None:
        """Check or uncheck a specific category.
        
        Args:
            path: Category path.
            checked: True to check, False to uncheck.
        """
        if path in self._category_items:
            self._model.blockSignals(True)
            check_state = Qt.Checked if checked else Qt.Unchecked
            self._category_items[path].setCheckState(check_state)
            self._model.blockSignals(False)
    
    def clear(self) -> None:
        """Clear all categories."""
        self._model.blockSignals(True)
        self._model.clear()
        self._category_items.clear()
        self._all_categories.clear()
        self._model.blockSignals(False)
    
    # === Tab Management ===
    
    def set_current_tab(self, index: int) -> None:
        """Set the current tab by index.
        
        Args:
            index: Tab index (0=Categories, 1=Filters, 2=Highlights).
        """
        self._tab_widget.setCurrentIndex(index)
    
    def get_current_tab(self) -> int:
        """Get the current tab index.
        
        Returns:
            Current tab index.
        """
        return self._tab_widget.currentIndex()
    
    # === Search Management ===
    
    def set_search_text(self, text: str) -> None:
        """Set the search text.
        
        Args:
            text: Search text.
        """
        self._search_input.setText(text)
    
    def get_search_text(self) -> str:
        """Get the current search text.
        
        Returns:
            Current search text.
        """
        return self._search_input.text()
    
    def clear_search(self) -> None:
        """Clear the search input."""
        self._search_input.clear()
    
    # === Filters Tab Management ===
    
    # Ref: docs/specs/features/saved-filters.md §4.3
    def get_filters_content(self) -> FiltersTabContent:
        """Get the filters tab content widget.
        
        Returns:
            The FiltersTabContent widget.
        """
        return self._filters_content
    