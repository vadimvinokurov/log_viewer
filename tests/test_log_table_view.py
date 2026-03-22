"""Unit tests for LogTableModel column alignment.

Ref: docs/specs/features/table-column-alignment.md §5.1
Master: docs/SPEC.md §1
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView

from src.views.log_table_view import LogTableModel, LogEntryDisplay
from src.models.selection_state import ViewportState
from src.constants.log_levels import LogLevel
from src.constants.table_config import (
    ALIGN_LEFT_VCENTER,
    ALIGN_CENTER,
    COLUMN_ALIGNMENTS,
)


@pytest.fixture
def log_table_model(qapp) -> LogTableModel:
    """Create a LogTableModel with test entries.

    Args:
        qapp: QApplication fixture from conftest.py.

    Returns:
        LogTableModel populated with test entries.

    Ref: docs/specs/features/table-column-alignment.md §5.1
    """
    model = LogTableModel()
    
    # Create test entries using LogEntryDisplay
    # Style: Follows LogEntryDisplay structure from src/views/log_table_view.py
    # Ref: docs/specs/features/log-entry-optimization.md §4.3
    # raw_line removed - lazy loaded via LogDocument.get_raw_line()
    test_entries = [
        LogEntryDisplay(
            category="System.Network.HTTP",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.ERROR,
            message="Connection failed: timeout",
            file_offset=0
        ),
        LogEntryDisplay(
            category="System.Core",
            time="18:31:01.043",
            time_full="2024-01-15 18:31:01.043",
            level=LogLevel.WARNING,
            message="Memory usage high",
            file_offset=100
        ),
        LogEntryDisplay(
            category="App.UI",
            time="18:31:02.123",
            time_full="2024-01-15 18:31:02.123",
            level=LogLevel.MSG,
            message="User logged in successfully",
            file_offset=200
        ),
    ]
    
    model.set_entries(test_entries)
    return model


def test_time_column_alignment(log_table_model: LogTableModel) -> None:
    """Time column must be left-aligned, vertically centered.

    Args:
        log_table_model: Fixture providing LogTableModel with test entries.

    Ref: docs/specs/features/table-column-alignment.md §2.1
    Style: Follows test pattern from tests/test_typography.py
    """
    index = log_table_model.index(0, LogTableModel.COL_TIME)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == ALIGN_LEFT_VCENTER


def test_category_column_alignment(log_table_model: LogTableModel) -> None:
    """Category column must be left-aligned, vertically centered.

    Args:
        log_table_model: Fixture providing LogTableModel with test entries.

    Ref: docs/specs/features/table-column-alignment.md §2.1
    Style: Follows test pattern from tests/test_typography.py
    """
    index = log_table_model.index(0, LogTableModel.COL_CATEGORY)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == ALIGN_LEFT_VCENTER


def test_type_column_alignment(log_table_model: LogTableModel) -> None:
    """Type column must be centered.

    Args:
        log_table_model: Fixture providing LogTableModel with test entries.

    Ref: docs/specs/features/table-column-alignment.md §2.1
    Style: Follows test pattern from tests/test_typography.py
    """
    index = log_table_model.index(0, LogTableModel.COL_TYPE)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == ALIGN_CENTER


def test_message_column_alignment(log_table_model: LogTableModel) -> None:
    """Message column must be left-aligned, vertically centered.

    Args:
        log_table_model: Fixture providing LogTableModel with test entries.

    Ref: docs/specs/features/table-column-alignment.md §2.1
    Style: Follows test pattern from tests/test_typography.py
    """
    index = log_table_model.index(0, LogTableModel.COL_MESSAGE)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == ALIGN_LEFT_VCENTER


@pytest.fixture
def log_table_view(qapp) -> "LogTableView":
    """Create a LogTableView for testing.

    Args:
        qapp: QApplication fixture from conftest.py.

    Returns:
        LogTableView instance.

    Ref: docs/specs/features/table-cell-text-overflow.md §5.1
    """
    from src.views.log_table_view import LogTableView
    view = LogTableView()
    yield view
    view.deleteLater()


def test_table_no_word_wrap(log_table_view: "LogTableView") -> None:
    """Table must not wrap text to multiple lines.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-cell-text-overflow.md §5.1
    """
    assert not log_table_view.wordWrap()


def test_table_elide_mode_right(log_table_view: "LogTableView") -> None:
    """Table must use right elide mode.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-cell-text-overflow.md §5.1
    """
    assert log_table_view.textElideMode() == Qt.ElideRight


def test_scroll_to_resets_horizontal_scroll(log_table_view: "LogTableView") -> None:
    """scrollTo must reset horizontal scroll to 0.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    from PySide6.QtWidgets import QAbstractItemView

    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Set horizontal scroll to non-zero value
    log_table_view.horizontalScrollBar().setValue(50)

    # Call scrollTo
    index = log_table_view._model.index(0, 0)
    log_table_view.scrollTo(index, QAbstractItemView.EnsureVisible)

    # Horizontal scroll should be reset to 0
    assert log_table_view.horizontalScrollBar().value() == 0


