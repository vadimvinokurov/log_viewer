"""Theme definitions for Log Viewer."""

from __future__ import annotations

from typing import Any


DARK_THEME: dict[str, Any] = {
    "name": "dark",
    "background": "#1E1E1E",
    "foreground": "#D4D4D4",
    "level_colors": {
        "CRITICAL": "bold red",
        "ERROR": "red",
        "WARNING": "yellow",
        "INFO": "white",
        "DEBUG": "cyan",
        "TRACE": "dim",
    },
}

LIGHT_THEME: dict[str, Any] = {
    "name": "light",
    "background": "#FFFFFF",
    "foreground": "#1E1E1E",
    "level_colors": {
        "CRITICAL": "bold red",
        "ERROR": "red",
        "WARNING": "dark_orange",
        "INFO": "black",
        "DEBUG": "dark_cyan",
        "TRACE": "grey37",
    },
}


def get_theme(name: str) -> dict[str, Any]:
    """Get theme by name. Returns dark theme for unknown names."""
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME
