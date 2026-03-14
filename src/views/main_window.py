"""Main application window with new UI design.

This module provides the redesigned main window with:
- Search toolbar with statistics bar at the top
- Horizontal splitter (75% log table / 25% CategoryPanel)
"""
from __future__ import annotations

import os
from typing import Optional
from beartype import beartype

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShortcut, QKeySequence

from src.styles.stylesheet import get_application_stylesheet
from src.views.log_table_view import LogTableView, LogEntry
from src.views.category_panel import CategoryPanel
from src.views.widgets.search_toolbar import SearchToolbarWithStats
from src.views.widgets.main_status_bar import MainStatusBar
from src.views.widgets.collapsible_panel import CollapsiblePanel
from src.views.find_dialog import FindDialog
from src.views.widgets.error_dialog import ErrorDialog
from src.constants.app_constants import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, APPLICATION_NAME, STATUS_MESSAGE_TIMEOUT
)
from src.constants.dimensions import SPLITTER_LEFT_RATIO, SPLITTER_RIGHT_RATIO


# Keyboard shortcuts
SHORTCUT_OPEN_FILE = "Ctrl+O"
SHORTCUT_RELOAD = "F5"
SHORTCUT_CLOSE = "Ctrl+W"
SHORTCUT_FIND = "Ctrl+F"
SHORTCUT_EXIT = "Ctrl+Q"

# About dialog text
ABOUT_TITLE = f"About {APPLICATION_NAME}"
ABOUT_TEXT = f"""{APPLICATION_NAME} v2.0

A fast, feature-rich log file viewer.

Features:
- Modern flat UI design
- File tabs for multiple files
- System filtering with tree view
- Colored statistics counters
- Advanced search and highlighting
"""


