"""Highlight list widget for the GUI log viewer."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.models import Highlight, SearchMode
from log_viewer.core.themes import _t
from log_viewer.gui.scroll_utils import install_hover_scrollbar

_MODE_PREFIX: dict[SearchMode, str] = {
    SearchMode.PLAIN: ":h",
    SearchMode.REGEX: ":hr",
    SearchMode.SIMPLE: ":hs",
}


_ITEM_STYLE = f"""
QLabel {{
    color: {_t('ink')};
    font-size: 12px;
}}
QLabel[disabled="true"] {{
    color: {_t('slate')};
}}
QPushButton {{
    background-color: transparent;
    border: none;
    color: {_t('slate')};
    font-size: 11px;
    padding: 0px;
    border-radius: 4px;
}}
QPushButton:hover {{
    color: {_t('destructive')};
    background-color: {_t('recessed')};
}}
"""


class HighlightItemWidget(QWidget):
    """Single highlight row: checkbox + color dot + label + delete button."""

    def __init__(
        self,
        index: int,
        highlight: Highlight,
        on_toggle: int,
        on_delete: int,
        on_color_change: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(10)

        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state: on_toggle(index, bool(state)))
        layout.addWidget(checkbox)

        # Color dot (clickable)
        self._color_hex = highlight.color
        self._dot = QPushButton()
        self._dot.setFixedSize(12, 12)
        self._dot.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dot.setStyleSheet(
            f"border-radius: 6px; background-color: {self._color_hex}; border: none;"
        )
        self._dot.clicked.connect(lambda: self._pick_color(index, on_color_change))
        layout.addWidget(self._dot)

        # Command text
        mode_prefix = _MODE_PREFIX.get(highlight.mode, ":h")
        full_text = f"{mode_prefix} {highlight.pattern}"
        label = QLabel(full_text)
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        label.setToolTip(full_text)
        layout.addWidget(label, stretch=1)

        delete_btn = QPushButton("\u2715")
        delete_btn.setFixedSize(18, 18)
        delete_btn.clicked.connect(lambda: on_delete(index))
        layout.addWidget(delete_btn)

        self.setStyleSheet(_ITEM_STYLE)

    def _pick_color(self, index: int, on_color_change: int) -> None:
        initial = QColor(self._color_hex)
        color = QColorDialog.getColor(initial, self, "Select Highlight Color")
        if color.isValid():
            self._color_hex = color.name()
            self._dot.setStyleSheet(
                f"border-radius: 6px; background-color: {self._color_hex}; border: none;"
            )
            on_color_change(index, self._color_hex)


class HighlightListWidget(QWidget):
    """Scrollable list of highlight items."""

    highlight_changed = Signal()
    highlight_color_changed = Signal(int, str)
    highlight_removed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._highlights: list[Highlight] = []
        self._enabled: list[bool] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            f"""
            QScrollArea {{
                border: none;
                background-color: {_t('panel')};
            }}
            """
        )

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        install_hover_scrollbar(self._scroll)
        outer.addWidget(self._scroll)

    def set_highlights(self, highlights: list[Highlight], enabled: list[bool] | None = None) -> None:
        self._highlights = list(highlights)
        self._enabled = list(enabled) if enabled else [True] * len(highlights)
        self._rebuild()

    def toggle_highlight(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled
        item = self._container_layout.itemAt(index)
        if item and item.widget():
            label = item.widget().findChild(QLabel)
            if label:
                label.setProperty("disabled", not enabled)
                label.style().unpolish(label)
                label.style().polish(label)
        self.highlight_changed.emit()

    def remove_highlight(self, index: int) -> None:
        del self._highlights[index]
        del self._enabled[index]
        self._rebuild()
        self.highlight_removed.emit(index)

    def change_color(self, index: int, color_hex: str) -> None:
        self._highlights[index].color = color_hex
        self.highlight_color_changed.emit(index, color_hex)

    def get_active_highlights(self) -> list[Highlight]:
        return [h for h, e in zip(self._highlights, self._enabled) if e]

    def count(self) -> int:
        return len(self._highlights)

    def _rebuild(self) -> None:
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, hl in enumerate(self._highlights):
            w = HighlightItemWidget(
                index=i,
                highlight=hl,
                on_toggle=self.toggle_highlight,
                on_delete=self.remove_highlight,
                on_color_change=self.change_color,
            )
            if not self._enabled[i]:
                checkbox = w.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
                label = w.findChild(QLabel)
                if label:
                    label.setProperty("disabled", True)
                    label.style().unpolish(label)
                    label.style().polish(label)
            self._container_layout.insertWidget(self._container_layout.count() - 1, w)
