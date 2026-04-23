"""Vim-style command bar widget."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class CommandBar(QWidget):
    command_submitted = Signal(str, str)  # text (without prefix), prefix
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._prefix: str = ":"
        self._history: list[str] = []
        self._history_index: int = -1
        self._visible: bool = False
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)

        self._prefix_label = QLabel(":")
        self._prefix_label.setFixedWidth(12)
        self._prefix_label.setStyleSheet("color: #aaaaaa; font-family: monospace;")

        self._input = QLineEdit()
        self._input.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #ffffff; "
            "border: none; font-family: monospace; padding: 2px; }"
        )
        self._input.returnPressed.connect(self._on_return)
        self._input.installEventFilter(self)

        layout.addWidget(self._prefix_label)
        layout.addWidget(self._input)

    def activate(self, prefix: str) -> None:
        self._prefix = prefix
        self._prefix_label.setText(prefix)
        self._input.clear()
        self._history_index = -1
        self._visible = True
        self.show()
        self._input.setFocus()

    def deactivate(self) -> None:
        self._visible = False
        self._input.clear()
        self.hide()

    def is_active(self) -> bool:
        return self._visible

    def eventFilter(self, obj: object, event: QKeyEvent) -> bool:
        if obj is not self._input:
            return False
        if event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.deactivate()
                self.cancelled.emit()
                return True
            elif key == Qt.Key_Up:
                self._navigate_history(-1)
                return True
            elif key == Qt.Key_Down:
                self._navigate_history(1)
                return True
        return False

    def _on_return(self) -> None:
        text = self._input.text()
        if not text:
            self.deactivate()
            self.cancelled.emit()
            return
        full_command = f"{self._prefix}{text}"
        self._add_to_history(full_command)
        self.command_submitted.emit(text, self._prefix)
        self.deactivate()

    def _navigate_history(self, direction: int) -> None:
        if not self._history:
            return
        self._history_index += direction
        if self._history_index < 0:
            self._history_index = 0
        elif self._history_index >= len(self._history):
            self._history_index = len(self._history) - 1
            self._input.clear()
            return
        entry = self._history[-(self._history_index + 1)]
        if entry and entry[0] in (":", "/", "?"):
            self._input.setText(entry[1:])
        else:
            self._input.setText(entry)

    def _add_to_history(self, full_command: str) -> None:
        self._history.append(full_command)
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def show_error(self, message: str) -> None:
        self._input.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #ff4444; "
            "border: none; font-family: monospace; padding: 2px; }"
        )
        self._input.setText(f"Error: {message}")