class MainWindow(QMainWindow):
    """Main application window with redesigned UI."""

    # Signals
    file_opened = Signal(str)  # filepath
    file_closed = Signal()  # file closed
    refresh_requested = Signal()
    auto_reload_toggled = Signal(bool)  # enabled
    find_requested = Signal(str, bool)  # text, case_sensitive
    category_toggled = Signal(str, bool)  # category_path, checked
    categories_batch_changed = Signal()  # all categories changed at once
    filter_applied = Signal(str, str)  # search_text, mode
    filter_cleared = Signal()
    counter_toggled = Signal(str, bool)  # counter_type, visible
    open_file_requested = Signal()  # open file button clicked

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self._setup_window()
        self._create_components()
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()

    def _setup_window(self) -> None:
        """Set up window properties."""
        self.setWindowTitle(APPLICATION_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setStyleSheet(get_application_stylesheet())

    def _create_components(self) -> None:
        """Create UI components."""
        self._search_toolbar: SearchToolbarWithStats = SearchToolbarWithStats()
        self._collapsible_panel: CollapsiblePanel = CollapsiblePanel()
        self._log_table: LogTableView = LogTableView()
        self._category_panel: CategoryPanel = CategoryPanel()
        self._status_bar: MainStatusBar = MainStatusBar()
        self._find_dialog: Optional[FindDialog] = None
        self._current_file: Optional[str] = None
        self._pending_filepath: Optional[str] = None
        self._auto_reload_enabled: bool = True

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        # Central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add toolbar
        self.addToolBar(Qt.TopToolBarArea, self._create_toolbar())

        # Add splitter with log table and systems panel
        layout.addWidget(self._create_splitter())

        # Add status bar
        self.setStatusBar(self._status_bar)

    def _create_toolbar(self) -> QToolBar:
        """Create and configure the main toolbar.
        
        Returns:
            Configured toolbar.
        """
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        # Wrap search toolbar in collapsible panel
        self._collapsible_panel.setContent(self._search_toolbar)
        toolbar.addWidget(self._collapsible_panel)
        
        return toolbar

    def _create_splitter(self) -> QSplitter:
        """Create the main splitter with log table and category panel.
        
        Returns:
            Configured splitter.
        """
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._log_table)
        splitter.addWidget(self._category_panel)
        
        # Set initial sizes based on ratios
        left_size = int(self.width() * SPLITTER_LEFT_RATIO / 100)
        right_size = int(self.width() * SPLITTER_RIGHT_RATIO / 100)
        splitter.setSizes([left_size, right_size])
        
        return splitter

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        shortcuts = [
            (QKeySequence(SHORTCUT_OPEN_FILE), self._on_open_file_requested),
            (QKeySequence(SHORTCUT_RELOAD), self._on_reload),
            (QKeySequence(SHORTCUT_CLOSE), self._on_close),
            (QKeySequence(SHORTCUT_FIND), self._on_find),
            (QKeySequence(SHORTCUT_EXIT), self.close),
        ]
        
        for key_sequence, handler in shortcuts:
            shortcut = QShortcut(key_sequence, self)
            shortcut.activated.connect(handler)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Search toolbar signals
        self._search_toolbar.filter_applied.connect(self.filter_applied)
        self._search_toolbar.filter_cleared.connect(self.filter_cleared)
        self._search_toolbar.open_file_clicked.connect(self._on_open_file_requested)
        self._search_toolbar.refresh_clicked.connect(self._on_reload)

        # Status bar signals (statistics counters)
        self._status_bar.counter_clicked.connect(self.counter_toggled)

        # Category panel signals
        self._category_panel.category_toggled.connect(self.category_toggled)
        self._category_panel.categories_batch_changed.connect(self.categories_batch_changed)

        # Log table signals
        self._log_table.find_requested.connect(self._on_find)

    # === Event Handlers ===

    def _on_reload(self) -> None:
        """Handle reload action."""
        self.refresh_requested.emit()

    def _on_close(self) -> None:
        """Handle close action - clear current file."""
        self.file_closed.emit()

    def _on_open_file_requested(self) -> None:
        """Handle open file button click or Ctrl+O shortcut."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log File",
            "",
            "Log Files (*.log *.txt);;All Files (*)"
        )
        
        if not filepath:
            return
        
        if self._current_file is None:
            self._open_file(filepath)
        else:
            self._handle_file_already_open(filepath)

    def _open_file(self, filepath: str) -> None:
        """Open a file.
        
        Args:
            filepath: Path to the file to open.
        """
        self._current_file = filepath
        self.file_opened.emit(filepath)
        self.setWindowTitle(f"{APPLICATION_NAME} - {filepath}")
        self._status_bar.set_file(os.path.basename(filepath))

    def _handle_file_already_open(self, filepath: str) -> None:
        """Handle case when a file is already open.
        
        Args:
            filepath: Path to the new file to open.
        """
        new_filename = os.path.basename(filepath)
        current_filename = os.path.basename(self._current_file or "")
        
        reply = QMessageBox.question(
            self,
            "Open File",
            f"Open '{new_filename}'?\n\n"
            f"Current file: {current_filename}\n\n"
            "Yes = Open in new window\n"
            "No = Close current and open new file\n"
            "Cancel = Keep current file",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self._pending_filepath = filepath
            self.open_file_requested.emit()
        elif reply == QMessageBox.No:
            self._current_file = filepath
            self.file_closed.emit()
            self.file_opened.emit(filepath)
            self.setWindowTitle(f"{APPLICATION_NAME} - {filepath}")
            self._status_bar.set_file(os.path.basename(filepath))

    def _on_auto_reload_toggled(self, checked: bool) -> None:
        """Handle auto-reload toggle.

        Args:
            checked: Whether auto-reload is enabled.
        """
        self._auto_reload_enabled = checked
        self.auto_reload_toggled.emit(checked)

    def _on_find(self) -> None:
        """Handle find action."""
        if self._find_dialog is None:
            self._find_dialog = FindDialog(self)
            self._find_dialog.find_requested.connect(self._on_find_requested)
            self._find_dialog.find_next.connect(self._on_find_next)
            self._find_dialog.find_previous.connect(self._on_find_previous)
            self._find_dialog.highlight_all.connect(self._on_highlight_all)
            self._find_dialog.clear_highlights.connect(self._on_clear_highlights)

        self._find_dialog.show()
        self._find_dialog.raise_()
        self._find_dialog.activateWindow()

    def _on_find_requested(self, text: str, case_sensitive: bool) -> None:
        """Handle find requested signal.

        Args:
            text: Text to find.
            case_sensitive: Whether search is case-sensitive.
        """
        self.find_requested.emit(text, case_sensitive)

    def _on_find_next(self) -> None:
        """Handle find next."""
        self._log_table.find_next()
        self._update_find_match_count()

    def _on_find_previous(self) -> None:
        """Handle find previous."""
        self._log_table.find_previous()
        self._update_find_match_count()

    def _on_highlight_all(self, text: str, case_sensitive: bool) -> None:
        """Handle highlight all.

        Args:
            text: Text to highlight.
            case_sensitive: Whether search is case-sensitive.
        """
        count = self._log_table.find_text(text, case_sensitive)
        if self._find_dialog:
            self._find_dialog.update_match_count(0 if count == 0 else 1, count)

    def _on_clear_highlights(self) -> None:
        """Handle clear highlights."""
        self._log_table.clear_find_highlights()

    def _update_find_match_count(self) -> None:
        """Update find dialog match count."""
        if self._find_dialog:
            current = self._log_table.get_current_find_match() + 1
            total = self._log_table.get_find_match_count()
            self._find_dialog.update_match_count(current, total)

    def _on_about(self) -> None:
        """Handle about action."""
        QMessageBox.about(self, ABOUT_TITLE, ABOUT_TEXT)

    # === Public API ===

    def open_file_dialog(self) -> None:
        """Show file open dialog."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log File",
            "",
            "Log Files (*.log *.txt);;All Files (*)"
        )

        if filepath:
            self._open_file(filepath)

    @beartype
    def set_current_file(self, filepath: str | None) -> None:
        """Set the current file path.
        
        Args:
            filepath: Path to the current file, or None if no file is open.
        """
        self._current_file = filepath
        if filepath:
            self.setWindowTitle(f"{APPLICATION_NAME} - {filepath}")
            self._status_bar.set_file(os.path.basename(filepath))
        else:
            self.setWindowTitle(APPLICATION_NAME)
            self._status_bar.set_file(None)

    def get_current_file(self) -> str | None:
        """Get the current file path.
        
        Returns:
            Path to the current file, or None if no file is open.
        """
        return self._current_file

    def get_pending_filepath(self) -> str | None:
        """Get the pending filepath for opening in a new window.
        
        Returns:
            Path to the pending file, or None if no file is pending.
        """
        return self._pending_filepath

    def clear_pending_filepath(self) -> None:
        """Clear the pending filepath."""
        self._pending_filepath = None

    def get_log_table(self) -> LogTableView:
        """Return the log table view."""
        return self._log_table

    def get_category_panel(self) -> CategoryPanel:
        """Return the category panel."""
        return self._category_panel

    def get_search_toolbar(self) -> SearchToolbarWithStats:
        """Return the search toolbar."""
        return self._search_toolbar
    
    def get_collapsible_panel(self) -> CollapsiblePanel:
        """Return the collapsible panel containing the search toolbar.
        
        Returns:
            CollapsiblePanel widget.
        """
        return self._collapsible_panel
    
    def is_search_panel_collapsed(self) -> bool:
        """Check if the search panel is collapsed.
        
        Returns:
            True if collapsed, False if expanded.
        """
        return self._collapsible_panel.isCollapsed()
    
    @beartype
    def set_search_panel_collapsed(self, collapsed: bool) -> None:
        """Set the collapsed state of the search panel.
        
        Args:
            collapsed: True to collapse, False to expand.
        """
        self._collapsible_panel.setCollapsed(collapsed)
    
    def toggle_search_panel(self) -> None:
        """Toggle the search panel visibility."""
        self._collapsible_panel.toggle()

    @beartype
    def show_error(self, title: str, message: str) -> None:
        """Show an error message dialog."""
        QMessageBox.critical(self, title, message)

    @beartype
    def show_error_with_details(self, title: str, message: str, details: str = "") -> None:
        """Show an error message dialog with details.

        Args:
            title: Dialog title.
            message: Error message.
            details: Technical details/stack trace.
        """
        ErrorDialog.show_error(title, message, details, self)

    @beartype
    def show_info(self, title: str, message: str) -> None:
        """Show an information message dialog."""
        QMessageBox.information(self, title, message)

    @beartype
    def show_status(self, message: str, timeout: int = STATUS_MESSAGE_TIMEOUT) -> None:
        """Show a status message.

        Args:
            message: Status message to display.
            timeout: Timeout in milliseconds (default 3000).
        """
        self._status_bar.show_status(message, timeout)

    def clear_status(self) -> None:
        """Clear the status message."""
        self._status_bar.clear_status()

    def is_auto_reload_enabled(self) -> bool:
        """Check if auto-reload is enabled.

        Returns:
            True if auto-reload is enabled.
        """
        return self._auto_reload_enabled

    @beartype
    def set_auto_reload_enabled(self, enabled: bool) -> None:
        """Set auto-reload enabled state.

        Args:
            enabled: Whether to enable auto-reload.
        """
        self._auto_reload_enabled = enabled

    @beartype
    def set_log_entries(self, entries: list[LogEntry]) -> None:
        """Set log entries in the table.

        Args:
            entries: List of log entries.
        """
        self._log_table.set_entries(entries)

    @beartype
    def set_categories(self, categories: list) -> None:
        """Set categories in the category panel.

        Args:
            categories: List of category nodes.
        """
        self._category_panel.set_categories(categories)

    @beartype
    def update_statistics(self, stats: dict[str, int]) -> None:
        """Update statistics counters.

        Args:
            stats: Dictionary of counter types to counts.
        """
        self._status_bar.update_statistics(stats)