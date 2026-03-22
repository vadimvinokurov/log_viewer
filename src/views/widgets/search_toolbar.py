"""Search toolbar with input field and filter icons.

This module provides a search input widget with filter action buttons,
including filter mode selection.

Ref: docs/specs/global/color-palette.md §10.2
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, Signal

from src.views.components.search_input import SearchInput
from src.constants.colors import UIColors


# Stylesheet for icon buttons (open file, refresh, settings)
# Ref: docs/specs/global/color-palette.md §10.2.1
_ICON_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {UIColors.BACKGROUND_SECONDARY};
        border: 1px solid {UIColors.BORDER_DEFAULT};
        border-radius: 3px;
        padding: 0px;
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
    }}
    QPushButton:hover {{
        background-color: {UIColors.BACKGROUND_HOVER};
        border: 1px solid {UIColors.BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {UIColors.BACKGROUND_ACTIVE};
    }}
"""


class SearchToolbar(QWidget):
    """Toolbar with search input and filter buttons.
    
    Provides:
    - Open file button (folder icon)
    - Refresh button (refresh icon)
    - Search input (stretches to fill available space)
    - Filter mode dropdown (Plain/Regex/Simple)
    - Save filter button (floppy disk icon)
    
    Filter is applied on Enter. Empty text clears the filter.
    
    // Ref: docs/specs/features/saved-filters.md §4.1
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    """
    
    # Signals
    filter_applied = Signal(str, str)  # search_text, mode - emitted when Enter is pressed
    filter_cleared = Signal()  # emitted when Enter is pressed on empty text
    open_file_clicked = Signal()  # open file button clicked
    refresh_clicked = Signal()  # refresh button clicked
    save_filter_requested = Signal(str, str)  # filter_text, mode - emitted when save button clicked
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the search toolbar.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Open file button (folder icon)
        self._open_file_button = QPushButton("📁")
        self._open_file_button.setFixedSize(24, 24)
        self._open_file_button.setToolTip("Open file (Ctrl+O)")
        self._open_file_button.setCursor(Qt.PointingHandCursor)
        self._open_file_button.setStyleSheet(_ICON_BUTTON_STYLE)
        layout.addWidget(self._open_file_button)
        
        # Refresh button (refresh icon)
        self._refresh_button = QPushButton("🔄")
        self._refresh_button.setFixedSize(24, 24)
        self._refresh_button.setToolTip("Refresh file (F5)")
        self._refresh_button.setCursor(Qt.PointingHandCursor)
        self._refresh_button.setStyleSheet(_ICON_BUTTON_STYLE)
        layout.addWidget(self._refresh_button)
        
        # Separator
        separator = QLabel("|")
        separator.setFixedWidth(10)
        separator.setAlignment(Qt.AlignCenter)
        layout.addWidget(separator)
        
        # Search input - stretches to fill available space
        self._search_input = SearchInput()
        self._search_input.setPlaceholderText("Enter filter text (Enter to apply, empty to clear)...")
        layout.addWidget(self._search_input, 1)  # stretch factor 1
        
        # Filter mode dropdown
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Plain", "plain")
        self._mode_combo.addItem("Regex", "regex")
        self._mode_combo.addItem("Simple", "simple")
        self._mode_combo.setToolTip(
            "Plain: Case-insensitive substring search\n"
            "Regex: Python regular expression\n"
            "Simple: Custom query language (and, or, not)"
        )
        self._mode_combo.setFixedWidth(80)
        layout.addWidget(self._mode_combo)
        
        # Save filter button (floppy disk icon)
        # Ref: docs/specs/features/saved-filters.md §4.1
        self._save_button = QPushButton("💾")
        self._save_button.setFixedSize(24, 24)
        self._save_button.setToolTip("Save current filter")
        self._save_button.setCursor(Qt.PointingHandCursor)
        self._save_button.setStyleSheet(_ICON_BUTTON_STYLE)
        self._save_button.setEnabled(False)  # Initially disabled (enabled when text present)
        layout.addWidget(self._save_button)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._open_file_button.clicked.connect(self.open_file_clicked)
        self._refresh_button.clicked.connect(self.refresh_clicked)
        self._search_input.returnPressed.connect(self._on_return_pressed)
        self._save_button.clicked.connect(self._on_save_clicked)
        self._search_input.textChanged.connect(self._on_text_changed)
    
    def _on_return_pressed(self) -> None:
        """Handle Enter key press in search input.
        
        If text is empty, clears the filter.
        If text is not empty, applies the filter.
        """
        text = self._search_input.text().strip()
        if text:
            mode = self._mode_combo.currentData()
            self.filter_applied.emit(text, mode)
        else:
            self.filter_cleared.emit()
    
    def _on_save_clicked(self) -> None:
        """Handle save button click.
        
        Emits save_filter_requested signal with current filter text and mode.
        
        // Ref: docs/specs/features/saved-filters.md §4.1
        """
        text = self._search_input.text().strip()
        mode = self._mode_combo.currentData()
        if text:
            self.save_filter_requested.emit(text, mode)
    
    def _on_text_changed(self, text: str) -> None:
        """Enable/disable save button based on text.
        
        Args:
            text: Current text in search input.
        
        // Ref: docs/specs/features/saved-filters.md §4.1
        """
        self._save_button.setEnabled(bool(text.strip()))
    
    def set_search_text(self, text: str) -> None:
        """Set the search text.
        
        Args:
            text: Text to set.
        """
        self._search_input.setText(text)
    
    def get_search_text(self) -> str:
        """Get the current search text.
        
        Returns:
            Current search text.
        """
        return self._search_input.text()
    
    def get_filter_mode(self) -> str:
        """Get the current filter mode.
        
        Returns:
            Current filter mode ('plain', 'regex', or 'simple').
        """
        return self._mode_combo.currentData()
    
    def set_filter_mode(self, mode: str) -> None:
        """Set the filter mode.
        
        Args:
            mode: Filter mode ('plain', 'regex', or 'simple').
        """
        index = self._mode_combo.findData(mode)
        if index >= 0:
            self._mode_combo.setCurrentIndex(index)
    
    def clear_search(self) -> None:
        """Clear the search input."""
        self._search_input.clear()
    
    def set_focus(self) -> None:
        """Set focus to the search input."""
        self._search_input.setFocus()
    
    def select_all(self) -> None:
        """Select all text in the search input."""
        self._search_input.selectAll()