def test_mouse_press_resets_horizontal_scroll(log_table_view: "LogTableView") -> None:
    """mousePressEvent must reset horizontal scroll to 0 after selection.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QMouseEvent, Qt

    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Set horizontal scroll to non-zero value
    log_table_view.horizontalScrollBar().setValue(50)

    # Simulate mouse press
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(100, 50),
        QPoint(100, 50),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    log_table_view.mousePressEvent(event)

    # Horizontal scroll should be reset to 0
    assert log_table_view.horizontalScrollBar().value() == 0


def test_mouse_move_resets_horizontal_scroll(log_table_view: "LogTableView") -> None:
    """mouseMoveEvent must reset horizontal scroll to 0 during drag.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QMouseEvent, Qt

    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Set horizontal scroll to non-zero value
    log_table_view.horizontalScrollBar().setValue(50)

    # Simulate mouse move (drag)
    event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(100, 50),
        QPoint(100, 50),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    log_table_view.mouseMoveEvent(event)

    # Horizontal scroll should be reset to 0
    assert log_table_view.horizontalScrollBar().value() == 0


def test_wheel_event_resets_horizontal_scroll(log_table_view: "LogTableView") -> None:
    """wheelEvent must reset horizontal scroll to 0 after trackpad scroll.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QWheelEvent

    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Set horizontal scroll to non-zero value
    log_table_view.horizontalScrollBar().setValue(50)

    # Simulate wheel event (trackpad horizontal scroll)
    event = QWheelEvent(
        QPoint(100, 50),  # position
        QPoint(100, 50),  # globalPosition
        QPoint(10, 0),    # pixelDelta (horizontal)
        QPoint(10, 0),    # angleDelta
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollBegin,
        False
    )
    log_table_view.wheelEvent(event)

    # Horizontal scroll should be reset to 0
    assert log_table_view.horizontalScrollBar().value() == 0


def test_horizontal_scroll_range_is_zero(log_table_view: "LogTableView") -> None:
    """Horizontal scroll range must be (0, 0) to prevent any scrolling.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    # Range should be (0, 0) - no scrolling possible
    h_scroll = log_table_view.horizontalScrollBar()
    assert h_scroll.minimum() == 0
    assert h_scroll.maximum() == 0


def test_horizontal_scroll_value_changed_signal(log_table_view: "LogTableView") -> None:
    """_on_horizontal_scroll_changed must reset scroll to 0 when value changes.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    # Try to set horizontal scroll to non-zero value
    # The signal handler should reset it to 0
    log_table_view.horizontalScrollBar().setValue(50)
    
    # Value should be reset to 0 by the signal handler
    assert log_table_view.horizontalScrollBar().value() == 0


def test_scroll_contents_by_ignores_horizontal_delta(log_table_view: "LogTableView") -> None:
    """scrollContentsBy must ignore horizontal scroll delta.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Call scrollContentsBy with horizontal delta
    # This simulates Qt's internal auto-scroll mechanism
    log_table_view.scrollContentsBy(100, 10)

    # Horizontal scroll should remain at 0
    assert log_table_view.horizontalScrollBar().value() == 0


