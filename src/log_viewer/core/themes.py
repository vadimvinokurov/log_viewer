"""Apple-inspired theme tokens for Log Viewer.

Design system derived from Apple HIG — fog canvas, snow cards,
ink text, and a single azure accent. No shadows; elevation by value.
"""

from __future__ import annotations

from typing import Any


# ── Light theme (Apple-inspired) ──────────────────────────────────────────────

LIGHT_THEME: dict[str, Any] = {
    "name": "light",

    # Surfaces
    "canvas":       "#f5f5f7",
    "card":         "#ffffff",
    "recessed":     "#f0f0f2",
    "log_table":    "#fafafa",
    "panel":        "#f5f5f7",
    "tab_bg":       "#e8e8ed",

    # Text
    "ink":          "#1d1d1f",
    "graphite":     "#707070",
    "slate":        "#86868b",

    # Borders & dividers
    "silver_mist":  "#e8e8ed",
    "border_focus": "#0071e3",

    # Accent (sparingly — primary CTA only)
    "azure":        "#0071e3",
    "azure_hover":  "#0077ED",

    # Semantic / destructive
    "caution":      "#b64400",
    "destructive":  "#CC3333",

    # Selection
    "selection_bg": "#0071e3",
    "selection_fg": "#ffffff",

    # Pinned row
    "pinned_bg":    "#eef4ff",

    # Scrollbar
    "scrollbar":    "#c1c1c6",

    # Level colors
    "level_colors": {
        "CRITICAL": "#CC0000",
        "ERROR":    "#CC0000",
        "WARNING":  "#8A6D00",
    },
}


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


def get_theme(name: str) -> dict[str, Any]:
    """Get theme by name. Returns light theme for unknown names."""
    if name == "dark":
        return DARK_THEME
    return LIGHT_THEME


# ── Convenience accessors ─────────────────────────────────────────────────────

def _t(key: str) -> str:
    """Get a light-theme token value by key."""
    return LIGHT_THEME[key]
