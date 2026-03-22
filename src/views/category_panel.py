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

from enum import Enum
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTreeView,
    QLineEdit, QLabel, QAbstractItemView, QPushButton
)
from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor

from src.styles.stylesheet import (
    get_tree_stylesheet,
    get_tab_stylesheet,
    get_expand_collapse_button_stylesheet,
)
from src.models import CategoryDisplayNode
from src.constants.dimensions import get_tree_indentation
from src.views.components.filters_tab import FiltersTabContent
from src.views.components.highlights_tab import HighlightsTabContent


class ExpandCollapseState(Enum):
    """Expand/collapse button state.
    
    The state represents the current expansion state of the tree,
    not the button action. When state is EXPANDED, the button shows
    a collapse icon (indicating "click to collapse").
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §4.1
    """
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"


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
    
    # Highlight signals (forwarded from HighlightsTabContent)
    # Ref: docs/specs/features/highlight-panel.md §7.2
    highlight_pattern_added = Signal(str, QColor, bool)      # text, color, is_regex
    highlight_pattern_removed = Signal(str)                   # text
    highlight_pattern_enabled_changed = Signal(str, bool)    # text, enabled
    highlight_pattern_edited = Signal(str, str, QColor, bool)  # old_text, new_text, color, is_regex
    
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
        
        # Expand/collapse state
        # Ref: docs/specs/features/category-tree-expand-collapse.md §4.3
        self._expand_state: ExpandCollapseState = ExpandCollapseState.COLLAPSED
        self._expand_button: QPushButton | None = None
        
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
        
        # Expand/collapse button in search bar
        # Ref: docs/specs/features/category-tree-expand-collapse.md §3.2
        self._setup_expand_button()
        search_layout.addWidget(self._expand_button)
        
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
        # Ref: docs/specs/features/category-panel-styles.md §5.4
        # Indentation controls branch indicator width + child offset
        # Ref: docs/specs/features/category-tree-click-target-spacing.md §5.4
        self._tree_view.setIndentation(get_tree_indentation())
        
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
        
        # Highlights tab content
        # Ref: docs/specs/features/highlight-panel.md §7.1
        self._highlights_content = HighlightsTabContent()
        highlights_layout = QVBoxLayout(self._highlights_tab)
        highlights_layout.setContentsMargins(4, 4, 4, 4)
        highlights_layout.addWidget(self._highlights_content)
        
        # Connect signals from HighlightsTabContent
        self._highlights_content.pattern_added.connect(self._on_highlight_pattern_added_forward)
        self._highlights_content.pattern_removed.connect(self.highlight_pattern_removed)
        self._highlights_content.pattern_enabled_changed.connect(self.highlight_pattern_enabled_changed)
        self._highlights_content.pattern_edited.connect(self.highlight_pattern_edited)
        
        # Connect tab change
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self._tab_widget)
    
    def _on_highlight_pattern_added_forward(self, text: str, color: QColor, is_regex: bool) -> None:
        """Forward highlight pattern added signal.
        
        Args:
            text: Pattern text.
            color: Highlight color.
            is_regex: Whether pattern is regex.
        """
        self.highlight_pattern_added.emit(text, color, is_regex)
    
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
            # Set state to EXPANDED
            # Ref: docs/specs/features/category-tree-expand-collapse.md §8.2
            self._expand_state = ExpandCollapseState.EXPANDED
            self._update_expand_button_icon()
            return
        
        # Hide items that don't match
        text_lower = text.lower()
        self._filter_items(self._model.invisibleRootItem(), text_lower)
        self._tree_view.expandAll()
        # Set state to EXPANDED
        # Ref: docs/specs/features/category-tree-expand-collapse.md §8.2
        self._expand_state = ExpandCollapseState.EXPANDED
        self._update_expand_button_icon()
    
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
        
        # Update parent check state (partially checked if some children checked)
        self._update_parent_check_state(item)
        
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
    
    def _update_parent_check_state(self, item: QStandardItem) -> None:
        """Update parent check state based on children states.
        
        When some children are checked and some are unchecked, the parent
        should show PartiallyChecked state.
        
        Args:
            item: The item whose parent needs to be updated.
        """
        parent = item.parent()
        if parent is None:
            return
        
        # Count checked/unchecked children
        checked_count = 0
        unchecked_count = 0
        total_children = parent.rowCount()
        
        for row in range(total_children):
            child = parent.child(row)
            if child:
                state = child.checkState()
                if state == Qt.Checked:
                    checked_count += 1
                elif state == Qt.Unchecked:
                    unchecked_count += 1
        
        # Determine parent state
        if checked_count == total_children:
            # All children checked
            parent.setCheckState(Qt.Checked)
        elif unchecked_count == total_children:
            # All children unchecked
            parent.setCheckState(Qt.Unchecked)
        else:
            # Some children checked, some unchecked
            parent.setCheckState(Qt.PartiallyChecked)
        
        # Recursively update ancestors
        self._update_parent_check_state(parent)
    
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
        
        # Update parent check states after building tree
        # This ensures parents show PartiallyChecked when some children are checked
        self._update_all_parent_states()
        
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
        
        # Collapse all items
        self._tree_view.collapseAll()
        
        # Set state to COLLAPSED
        # Ref: docs/specs/features/category-tree-expand-collapse.md §8.1
        self._expand_state = ExpandCollapseState.COLLAPSED
        self._update_expand_button_icon()
    
    def _update_all_parent_states(self) -> None:
        """Update all parent check states based on their children.
        
        This should be called after building the tree to ensure parents
        show PartiallyChecked when some children are checked.
        """
        root = self._model.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            if item:
                self._update_parent_states_recursive(item)
    
    def _update_parent_states_recursive(self, item: QStandardItem) -> None:
        """Recursively update parent states for all items with children.
        
        Args:
            item: The item to process.
        """
        # First, process children recursively
        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                self._update_parent_states_recursive(child)
        
        # Then update this item's state based on children
        if item.rowCount() > 0:
            checked_count = 0
            unchecked_count = 0
            total_children = item.rowCount()
            
            for row in range(total_children):
                child = item.child(row)
                if child:
                    state = child.checkState()
                    if state == Qt.Checked:
                        checked_count += 1
                    elif state == Qt.Unchecked:
                        unchecked_count += 1
            
            # Set parent state based on children
            if checked_count == total_children:
                item.setCheckState(Qt.Checked)
            elif unchecked_count == total_children:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.PartiallyChecked)
    
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
        
        # Update all parent states after restoring
        self._update_all_parent_states()
        
        # Unblock signals
        self._model.blockSignals(False)
        
        # Force viewport repaint
        self._tree_view.viewport().update()
    
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
        
        # Update all items (including parents)
        # We need to update from root items down to ensure proper state propagation
        root = self._model.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            if item:
                self._set_check_state_recursive(item, check_state)
        
        # Clear batch updating flag
        self._batch_updating = False
        
        # Force viewport repaint to show updated checkbox states
        # This is needed because setCheckState doesn't trigger immediate repaint
        self._tree_view.viewport().update()
        
        # Emit single batch signal instead of per-category signals
        # This allows controller to perform a single filter update
        self.categories_batch_changed.emit()
    
    def expand_all(self) -> None:
        """Expand all category nodes in the tree.
        
        Sets all nodes to expanded state and updates button icon.
        Emits no signals - this is a view-only operation.
        
        Performance:
            O(n) where n = total number of nodes
            Target: <100ms for 10,000 nodes
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §7.1
        """
        # Update state first
        self._expand_state = ExpandCollapseState.EXPANDED
        
        # Use Qt's built-in expandAll for efficiency
        # Ref: QTreeView::expandAll() - O(n) traversal
        self._tree_view.expandAll()
        
        # Update button icon
        self._update_expand_button_icon()
    
    def collapse_all(self) -> None:
        """Collapse all category nodes in the tree.
        
        Sets all nodes to collapsed state and updates button icon.
        Emits no signals - this is a view-only operation.
        
        Performance:
            O(n) where n = total number of nodes
            Target: <100ms for 10,000 nodes
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §7.2
        """
        # Update state first
        self._expand_state = ExpandCollapseState.COLLAPSED
        
        # Use Qt's built-in collapseAll for efficiency
        # Ref: QTreeView::collapseAll() - O(n) traversal
        self._tree_view.collapseAll()
        
        # Update button icon
        self._update_expand_button_icon()
    
    def is_all_expanded(self) -> bool:
        """Check if all nodes are expanded.
        
        Returns:
            True if all nodes are expanded, False otherwise.
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §5.1
        """
        return self._expand_state == ExpandCollapseState.EXPANDED
    
    def is_all_collapsed(self) -> bool:
        """Check if all nodes are collapsed.
        
        Returns:
            True if all nodes are collapsed, False otherwise.
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §5.1
        """
        return self._expand_state == ExpandCollapseState.COLLAPSED
    
    def _update_expand_button_icon(self) -> None:
        """Update button icon based on current state.
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §7.4
        """
        if self._expand_button is None:
            return
        
        if self._expand_state == ExpandCollapseState.EXPANDED:
            # Show collapse icon (▼) - indicates "click to collapse"
            self._expand_button.setText("▼")
            self._expand_button.setToolTip("Collapse all categories")
        else:
            # Show expand icon (▶) - indicates "click to expand"
            self._expand_button.setText("▶")
            self._expand_button.setToolTip("Expand all categories")
    
    def _setup_expand_button(self) -> None:
        """Set up the expand/collapse button.
        
        Creates the button with proper styling, accessibility, and signal connections.
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §9.2
        """
        self._expand_button = QPushButton()
        self._expand_button.setObjectName("expandCollapseButton")
        self._expand_button.setFixedWidth(32)
        self._expand_button.setAccessibleName("Expand/Collapse Categories")
        self._expand_button.clicked.connect(self._on_expand_collapse_clicked)
        
        # Apply stylesheet
        # Ref: docs/specs/features/category-tree-expand-collapse.md §6.3
        self._expand_button.setStyleSheet(get_expand_collapse_button_stylesheet())
        
        # Set initial state
        self._expand_state = ExpandCollapseState.COLLAPSED
        self._update_expand_button_icon()
    
    def _on_expand_collapse_clicked(self) -> None:
        """Handle expand/collapse button click.
        
        Toggles between expanded and collapsed states.
        
        // Ref: docs/specs/features/category-tree-expand-collapse.md §7.3
        """
        if self._expand_state == ExpandCollapseState.EXPANDED:
            self.collapse_all()
        else:
            self.expand_all()
    
    def _set_check_state_recursive(self, item: QStandardItem, check_state: Qt.CheckState) -> None:
        """Set check state for an item and all its children recursively.
        
        Args:
            item: The item to update.
            check_state: The check state to set.
        """
        item.setCheckState(check_state)
        
        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                self._set_check_state_recursive(child, check_state)
    
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
        
        # Reset state to COLLAPSED
        # Ref: docs/specs/features/category-tree-expand-collapse.md §8.3
        self._expand_state = ExpandCollapseState.COLLAPSED
        self._update_expand_button_icon()
    
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
    
    # === Highlights Tab Management ===
    
    # Ref: docs/specs/features/highlight-panel.md §7.1
    def get_highlights_content(self) -> HighlightsTabContent:
        """Get the highlights tab content widget.
        
        Returns:
            The HighlightsTabContent widget.
        """
        return self._highlights_content
    