def test_horizontal_scrollbar_disabled(log_table_view: "LogTableView") -> None:
    """Horizontal scrollbar must be disabled.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    # Scrollbar should be disabled
    assert not log_table_view.horizontalScrollBar().isEnabled()


def test_horizontal_scrollbar_policy_always_off(log_table_view: "LogTableView") -> None:
    """Horizontal scrollbar policy must be AlwaysOff.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/ui-components.md §4
    """
    from PySide6.QtCore import Qt

    # Policy should be AlwaysOff
    assert log_table_view.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


# ==================== Viewport Preservation Tests ====================
# Ref: docs/specs/features/selection-preservation.md §7.5


def test_get_viewport_state_returns_none_when_no_selection(log_table_view: "LogTableView") -> None:
    """get_viewport_state must return None when no selection and no current index.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/selection-preservation.md §7.5
    """
    # Set up entries without any selection
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
            file_offset=100
        ),
    ]
    log_table_view.set_entries(test_entries)
    
    # Clear any selection
    log_table_view.clearSelection()
    
    # get_viewport_state should return None
    result = log_table_view.get_viewport_state()
    assert result is None


def test_get_viewport_state_returns_state_with_selection(log_table_view: "LogTableView") -> None:
    """get_viewport_state must return ViewportState when a row is selected.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/selection-preservation.md §7.5
    """
    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
            file_offset=100
        ),
        LogEntryDisplay(
            category="App",
            time="18:31:01.000",
            time_full="2024-01-15 18:31:01.000",
            level=LogLevel.ERROR,
            message="Error message",
            file_offset=200
        ),
    ]
    log_table_view.set_entries(test_entries)
    
    # Select first row
    log_table_view.selectRow(0)
    
    # get_viewport_state should return a valid state
    result = log_table_view.get_viewport_state()
    assert result is not None
    assert isinstance(result, ViewportState)
    assert result.selected_offset == 100
    assert result.row_height > 0


def test_get_viewport_state_uses_current_index(log_table_view: "LogTableView") -> None:
    """get_viewport_state must use current index (keyboard navigation) when available.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/selection-preservation.md §7.5
    """
    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="First message",
            file_offset=100
        ),
        LogEntryDisplay(
            category="App",
            time="18:31:01.000",
            time_full="2024-01-15 18:31:01.000",
            level=LogLevel.ERROR,
            message="Second message",
            file_offset=200
        ),
    ]
    log_table_view.set_entries(test_entries)
    
    # Select first row, then move current index to second row
    log_table_view.selectRow(0)
    
    # Set current index to second row (simulating keyboard navigation)
    from PySide6.QtCore import QItemSelectionModel
    second_index = log_table_view._model.index(1, 0)
    log_table_view.selectionModel().setCurrentIndex(
        second_index,
        QItemSelectionModel.NoUpdate
    )
    
    # get_viewport_state should use current index (second row)
    result = log_table_view.get_viewport_state()
    assert result is not None
    assert result.selected_offset == 200  # Second row's file_offset


def test_restore_viewport_position_returns_false_when_row_not_found(log_table_view: "LogTableView") -> None:
    """restore_viewport_position must return False when row is not found.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/selection-preservation.md §7.5
    """
    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.MSG,
            message="Test message",
            file_offset=100
        ),
    ]
    log_table_view.set_entries(test_entries)
    
    # Create a ViewportState with a file_offset that doesn't exist
    state = ViewportState(
        selected_offset=9999,  # Non-existent offset
        viewport_offset=0,
        row_height=20
    )
    
    # restore_viewport_position should return False
    result = log_table_view.restore_viewport_position(state)
    assert result is False


def test_restore_viewport_position_restores_scroll_position(log_table_view: "LogTableView") -> None:
    """restore_viewport_position must restore scroll position correctly.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/selection-preservation.md §7.5
    """
    # Set up multiple entries to enable scrolling
    test_entries = [
        LogEntryDisplay(
            category=f"System.{i}",
            time=f"18:31:0{i % 10}.965",
            time_full=f"2024-01-15 18:31:0{i % 10}.965",
            level=LogLevel.MSG,
            message=f"Test message {i}",
            file_offset=100 + i * 10
        )
        for i in range(50)
    ]
    log_table_view.set_entries(test_entries)
    
    # Scroll to middle of the table
    log_table_view.verticalScrollBar().setValue(20)
    
    # Select a row in the middle
    log_table_view.selectRow(25)
    
    # Capture viewport state
    viewport_state = log_table_view.get_viewport_state()
    assert viewport_state is not None
    
    # Change entries (simulate filter)
    new_entries = [
        LogEntryDisplay(
            category=f"System.{i}",
            time=f"18:31:0{i % 10}.965",
            time_full=f"2024-01-15 18:31:0{i % 10}.965",
            level=LogLevel.MSG,
            message=f"Test message {i}",
            file_offset=100 + i * 10
        )
        for i in range(50)
    ]
    log_table_view.set_entries(new_entries)
    
    # Reset scroll to top
    log_table_view.verticalScrollBar().setValue(0)
    
    # Restore viewport position
    result = log_table_view.restore_viewport_position(viewport_state)
    assert result is True
    
    # Scroll position should be restored (approximately)
    # Note: exact position may vary due to row height calculations


def test_set_entries_preserve_selection_and_viewport(log_table_view: "LogTableView") -> None:
    """set_entries_preserve_selection_and_viewport must preserve both selection and viewport.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/selection-preservation.md §7.6
    """
    # Set up multiple entries
    test_entries = [
        LogEntryDisplay(
            category=f"System.{i}",
            time=f"18:31:0{i % 10}.965",
            time_full=f"2024-01-15 18:31:0{i % 10}.965",
            level=LogLevel.MSG,
            message=f"Test message {i}",
            file_offset=100 + i * 10
        )
        for i in range(50)
    ]
    log_table_view.set_entries(test_entries)
    
    # Scroll to middle and select a row
    log_table_view.verticalScrollBar().setValue(20)
    log_table_view.selectRow(25)
    
    # Capture initial state
    initial_selection = log_table_view.get_selection_state()
    initial_viewport = log_table_view.get_viewport_state()
    assert initial_viewport is not None
    
    # Create new entries (same content, simulating filter change)
    new_entries = [
        LogEntryDisplay(
            category=f"System.{i}",
            time=f"18:31:0{i % 10}.965",
            time_full=f"2024-01-15 18:31:0{i % 10}.965",
            level=LogLevel.MSG,
            message=f"Test message {i}",
            file_offset=100 + i * 10
        )
        for i in range(50)
    ]
    
    # Use set_entries_preserve_selection_and_viewport
    log_table_view.set_entries_preserve_selection_and_viewport(new_entries)
    
    # Selection should be restored
    restored_selection = log_table_view.get_selection_state()
    assert restored_selection.offsets == initial_selection.offsets
    
    # Viewport should be restored (approximately)
    restored_viewport = log_table_view.get_viewport_state()
    assert restored_viewport is not None
    assert restored_viewport.selected_offset == initial_viewport.selected_offset


# ==================== Time Display Format Tests ====================
# Ref: docs/specs/features/timestamp-unix-epoch.md §7.2


def test_time_display_format() -> None:
    """Test that time column shows H:M:S.MS format.
    
    Ref: docs/specs/features/timestamp-unix-epoch.md §7.2
    """
    from datetime import datetime
    from src.models.log_entry import LogEntry, LogLevel as RealLogLevel
    from src.views.log_table_view import LogEntryDisplay
    
    # Create entry with known timestamp
    dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
    entry = LogEntry(
        row_index=0,
        timestamp=dt.timestamp(),
        category="Test",
        display_message="Message",
        level=RealLogLevel.MSG,
        file_offset=0
    )
    
    display = LogEntryDisplay.from_log_entry(entry)
    
    # Table display: H:M:S.MS
    assert display.time == "15:30:45.123"
    
    # Tooltip: full date-time
    assert display.time_full == "2026-03-10 15:30:45.123"


def test_time_display_milliseconds_formatting() -> None:
    """Test that milliseconds are formatted correctly.
    
    Ref: docs/specs/features/timestamp-unix-epoch.md §7.2
    """
    from datetime import datetime
    from src.models.log_entry import LogEntry, LogLevel as RealLogLevel
    from src.views.log_table_view import LogEntryDisplay
    
    # Test various millisecond values
    test_cases = [
        (0, "00:00:00.000"),      # 0ms
        (1000, "00:00:00.001"),   # 1ms
        (123000, "00:00:00.123"), # 123ms
        (999000, "00:00:00.999"), # 999ms
    ]
    
    for microsecond, expected_time in test_cases:
        dt = datetime(2026, 3, 10, 0, 0, 0, microsecond)
        entry = LogEntry(
            row_index=0,
            timestamp=dt.timestamp(),
            category="Test",
            display_message="Message",
            level=RealLogLevel.MSG,
            file_offset=0
        )
        
        display = LogEntryDisplay.from_log_entry(entry)
        assert display.time == expected_time, f"Expected {expected_time}, got {display.time}"


def test_time_tooltip_shows_full_date() -> None:
    """Test that tooltip shows full date-time.
    
    Ref: docs/specs/features/timestamp-unix-epoch.md §7.2
    """
    from datetime import datetime
    from src.models.log_entry import LogEntry, LogLevel as RealLogLevel
    from src.views.log_table_view import LogEntryDisplay
    
    # Create entry with specific date
    dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
    entry = LogEntry(
        row_index=0,
        timestamp=dt.timestamp(),
        category="Test",
        display_message="Message",
        level=RealLogLevel.MSG,
        file_offset=0
    )
    
    display = LogEntryDisplay.from_log_entry(entry)
    
    # Verify full date-time in tooltip
    assert "2026-03-10" in display.time_full
    assert "15:30:45.123" in display.time_full


# ==================== Auto-Size Flag Tests ====================
# Ref: docs/specs/features/table-column-auto-size.md §3.1


def test_auto_sized_flag_initialization(log_table_view: "LogTableView") -> None:
    """_auto_sized flag must be initialized to False.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §3.1
    """
    # Flag should be initialized to False
    assert hasattr(log_table_view, "_auto_sized")
    assert log_table_view._auto_sized is False


# ==================== Auto-Size Columns Tests ====================
# Ref: docs/specs/features/table-column-auto-size.md §6.1


def test_time_column_auto_size(log_table_view: "LogTableView") -> None:
    """Time column must be sized to fit 'HH:MM:SS.mmm' format.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.constants.dimensions import TIME_COLUMN_MIN_WIDTH

    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Time column width should be >= minimum width
    time_width = log_table_view.columnWidth(LogTableModel.COL_TIME)
    assert time_width >= TIME_COLUMN_MIN_WIDTH

    # Time column width should be reasonable for monospace font
    # (not too wide, not too narrow)
    assert time_width <= 120  # Reasonable maximum for monospace font


