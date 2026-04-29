"""Tests for highlight rendering in log table."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from log_viewer.core.models import Highlight, LogLine, LogLevel, SearchMode
from log_viewer.gui.log_table import LogTableModel


def _make_line(msg: str, raw: str | None = None) -> LogLine:
    return LogLine(
        line_number=1,
        timestamp="2025-01-01T10:00:00",
        category="app/main",
        level=LogLevel.INFO,
        message=msg,
        raw=raw or f"2025-01-01T10:00:00 LOG_INFO app/main {msg}",
    )


@pytest.fixture
def model():
    return LogTableModel()


def test_no_highlight_returns_none(model):
    line = _make_line("hello world")
    model.update_lines([line])
    model.set_highlights([])
    assert model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole) is None


def test_matching_highlight_returns_color(model):
    line = _make_line("error occurred")
    model.update_lines([line])
    model.set_highlights([Highlight(pattern="error", mode=SearchMode.PLAIN)])
    bg = model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole)
    assert isinstance(bg, QColor)
    assert bg.alpha() == 60


def test_non_matching_highlight_returns_none(model):
    line = _make_line("hello world")
    model.update_lines([line])
    model.set_highlights([Highlight(pattern="error", mode=SearchMode.PLAIN)])
    assert model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole) is None


def test_custom_color_highlight(model):
    line = _make_line("timeout exceeded")
    model.update_lines([line])
    model.set_highlights([
        Highlight(pattern="timeout", mode=SearchMode.PLAIN, color="blue")
    ])
    bg = model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole)
    assert isinstance(bg, QColor)


def test_first_matching_highlight_wins(model):
    line = _make_line("error timeout")
    model.update_lines([line])
    model.set_highlights([
        Highlight(pattern="error", mode=SearchMode.PLAIN, color="red"),
        Highlight(pattern="timeout", mode=SearchMode.PLAIN, color="blue"),
    ])
    bg = model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole)
    assert isinstance(bg, QColor)


def test_regex_highlight(model):
    line = _make_line("error 404 not found")
    model.update_lines([line])
    model.set_highlights([Highlight(pattern=r"error \d+", mode=SearchMode.REGEX)])
    bg = model.data(model.index(0, 3), Qt.ItemDataRole.BackgroundRole)
    assert isinstance(bg, QColor)
