"""Command input bar with Enter/Escape handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit

if TYPE_CHECKING:
    from log_viewer.core.command_history import CommandHistory


class CommandInput(QLineEdit):
    """QLineEdit with Enter/Escape handling and history navigation."""

    command_submitted = Signal(str)
    editing_finished = Signal()

    def __init__(self, history: Optional[CommandHistory] = None) -> None:
        super().__init__()
        self.setPlaceholderText(":type command...")
        self._history = history

    def keyPressEvent(self, event: object) -> None:  # type: ignore[override]
        from PySide6.QtGui import QKeyEvent

        assert isinstance(event, QKeyEvent)
        key = event.key()

        if key == Qt.Key.Key_Return:
            text = self.text()
            if text:
                if self._history:
                    self._history.add(text)
                self.command_submitted.emit(text)
                self.clear()
                self.editing_finished.emit()
            return

        if key == Qt.Key.Key_Escape:
            self.clear()
            self.editing_finished.emit()
            return

        if key == Qt.Key.Key_Up:
            if self._history:
                self.setText(self._history.navigate_up())
            return

        if key == Qt.Key.Key_Down:
            if self._history:
                self.setText(self._history.navigate_down())
            return

        super().keyPressEvent(event)
