"""Pinned lines list widget for the side panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.models import LogLine

from log_viewer.gui.styles import LIST_SCROLL_AREA, PINNED_LIST_ITEM, styles


class PinnedItemWidget(QWidget):
    """Single pinned line row: line number + message preview + delete button."""

    def __init__(
        self,
        index: int,
        line_number: int,
        message: str,
        on_delete: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(10)

        num_label = QLabel(f"#{line_number}")
        num_label.setFixedWidth(40)
        layout.addWidget(num_label)

        msg_label = QLabel(message[:80])
        msg_label.setMinimumWidth(0)
        msg_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        msg_label.setToolTip(message)
        layout.addWidget(msg_label, stretch=1)

        delete_btn = QPushButton("\u2715")
        delete_btn.setFixedSize(18, 18)
        delete_btn.clicked.connect(lambda: on_delete(index))
        layout.addWidget(delete_btn)

        styles.apply(self, PINNED_LIST_ITEM)


class PinnedListWidget(QWidget):
    """Scrollable list of pinned line items."""

    pin_removed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_numbers: list[int] = []

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

    def set_pins(self, line_numbers: list[int], lines: dict[int, LogLine]) -> None:
        """Update display with current pinned lines.

        Args:
            line_numbers: 1-based line numbers that are pinned.
            lines: Dict mapping line_number to LogLine for message preview.
        """
        self._line_numbers = list(line_numbers)
        self._rebuild(lines)

    def remove_pin(self, index: int) -> None:
        """Remove a pinned line by display index."""
        line_number = self._line_numbers.pop(index)
        self._rebuild_from_lines()
        self.pin_removed.emit(line_number)

    def count(self) -> int:
        return len(self._line_numbers)

    def _rebuild(self, lines: dict[int, LogLine]) -> None:
        self._clear_items()
        for i, ln in enumerate(self._line_numbers):
            line = lines.get(ln)
            msg = line.message if line else "(line not found)"
            w = PinnedItemWidget(
                index=i,
                line_number=ln,
                message=msg,
                on_delete=self._on_delete,
            )
            self._container_layout.insertWidget(self._container_layout.count() - 1, w)

    def _rebuild_from_lines(self) -> None:
        """Rebuild without line data — uses stored line numbers only."""
        self._clear_items()
        for i, ln in enumerate(self._line_numbers):
            w = PinnedItemWidget(
                index=i,
                line_number=ln,
                message="",
                on_delete=self._on_delete,
            )
            self._container_layout.insertWidget(self._container_layout.count() - 1, w)

    def _on_delete(self, index: int) -> None:
        self.remove_pin(index)

    def _clear_items(self) -> None:
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
