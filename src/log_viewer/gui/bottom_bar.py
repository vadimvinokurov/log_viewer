"""Bottom bar with command input and status display."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from log_viewer.gui.command_input import CommandInput


class BottomBar(QWidget):
    """Horizontal bar: command input (left) + status label (right)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.command_input = CommandInput()
        layout.addWidget(self.command_input, stretch=1)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_label)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def activate_command_mode(self) -> None:
        self.command_input.setText(":")
        self.command_input.setFocus()
        self.command_input.setCursorPosition(1)
