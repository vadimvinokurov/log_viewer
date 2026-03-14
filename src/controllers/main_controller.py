"""Main controller for the new UI design.

This module provides the controller for the redesigned MainWindow,
integrating with the existing Model and Core layers.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from beartype import beartype

from src.models.log_document import LogDocument
from src.models.log_entry import LogEntry, LogLevel
from src.views.main_window import MainWindow
from src.controllers.filter_controller import FilterController
from src.controllers.file_controller import FileController
from src.controllers.index_worker import IndexWorker
from src.core.category_tree import CategoryTree, build_category_display_nodes
from src.services.statistics_service import StatisticsService
from src.services.highlight_service import HighlightService
from src.utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class MainController(QObject):
    """Main controller for the new UI design.

    Coordinates between views and models, handling user actions
    and updating the UI accordingly.
    """

    # Statistics update signal
    statistics_updated = Signal(dict)  # stats dict

    @beartype
    def __init__(self, window: MainWindow) -> None:
        """Initialize the controller.

        Args:
            window: The main application window
        """
        super().__init__()
        self._window = window
        self._document: LogDocument | None = None
        self._index_worker: IndexWorker | None = None
        self._all_entries: list[LogEntry] = []
        self._filtered_entries: list[LogEntry] = []

        # Initialize services
        self._statistics_service = StatisticsService()
        self._highlight_service = HighlightService()

        # Initialize filter controller
        self._filter_controller = FilterController(self)

        # Initialize settings manager
        self._settings_manager = SettingsManager()

        # Initialize file controller
        self._file_controller = FileController(self)
        self._setup_file_controller()

        # Initialize category tree
        self._category_tree = CategoryTree()

        # Load settings
        self._load_settings()

        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect UI signals to handlers."""
        # File operations
        self._window.file_opened.connect(self.open_file)
        self._window.file_closed.connect(self.close_file)
        self._window.refresh_requested.connect(self.refresh)
        self._window.auto_reload_toggled.connect(self._on_auto_reload_toggled)
        self._window.find_requested.connect(self._on_find_requested)
        self._window.open_file_requested.connect(self._on_open_file_requested)

        # Filter operations
        self._window.filter_applied.connect(self._on_filter_applied_from_ui)
        self._window.filter_cleared.connect(self._on_filter_cleared)

        # Category filtering
        self._window.category_toggled.connect(self._on_category_toggled)

        # Counter filtering (log levels)
        self._window.counter_toggled.connect(self._on_counter_toggled)

        # Filter controller signals
        self._filter_controller.filter_applied.connect(self._on_filter_applied)
        self._filter_controller.filter_error.connect(self._on_filter_error)

    def _setup_file_controller(self) -> None:
        """Set up file controller connections."""
        self._file_controller.file_changed.connect(self._on_file_changed)
        self._file_controller.file_removed.connect(self._on_file_removed)

    def _load_settings(self) -> None:
        """Load application settings."""
        settings = self._settings_manager.load()

        # Load highlight patterns
        for pattern_data in settings.highlight_patterns:
            try:
                color = QColor(pattern_data.color_hex)
                self._highlight_service.add_user_pattern(
                    pattern=pattern_data.text,
                    color=color,
                    is_regex=pattern_data.is_regex,
                    enabled=pattern_data.enabled
                )
            except Exception as e:
                logger.warning(f"Failed to load highlight pattern: {e}")

        # Set highlight engine on log table view
        self._window.get_log_table().set_highlight_engine(
            self._highlight_service.get_combined_engine()
        )

        # Restore window geometry if available
        geometry = self._settings_manager.get_window_geometry()
        if geometry:
            self._window.restoreGeometry(geometry)

        # Restore column widths if available
        if settings.column_widths:
            self._window.get_log_table().set_column_widths(settings.column_widths)

        logger.info("Settings loaded")

    def _save_settings(self) -> None:
        """Save application settings."""
        from src.utils.settings_manager import HighlightPatternData

        # Save highlight patterns
        patterns = []
        for p in self._highlight_service.get_user_patterns():
            patterns.append(HighlightPatternData(
                text=p.text,
                color_hex=p.color.name(),
                is_regex=p.is_regex,
                enabled=p.enabled
            ))
        self._settings_manager.settings.highlight_patterns = patterns

        # Save last file
        if self._document:
            self._settings_manager.set_last_file(self._document.filepath)

        # Save window geometry
        self._settings_manager.set_window_geometry(self._window.saveGeometry())

        # Save column widths
        self._settings_manager.set_column_widths(
            self._window.get_log_table().get_column_widths()
        )
        
        # Save category states
        self._save_category_states()

        self._settings_manager.save()
        logger.info("Settings saved")

    @beartype
    def open_file(self, filepath: str) -> None:
        """Open a log file.

        Args:
            filepath: Path to the log file
        """
        # Close existing document
        if self._document is not None:
            self._document.close()
            self._document = None

        # Clear UI
        self._window.get_log_table().clear()
        self._window.get_category_panel().clear()
        self._window.show_status("Loading...", 0)

        # Reset statistics service
        self._statistics_service.clear_cache()

        # Create new document
        try:
            self._document = LogDocument(filepath)
            
            # Track current file in window
            self._window.set_current_file(filepath)

            # Start indexing in background thread
            self._index_worker = IndexWorker(self._document)
            self._index_worker.finished.connect(
                lambda: self._on_index_complete(filepath)
            )
            self._index_worker.start()

        except Exception as e:
            self._window.show_error("Error Opening File", str(e))

    def _on_open_file_requested(self) -> None:
        """Handle request to open a new file in a separate window.
        
        This is called when user wants to open a file in a new window
        while another file is already open.
        """
        import sys
        import subprocess
        from pathlib import Path
        
        # Get the pending filepath from the window
        pending_filepath = self._window.get_pending_filepath()
        self._window.clear_pending_filepath()
        
        if not pending_filepath:
            return
        
        # Get the path to the main script
        main_script = Path(sys.argv[0]).absolute()
        
        # Launch a new instance of the application with the file
        try:
            if main_script.suffix == '.py':
                # Running as Python script
                subprocess.Popen([sys.executable, str(main_script), pending_filepath])
            else:
                # Running as executable
                subprocess.Popen([str(main_script), pending_filepath])
        except Exception as e:
            logger.error(f"Failed to open new window: {e}")
            self._window.show_error(
                "Error Opening New Window",
                f"Failed to open a new window: {e}"
            )

    @beartype
    def _on_index_complete(self, filepath: str) -> None:
        """Handle completion of document indexing.

        Args:
            filepath: Path to the opened file
        """
        if self._document is None:
            return

        # Update window title
        self._window.setWindowTitle(f"Log Viewer - {filepath}")

        # Load all entries
        self._all_entries = []
        for i in range(self._document.get_line_count()):
            entry = self._document.get_line(i)
            if entry:
                self._all_entries.append(entry)

        # Calculate statistics using service
        self._statistics_service.calculate(self._all_entries)

        # Build category tree
        categories = self._document.get_categories()
        self._category_tree = CategoryTree()
        for category in categories:
            self._category_tree.add_category(category)

        # Update filter controller with categories
        self._filter_controller.set_categories(categories)

        # Update category panel with category tree
        category_nodes = build_category_display_nodes(self._category_tree)
        self._window.get_category_panel().set_categories(category_nodes)
        
        # Restore category checkbox states from settings
        self._restore_category_states()

        # Start watching the file for changes
        self._file_controller.stop_watching()
        self._file_controller.open_file(filepath)

        # Show status message
        self._window.show_status(f"Loaded {len(self._all_entries)} entries", 3000)

        # Apply initial filter (shows all entries)
        self._apply_filters()

    def refresh(self) -> None:
        """Refresh current file."""
        if self._document is not None:
            filepath = self._document.filepath
            self.open_file(filepath)

    def close_file(self) -> None:
        """Close current file and clear UI."""
        # Close file via file controller
        if self._document is not None:
            self._file_controller.close_file(self._document.filepath)
            self._document = None

        # Clear data
        self._all_entries = []
        self._filtered_entries = []

        # Clear UI
        self._window.get_log_table().clear()
        self._window.get_category_panel().clear()
        self._window.update_statistics({
            "critical": 0,
            "error": 0,
            "warning": 0,
            "msg": 0,
            "debug": 0,
            "trace": 0
        })

        # Clear current file in window
        self._window.set_current_file(None)

        # Reset filter controller
        self._filter_controller.reset()

        # Reset statistics service
        self._statistics_service.clear_cache()

        # Show status message
        self._window.show_status("File closed", 3000)

        logger.info("File closed")

    @beartype
    def _on_filter_applied_from_ui(self, text: str, mode: str) -> None:
        """Handle filter applied from UI.

        Args:
            text: Filter text.
            mode: Filter mode ('plain', 'regex', or 'simple').
        """
        from src.models.filter_state import FilterMode
        
        # Map mode string to FilterMode enum
        mode_map = {
            "plain": FilterMode.PLAIN,
            "regex": FilterMode.REGEX,
            "simple": FilterMode.SIMPLE,
        }
        filter_mode = mode_map.get(mode, FilterMode.PLAIN)
        
        # Update filter controller
        self._filter_controller.set_filter_text(text)
        self._filter_controller.set_filter_mode(filter_mode)
        self._filter_controller.apply_filter()

    @beartype
    def _on_filter_cleared(self) -> None:
        """Handle filter cleared from UI."""
        # Clear filter text and reset mode
        self._filter_controller.set_filter_text("")
        self._filter_controller.apply_filter()

    @beartype
    def _on_category_toggled(self, category_path: str, checked: bool) -> None:
        """Handle category toggle from category panel.

        Args:
            category_path: Category path.
            checked: Whether it's checked.
        """
        # Use toggle() to cascade state to children in CategoryTree
        # This matches the UI behavior where checkboxes cascade to children
        # Ref: docs/specs/features/category-checkbox-behavior.md §3.1, §3.2
        self._filter_controller.toggle_category(category_path, checked)
        self._filter_controller.apply_filter()
        
        # Save category states to settings
        self._save_category_states()
    
    def _save_category_states(self) -> None:
        """Save current category checkbox states to settings."""
        category_states = self._window.get_category_panel().get_category_states()
        self._settings_manager.set_category_states(category_states)
    
    def _restore_category_states(self) -> None:
        """Restore category checkbox states from settings.
        
        If no saved state exists for a category, it defaults to checked (enabled).
        """
        saved_states = self._settings_manager.get_category_states()
        
        if saved_states:
            # Apply saved states
            self._window.get_category_panel().set_category_states(saved_states)
            
            # Update filter controller with restored states
            for category_path, checked in saved_states.items():
                self._filter_controller.set_category_enabled(category_path, checked)
        # If no saved states, all categories remain checked (default from set_categories)

    @beartype
    def _on_counter_toggled(self, counter_type: str, visible: bool) -> None:
        """Handle counter toggle from statistics bar.

        Args:
            counter_type: Counter type (critical, error, warning, msg, debug, trace).
            visible: Whether logs of this type should be visible.
        """
        # Map counter type to LogLevel enum
        level_map = {
            "critical": LogLevel.CRITICAL,
            "error": LogLevel.ERROR,
            "warning": LogLevel.WARNING,
            "msg": LogLevel.MSG,
            "debug": LogLevel.DEBUG,
            "trace": LogLevel.TRACE,
        }

        level = level_map.get(counter_type)
        if level:
            self._filter_controller.toggle_level(level.value, visible)
            self._filter_controller.apply_filter()

    def _on_filter_applied(self) -> None:
        """Handle filter applied signal from filter controller."""
        self._apply_filters()

    @beartype
    def _on_filter_error(self, error_message: str) -> None:
        """Handle filter error signal from filter controller.

        Args:
            error_message: Error message to display
        """
        self._window.show_error("Filter Error", error_message)

    def _apply_filters(self) -> None:
        """Apply current filters to entries."""
        if not self._all_entries:
            return

        # Get the compiled filter from filter controller
        filter_func = self._filter_controller.get_filter()

        # Filter entries
        if filter_func is None:
            self._filtered_entries = self._all_entries.copy()
        else:
            self._filtered_entries = [
                entry for entry in self._all_entries
                if filter_func(entry)
            ]

        # Convert to display format for the new UI
        from src.views.log_table_view import LogEntryDisplay
        display_entries = [
            LogEntryDisplay.from_log_entry(entry)
            for entry in self._filtered_entries
        ]

        # Update display
        self._window.get_log_table().set_entries(display_entries)
        self._update_statistics()

    def _update_statistics(self) -> None:
        """Update the statistics display."""
        shown = len(self._filtered_entries)

        # Get statistics from service
        stats = self._statistics_service.update_shown_count(shown)
        if stats is None:
            stats = self._statistics_service.calculate(self._all_entries, shown)

        # Convert to dictionary for UI
        ui_stats = stats.to_dict()

        self._window.update_statistics(ui_stats)

    def get_highlight_engine(self):
        """Get the highlight engine.

        Returns:
            The combined highlight engine instance.
        """
        return self._highlight_service.get_combined_engine()

    def add_highlight_pattern(self, text: str, color: QColor, is_regex: bool = False) -> None:
        """Add a highlight pattern.

        Args:
            text: Pattern text.
            color: Highlight color.
            is_regex: Whether pattern is a regex.
        """
        self._highlight_service.add_user_pattern(
            pattern=text,
            color=color,
            is_regex=is_regex
        )
        self._window.get_log_table().refresh_highlighting()

    def remove_highlight_pattern(self, pattern: str) -> None:
        """Remove a highlight pattern.

        Args:
            pattern: Pattern text to remove.
        """
        self._highlight_service.remove_user_pattern(pattern)
        self._window.get_log_table().refresh_highlighting()

    def clear_highlight_patterns(self) -> None:
        """Clear all highlight patterns."""
        self._highlight_service.clear_all()
        self._window.get_log_table().refresh_highlighting()

    def _on_auto_reload_toggled(self, enabled: bool) -> None:
        """Handle auto-reload toggle.

        Args:
            enabled: Whether auto-reload is enabled.
        """
        self._file_controller.set_auto_reload(enabled)
        logger.info(f"Auto-reload {'enabled' if enabled else 'disabled'}")

    def _on_file_changed(self, filepath) -> None:
        """Handle file change on disk.

        Args:
            filepath: Path to the changed file (Path object).
        """
        from PySide6.QtWidgets import QMessageBox

        if not self._file_controller.is_auto_reload_enabled():
            return

        filepath_str = str(filepath)

        # Prompt user to reload
        reply = QMessageBox.question(
            self._window,
            "File Changed",
            f"The file '{filepath_str}' has been modified.\n\nDo you want to reload it?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.refresh()
        else:
            self._window.show_status("File changed - reload skipped", 3000)

    def _on_file_removed(self, filepath) -> None:
        """Handle file removal on disk.

        Args:
            filepath: Path to the removed file (Path object).
        """
        filepath_str = str(filepath)
        self._window.show_error(
            "File Removed",
            f"The file '{filepath_str}' has been removed or moved."
        )
        self._file_controller.stop_watching()

    def _on_find_requested(self, text: str, case_sensitive: bool) -> None:
        """Handle find requested from main window.

        Args:
            text: Text to find.
            case_sensitive: Whether search is case-sensitive.
        """
        count = self._window.get_log_table().find_text(text, case_sensitive)
        self._window.show_status(f"Found {count} matches", 3000)

    def handle_error(self, title: str, message: str, details: str = "") -> None:
        """Handle error with user feedback.

        Args:
            title: Error dialog title.
            message: User-friendly error message.
            details: Technical details/stack trace.
        """
        logger.error(f"{title}: {message}")
        if details:
            logger.debug(f"Details: {details}")
        self._window.show_error_with_details(title, message, details)

    def close(self) -> None:
        """Clean up resources."""
        # Save settings before closing
        self._save_settings()

        # Clean up file controller
        self._file_controller.cleanup()

        if self._index_worker is not None:
            self._index_worker.wait()
            self._index_worker = None

        if self._document is not None:
            self._document.close()
            self._document = None