"""Command history with persistence and navigation."""

from __future__ import annotations

import json
from typing import Optional

from log_viewer.core.config import ConfigManager


class CommandHistory:
    """Persist command history to ~/.logviewer/history.json with up/down navigation."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self.commands: list[str] = []
        self._position: int = 0
        self._load()

    def _load(self) -> None:
        """Load history from disk."""
        path = self._config.history_path
        if path.exists():
            try:
                self.commands = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                self.commands = []
        self._position = len(self.commands)

    def _save(self) -> None:
        """Persist history to disk."""
        self._config.history_path.parent.mkdir(parents=True, exist_ok=True)
        self._config.history_path.write_text(
            json.dumps(self.commands, ensure_ascii=False), encoding="utf-8"
        )

    def add(self, command: str) -> None:
        """Add a command, removing consecutive duplicates and trimming to max size."""
        if not command.strip():
            return
        if self.commands and self.commands[-1] == command:
            return
        self.commands.append(command)
        max_size = self._config.get("history_size", 100)
        if len(self.commands) > max_size:
            self.commands = self.commands[-max_size:]
        self._position = len(self.commands)
        self._save()

    def navigate_up(self) -> str:
        """Navigate to previous command. Returns empty string at top."""
        if not self.commands:
            return ""
        if self._position > 0:
            self._position -= 1
        return self.commands[self._position]

    def navigate_down(self) -> str:
        """Navigate to next command. Returns empty string at bottom."""
        if not self.commands:
            return ""
        if self._position < len(self.commands) - 1:
            self._position += 1
            return self.commands[self._position]
        self._position = len(self.commands)
        return ""
