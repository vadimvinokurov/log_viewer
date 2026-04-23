"""Log table view with column structure.

This module provides a table view for log entries
with columns: Time, Category, Type, Message.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from beartype import beartype

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QTableView, QAbstractItemView, QHeaderView, QScrollBar
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QItemSelection
from PySide6.QtGui import (
    QColor, QGuiApplication, QKeyEvent, QMouseEvent, QShortcut, QWheelEvent
)

from src.styles.stylesheet import get_table_stylesheet
from src.constants.typography import Typography
from src.constants.table_config import get_column_alignment
from src.core.highlight_engine import HighlightEngine
from src.services.find_service import FindService
from src.services.highlight_service import HighlightService
from src.views.delegates import HighlightDelegate
from src.views.table_context_menu import TableContextMenu
from src.constants.colors import LogTextColors, LogIconColors, UIColors
from src.models.selection_state import SelectionState, ViewportState
from src.constants.log_levels import LogLevel, LOG_LEVEL_CONFIGS
from src.constants.dimensions import (
    get_table_cell_height,
    MIN_COLUMN_WIDTH,
    TIME_COLUMN_MIN_WIDTH,
    TIME_COLUMN_PADDING,
    TYPE_COLUMN_MIN_WIDTH,
    TYPE_COLUMN_PADDING,
    CATEGORY_COLUMN_MIN_WIDTH,
    CATEGORY_COLUMN_MAX_WIDTH,
    CATEGORY_COLUMN_PADDING,
    CATEGORY_COLUMN_SAMPLE_SIZE,
    MESSAGE_COLUMN_MIN_WIDTH,
)


# Text colors for log levels (converted from hex to QColor)
# Ref: docs/specs/features/log-level-text-color.md §4.1
LEVEL_TEXT_COLORS = {
    LogLevel.CRITICAL: QColor(LogTextColors.CRITICAL),
    LogLevel.ERROR: QColor(LogTextColors.ERROR),
    LogLevel.WARNING: QColor(LogTextColors.WARNING),
    LogLevel.MSG: None,  # Default text color
    LogLevel.DEBUG: None,  # Default text color
    LogLevel.TRACE: None,  # Default text color
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
    
    Ref: docs/specs/features/selection-preservation.md §3.3
    Ref: docs/specs/features/log-entry-optimization.md §4.3
    Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
    Master: docs/SPEC.md §1
    """
    category: str
    time: str            # H:M:S.MS format for table display
    time_full: str       # Full date-time for tooltip (YYYY-MM-DD H:M:S.MS)
    level: LogLevel
    message: str
    file_offset: int = 0
    
    @property
    def level_icon(self) -> str:
        """Get the icon character for the level."""
        config = LOG_LEVEL_CONFIGS.get(self.level)
        return config.icon if config else "?"
    
    @classmethod
    def from_log_entry(cls, entry) -> "LogEntryDisplay":
        """Create a display entry from a real LogEntry.
        
        // Ref: docs/specs/features/log-entry-optimization.md §4.3
        // raw_line removed - lazy loaded via LogDocument.get_raw_line()
        // Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        // timestamp is Unix Epoch float, convert to display formats
        
        Args:
            entry: LogEntry from src.models.log_entry (timestamp is Unix Epoch float)
            
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
        
        # Convert Unix Epoch to datetime
        dt = datetime.fromtimestamp(entry.timestamp)
        
        # Format for table: H:M:S.MS
        time_str = dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        
        # Format for tooltip: YYYY-MM-DD H:M:S.MS
        time_full = dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        
        display_level = level_map.get(entry.level, LogLevel.MSG)
        
        # Use full category path
        category = entry.category if entry.category else ""
        
        return cls(
            category=category,
            time=time_str,
            time_full=time_full,
            level=display_level,
            message=entry.display_message,
            file_offset=entry.file_offset
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

        elif role == Qt.ForegroundRole:
            # Log level text color applies to all columns
            # Ref: docs/specs/features/log-level-text-color.md §4.1
            level_color = LEVEL_TEXT_COLORS.get(entry.level)
            if level_color:
                return level_color
            
            # Icon column still uses icon colors if no level color
            if col == self.COL_TYPE:
                return LEVEL_ICON_COLORS.get(entry.level)

        # Ref: docs/specs/features/table-column-alignment.md §3.1
        elif role == Qt.TextAlignmentRole:
            return get_column_alignment(col)

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
                # Show full timestamp (YYYY-MM-DD H:M:S.MS)
                # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
                return entry.time_full
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
        self._document: Optional["LogDocument"] = None  # For lazy loading raw lines
        self._auto_sized = False  # Track if auto-size has been applied
        
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
        """Setup scrollbar behavior to completely block horizontal scrolling.
        
        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1
        
        This method implements multiple layers of protection:
        1. Policy: Always hide horizontal scrollbar
        2. Disabled: Prevent any interaction
        3. Range: Set to (0, 0) to prevent any scrolling
        4. Signal: Connect to valueChanged to reset any changes
        
        Ref: docs/specs/features/selection-preservation.md §7.9
        Vertical scroll mode is set to ScrollPerItem for correct viewport restoration.
        """
        # Layer 1: Hide horizontal scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Layer 2: Disable the scrollbar widget
        self.horizontalScrollBar().setDisabled(True)
        
        # Layer 3: Set range to (0, 0) - no scrolling possible
        self.horizontalScrollBar().setRange(0, 0)
        
        # Layer 4: Connect to valueChanged signal to reset any changes
        # This catches any programmatic or internal scroll changes
        self.horizontalScrollBar().valueChanged.connect(self._on_horizontal_scroll_changed)
        
        # Set scroll modes
        # Horizontal: ScrollPerPixel for smooth horizontal scrolling (blocked anyway)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        # Vertical: ScrollPerItem for correct viewport restoration formula
        # Ref: docs/specs/features/selection-preservation.md §7.9.1
        # ScrollPerItem mode means scroll values are in ROWS, not pixels
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)

    def _on_horizontal_scroll_changed(self, value: int) -> None:
        """Reset horizontal scroll to 0 whenever it changes.
        
        This is connected to the horizontal scrollbar's valueChanged signal
        to catch any programmatic or internal scroll changes.
        
        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1
        
        Args:
            value: The new scroll value (ignored).
        """
        if value != 0:
            # Block signals to prevent infinite loop
            self.horizontalScrollBar().blockSignals(True)
            self.horizontalScrollBar().setValue(0)
            self.horizontalScrollBar().blockSignals(False)

    def updateGeometries(self) -> None:
        """Override to keep horizontal scrollbar range at (0, 0).
        
        Qt's internal geometry updates recalculate scrollbar ranges based on
        content/viewport sizes. This override ensures the horizontal scrollbar
        remains disabled even after Qt's geometry updates.
        
        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1
        """
        super().updateGeometries()
        # Reset horizontal scrollbar range to prevent any scrolling
        self.horizontalScrollBar().setRange(0, 0)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Override to prevent horizontal scrolling.
        
        This is the core protection layer that intercepts scroll operations
        at the viewport level. By passing dx=0 to parent, we ensure that
        no horizontal scrolling ever occurs, even during auto-scroll.
        
        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1
        
        Args:
            dx: Horizontal scroll delta (ignored, always treated as 0).
            dy: Vertical scroll delta (passed through).
        """
        # Only allow vertical scrolling - pass dx=0 to parent
        super().scrollContentsBy(0, dy)
        
        # Ensure horizontal scroll bar stays at 0
        self.horizontalScrollBar().setValue(0)

    def _setup_header(self) -> None:
        """Setup table header.
        
        Ref: docs/specs/features/table-unified-styles.md §3.2
        Ref: docs/specs/features/table-column-auto-size.md §3.2
        Master: docs/SPEC.md §1
        """
        header = self.horizontalHeader()
        # Ref: Unified cell height for header and rows
        header.setFixedHeight(get_table_cell_height())
        header.setSectionsClickable(False)
        
        # Use Interactive mode for all columns (allows user resize)
        # Ref: docs/specs/features/table-column-auto-size.md §3.2
        header.setSectionResizeMode(LogTableModel.COL_TIME, QHeaderView.Interactive)
        header.setSectionResizeMode(LogTableModel.COL_CATEGORY, QHeaderView.Interactive)
        header.setSectionResizeMode(LogTableModel.COL_TYPE, QHeaderView.Interactive)
        header.setSectionResizeMode(LogTableModel.COL_MESSAGE, QHeaderView.Interactive)
        
        # Set minimum section size (allows user to resize down to minimum)
        header.setMinimumSectionSize(MIN_COLUMN_WIDTH)
        
        # Stretch last section (Message column) to fill remaining space
        header.setStretchLastSection(True)

        self.setSortingEnabled(False)
        self.setShowGrid(False)
        self.setStyleSheet(get_table_stylesheet())
        self.setWordWrap(False)
        self.setTextElideMode(Qt.ElideRight)

    def _setup_delegate(self) -> None:
        """Setup highlight delegate and row height.
        
        Ref: docs/specs/features/table-unified-styles.md §3.2
        Master: docs/SPEC.md §1
        """
        self.setItemDelegate(self._highlight_delegate)
        
        # Ref: Unified cell height for header and rows
        row_height = get_table_cell_height()
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
        elif event.key() == Qt.Key_N and event.modifiers() == Qt.NoModifier:
            self.find_next()
            event.accept()
        elif event.key() == Qt.Key_N and event.modifiers() == Qt.ShiftModifier:
            self.find_previous()
            event.accept()
        else:
            super().keyPressEvent(event)

    def set_document(self, document: Optional["LogDocument"]) -> None:
        """Set the document for lazy loading raw lines.
        
        // Ref: docs/specs/features/log-entry-optimization.md §4.3
        // Document reference needed for lazy loading raw lines for clipboard
        
        Args:
            document: LogDocument instance or None
        """
        self._document = document

    def copy_selected(self) -> None:
        """Copy selected rows to clipboard.
        
        // Ref: docs/specs/features/log-entry-optimization.md §4.3
        // Lazy loads raw_line via LogDocument.get_raw_line() for clipboard
        """
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
                # Lazy load raw_line for clipboard
                if self._document:
                    try:
                        raw_line = self._document.get_raw_line(entry.file_offset)
                        lines.append(raw_line)
                    except (FileNotFoundError, IOError):
                        # Fallback to display message if file unavailable
                        lines.append(entry.message)
                else:
                    # Fallback to display message if no document
                    lines.append(entry.message)

        # Copy to clipboard
        if lines:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText("\n".join(lines))

    def set_entries(self, entries: List[LogEntry]) -> None:
        """Set log entries."""
        self._model.set_entries(entries)
        self._force_row_height()
        
        # Auto-size columns only on first load
        # Ref: docs/specs/features/table-column-auto-size.md §3.1
        if not self._auto_sized:
            self._auto_size_columns()
            self._auto_sized = True

    def _force_row_height(self) -> None:
        """Force all rows to have the same height.
        
        Ref: docs/specs/features/table-unified-styles.md §3.2
        Master: docs/SPEC.md §1
        """
        # Ref: Unified cell height for header and rows
        row_height = get_table_cell_height()
        for row in range(self._model.rowCount()):
            self.setRowHeight(row, row_height)

    def _auto_size_columns(self) -> None:
        """Auto-size Time, Type, and Category columns based on content.
        
        This method calculates optimal column widths based on content:
        - Time column: Fixed format "HH:MM:SS.mmm" (monospace font)
        - Type column: Single icon character (UI font)
        - Category column: Sample first 100 entries (UI font)
        
        Auto-size only runs once on initial file load. Subsequent loads
        preserve user's manual adjustments.
        
        Ref: docs/specs/features/table-column-auto-size.md §3.2
        Master: docs/SPEC.md §1
        """
        from PySide6.QtGui import QFontMetrics
        
        # Time column: Fixed format "HH:MM:SS.mmm"
        # Use monospace font for accurate width calculation
        time_font_metrics = QFontMetrics(Typography.LOG_FONT)
        time_text = "00:00:00.000"  # Representative sample (12 characters)
        time_width = time_font_metrics.horizontalAdvance(time_text)
        time_width += TIME_COLUMN_PADDING  # 4px left + 4px right
        time_width = max(time_width, TIME_COLUMN_MIN_WIDTH)  # Minimum width
        self.setColumnWidth(LogTableModel.COL_TIME, time_width)
        
        # Type column: Single icon character
        # Use UI font (icon characters are not monospace)
        type_font_metrics = QFontMetrics(Typography.UI_FONT)
        type_text = "W"  # Representative sample (widest icon character)
        type_width = type_font_metrics.horizontalAdvance(type_text)
        type_width += TYPE_COLUMN_PADDING  # 8px left + 8px right (centered icon)
        type_width = max(type_width, TYPE_COLUMN_MIN_WIDTH)  # Minimum width
        self.setColumnWidth(LogTableModel.COL_TYPE, type_width)
        
        # Category column: Sample visible entries
        # Use UI font for category text
        category_font_metrics = QFontMetrics(Typography.UI_FONT)
        max_category_width = 0
        
        # Sample first 100 visible entries (or all if fewer)
        entries = self._model.get_entries()
        sample_size = min(CATEGORY_COLUMN_SAMPLE_SIZE, len(entries))
        for i in range(sample_size):
            entry = entries[i]
            category_width = category_font_metrics.horizontalAdvance(entry.category)
            max_category_width = max(max_category_width, category_width)
        
        # Add padding
        max_category_width += CATEGORY_COLUMN_PADDING  # 4px left + 4px right
        
        # Clamp to min/max
        category_width = max(
            CATEGORY_COLUMN_MIN_WIDTH,
            min(max_category_width, CATEGORY_COLUMN_MAX_WIDTH)
        )
        self.setColumnWidth(LogTableModel.COL_CATEGORY, category_width)
        
        # Message column: No auto-size, uses Stretch mode
        # (already set in _setup_header)

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

    def get_selection_state(self) -> SelectionState:
        """Capture current selection state including current index.
        
        Returns:
            SelectionState containing file_offset values for all selected rows
            and the current entry for keyboard navigation.
        
        Performance: O(s) where s = number of selected rows.
        Thread: Main thread only (per docs/specs/global/threading.md §8.1).
        
        Ref: docs/specs/features/selection-preservation.md §5.1
        """
        entries = self.get_selected_entries()
        
        # Get current index for keyboard navigation
        current_index = self.selectionModel().currentIndex()
        current_entry = None
        if current_index.isValid():
            current_entry = self._model.get_entry(current_index.row())
        
        return SelectionState.from_entries(entries, current_entry)

    @beartype
    def restore_selection(self, state: SelectionState, skip_scroll: bool = False) -> bool:
        """Restore selection from a previous state.
        
        Args:
            state: Selection state captured before filter change.
            skip_scroll: If True, skip scrolling to selection. Use this when
                viewport position will be restored separately by restore_viewport_position().
                Defaults to False (scroll to first selected row).
            
        Returns:
            True if any selection was restored, False if all selected rows
            are now hidden.
        
        Side Effects:
            - Clears previous selection
            - Selects rows that remain visible
            - Restores current index for keyboard navigation
            - Scrolls to first selected row (if skip_scroll is False)
            - Emits selection_changed signal
        
        Performance: O(m) where m = number of new visible entries.
        Thread: Main thread only.
        
        Ref: docs/specs/features/selection-preservation.md §5.1
        Ref: docs/specs/features/selection-preservation.md §7.4 (skip_scroll for viewport)
        """
        if state.is_empty():
            self.clearSelection()
            return False
        
        # Get indices for entries that remain visible
        entries = self._model.get_entries()
        indices = state.restore_indices(entries)
        
        if not indices:
            self.clearSelection()
            return False
        
        # Build selection
        from PySide6.QtCore import QItemSelectionModel
        selection = QItemSelection()
        for row in indices:
            index = self._model.index(row, 0)
            selection.select(index, index)
        
        # Apply selection
        self.selectionModel().select(
            selection,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        
        # Restore current index for keyboard navigation
        if state.current_offset is not None:
            for row in indices:
                entry = self._model.get_entry(row)
                if entry and entry.file_offset == state.current_offset:
                    current_index = self._model.index(row, 0)
                    self.selectionModel().setCurrentIndex(
                        current_index,
                        QItemSelectionModel.NoUpdate
                    )
                    break
        
        # Scroll to current index row (if exists) or first selected row
        # Ref: docs/specs/features/selection-preservation.md §5.1
        # Ref: docs/specs/features/selection-preservation.md §7.4 (skip_scroll for viewport)
        # The viewport state is captured for the current index row (keyboard focus),
        # so we must scroll to that row for correct viewport restoration.
        # However, if skip_scroll is True, viewport restoration will handle scrolling.
        if not skip_scroll:
            if state.current_offset is not None:
                # Find the current index row in the new entries
                for row in indices:
                    entry = self._model.get_entry(row)
                    if entry and entry.file_offset == state.current_offset:
                        self.scrollTo(self._model.index(row, 0))
                        break
                else:
                    # Current index row not found in visible entries, scroll to first selected
                    self.scrollTo(self._model.index(indices[0], 0))
            else:
                # No current index, scroll to first selected row
                self.scrollTo(self._model.index(indices[0], 0))
        
        # Emit signal
        self.selection_changed.emit()
        
        return True

    def set_entries_preserve_selection(
        self, 
        entries: List[LogEntry]
    ) -> None:
        """Set entries while preserving selection for visible rows.
        
        Convenience method that combines get_selection_state(),
        set_entries(), and restore_selection().
        
        Args:
            entries: New filtered entries to display.
        
        Performance: O(n + m) where n = old entry count, m = new entry count.
        Thread: Main thread only.
        
        Ref: docs/specs/features/selection-preservation.md §5.1
        """
        state = self.get_selection_state()
        self.set_entries(entries)
        self.restore_selection(state)

    # ==================== Viewport Preservation ====================

    @beartype
    def get_viewport_state(self) -> ViewportState | None:
        """Capture current viewport position for preservation.
        
        Returns:
            ViewportState if a row is selected or has current index,
            None if no selection and no current index.
        
        Note:
            The viewport_offset can be negative (row above viewport) or
            >= viewport_height (row below viewport). This is intentional -
            the viewport position should be captured even if the row is
            scrolled out of view, so it can be restored correctly.
        
        Performance: O(1).
        Thread: Main thread only.
        
        Ref: docs/specs/features/selection-preservation.md §7.5
        """
        # Get current index (keyboard navigation position)
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            row = current_index.row()
            entry = self._model.get_entry(row)
            if entry:
                # rowViewportPosition returns viewport-relative Y position (pixels from top)
                # Can be negative (row above viewport) or >= viewport_height (row below viewport)
                viewport_y = self.rowViewportPosition(row)
                return ViewportState(
                    selected_offset=entry.file_offset,
                    viewport_offset=viewport_y,
                    row_height=self.rowHeight(row)
                )
        
        # Fall back to first selected row
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            entry = self._model.get_entry(row)
            if entry:
                # rowViewportPosition returns viewport-relative Y position (pixels from top)
                # Can be negative (row above viewport) or >= viewport_height (row below viewport)
                viewport_y = self.rowViewportPosition(row)
                return ViewportState(
                    selected_offset=entry.file_offset,
                    viewport_offset=viewport_y,
                    row_height=self.rowHeight(row)
                )
        
        return None

    @beartype
    def restore_viewport_position(self, state: ViewportState) -> bool:
        """Restore viewport position from a previous state.
        
        Args:
            state: Viewport state captured before filter change.
            
        Returns:
            True if viewport position was restored, False if row not found.
        
        Side Effects:
            - Adjusts vertical scroll bar to restore visual position
            - Does NOT change selection (selection is handled separately)
        
        Performance: O(m) where m = number of visible entries.
        Thread: Main thread only.
        
        Ref: docs/specs/features/selection-preservation.md §7.5
        """
        # Find row by file_offset
        for row in range(self._model.rowCount()):
            entry = self._model.get_entry(row)
            if entry and entry.file_offset == state.selected_offset:
                # Convert viewport offset from pixels to rows
                # viewport_offset is in pixels, row_height is in pixels
                # viewport_offset_rows is how many rows we need to scroll up
                row_height = state.row_height if state.row_height else self.rowHeight(row)
                viewport_offset_rows = state.viewport_offset / row_height
                
                # Calculate new scroll value (in rows)
                # We want the row to appear at viewport_offset from top
                # So we scroll to (row - viewport_offset_rows)
                new_scroll_value = row - viewport_offset_rows
                
                # Clamp to valid scroll range
                scroll_bar = self.verticalScrollBar()
                clamped_scroll = max(0, min(new_scroll_value, scroll_bar.maximum()))
                
                scroll_bar.setValue(int(clamped_scroll))
                
                return True
        
        return False

    def set_entries_preserve_selection_and_viewport(
        self,
        entries: List[LogEntry]
    ) -> None:
        """Set entries while preserving both selection and viewport position.
        
        Complete preservation flow:
        1. Capture selection state (selected rows + current index)
        2. Capture viewport state (visual position)
        3. Set new entries
        4. Restore selection
        5. Restore viewport position
        
        Args:
            entries: New filtered entries to display.
        
        Performance: O(n + m) where n = old entry count, m = new entry count.
        Thread: Main thread only.
        
        Ref: docs/specs/features/selection-preservation.md §7.6
        """
        # Capture states BEFORE
        selection_state = self.get_selection_state()
        viewport_state = self.get_viewport_state()
        
        # Apply new entries
        self.set_entries(entries)
        
        # Restore states AFTER
        self.restore_selection(selection_state)
        
        if viewport_state:
            self.restore_viewport_position(viewport_state)

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
        # Ref: docs/specs/global/color-palette.md §10.2.3
        self._highlight_service.set_find_pattern(text, QColor(UIColors.FIND_HIGHLIGHT), case_sensitive)
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

    def scrollTo(self, index: QModelIndex, hint: QAbstractItemView.ScrollHint = QAbstractItemView.EnsureVisible) -> None:
        """Scroll to index but only vertically.

        Override to prevent horizontal scrolling. Always keeps first column visible.

        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1

        Args:
            index: Model index to scroll to.
            hint: Scroll hint (ignored for horizontal).
        """
        # Call parent scrollTo for vertical positioning
        super().scrollTo(index, hint)

        # Reset horizontal scroll to show first column
        self.horizontalScrollBar().setValue(0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press, ensuring horizontal scroll stays at 0.

        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1

        Args:
            event: Mouse event.
        """
        super().mousePressEvent(event)
        # Reset horizontal scroll after selection
        self.horizontalScrollBar().setValue(0)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move, preventing horizontal scroll during drag.

        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1

        Args:
            event: Mouse event.
        """
        # Call parent implementation (allows vertical drag-to-scroll)
        super().mouseMoveEvent(event)

        # Reset horizontal scroll position
        self.horizontalScrollBar().setValue(0)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle wheel event, preventing horizontal scroll from trackpad.

        Ref: docs/specs/features/ui-components.md §4
        Master: docs/SPEC.md §1

        Args:
            event: Wheel event.
        """
        # Call parent implementation (allows vertical scrolling)
        super().wheelEvent(event)

        # Reset horizontal scroll
        self.horizontalScrollBar().setValue(0)

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
        
        This method provides size hints for Qt's internal layout calculations.
        The actual column widths are set by _auto_size_columns() on first load.
        
        Args:
            column: Column index.
        
        Returns:
            Size hint for the column (minimum width).
        
        Ref: docs/specs/features/table-column-auto-size.md §3.2
        Master: docs/SPEC.md §1
        """
        # Return minimum widths as size hints
        # These are used by Qt for initial layout before auto-size runs
        if column == LogTableModel.COL_TIME:
            return TIME_COLUMN_MIN_WIDTH
        elif column == LogTableModel.COL_CATEGORY:
            return CATEGORY_COLUMN_MIN_WIDTH
        elif column == LogTableModel.COL_TYPE:
            return TYPE_COLUMN_MIN_WIDTH
        elif column == LogTableModel.COL_MESSAGE:
            return MESSAGE_COLUMN_MIN_WIDTH
        return MIN_COLUMN_WIDTH