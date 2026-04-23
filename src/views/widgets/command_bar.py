"""Command bar logic — input handling, history, parsing signals.

The actual UI lives in MainStatusBar. This class owns the QLineEdit,
prefix label, and all command-related logic (history, events).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLabel, QLineEdit

HISTORY_DIR = Path.home() / ".logviewer"
HISTORY_FILE = HISTORY_DIR / "history.json"
DEFAULT_HISTORY_SIZE = 100

# Style matching the status bar (24px height, same bg)
_INPUT_STYLE = (
    "QLineEdit { background: transparent; color: #333333; "
    "border: none; padding: 0 4px; }"
)
_INPUT_STYLE_ERROR = (
    "QLineEdit { background: transparent; color: #cc0000; "
    "border: none; padding: 0 4px; }"
)
_PREFIX_STYLE = "color: #666666; padding: 0 2px 0 6px; font-weight: bold;"


class CommandBar:
    """Command bar logic: input widget, prefix label, history, events.

    Created by MainStatusBar, which owns the actual widgets and Qt signals.
    """

    def __init__(self) -> None:
        self._prefix: str = ":"
        self._history: list[str] = []
        self._max_history: int = DEFAULT_HISTORY_SIZE
        self._history_index: int = -1
        self._visible: bool = False
        self._on_submitted: Callable[[str, str], None] | None = None
        self._on_cancelled: Callable[[], None] | None = None
        self._load_history()
        self._create_widgets()

    def _create_widgets(self) -> None:
        self._prefix_label = QLabel(":")
        self._prefix_label.setStyleSheet(_PREFIX_STYLE)

        self._input = QLineEdit()
        self._input.setStyleSheet(_INPUT_STYLE)
        self._input.setPlaceholderText("")
        self._input.returnPressed.connect(self._on_return)

    def set_callbacks(
        self,
        on_submitted: Callable[[str, str], None],
        on_cancelled: Callable[[], None],
    ) -> None:
        """Set callbacks for command submission and cancellation."""
        self._on_submitted = on_submitted
        self._on_cancelled = on_cancelled

    @property
    def prefix_label(self) -> QLabel:
        return self._prefix_label

    @property
    def input(self) -> QLineEdit:
        return self._input

    def activate(self, prefix: str) -> None:
        self._prefix = prefix
        self._prefix_label.setText(prefix)
        self._input.clear()
        self._input.setStyleSheet(_INPUT_STYLE)
        self._history_index = -1
        self._visible = True
        self._input.setFocus()

    def deactivate(self) -> None:
        self._visible = False
        self._input.clear()
        self._input.setStyleSheet(_INPUT_STYLE)

    def is_active(self) -> bool:
        return self._visible

    def eventFilter(self, obj: object, event: QKeyEvent) -> bool:
        if obj is not self._input:
            return False
        if event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.deactivate()
                if self._on_cancelled:
                    self._on_cancelled()
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
            if self._on_cancelled:
                self._on_cancelled()
            return
        full_command = f"{self._prefix}{text}"
        self._add_to_history(full_command)
        if self._on_submitted:
            self._on_submitted(text, self._prefix)
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
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        self._save_history()

    def _load_history(self) -> None:
        try:
            if HISTORY_FILE.exists():
                data = json.loads(HISTORY_FILE.read_text())
                if isinstance(data, dict):
                    commands = data.get("commands", [])
                elif isinstance(data, list):
                    commands = data
                else:
                    commands = []
                self._history = commands[-self._max_history:]
        except (json.JSONDecodeError, OSError):
            self._history = []

    def _save_history(self) -> None:
        try:
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            HISTORY_FILE.write_text(
                json.dumps({"commands": self._history[-self._max_history:]})
            )
        except OSError:
            pass

    def set_max_history(self, size: int) -> None:
        self._max_history = size

    def show_error(self, message: str) -> None:
        self._input.setStyleSheet(_INPUT_STYLE_ERROR)
        self._input.setText(f"Error: {message}")
