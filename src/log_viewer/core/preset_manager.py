"""Preset manager for Log Viewer — save/load filter+highlight+category combos."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from log_viewer.core.config import ConfigManager


def _serialize_filter(f: Any) -> dict[str, Any]:
    if isinstance(f, dict):
        return f
    return {"pattern": f.pattern, "mode": f.mode.value, "case_sensitive": f.case_sensitive}


def _serialize_highlight(h: Any) -> dict[str, Any]:
    if isinstance(h, dict):
        return h
    return {
        "pattern": h.pattern,
        "mode": h.mode.value,
        "case_sensitive": h.case_sensitive,
        "color": h.color,
    }


class PresetManager:
    """Save/load/delete presets as YAML files in the presets directory."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config

    def _presets_dir(self) -> Path:
        d = self._config.presets_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _preset_path(self, name: str) -> Path:
        return self._presets_dir() / f"{name}.yaml"

    def exists(self, name: str) -> bool:
        return self._preset_path(name).exists()

    def save(self, name: str, state: dict) -> None:
        """Save current store state (filters, highlights, disabled_categories) to YAML."""
        data: dict[str, Any] = {
            "filters": [_serialize_filter(f) for f in state.get("filters", [])],
            "highlights": [_serialize_highlight(h) for h in state.get("highlights", [])],
            "disabled_categories": list(state.get("disabled_categories", [])),
        }
        self._preset_path(name).write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    def load(self, name: str) -> dict[str, Any]:
        """Load a preset by name. Raises FileNotFoundError if missing."""
        path = self._preset_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return {
            "filters": raw.get("filters", []),
            "highlights": raw.get("highlights", []),
            "disabled_categories": raw.get("disabled_categories", []),
        }

    def delete(self, name: str) -> None:
        """Delete a preset. Raises FileNotFoundError if missing."""
        path = self._preset_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found")
        path.unlink()

    def list_presets(self) -> list[str]:
        """List all preset names (without .yaml extension)."""
        d = self._presets_dir()
        return sorted(p.stem for p in d.glob("*.yaml"))
