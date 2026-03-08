"""Hover-to-show scrollbar behavior for scroll areas."""

from __future__ import annotations

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QAbstractScrollArea

from log_viewer.core.themes import _t


class HoverScrollBarFilter(QObject):
    """Event filter that shows scrollbars when hovering over the scroll area."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if event.type() == QEvent.Type.Enter:
            self._set_hovered(obj, True)
        elif event.type() == QEvent.Type.Leave:
            self._set_hovered(obj, False)
        return False

    @staticmethod
    def _set_hovered(widget: QObject, hovered: bool) -> None:
        scroll_area = widget if isinstance(widget, QAbstractScrollArea) else None
        if scroll_area is None:
            return
        for sb in (scroll_area.verticalScrollBar(), scroll_area.horizontalScrollBar()):
            if sb:
                sb.setProperty("_area_hovered", hovered)
                sb.style().unpolish(sb)
                sb.style().polish(sb)


_SCROLLBAR_QSS = f"""
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border: none;
    margin: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: transparent;
    min-height: 30px;
    border-radius: 4px;
    margin: 1px;
}}
QScrollBar::handle:horizontal {{
    background: transparent;
    min-width: 30px;
    border-radius: 4px;
    margin: 1px;
}}
QScrollBar[_area_hovered="true"]::handle:vertical,
QScrollBar[_area_hovered="true"]::handle:horizontal {{
    background: {_t('scrollbar')};
}}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {{
    background: {_t('ink')};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
"""


def install_hover_scrollbar(widget: QAbstractScrollArea) -> None:
    """Install hover-show scrollbar behavior and append overlay QSS."""
    widget.installEventFilter(HoverScrollBarFilter(widget))
    existing = widget.styleSheet()
    widget.setStyleSheet(existing + _SCROLLBAR_QSS)
