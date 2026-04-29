"""Filter list widget for the GUI log viewer."""

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

from log_viewer.core.models import Filter, SearchMode

_MODE_PREFIX: dict[SearchMode, str] = {
    SearchMode.PLAIN: ":f",
    SearchMode.REGEX: ":fr",
    SearchMode.SIMPLE: ":fs",
}


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
        layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state: on_toggle(index, bool(state)))
        layout.addWidget(checkbox)

        prefix = _MODE_PREFIX[filt.mode]
        label = QLabel(f"{prefix} {filt.pattern}")
        label.setFont(label.font())  # inherit for now; set monospace below
        font = label.font()
        font.setFamily("Monospace")
        label.setFont(font)
        layout.addWidget(label)

        delete_btn = QPushButton("\u2715")
        delete_btn.setFlat(True)
        delete_btn.setFixedWidth(20)
        delete_btn.clicked.connect(lambda: on_delete(index))
        layout.addWidget(delete_btn)


class FilterListWidget(QWidget):
    """Scrollable list of filter items."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filters: list[Filter] = []
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

    def set_filters(self, filters: list[Filter]) -> None:
        self._filters = list(filters)
        self._enabled = [True] * len(filters)
        self._rebuild()

    def toggle_filter(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled
        # Update visual: grey out the label when disabled
        item = self._container_layout.itemAt(index)
        if item and item.widget():
            label = item.widget().findChild(QLabel)
            if label:
                if enabled:
                    label.setStyleSheet("")
                else:
                    label.setStyleSheet("color: gray;")

    def remove_filter(self, index: int) -> None:
        del self._filters[index]
        del self._enabled[index]
        self._rebuild()

    def get_active_filters(self) -> list[Filter]:
        return [f for f, e in zip(self._filters, self._enabled) if e]

    def count(self) -> int:
        return len(self._filters)

    def _rebuild(self) -> None:
        # Remove all items except the trailing stretch
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Insert new items before the stretch (which is now at index 0)
        for i, filt in enumerate(self._filters):
            w = FilterItemWidget(
                index=i,
                filt=filt,
                on_toggle=self.toggle_filter,
                on_delete=self.remove_filter,
            )
            self._container_layout.insertWidget(self._container_layout.count() - 1, w)
