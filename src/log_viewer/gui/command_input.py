"""Command input bar with Enter/Escape handling."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit


class CommandInput(QLineEdit):
    """QLineEdit with Enter/Escape handling."""

    command_submitted = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setPlaceholderText(":type command...")

    def keyPressEvent(self, event: object) -> None:  # type: ignore[override]
        from PySide6.QtGui import QKeyEvent

        assert isinstance(event, QKeyEvent)
        key = event.key()

        if key == Qt.Key.Key_Return:
            text = self.text()
            if text:
                self.command_submitted.emit(text)
                self.clear()
            return

        if key == Qt.Key.Key_Escape:
            self.clear()
            return

        super().keyPressEvent(event)
