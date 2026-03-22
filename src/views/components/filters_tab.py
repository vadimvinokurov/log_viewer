"""Filters tab content for the CategoryPanel.

// Ref: docs/specs/features/saved-filters.md §4.2
// Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
// Thread: Main thread only (Qt UI component per docs/specs/global/threading.md §8.1)
// Memory: Qt parent-child ownership (parent: CategoryPanel)
// Perf: O(n) to populate list, O(1) for single add/remove
"""
from __future__ import annotations

from beartype import beartype
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
)

from src.models.saved_filter import SavedFilter
from src.styles.stylesheet import get_panel_list_stylesheet


class FiltersTabContent(QWidget):
    """Content for the Filters tab in CategoryPanel.
    
    Displays a list of saved filters with checkboxes for enable/disable,
    and buttons for delete and rename operations.
    
    // Ref: docs/specs/features/saved-filters.md §4.2
    """
    
    # Signals
    filter_enabled_changed = Signal(str, bool)  # filter_id, enabled
    filter_deleted = Signal(str)                 # filter_id
    filter_renamed = Signal(str, str)            # filter_id, new_name
    
    @beartype
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the filters tab content.
        
        Args:
            parent: Parent widget (CategoryPanel).
        """
        super().__init__(parent)
        self._filter_items: dict[str, QListWidgetItem] = {}
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Filter list - unified styling with tree view
        # Ref: docs/specs/features/panel-content-unified-styles.md §3.4
        self._filter_list = QListWidget()
        self._filter_list.setStyleSheet(get_panel_list_stylesheet())
        self._filter_list.itemChanged.connect(self._on_item_changed)
        self._filter_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._filter_list)
        
        # Button bar
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        self._delete_button = QPushButton("Delete")
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self._delete_button)
        
        self._rename_button = QPushButton("Rename")
        self._rename_button.setEnabled(False)
        self._rename_button.clicked.connect(self._on_rename_clicked)
        button_layout.addWidget(self._rename_button)
        
        layout.addLayout(button_layout)
    
    @beartype
    def set_filters(self, filters: list[SavedFilter]) -> None:
        """Populate filter list.
        
        Args:
            filters: List of saved filters to display.
        """
        # Block signals during batch update
        self._filter_list.blockSignals(True)
        
        # Clear existing items
        self._filter_list.clear()
        self._filter_items.clear()
        
        # Unblock signals before adding items (to connect itemChanged)
        self._filter_list.blockSignals(False)
        
        # Add each filter
        for filter in filters:
            self.add_filter(filter)
    
    @beartype
    def add_filter(self, filter: SavedFilter) -> None:
        """Add single filter to list.
        
        Args:
            filter: The filter to add.
        """
        # Block signals while setting up the item to prevent
        # spurious itemChanged signals during initialization
        self._filter_list.blockSignals(True)
        
        # Create list item
        item = QListWidgetItem(self._filter_list)
        
        # Store filter_id in item data
        item.setData(Qt.ItemDataRole.UserRole, filter.id)
        
        # Set checkbox state
        item.setCheckState(Qt.Checked if filter.enabled else Qt.Unchecked)
        
        # Set display text (name on first line)
        item.setText(filter.name)
        
        # Unblock signals after setup
        self._filter_list.blockSignals(False)
        
        # Store in dictionary for O(1) lookup
        self._filter_items[filter.id] = item
        
        # Set tooltip with full details
        mode_text = f"[{filter.filter_mode.value}]"
        item.setToolTip(f'{filter.name}\n"{filter.filter_text}" {mode_text}')
    
    @beartype
    def remove_filter(self, filter_id: str) -> None:
        """Remove filter from list.
        
        Args:
            filter_id: The ID of the filter to remove.
        """
        if filter_id not in self._filter_items:
            return
        
        item = self._filter_items[filter_id]
        
        # Remove from list
        row = self._filter_list.row(item)
        self._filter_list.takeItem(row)
        
        # Remove from dictionary
        del self._filter_items[filter_id]
    
    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Handle item checkbox change.
        
        Args:
            item: The changed item.
        """
        filter_id = item.data(Qt.ItemDataRole.UserRole)
        if not filter_id:
            return
        
        enabled = item.checkState() == Qt.Checked
        self.filter_enabled_changed.emit(filter_id, enabled)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in the list."""
        selected = self._filter_list.currentItem() is not None
        self._delete_button.setEnabled(selected)
        self._rename_button.setEnabled(selected)
    
    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        item = self._filter_list.currentItem()
        if not item:
            return
        
        filter_id = item.data(Qt.ItemDataRole.UserRole)
        if filter_id:
            self.filter_deleted.emit(filter_id)
    
    def _on_rename_clicked(self) -> None:
        """Handle rename button click."""
        item = self._filter_list.currentItem()
        if not item:
            return
        
        filter_id = item.data(Qt.ItemDataRole.UserRole)
        if filter_id:
            # Start inline edit
            self._filter_list.editItem(item)
    
    def _on_item_renamed(self, item: QListWidgetItem) -> None:
        """Handle item rename completion.
        
        This is called when the user finishes editing an item name.
        
        Args:
            item: The renamed item.
        """
        filter_id = item.data(Qt.ItemDataRole.UserRole)
        if not filter_id:
            return
        
        new_name = item.text().strip()
        if new_name:
            self.filter_renamed.emit(filter_id, new_name)