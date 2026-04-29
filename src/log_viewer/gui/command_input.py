"""Command input with Tab autocomplete cycling."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit


class CommandInput(QLineEdit):
    """QLineEdit with Tab-autocomplete cycling and Enter/Escape handling."""

    command_submitted = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setPlaceholderText(":type command...")
        self._suggestions: list[str] = []
        self._suggestion_index: int = 0

    def set_suggestions(self, suggestions: list[str]) -> None:
        self._suggestions = suggestions
        self._suggestion_index = 0

    def _apply_suggestion(self) -> None:
        if not self._suggestions:
            return
        self.setText(self._suggestions[self._suggestion_index])
        self._suggestion_index = (self._suggestion_index + 1) % len(self._suggestions)

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

        if key == Qt.Key.Key_Tab:
            self._apply_suggestion()
            return

        if key == Qt.Key.Key_Escape:
            self.clear()
            return

        # Reset suggestion index on regular typing so Tab starts from first match
        self._suggestion_index = 0
        super().keyPressEvent(event)
