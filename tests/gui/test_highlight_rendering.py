"""Tests for highlight rendering in log table."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from log_viewer.core.models import Highlight, LogLine, LogLevel, SearchMode
from log_viewer.gui.log_table import LogTableModel


def _make_line(msg: str, raw: str | None = None) -> LogLine:
    return LogLine(
        line_number=1,
        timestamp="2025-01-01T10:00:00",
        category="app/main",
        level=LogLevel.INFO,
        message=msg,
        file_offset=0,
        line_length=0,
    )


@pytest.fixture
def model():
    return LogTableModel()


def test_highlights_accessor(model):
    hl = Highlight(pattern="error", mode=SearchMode.PLAIN)
    model.set_highlights([hl])
    assert model.highlights() == [hl]


def test_background_role_returns_none_with_highlights(model):
    """BackgroundRole no longer handles highlights (delegate does)."""
    line = _make_line("error occurred")
    model.update_lines([line])
    model.set_highlights([Highlight(pattern="error", mode=SearchMode.PLAIN)])
    assert model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole) is None


def test_background_role_returns_none_without_highlights(model):
    line = _make_line("hello world")
    model.update_lines([line])
    model.set_highlights([])
    assert model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole) is None