"""Theme tokens for Log Viewer.

Color palette from the LogViewer Plugin UI/UX Design Specification.
Gray-scale surfaces, warm-brown text, and blue accent for selections.
"""

from __future__ import annotations

from typing import Any


THEME: dict[str, Any] = {
    "name": "light",

    # Surfaces (Gray palette from spec)
    "canvas":       "#E7E7E7",   # Gray5 — main background
    "card":         "#F5F5F5",   # between Gray4/Gray5 — raised surfaces
    "recessed":     "#D6D6D6",   # Gray4 — hover / recessed areas
    "log_table":    "#E7E7E7",   # Gray5 — log list background
    "panel":        "#E7E7E7",   # Gray5 — side panel background
    "tab_bg":       "#D6D6D6",   # Gray4 — inactive tab / input background

    # Text
    "ink":          "#382F27",   # LogItemTextMouseOver — primary text
    "graphite":     "#8491A3",   # BorderMouseOver — secondary text
    "slate":        "#8491A3",   # BorderMouseOver — muted / placeholder text

    # Borders & dividers
    "silver_mist":  "#D6D6D6",   # Gray4 — border color
    "border_focus": "#0078D7",   # ContainerPanelHighlighted — focus ring

    # Accent
    "azure":        "#0078D7",   # ContainerPanelHighlighted
    "azure_hover":  "#2587CF",   # AutoScrollToEndMouseOver

    # Semantic / destructive
    "caution":      "#6A5302",   # Warning color from spec
    "destructive":  "#781111",   # Error color from spec

    # Selection (log item selected state)
    "selection_bg": "#B7CFD5",   # LogItemSelected — light teal selection
    "selection_fg": "#382F27",   # Keep text color unchanged on selection

    # Pinned row
    "pinned_bg":    "#B7CFD5",   # LogItemSelected

    # Level colors (from spec §2.1.2)
    "level_colors": {
        "CRITICAL": "#781111",
        "ERROR":    "#781111",
        "WARNING":  "#6A5302",
        "INFO":     "#382F27",
        "DEBUG":    "#382F27",
        "TRACE":    "#5E8C5E",
    },
}


# ── Convenience accessor ──────────────────────────────────────────────────────

def _t(key: str) -> str:
    """Get a theme token value by key."""
    return THEME[key]
