"""Unit tests for LogTableModel column alignment.

Ref: docs/specs/features/table-column-alignment.md §5.1
Master: docs/SPEC.md §1
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from src.views.log_table_view import LogTableModel, LogEntryDisplay
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
    test_entries = [
        LogEntryDisplay(
            category="System.Network.HTTP",
            time="18:31:00.965",
            level=LogLevel.ERROR,
            message="Connection failed: timeout",
            raw_line="25-02-2026T18:31:00.965 System.Network.HTTP LOG_ERROR Connection failed: timeout"
        ),
        LogEntryDisplay(
            category="System.Core",
            time="18:31:01.043",
            level=LogLevel.WARNING,
            message="Memory usage high",
            raw_line="25-02-2026T18:31:01.043 System.Core LOG_WARNING Memory usage high"
        ),
        LogEntryDisplay(
            category="App.UI",
            time="18:31:02.123",
            level=LogLevel.MSG,
            message="User logged in successfully",
            raw_line="25-02-2026T18:31:02.123 App.UI User logged in successfully"
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
            level=LogLevel.MSG,
            message="Test message",
            raw_line="test line"
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
            level=LogLevel.MSG,
            message="Test message",
            raw_line="test line"
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
            level=LogLevel.MSG,
            message="Test message",
            raw_line="test line"
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
            level=LogLevel.MSG,
            message="Test message",
            raw_line="test line"
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
            level=LogLevel.MSG,
            message="Test message",
            raw_line="test line"
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