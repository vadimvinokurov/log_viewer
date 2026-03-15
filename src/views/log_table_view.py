"""Log table view with column structure.

This module provides a table view for log entries
with columns: Time, Category, Type, Message.
"""
from __future__ import annotations

from typing import Optional, List
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QTableView, QAbstractItemView, QHeaderView, QScrollBar
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import (
    QColor, QGuiApplication, QKeyEvent, QShortcut
)

from src.styles.stylesheet import get_table_stylesheet
from src.constants.typography import Typography
from src.core.highlight_engine import HighlightEngine
from src.services.find_service import FindService
from src.services.highlight_service import HighlightService
from src.views.delegates import HighlightDelegate
from src.views.table_context_menu import TableContextMenu
from src.constants.colors import LogColors, LogIconColors
from src.constants.log_levels import LogLevel, LOG_LEVEL_CONFIGS
from src.constants.dimensions import (
    get_table_row_height,
    TABLE_HEADER_HEIGHT,
    TIME_COLUMN_WIDTH,
    CATEGORY_COLUMN_WIDTH,
    TYPE_COLUMN_WIDTH,
    MESSAGE_COLUMN_WIDTH,
    MIN_COLUMN_WIDTH,
)


# Background colors for log levels (converted from hex to QColor)
LEVEL_COLORS = {
    LogLevel.CRITICAL: QColor(LogColors.CRITICAL),
    LogLevel.ERROR: QColor(LogColors.ERROR),
    LogLevel.WARNING: QColor(LogColors.WARNING),
    LogLevel.MSG: None,  # Default white
    LogLevel.DEBUG: QColor(LogColors.DEBUG),
    LogLevel.TRACE: QColor(LogColors.TRACE),
}

# Icon colors for log levels (converted from hex to QColor)
LEVEL_ICON_COLORS = {
    LogLevel.CRITICAL: QColor(LogIconColors.CRITICAL),
    LogLevel.ERROR: QColor(LogIconColors.ERROR),
    LogLevel.WARNING: QColor(LogIconColors.WARNING),
    LogLevel.MSG: QColor(LogIconColors.MSG),
    LogLevel.DEBUG: QColor(LogIconColors.DEBUG),
    LogLevel.TRACE: QColor(LogIconColors.TRACE),
}


@dataclass
class LogEntryDisplay:
    """Display model for log entry in the new UI.
    
    This is an adapter that converts from the real LogEntry model
    to the display format expected by the new table view.
    """
    category: str
    time: str
    level: LogLevel
    message: str
    raw_line: str = ""  # Original raw line for copying
    
    @property
    def level_icon(self) -> str:
        """Get the icon character for the level."""
        config = LOG_LEVEL_CONFIGS.get(self.level)
        return config.icon if config else "?"
    
    @classmethod
    def from_log_entry(cls, entry) -> "LogEntryDisplay":
        """Create a display entry from a real LogEntry.
        
        Args:
            entry: LogEntry from src.models.log_entry
            
        Returns:
            LogEntryDisplay instance.
        """
        from src.models.log_entry import LogLevel as RealLogLevel
        
        # Map real log level to display log level
        level_map = {
            RealLogLevel.CRITICAL: LogLevel.CRITICAL,
            RealLogLevel.ERROR: LogLevel.ERROR,
            RealLogLevel.WARNING: LogLevel.WARNING,
            RealLogLevel.MSG: LogLevel.MSG,
            RealLogLevel.DEBUG: LogLevel.DEBUG,
            RealLogLevel.TRACE: LogLevel.TRACE,
        }
        
        # Use full category path
        category = entry.category if entry.category else ""
        
        # Parse timestamp to get time component
        time_str = entry.timestamp
        if " " in time_str:
            # If timestamp has date and time, extract time part
            time_str = time_str.split(" ")[-1]
        
        display_level = level_map.get(entry.level, LogLevel.MSG)
        
        return cls(
            category=category,
            time=time_str,
            level=display_level,
            message=entry.display_message,
            raw_line=entry.raw_line
        )


