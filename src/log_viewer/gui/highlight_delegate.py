"""Delegate that renders character-level highlight backgrounds."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem, QStyledItemDelegate, QStyle

from log_viewer.core.filter_engine import find_spans
from log_viewer.core.themes import _t

_BASE_BG = QColor(_t("log_table"))


class HighlightDelegate(QStyledItemDelegate):
    """Paints colored rectangles behind matched highlight spans."""

    def __init__(self) -> None:
        super().__init__()
        self._span_cache: dict[tuple[str, str, str, bool], list[tuple[int, int]]] = {}
        self._cache_version: int = 0
        self._highlights_version: int = -1

    def _get_spans(
        self, text: str, pattern: str, mode: str, case_sensitive: bool, hl_sig: int
    ) -> list[tuple[int, int]]:
        """Get cached spans or compute and cache them."""
        if hl_sig != self._highlights_version:
            self._span_cache.clear()
            self._highlights_version = hl_sig

        key = (text, pattern, mode, case_sensitive)
        if key not in self._span_cache:
            self._span_cache[key] = find_spans(text, pattern, mode, case_sensitive)
        return self._span_cache[key]

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        self.initStyleOption(option, index)
        painter.save()

        # 1. Default background (selection, pinned, or base)
        if option.state & QStyle.StateFlag.State_Selected:
            bg = option.palette.color(option.palette.ColorRole.Highlight)
        else:
            bg_data = index.data(Qt.ItemDataRole.BackgroundRole)
            bg = bg_data if isinstance(bg_data, QColor) else _BASE_BG
        painter.fillRect(option.rect, bg)

        # 2. Cell text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            painter.restore()
            return

        # 3. Highlight spans
        model = index.model()
        highlights = model.highlights() if hasattr(model, "highlights") else []

        if highlights:
            # Version tracks highlight changes for cache invalidation
            hl_sig = hash(frozenset((h.pattern, h.mode.value, h.case_sensitive, h.color) for h in highlights))
            metrics = QFontMetrics(option.font)
            painter.setClipRect(option.rect)
            for hl in highlights:
                spans = self._get_spans(text, hl.pattern, hl.mode, hl.case_sensitive, hl_sig)
                color = QColor(hl.color)
                color.setAlpha(60)
                for start, end in spans:
                    px_start = metrics.horizontalAdvance(text[:start])
                    px_end = metrics.horizontalAdvance(text[:end])
                    rect = QRect(
                        option.rect.x() + px_start,
                        option.rect.y(),
                        px_end - px_start,
                        option.rect.height(),
                    )
                    painter.fillRect(rect, color)

        # 4. Text on top
        painter.setFont(option.font)
        if option.state & QStyle.StateFlag.State_Selected:
            fg = option.palette.color(option.palette.ColorRole.HighlightedText)
        else:
            fg_data = index.data(Qt.ItemDataRole.ForegroundRole)
            fg = (
                fg_data
                if isinstance(fg_data, QColor)
                else option.palette.color(option.palette.ColorRole.Text)
            )
        painter.setPen(fg)
        painter.drawText(option.rect, Qt.AlignmentFlag.AlignVCenter, text)

        painter.restore()