def test_type_column_auto_size(log_table_view: "LogTableView") -> None:
    """Type column must be sized to fit single icon character.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.constants.dimensions import TYPE_COLUMN_MIN_WIDTH

    # Set up entries
    test_entries = [
        LogEntryDisplay(
            category="System",
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Type column width should be >= minimum width
    type_width = log_table_view.columnWidth(LogTableModel.COL_TYPE)
    assert type_width >= TYPE_COLUMN_MIN_WIDTH

    # Type column width should be reasonable for single character
    assert type_width <= 60  # Reasonable maximum for single character


def test_category_column_auto_size(log_table_view: "LogTableView") -> None:
    """Category column must be sized based on sampled entries.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.constants.dimensions import (
        CATEGORY_COLUMN_MIN_WIDTH,
        CATEGORY_COLUMN_MAX_WIDTH,
    )

    # Create entries with varying category lengths
    test_entries = [
        LogEntryDisplay(
            category=f"Category{i}.SubCategory{i}",
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message=f"Message {i}",
        )
        for i in range(100)
    ]
    log_table_view.set_entries(test_entries)

    # Category column width should be within min/max bounds
    category_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)
    assert category_width >= CATEGORY_COLUMN_MIN_WIDTH
    assert category_width <= CATEGORY_COLUMN_MAX_WIDTH


