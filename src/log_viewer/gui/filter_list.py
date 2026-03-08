"""Filter list widget for the GUI log viewer."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.models import Filter, SearchMode
from log_viewer.core.themes import _t
from log_viewer.gui.scroll_utils import install_hover_scrollbar

_MODE_PREFIX: dict[SearchMode, str] = {
    SearchMode.PLAIN: ":f",
    SearchMode.REGEX: ":fr",
    SearchMode.SIMPLE: ":fs",
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


class FilterItemWidget(QWidget):
    """Single filter row: checkbox + label + delete button."""

    def __init__(
        self,
        index: int,
        filt: Filter,
        on_toggle: int,
        on_delete: int,
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

        prefix = _MODE_PREFIX[filt.mode]
        label = QLabel(f"{prefix} {filt.pattern}")
        layout.addWidget(label, stretch=1)

        delete_btn = QPushButton("\u2715")
        delete_btn.setFixedSize(18, 18)
        delete_btn.clicked.connect(lambda: on_delete(index))
        layout.addWidget(delete_btn)

        self.setStyleSheet(_ITEM_STYLE)


class FilterListWidget(QWidget):
    """Scrollable list of filter items."""

    filter_changed = Signal()
    filter_removed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filters: list[Filter] = []
        self._enabled: list[bool] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
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

    def set_filters(self, filters: list[Filter], enabled: list[bool] | None = None) -> None:
        self._filters = list(filters)
        self._enabled = list(enabled) if enabled else [True] * len(filters)
        self._rebuild()

    def toggle_filter(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled
        item = self._container_layout.itemAt(index)
        if item and item.widget():
            label = item.widget().findChild(QLabel)
            if label:
                label.setProperty("disabled", not enabled)
                label.style().unpolish(label)
                label.style().polish(label)
        self.filter_changed.emit()

    def remove_filter(self, index: int) -> None:
        del self._filters[index]
        del self._enabled[index]
        self._rebuild()
        self.filter_removed.emit(index)

    def get_active_filters(self) -> list[Filter]:
        return [f for f, e in zip(self._filters, self._enabled) if e]

    def count(self) -> int:
        return len(self._filters)

    def _rebuild(self) -> None:
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, filt in enumerate(self._filters):
            w = FilterItemWidget(
                index=i,
                filt=filt,
                on_toggle=self.toggle_filter,
                on_delete=self.remove_filter,
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
