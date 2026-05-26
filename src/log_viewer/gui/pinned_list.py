"""Pinned rules list widget for the side panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.models import Filter, SearchMode

from log_viewer.gui.styles import LIST_ITEM, LIST_SCROLL_AREA, styles

_MODE_PREFIX: dict[SearchMode, str] = {
    SearchMode.PLAIN: ":p",
    SearchMode.REGEX: ":pr",
    SearchMode.SIMPLE: ":ps",
    SearchMode.LINE_NUMBER: ":pn",
}


class PinItemWidget(QWidget):
    """Single pin rule row: checkbox + label + delete button."""

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
        full_text = f"{prefix} {filt.pattern}"
        label = QLabel(full_text)
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        label.setToolTip(full_text)
        layout.addWidget(label, stretch=1)

        delete_btn = QPushButton("\u2715")
        delete_btn.setFixedSize(18, 18)
        delete_btn.clicked.connect(lambda: on_delete(index))
        layout.addWidget(delete_btn)

        styles.apply(self, LIST_ITEM)


class PinnedListWidget(QWidget):
    """Scrollable list of pin rule items."""

    pin_changed = Signal()
    pin_removed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rules: list[Filter] = []
        self._enabled: list[bool] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        styles.apply(self._scroll, LIST_SCROLL_AREA)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    def set_pins(self, rules: list[Filter], enabled: list[bool] | None = None) -> None:
        self._rules = list(rules)
        self._enabled = list(enabled) if enabled else [True] * len(rules)
        self._rebuild()

    def toggle_pin(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled
        item = self._container_layout.itemAt(index)
        if item and item.widget():
            label = item.widget().findChild(QLabel)
            if label:
                label.setProperty("disabled", not enabled)
                label.style().unpolish(label)
                label.style().polish(label)
        self.pin_changed.emit()

    def remove_pin(self, index: int) -> None:
        del self._rules[index]
        del self._enabled[index]
        self._rebuild()
        self.pin_removed.emit(index)

    def count(self) -> int:
        return len(self._rules)

    def _rebuild(self) -> None:
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, filt in enumerate(self._rules):
            w = PinItemWidget(
                index=i,
                filt=filt,
                on_toggle=self.toggle_pin,
                on_delete=self.remove_pin,
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
