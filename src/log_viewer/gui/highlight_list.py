"""Highlight list widget for the GUI log viewer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.models import Highlight, SearchMode

_MODE_PREFIX: dict[SearchMode, str] = {
    SearchMode.PLAIN: ":h",
    SearchMode.REGEX: ":hr",
    SearchMode.SIMPLE: ":hs",
}

_COLOR_MAP: dict[str, str] = {
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "blue": "#89b4fa",
    "magenta": "#cba6f7",
    "cyan": "#94e2d5",
}


class HighlightItemWidget(QWidget):
    """Single highlight row: checkbox + color dot + label + delete button."""

    def __init__(
        self,
        index: int,
        highlight: Highlight,
        on_toggle: int,
        on_delete: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state: on_toggle(index, bool(state)))
        layout.addWidget(checkbox)

        # Color dot
        color_hex = _COLOR_MAP.get(highlight.color, "#f38ba8")
        dot = QLabel()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(
            f"border-radius: 7px; background-color: {color_hex};"
        )
        layout.addWidget(dot)

        # Command text
        if highlight.color != "red":
            text = f":h/color={highlight.color}/{highlight.pattern}"
        else:
            text = f":h {highlight.pattern}"
        label = QLabel(text)
        font = label.font()
        font.setFamily("Monospace")
        label.setFont(font)
        layout.addWidget(label)

        delete_btn = QPushButton("\u2715")
        delete_btn.setFlat(True)
        delete_btn.setFixedWidth(20)
        delete_btn.clicked.connect(lambda: on_delete(index))
        layout.addWidget(delete_btn)


class HighlightListWidget(QWidget):
    """Scrollable list of highlight items."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._highlights: list[Highlight] = []
        self._enabled: list[bool] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self._highlights = list(highlights)
        self._enabled = [True] * len(highlights)
        self._rebuild()

    def toggle_highlight(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled
        item = self._container_layout.itemAt(index)
        if item and item.widget():
            label = item.widget().findChild(QLabel)
            if label:
                if enabled:
                    label.setStyleSheet("")
                else:
                    label.setStyleSheet("color: gray;")

    def remove_highlight(self, index: int) -> None:
        del self._highlights[index]
        del self._enabled[index]
        self._rebuild()

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
            )
            self._container_layout.insertWidget(self._container_layout.count() - 1, w)
