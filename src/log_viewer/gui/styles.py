"""Central style definitions for Log Viewer.

All QSS stylesheets live here. Widgets import and apply them at init time.
Theme tokens come from core/themes.py; this module provides template-based
QSS that gets resolved against the current theme.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from log_viewer.core.themes import _t
from log_viewer.core.typography import Typography


def _resolve(template: str) -> str:
    """Replace {{token}} placeholders with theme values."""
    import re

    # Virtual tokens not in LIGHT_THEME — resolved from Typography
    _VIRTUAL = {
        "font_primary": Typography.PRIMARY,
        "font_mono": Typography.MONOSPACE,
    }

    def _sub(m):
        key = m.group(1)
        if key in _VIRTUAL:
            return _VIRTUAL[key]
        return _t(key)

    return re.sub(r'\{\{(\w+)\}\}', _sub, template)


# ── Widget type stylesheets (templates with {{token}} placeholders) ──────────

APP_BASE = """
* {
    font-family: {{font_primary}};
}
QTableView {
    font-family: {{font_mono}};
}
"""

LOG_TABLE = """
QTableView {
    background-color: {{log_table}};
    alternate-background-color: {{card}};
}
"""

LOG_TABLE_HEADER = """
QHeaderView::section {
    background-color: {{log_table}};
    color: {{graphite}};
    padding: 0px 8px;
    border: none;
    border-bottom: 1px solid {{silver_mist}};
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
"""

SIDE_PANEL = """
QTabWidget::pane {
    border: none;
    background-color: {{panel}};
}
QTabBar::tab {
    background-color: {{tab_bg}};
    color: {{graphite}};
    padding: 6px 14px;
    border: none;
    border-radius: 8px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: {{card}};
    color: {{ink}};
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background-color: {{silver_mist}};
    color: {{ink}};
}
"""

CATEGORY_TREE = """
QTreeWidget {
    background-color: {{panel}};
    border: none;
    outline: none;
}
QTreeWidget::item {
    outline: none;
}
QTreeWidget::item:selected {
    background-color: transparent;
    color: {{ink}};
}
"""

CATEGORY_TOGGLE_BTN = """
QPushButton {
    background-color: {{tab_bg}};
    border: none;
    border-radius: 8px;
    color: {{ink}};
    font-size: 12px;
}
QPushButton:hover {
    background-color: {{silver_mist}};
}
"""

CATEGORY_SEARCH = """
QLineEdit {
    background-color: {{tab_bg}};
    border: none;
    border-radius: 8px;
    padding: 5px 10px;
    color: {{ink}};
    font-size: 12px;
}
QLineEdit:focus {
    background-color: {{card}};
    border: 1px solid {{border_focus}};
}
"""

LIST_ITEM = """
QLabel {
    color: {{ink}};
    font-size: 12px;
}
QLabel[disabled="true"] {
    color: {{slate}};
}
QPushButton {
    background-color: transparent;
    border: none;
    color: {{slate}};
    font-size: 11px;
    padding: 0px;
    border-radius: 4px;
}
QPushButton:hover {
    color: {{destructive}};
    background-color: {{recessed}};
}
"""

PINNED_LIST_ITEM = """
QLabel {
    color: {{ink}};
    font-size: 12px;
}
QPushButton {
    background-color: transparent;
    border: none;
    color: {{slate}};
    font-size: 11px;
    padding: 0px;
    border-radius: 4px;
}
QPushButton:hover {
    color: {{destructive}};
    background-color: {{recessed}};
}
"""

LIST_SCROLL_AREA = """
QScrollArea {
    border: none;
    background-color: {{panel}};
}
"""

BOTTOM_BAR = """
BottomBar {
    background-color: {{canvas}};
    border-top: 1px solid {{silver_mist}};
}
QLineEdit {
    color: {{ink}};
    background-color: {{card}};
    border: 1px solid {{silver_mist}};
    border-radius: 8px;
    padding: 3px 10px;
    selection-background-color: {{selection_bg}};
    selection-color: {{selection_fg}};
    font-size: 12px;
}
QLineEdit:focus {
    border-color: {{border_focus}};
}
"""

LEVEL_BUTTON_ACTIVE = """
LevelButton {{ color: {color}; background: transparent;
    border: none; border-radius: 6px; padding: 2px 6px; font-size: 12px; }}
LevelButton:hover {{ background: {recessed}; }}
"""

LEVEL_BUTTON_INACTIVE = """
LevelButton {{ color: {slate}; background: transparent;
    border: none; border-radius: 6px; padding: 2px 6px; font-size: 12px; }}
LevelButton:hover {{ background: {recessed}; }}
"""

ACTION_BUTTON = """
_ActionButton {{ color: {ink}; background: transparent;
    border: none; border-radius: 6px; padding: 2px 8px; font-size: 12px; }}
_ActionButton:hover {{ background: {recessed}; }}
"""

EMPTY_LABEL = "color: {{slate}}; font-size: 15px; letter-spacing: -0.01em;"

COLOR_DOT = "border-radius: 6px; background-color: {color}; border: none;"


# ── StyleEngine ──────────────────────────────────────────────────────────────

class StyleEngine:
    """Resolves QSS templates against the current theme and applies them."""

    def resolve(self, template: str) -> str:
        """Resolve {{token}} placeholders in a template string."""
        return _resolve(template)

    def apply(self, widget: QWidget, template: str) -> None:
        """Resolve template and apply as stylesheet on widget."""
        widget.setStyleSheet(self.resolve(template))

    def level_button_active(self, color: str) -> str:
        """Return active level button QSS with the given level color."""
        return LEVEL_BUTTON_ACTIVE.format(
            color=color, recessed=_t("recessed"),
        )

    def level_button_inactive(self) -> str:
        """Return inactive level button QSS."""
        return LEVEL_BUTTON_INACTIVE.format(
            slate=_t("slate"), recessed=_t("recessed"),
        )

    def action_button(self) -> str:
        """Return action button QSS."""
        return ACTION_BUTTON.format(
            ink=_t("ink"), recessed=_t("recessed"),
        )

    def color_dot(self, color_hex: str) -> str:
        """Return color dot QSS with the given color."""
        return COLOR_DOT.format(color=color_hex)


# Module-level singleton
styles = StyleEngine()