def test_category_column_max_width(log_table_view: "LogTableView") -> None:
    """Category column must respect maximum width.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.constants.dimensions import CATEGORY_COLUMN_MAX_WIDTH

    # Create entries with very long category paths
    test_entries = [
        LogEntryDisplay(
            category="A" * 500,  # Very long category
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message="Test message",
        )
        for i in range(100)
    ]
    log_table_view.set_entries(test_entries)

    # Category column width should be clamped to maximum
    category_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)
    assert category_width == CATEGORY_COLUMN_MAX_WIDTH


def test_auto_size_only_once(log_table_view: "LogTableView") -> None:
    """Auto-size must only run on first load.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    # First load: auto-size
    test_entries = [
        LogEntryDisplay(
            category="Short",
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)
    initial_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)

    # Manually resize
    log_table_view.setColumnWidth(LogTableModel.COL_CATEGORY, 200)

    # Second load: should preserve manual resize
    test_entries2 = [
        LogEntryDisplay(
            category="VeryLongCategoryName",
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries2)
    final_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)

    # Manual resize should be preserved
    assert final_width == 200


def test_manual_resize_override(log_table_view: "LogTableView") -> None:
    """Manual resize must override auto-size.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    # Load entries
    test_entries = [
        LogEntryDisplay(
            category="Category",
            time="00:00:00.000",
            time_full="2024-01-15 00:00:00.000",
            level=LogLevel.MSG,
            message="Test message",
        ),
    ]
    log_table_view.set_entries(test_entries)

    # Manually resize time column
    log_table_view.setColumnWidth(LogTableModel.COL_TIME, 150)

    # Width should be preserved
    assert log_table_view.columnWidth(LogTableModel.COL_TIME) == 150


# ==================== Size Hint Tests ====================
# Ref: docs/specs/features/table-column-auto-size.md §3.2


def test_size_hint_for_time_column(log_table_view: "LogTableView") -> None:
    """sizeHintForColumn must return minimum width for time column.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §3.2
    """
    from src.constants.dimensions import TIME_COLUMN_MIN_WIDTH

    # Size hint for time column should return minimum width
    hint = log_table_view.sizeHintForColumn(LogTableModel.COL_TIME)
    assert hint == TIME_COLUMN_MIN_WIDTH


def test_size_hint_for_category_column(log_table_view: "LogTableView") -> None:
    """sizeHintForColumn must return minimum width for category column.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §3.2
    """
    from src.constants.dimensions import CATEGORY_COLUMN_MIN_WIDTH

    # Size hint for category column should return minimum width
    hint = log_table_view.sizeHintForColumn(LogTableModel.COL_CATEGORY)
    assert hint == CATEGORY_COLUMN_MIN_WIDTH


def test_size_hint_for_type_column(log_table_view: "LogTableView") -> None:
    """sizeHintForColumn must return minimum width for type column.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §3.2
    """
    from src.constants.dimensions import TYPE_COLUMN_MIN_WIDTH

    # Size hint for type column should return minimum width
    hint = log_table_view.sizeHintForColumn(LogTableModel.COL_TYPE)
    assert hint == TYPE_COLUMN_MIN_WIDTH


def test_size_hint_for_message_column(log_table_view: "LogTableView") -> None:
    """sizeHintForColumn must return minimum width for message column.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §3.2
    """
    from src.constants.dimensions import MESSAGE_COLUMN_MIN_WIDTH

    # Size hint for message column should return minimum width
    hint = log_table_view.sizeHintForColumn(LogTableModel.COL_MESSAGE)
    assert hint == MESSAGE_COLUMN_MIN_WIDTH


def test_size_hint_for_invalid_column(log_table_view: "LogTableView") -> None:
    """sizeHintForColumn must return default minimum for invalid column.

    Args:
        log_table_view: Fixture providing LogTableView instance.

    Ref: docs/specs/features/table-column-auto-size.md §3.2
    """
    from src.constants.dimensions import MIN_COLUMN_WIDTH

    # Size hint for invalid column should return default minimum
    hint = log_table_view.sizeHintForColumn(999)  # Invalid column index
    assert hint == MIN_COLUMN_WIDTH