class SearchToolbarWithStats(QWidget):
    """Search toolbar wrapper for backward compatibility.
    
    Note: Statistics bar has been moved to MainStatusBar.
    This class now wraps SearchToolbar for backward compatibility.
    """
    
    # Signals (forwarded from search toolbar)
    filter_applied = Signal(str, str)  # search_text, mode
    filter_cleared = Signal()
    open_file_clicked = Signal()
    refresh_clicked = Signal()
    save_filter_requested = Signal(str, str)  # filter_text, mode
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the toolbar wrapper.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Just the search toolbar
        self._search_toolbar = SearchToolbar()
        layout.addWidget(self._search_toolbar)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._search_toolbar.filter_applied.connect(self.filter_applied)
        self._search_toolbar.filter_cleared.connect(self.filter_cleared)
        self._search_toolbar.open_file_clicked.connect(self.open_file_clicked)
        self._search_toolbar.refresh_clicked.connect(self.refresh_clicked)
        self._search_toolbar.save_filter_requested.connect(self.save_filter_requested)
    
    # Forward methods to search toolbar
    def set_search_text(self, text: str) -> None:
        """Set the search text."""
        self._search_toolbar.set_search_text(text)
    
    def get_search_text(self) -> str:
        """Get the current search text."""
        return self._search_toolbar.get_search_text()
    
    def get_filter_mode(self) -> str:
        """Get the current filter mode.
        
        Returns:
            Current filter mode ('plain', 'regex', or 'simple').
        """
        return self._search_toolbar.get_filter_mode()
    
    def set_filter_mode(self, mode: str) -> None:
        """Set the filter mode.
        
        Args:
            mode: Filter mode ('plain', 'regex', or 'simple').
        """
        self._search_toolbar.set_filter_mode(mode)
    
    def clear_search(self) -> None:
        """Clear the search input."""
        self._search_toolbar.clear_search()
    
    def set_focus(self) -> None:
        """Set focus to the search input."""
        self._search_toolbar.set_focus()