# Alias for backward compatibility with new UI code
LogEntry = LogEntryDisplay


class LogTableModel(QAbstractTableModel):
    """Model for log table with new column structure."""

    # Column indices
    COL_TIME = 0
    COL_CATEGORY = 1
    COL_TYPE = 2
    COL_MESSAGE = 3

    def __init__(self, parent=None) -> None:
        """Initialize the model."""
        super().__init__(parent)
        self._entries: List[LogEntry] = []
        self._headers = ["Time", "Category", "Type", "Message"]
        # Ref: docs/specs/features/typography-system.md §4.2 - Use pre-configured monospace font
        self._monospace_font = Typography.LOG_FONT

    def set_entries(self, entries: List[LogEntry]) -> None:
        """Set entries and reset model."""
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows."""
        if parent.isValid():
            return 0
        return len(self._entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns."""
        return 4

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object:
        """Return data for display and decoration."""
        if not index.isValid() or index.row() >= len(self._entries):
            return None

        entry = self._entries[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == self.COL_TIME:
                return entry.time
            elif col == self.COL_CATEGORY:
                return entry.category
            elif col == self.COL_TYPE:
                return entry.level_icon
            elif col == self.COL_MESSAGE:
                return entry.message

        elif role == Qt.BackgroundRole:
            return LEVEL_COLORS.get(entry.level)

        elif role == Qt.ForegroundRole:
            if col == self.COL_TYPE:
                return LEVEL_ICON_COLORS.get(entry.level)

        elif role == Qt.TextAlignmentRole:
            if col == self.COL_TYPE:
                return Qt.AlignCenter
            elif col == self.COL_TIME:
                return Qt.AlignLeft | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.FontRole:
            if col == self.COL_MESSAGE:
                return self._monospace_font

        elif role == Qt.ToolTipRole:
            # Show full message in tooltip for message column
            if col == self.COL_MESSAGE:
                return entry.message
            elif col == self.COL_CATEGORY:
                # Show full category path if available
                return entry.category
            elif col == self.COL_TIME:
                # Show full timestamp if available
                return entry.time
            return None

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> object:
        """Return header data."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None

    def get_entry(self, row: int) -> Optional[LogEntry]:
        """Get entry at row."""
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def get_entries(self) -> List[LogEntry]:
        """Get all entries."""
        return self._entries


class LogTableView(QTableView):
    """Table view for log entries with new column structure."""

    # Signal emitted when selection changes
    selection_changed = Signal()
    # Signal emitted when find is requested (Ctrl+F)
    find_requested = Signal()

    def __init__(self, parent=None) -> None:
        """Initialize the table view."""
        super().__init__(parent)
        self._model = LogTableModel(self)
        self._highlight_service = HighlightService()
        self._find_service = FindService()
        self._highlight_delegate = HighlightDelegate(parent=self)
        self._context_menu: Optional[TableContextMenu] = None
        
        self.setModel(self._model)
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        """Configure table view."""
        self._setup_selection()
        self._setup_scrollbars()
        self._setup_header()
        self._setup_delegate()

    def _setup_selection(self) -> None:
        """Setup selection behavior."""
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(False)

    def _setup_scrollbars(self) -> None:
        """Setup scrollbar behavior."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalScrollBar().setDisabled(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

    def _setup_header(self) -> None:
        """Setup table header."""
        header = self.horizontalHeader()
        header.setFixedHeight(TABLE_HEADER_HEIGHT)
        header.setSectionsClickable(False)
        
        # Use Interactive mode for all columns
        header.setSectionResizeMode(LogTableModel.COL_TIME, QHeaderView.Interactive)
        header.setSectionResizeMode(LogTableModel.COL_CATEGORY, QHeaderView.Interactive)
        header.setSectionResizeMode(LogTableModel.COL_TYPE, QHeaderView.Interactive)
        header.setSectionResizeMode(LogTableModel.COL_MESSAGE, QHeaderView.Interactive)

        # Set default column widths
        self.setColumnWidth(LogTableModel.COL_TIME, TIME_COLUMN_WIDTH)
        self.setColumnWidth(LogTableModel.COL_CATEGORY, CATEGORY_COLUMN_WIDTH)
        self.setColumnWidth(LogTableModel.COL_TYPE, TYPE_COLUMN_WIDTH)
        self.setColumnWidth(LogTableModel.COL_MESSAGE, MESSAGE_COLUMN_WIDTH)

        header.setMinimumSectionSize(MIN_COLUMN_WIDTH)
        header.setStretchLastSection(True)

        self.setSortingEnabled(False)
        self.setShowGrid(False)
        self.setStyleSheet(get_table_stylesheet())
        self.setWordWrap(False)
        self.setTextElideMode(Qt.ElideRight)

    def _setup_delegate(self) -> None:
        """Setup highlight delegate and row height."""
        self.setItemDelegate(self._highlight_delegate)
        
        row_height = get_table_row_height()
        v_header = self.verticalHeader()
        v_header.setDefaultSectionSize(row_height)
        v_header.setMinimumSectionSize(row_height)
        v_header.setMaximumSectionSize(row_height)
        v_header.setSectionResizeMode(QHeaderView.Fixed)
        v_header.setVisible(False)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        find_shortcut = QShortcut(Qt.CTRL | Qt.Key_F, self)
        find_shortcut.activated.connect(self._on_find_requested)

        select_all_shortcut = QShortcut(Qt.CTRL | Qt.Key_A, self)
        select_all_shortcut.activated.connect(self.selectAll)

    def _on_find_requested(self) -> None:
        """Handle find shortcut."""
        self.find_requested.emit()

    def set_highlight_engine(self, engine: Optional[HighlightEngine]) -> None:
        """Set the highlight engine.

        Args:
            engine: The highlight engine to use for text highlighting.
        """
        if engine:
            # Transfer patterns to highlight service
            self._highlight_service.clear_all()
            for pattern in engine.get_patterns():
                self._highlight_service.add_user_pattern(
                    pattern.text,
                    pattern.color,
                    pattern.is_regex,
                    pattern.enabled
                )
        else:
            self._highlight_service.clear_all()
        
        self._update_delegate()

    def get_highlight_engine(self) -> Optional[HighlightEngine]:
        """Get the current highlight engine.

        Returns:
            The current highlight engine or None.
        """
        return self._highlight_service.get_combined_engine()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press for copy."""
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self.copy_selected()
            event.accept()
        else:
            super().keyPressEvent(event)

    def copy_selected(self) -> None:
        """Copy selected rows to clipboard."""
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        # Sort rows by index
        sorted_rows = sorted(selected_rows, key=lambda x: x.row())

        # Collect raw lines
        lines = []
        for index in sorted_rows:
            entry = self._model.get_entry(index.row())
            if entry:
                lines.append(entry.raw_line or entry.message)

        # Copy to clipboard
        if lines:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText("\n".join(lines))

    def set_entries(self, entries: List[LogEntry]) -> None:
        """Set log entries."""
        self._model.set_entries(entries)
        self._force_row_height()

    def _force_row_height(self) -> None:
        """Force all rows to have the same height."""
        row_height = get_table_row_height()
        for row in range(self._model.rowCount()):
            self.setRowHeight(row, row_height)

    def get_entry(self, row: int) -> Optional[LogEntry]:
        """Get entry at row."""
        return self._model.get_entry(row)

    def get_selected_entries(self) -> List[LogEntry]:
        """Get all selected entries."""
        selected_rows = self.selectionModel().selectedRows()
        entries = []
        for index in selected_rows:
            entry = self._model.get_entry(index.row())
            if entry:
                entries.append(entry)
        return entries

    def clear(self) -> None:
        """Clear all entries."""
        self._model.set_entries([])

    def get_row_count(self) -> int:
        """Return the number of rows."""
        return self._model.rowCount()

    def refresh_highlighting(self) -> None:
        """Refresh the highlighting display."""
        self.viewport().update()

    def set_column_widths(self, widths: dict[str, int]) -> None:
        """Set column widths from dictionary.

        Args:
            widths: Dictionary mapping column names to widths.
        """
        column_map = {
            "time": LogTableModel.COL_TIME,
            "category": LogTableModel.COL_CATEGORY,
            "type": LogTableModel.COL_TYPE,
            "message": LogTableModel.COL_MESSAGE
        }
        for name, width in widths.items():
            if name.lower() in column_map:
                col = column_map[name.lower()]
                self.setColumnWidth(col, width)

    def get_column_widths(self) -> dict[str, int]:
        """Get current column widths.

        Returns:
            Dictionary mapping column names to widths.
        """
        return {
            "time": self.columnWidth(LogTableModel.COL_TIME),
            "category": self.columnWidth(LogTableModel.COL_CATEGORY),
            "type": self.columnWidth(LogTableModel.COL_TYPE),
            "message": self.columnWidth(LogTableModel.COL_MESSAGE)
        }

    # ==================== Find Operations ====================

    def find_text(self, text: str, case_sensitive: bool = False) -> int:
        """Find text in visible rows.

        Args:
            text: Text to search for.
            case_sensitive: Whether search is case-sensitive.

        Returns:
            Number of matches found.
        """
        if not text:
            self.clear_find_highlights()
            return 0

        # Use FindService for search
        entries = self._model.get_entries()
        match_count = self._find_service.find_text(text, entries, case_sensitive)

        # Update highlight service with find pattern
        self._highlight_service.set_find_pattern(text, QColor("#FFFF00"), case_sensitive)
        self._update_delegate()

        # Navigate to first match if any
        if match_count > 0:
            match = self._find_service.get_current_match()
            if match:
                self._navigate_to_match(match)

        return match_count

    def find_next(self) -> None:
        """Navigate to next match."""
        match = self._find_service.find_next()
        if match:
            self._navigate_to_match(match)

    def find_previous(self) -> None:
        """Navigate to previous match."""
        match = self._find_service.find_previous()
        if match:
            self._navigate_to_match(match)

    def _navigate_to_match(self, match) -> None:
        """Navigate to a specific match.

        Args:
            match: The match to navigate to.
        """
        index = self._model.index(match.row, match.column)
        self.scrollTo(index)
        self.selectRow(match.row)

    def clear_find_highlights(self) -> None:
        """Clear find highlights."""
        self._find_service.clear()
        self._highlight_service.clear_find_pattern()
        self._update_delegate()

    def _update_delegate(self) -> None:
        """Update the highlight delegate with combined engine."""
        combined_engine = self._highlight_service.get_combined_engine()
        self._highlight_delegate.set_highlight_engine(combined_engine)
        self.viewport().update()

    def get_find_match_count(self) -> int:
        """Get the number of find matches.

        Returns:
            Number of matches.
        """
        return self._find_service.get_match_count()

    def get_current_find_match(self) -> int:
        """Get the current find match index.

        Returns:
            Current match index (0-based), or -1 if no match.
        """
        return self._find_service.get_current_match_index() - 1 if self._find_service.has_matches() else -1

    # ==================== Context Menu ====================

    def contextMenuEvent(self, event) -> None:
        """Show context menu.

        Args:
            event: Context menu event.
        """
        if self._context_menu is None:
            self._context_menu = TableContextMenu(self, self)
        self._context_menu.show(event.globalPos())

    # ==================== Size Hints ====================

    def sizeHintForColumn(self, column: int) -> int:
        """Return size hint for column.

        Args:
            column: Column index.

        Returns:
            Size hint for the column.
        """
        widths = {
            LogTableModel.COL_TIME: 50,
            LogTableModel.COL_CATEGORY: 100,
            LogTableModel.COL_TYPE: 40,
            LogTableModel.COL_MESSAGE: 200,
        }
        if column in widths:
            return widths[column]
        return 100