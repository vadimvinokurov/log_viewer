"""Tests for LogTableModel and LogTableView."""

import pytest

from PySide6.QtCore import Qt

from log_viewer.core.models import LogLine, LogLevel
from log_viewer.gui.log_table import LogTableModel


@pytest.fixture
def sample_lines():
    return [
        LogLine(1, "2026-01-01T12:30:01", "app/api", LogLevel.INFO, "GET /api/users 200", 0, 10),
        LogLine(2, "2026-01-01T12:30:02", "app/api", LogLevel.ERROR, "POST /api/login 401", 11, 20),
        LogLine(3, "2026-01-01T12:30:03", "app/db", LogLevel.DEBUG, "Connection pool: 5/10", 31, 30),
    ]


@pytest.fixture
def model(sample_lines):
    return LogTableModel(sample_lines)


def test_model_row_count(model, sample_lines):
    assert model.rowCount() == len(sample_lines)


def test_model_column_count(model):
    assert model.columnCount() == 4


def test_model_header_data(model):
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Line"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Time"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Category"
    assert model.headerData(3, Qt.Orientation.Horizontal) == "Message"


def test_model_data_line_number(model):
    assert model.data(model.index(0, 0)) == "1"


def test_model_data_time(model):
    assert model.data(model.index(0, 1)) == "12:30:01"


def test_model_data_category(model):
    assert model.data(model.index(0, 2)) == "app/api"


def test_model_data_message(model):
    assert model.data(model.index(0, 3)) == "GET /api/users 200"


def test_model_data_error_row_has_foreground(model):
    fg = model.data(model.index(1, 3), Qt.ItemDataRole.ForegroundRole)
    assert fg is not None


def test_model_update_lines(model):
    new = [LogLine(10, "2026-01-01T13:00:00", "sys", LogLevel.INFO, "CPU: 45%", 40, 15)]
    model.update_lines(new)
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == "10"


def test_pinned_row_has_background(model):
    model.set_pinned_line_numbers({1})
    bg = model.data(model.index(0, 0), Qt.ItemDataRole.BackgroundRole)
    assert bg is not None


def test_non_pinned_row_has_no_background(model):
    model.set_pinned_line_numbers({2})
    bg = model.data(model.index(0, 0), Qt.ItemDataRole.BackgroundRole)
    assert bg is None


def test_update_lines_same_skips_reset(model):
    """update_lines with identical content should not trigger a model reset."""
    counter = [0]
    original_reset = model.beginResetModel

    def counting_reset() -> None:
        counter[0] += 1
        original_reset()

    model.beginResetModel = counting_reset

    # Pass same content (different list, same LogLine objects) — should skip
    same_lines = list(model.lines)
    model.update_lines(same_lines)
    assert counter[0] == 0

    # Pass same object again — should also skip
    model.update_lines(same_lines)
    assert counter[0] == 0

    # Different content — should reset
    new = [LogLine(10, "2026-01-01T13:00:00", "sys", LogLevel.INFO, "CPU: 45%", 40, 15)]
    model.update_lines(new)
    assert counter[0] == 1


def test_update_lines_different_triggers_reset(model):
    """update_lines with different lines should trigger a model reset."""
    counter = [0]
    original_reset = model.beginResetModel

    def counting_reset() -> None:
        counter[0] += 1
        original_reset()

    model.beginResetModel = counting_reset

    new = [LogLine(10, "2026-01-01T13:00:00", "sys", LogLevel.INFO, "CPU: 45%", 40, 15)]
    model.update_lines(new)
    assert counter[0] == 1
