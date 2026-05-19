"""Configuration manager for Log Viewer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


_DEFAULTS: dict[str, Any] = {
    "history_size": 100,
    "default_categories_enabled": True,
    "last_open_dir": "",
}


class ConfigManager:
    """Load/save ~/.logviewer/settings.json with sensible defaults."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._dir = config_dir or Path.home() / ".logviewer"
        self.config: dict[str, Any] = {}

    @property
    def config_path(self) -> Path:
        return self._dir / "settings.json"

    @property
    def history_path(self) -> Path:
        return self._dir / "history.json"

    def load(self) -> dict[str, Any]:
        """Load config from disk, creating with defaults if absent."""
        self._dir.mkdir(parents=True, exist_ok=True)

        if self.config_path.exists():
            raw = self.config_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        else:
            data = {}

        # Merge: stored values override defaults
        self.config = {**_DEFAULTS, **data}

        if not self.config_path.exists():
            self.save()

        return self.config

    def save(self) -> None:
        """Persist current config to disk."""
        self._dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value (in-memory only — call save() to persist)."""
        self.config[key] = value
