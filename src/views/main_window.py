"""Main application window with new UI design.

This module provides the redesigned main window with:
- Search toolbar with statistics bar at the top
- Horizontal splitter (75% log table / 25% CategoryPanel)
"""
from __future__ import annotations

import logging
import os
from typing import Optional
from beartype import beartype

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from src.styles.stylesheet import get_application_stylesheet
from src.views.log_table_view import LogTableView, LogEntry
from src.views.category_panel import CategoryPanel
from src.views.widgets.search_toolbar import SearchToolbarWithStats
from src.views.widgets.main_status_bar import MainStatusBar
from src.views.find_dialog import FindDialog
from src.views.widgets.error_dialog import ErrorDialog
from src.constants.app_constants import (
    APPLICATION_NAME, STATUS_MESSAGE_TIMEOUT
)
from src.constants.dimensions import SPLITTER_LEFT_RATIO, SPLITTER_RIGHT_RATIO


# Keyboard shortcuts
SHORTCUT_OPEN_FILE = "Ctrl+O"
SHORTCUT_RELOAD = "F5"
SHORTCUT_CLOSE = "Ctrl+W"
SHORTCUT_FIND = "Ctrl+F"
SHORTCUT_EXIT = "Ctrl+Q"
SHORTCUT_TOGGLE_PANELS = "Ctrl+Shift+P"

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
    """Main application window with redesigned UI.
    
    // Ref: docs/specs/features/panel-toggle-button.md §4.2
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    """

    # Signals
    file_opened = Signal(str)  # filepath
    file_closed = Signal()  # file closed
    refresh_requested = Signal()
    find_requested = Signal(str, bool)  # text, case_sensitive
    category_toggled = Signal(str, bool)  # category_path, checked
    categories_batch_changed = Signal()  # all categories changed at once
    filter_applied = Signal(str, str)  # search_text, mode
    filter_cleared = Signal()
    counter_toggled = Signal(str, bool)  # counter_type, visible
    open_file_requested = Signal()  # open file button clicked
    panels_toggled = Signal(bool)  # panels_visible

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
        self.setStyleSheet(get_application_stylesheet())

    def _create_components(self) -> None:
        """Create UI components."""
        self._search_toolbar: SearchToolbarWithStats = SearchToolbarWithStats()
        self._main_toolbar: QToolBar | None = None  # Store toolbar reference for visibility control
        self._log_table: LogTableView = LogTableView()
        self._category_panel: CategoryPanel = CategoryPanel()
        self._status_bar: MainStatusBar = MainStatusBar()
        self._find_dialog: Optional[FindDialog] = None
        self._current_file: Optional[str] = None
        self._pending_filepath: Optional[str] = None
        # Panel toggle state
        # Ref: docs/specs/features/panel-toggle-button.md §4.2
        self._panels_visible: bool = True
        self._stored_splitter_sizes: list[int] | None = None

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
        
        # Add search toolbar directly (visibility controlled by panel toggle button)
        # Ref: docs/specs/features/ui-components.md §6
        toolbar.addWidget(self._search_toolbar)
        
        # Store toolbar reference for visibility control
        self._main_toolbar = toolbar
        
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
            (QKeySequence(SHORTCUT_TOGGLE_PANELS), self._on_toggle_panels),
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
        
        # Status bar signals (panel toggle)
        # Ref: docs/specs/features/panel-toggle-button.md §4.2
        self._status_bar.panels_toggled.connect(self._on_status_bar_panels_toggled)

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
        
        Per docs/specs/features/file-open-dialog.md §3.1:
        - Yes = Open in new window
        - No = Open in current window (close old log)
        - Close (X) = Cancel (do nothing)
        """
        new_filename = os.path.basename(filepath)
        
        reply = QMessageBox.question(
            self,
            "Open File",
            f"Open '{new_filename}' in new windows?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Open in new window
            self._pending_filepath = filepath
            self.open_file_requested.emit()
        elif reply == QMessageBox.No:
            # Open in current window (close old log first)
            # Ref: docs/specs/features/file-open-dialog.md §3.1
            logger.debug(f"User chose No - opening in current window: {filepath}")
            
            # Set new file path
            self._current_file = filepath
            
            # Emit close signal - controller will handle cleanup
            # Ref: docs/specs/features/file-open-dialog.md §3.1
            # Thread: Main thread only (Qt requirement)
            # Memory: Controller clears UI models safely before destroying document
            logger.debug("Emitting file_closed signal")
            self.file_closed.emit()
            
            # Defer file opening to allow controller to finish closing
            # Use 200ms delay to give Qt more time to process events
            logger.debug("Scheduling deferred file open")
            QTimer.singleShot(200, lambda: self._open_file_deferred(filepath))
        # Close button (X) = do nothing (implicit cancel)

    def _open_file_deferred(self, filepath: str) -> None:
        """Open file after close events have been processed.
        
        Args:
            filepath: Path to the file to open.
        
        // Ref: docs/specs/features/file-open-dialog.md §3.1
        // This method is called via QTimer.singleShot to allow Qt to:
        // - Process the file_closed signal completely
        // - Finish any pending paint events
        // - Clean up the old model
        // Then safely open the new file
        """
        logger.debug(f"Opening file after close: {filepath}")
        self.file_opened.emit(filepath)
        self.setWindowTitle(f"{APPLICATION_NAME} - {filepath}")
        self._status_bar.set_file(os.path.basename(filepath))

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

    # === Panel Toggle API ===
    # Ref: docs/specs/features/panel-toggle-button.md §4.2

    def _on_toggle_panels(self) -> None:
        """Handle keyboard shortcut for panel toggle.
        
        Ref: docs/specs/features/panel-toggle-button.md §5.3
        """
        self.toggle_panels()

    def _on_status_bar_panels_toggled(self, visible: bool) -> None:
        """Handle panel toggle signal from status bar.
        
        Args:
            visible: True if panels should be visible, False if hidden.
        
        Ref: docs/specs/features/panel-toggle-button.md §4.2
        """
        self.set_panels_visible(visible)

    def toggle_panels(self) -> None:
        """Toggle visibility of all auxiliary panels.
        
        Hides/shows:
        - Search toolbar (top)
        - Category panel (right)
        
        Ref: docs/specs/features/panel-toggle-button.md §4.2
        """
        self.set_panels_visible(not self._panels_visible)

    def set_panels_visible(self, visible: bool) -> None:
        """Set panels visibility directly.
        
        Args:
            visible: True to show panels, False to hide.
        
        Ref: docs/specs/features/panel-toggle-button.md §6.1
        """
        if visible == self._panels_visible:
            return  # No change needed

        if visible:
            # Restore search toolbar (show toolbar container)
            if self._main_toolbar:
                self._main_toolbar.setVisible(True)
            
            # Restore category panel
            splitter = self.centralWidget().findChild(QSplitter)
            if splitter:
                if self._stored_splitter_sizes is not None:
                    # Restore stored sizes
                    splitter.setSizes(self._stored_splitter_sizes)
                else:
                    # Use default ratios
                    left_size = int(self.width() * SPLITTER_LEFT_RATIO / 100)
                    right_size = int(self.width() * SPLITTER_RIGHT_RATIO / 100)
                    splitter.setSizes([left_size, right_size])
        else:
            # Store current splitter sizes before hiding
            splitter = self.centralWidget().findChild(QSplitter)
            if splitter:
                self._stored_splitter_sizes = list(splitter.sizes())
            
            # Hide search toolbar (hide toolbar container)
            if self._main_toolbar:
                self._main_toolbar.setVisible(False)
            
            # Hide category panel
            if splitter:
                splitter.setSizes([self.width(), 0])
        
        # Store state
        self._panels_visible = visible
        
        # Update status bar button
        self._status_bar.set_panels_visible(visible)
        
        # Emit signal
        self.panels_toggled.emit(visible)

    def is_panels_visible(self) -> bool:
        """Check if panels are currently visible.
        
        Returns:
            True if panels are visible, False if hidden.
        
        Ref: docs/specs/features/panel-toggle-button.md §4.2
        """
        return self._panels_visible