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