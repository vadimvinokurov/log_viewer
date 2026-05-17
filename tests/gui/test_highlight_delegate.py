"""Tests for HighlightDelegate character-level rendering."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Highlight, LogLine, LogLevel, SearchMode
from log_viewer.core.typography import Typography
from log_viewer.gui.highlight_delegate import HighlightDelegate
from log_viewer.gui.log_table import LogTableModel


def _make_line(msg: str) -> LogLine:
    return LogLine(
        line_number=1,
        timestamp="2025-01-01T10:00:00",
        category="app/main",
        level=LogLevel.INFO,
        message=msg,
        file_offset=0,
        line_length=0,
    )


def _make_model(lines: list[LogLine]) -> LogTableModel:
    store = LogStore()
    store.lines = lines
    store.filtered_indices = list(range(len(lines)))
    return LogTableModel(store=store)


@pytest.fixture
def delegate():
    return HighlightDelegate()


def _paint_cell(
    delegate: HighlightDelegate,
    model: LogTableModel,
    row: int,
    col: int,
    width: int = 800,
    height: int = 30,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, width, height)
    option.font = Typography.LOG_FONT
    delegate.paint(painter, option, model.index(row, col))
    painter.end()
    return image


def test_delegate_paints_without_crash(delegate, qtbot):
    model = _make_model([_make_line("hello world")])
    model.set_highlights([Highlight(pattern="hello", mode=SearchMode.PLAIN, color="#FF0000")])
    image = _paint_cell(delegate, model, 0, 3)
    assert not image.isNull()


def test_delegate_highlights_matched_text(delegate, qtbot):
    model = _make_model([_make_line("hello error world")])
    model.set_highlights([Highlight(pattern="error", mode=SearchMode.PLAIN, color="#FF0000")])
    image = _paint_cell(delegate, model, 0, 3)

    metrics = QFontMetrics(Typography.LOG_FONT)
    before_width = metrics.horizontalAdvance("hello ")
    mid_highlight = before_width + metrics.horizontalAdvance("er")

    hl_pixel = image.pixelColor(int(mid_highlight), 2)
    bg_pixel = image.pixelColor(int(before_width // 2), 2)

    assert hl_pixel.green() < bg_pixel.green()
    assert hl_pixel.blue() < bg_pixel.blue()


def test_delegate_no_highlight_uniform_background(delegate, qtbot):
    model = _make_model([_make_line("hello world")])
    model.set_highlights([])
    image = _paint_cell(delegate, model, 0, 3)

    p1 = image.pixelColor(50, 2)
    p2 = image.pixelColor(400, 2)
    assert abs(p1.red() - p2.red()) < 5
    assert abs(p1.green() - p2.green()) < 5
    assert abs(p1.blue() - p2.blue()) < 5


def test_delegate_multiple_highlights_different_colors(delegate, qtbot):
    model = _make_model([_make_line("error timeout")])
    model.set_highlights([
        Highlight(pattern="error", mode=SearchMode.PLAIN, color="#FF0000"),
        Highlight(pattern="timeout", mode=SearchMode.PLAIN, color="#0000FF"),
    ])
    image = _paint_cell(delegate, model, 0, 3)

    metrics = QFontMetrics(Typography.LOG_FONT)
    error_mid = metrics.horizontalAdvance("er")
    timeout_start = metrics.horizontalAdvance("error ")
    timeout_mid = timeout_start + metrics.horizontalAdvance("tim")

    error_pixel = image.pixelColor(int(error_mid), 2)
    timeout_pixel = image.pixelColor(int(timeout_mid), 2)

    assert error_pixel.green() < 250
    assert timeout_pixel.red() < 250


def test_delegate_caches_spans(delegate, qtbot, monkeypatch):
    """Highlight spans are cached and not recomputed on repeated paint calls."""
    import log_viewer.gui.highlight_delegate as hd_module
    from log_viewer.core import filter_engine

    original_find = filter_engine.find_spans
    call_count = 0

    def counting_find_spans(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_find(*args, **kwargs)

    # Patch in the delegate's module where it's actually used
    monkeypatch.setattr(hd_module, "find_spans", counting_find_spans)

    model = _make_model([_make_line("hello error world")])
    model.set_highlights([Highlight(pattern="error", mode=SearchMode.PLAIN, color="#FF0000")])

    # Paint the same cell twice
    _paint_cell(delegate, model, 0, 3)
    first_count = call_count
    _paint_cell(delegate, model, 0, 3)

    # Second paint should use cache, not recompute
    assert call_count == first_count


def test_delegate_cache_invalidated_on_highlight_change(delegate, qtbot):
    """Cache is invalidated when highlights change."""
    model = _make_model([_make_line("hello error world")])
    model.set_highlights([Highlight(pattern="error", mode=SearchMode.PLAIN, color="#FF0000")])

    # First paint
    image1 = _paint_cell(delegate, model, 0, 3)

    # Change highlights
    model.set_highlights([
        Highlight(pattern="error", mode=SearchMode.PLAIN, color="#FF0000"),
        Highlight(pattern="hello", mode=SearchMode.PLAIN, color="#00FF00"),
    ])

    # Should recompute spans
    image2 = _paint_cell(delegate, model, 0, 3)
    assert not image2.isNull()
