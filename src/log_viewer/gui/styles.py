"""Central style definitions for Log Viewer.

All QSS stylesheets live here. Widgets import and apply them at init time.
Theme tokens come from core/themes.py; this module provides template-based
QSS that gets resolved against the current theme.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle, QWidget

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
"""

LOG_TABLE = """
QTableView {
    background-color: {{log_table}};
    alternate-background-color: {{card}};
    selection-background-color: {{selection_bg}};
    selection-color: {{selection_fg}};
}
"""

LOG_TABLE_HEADER = """
QHeaderView::section {
    background-color: {{log_table}};
    color: {{ink}};
    padding: 0px 8px;
    border: none;
    border-bottom: 1px solid {{silver_mist}};
    font-weight: bold;
    font-size: 11px;
}
"""

SIDE_PANEL = """
QTabWidget::pane {
    border: none;
    background-color: {{panel}};
}
QTabBar::tab {
    background-color: {{tab_bg}};
    color: {{ink}};
    padding: 6px 14px;
    border: none;
    border-radius: 8px;
    margin-right: 2px;
    font-weight: bold;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: {{card}};
    color: {{ink}};
    font-weight: bold;
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


# ── Cross-platform checkbox style ───────────────────────────────────────────

class AppProxyStyle(QProxyStyle):
    """Application proxy style for cross-platform visual customisations.

    Delegates to the platform's default style and overrides only specific
    primitives (e.g. checkbox drawing).
    """

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_IndicatorCheckBox:
            self._draw_checkbox(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    @staticmethod
    def _draw_checkbox(option, painter):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(option.rect)
        size = min(rect.width(), rect.height(), 16.0)
        x = rect.x() + (rect.width() - size) / 2
        y = rect.y() + (rect.height() - size) / 2
        box = QRectF(x, y, size, size)

        state = option.state
        checked = bool(state & QStyle.StateFlag.State_On)
        partial = bool(state & QStyle.StateFlag.State_NoChange)
        enabled = bool(state & QStyle.StateFlag.State_Enabled)
        hover = bool(state & QStyle.StateFlag.State_MouseOver)
        pressed = bool(state & QStyle.StateFlag.State_Sunken)

        radius = 4.0

        if checked or partial:
            bg = QColor("#b0b0b5") if not enabled else (
                QColor("#2587CF") if pressed else QColor("#0078D7")
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(box, radius, radius)

            pen = QPen(QColor("#ffffff"))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setWidthF(2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if checked:
                path = QPainterPath()
                path.moveTo(x + size * 0.22, y + size * 0.50)
                path.lineTo(x + size * 0.40, y + size * 0.68)
                path.lineTo(x + size * 0.78, y + size * 0.30)
                painter.drawPath(path)
            else:
                painter.drawLine(
                    QPointF(x + size * 0.25, y + size * 0.50),
                    QPointF(x + size * 0.75, y + size * 0.50),
                )
        else:
            if not enabled:
                bg, border = QColor("#E7E7E7"), QColor("#C8C8C8")
            elif hover:
                bg, border = QColor("#F5F5F5"), QColor("#8491A3")
            else:
                bg, border = QColor("#F5F5F5"), QColor("#D6D6D6")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(box, radius, radius)

            pen = QPen(border)
            pen.setWidthF(1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(box, radius, radius)

        painter.restore()


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
