"""Bottom bar with command input and level toggle buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from log_viewer.core.models import LogLevel
from log_viewer.core.themes import _t
from log_viewer.gui.command_input import CommandInput

_LEVEL_CONFIG: list[tuple[LogLevel, str, str]] = [
    (LogLevel.CRITICAL, "\u26d4", "#CC0000"),  # ⛔
    (LogLevel.ERROR, "\U0001f6d1", "#CC0000"),  # 🛑
    (LogLevel.WARNING, "\u26a0\ufe0f", "#8A6D00"),  # ⚠️
    (LogLevel.INFO, "\u2139\ufe0f", "#86868b"),  # ℹ️
    (LogLevel.DEBUG, "\U0001f7ea", "#7B61FF"),  # 🟪
    (LogLevel.TRACE, "\U0001f7e9", "#30A14E"),  # 🟩
]


class LevelButton(QPushButton):
    """A clickable button for one log level showing icon + count."""

    clicked = Signal()  # type: ignore[assignment]

    def __init__(self, level: LogLevel, icon: str, color: str) -> None:
        super().__init__()
        self._level = level
        self._color = color
        self._active = True
        self._count = 0
        self._icon = icon

        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self.setMinimumWidth(10)
        self.setStyleSheet(self._active_style())
        self._update_text()

    def _active_style(self) -> str:
        return (
            f"LevelButton {{ color: {self._color}; background: transparent; "
            "border: none; border-radius: 6px; padding: 2px 6px; font-size: 12px; }"
            f"LevelButton:hover {{ background: {_t('recessed')}; }}"
        )

    def _inactive_style(self) -> str:
        return (
            f"LevelButton {{ color: {_t('slate')}; background: transparent; "
            "border: none; border-radius: 6px; padding: 2px 6px; font-size: 12px; }"
            f"LevelButton:hover {{ background: {_t('recessed')}; }}"
        )

    def set_count(self, count: int) -> None:
        self._count = count
        self._update_text()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("level_active", active)
        self.setStyleSheet(self._active_style() if active else self._inactive_style())
        self._update_text()

    def _update_text(self) -> None:
        self.setText(f"{self._icon}{self._count}")


class LevelBar(QWidget):
    """Row of log-level toggle buttons."""

    level_clicked = Signal(LogLevel)

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._buttons: list[LevelButton] = []
        for level, icon, color in _LEVEL_CONFIG:
            btn = LevelButton(level, icon, color)
            btn.clicked.connect(lambda checked=False, lvl=level: self.level_clicked.emit(lvl))
            layout.addWidget(btn)
            self._buttons.append(btn)

    def set_counts(self, counts: dict[LogLevel, int]) -> None:
        for btn in self._buttons:
            btn.set_count(counts.get(btn._level, 0))

    def set_level_active(self, level: LogLevel, active: bool) -> None:
        for btn in self._buttons:
            if btn._level == level:
                btn.set_active(active)
                return

    def sync_from_store(self, disabled_levels: set[LogLevel], visible_counts: dict[LogLevel, int]) -> None:
        for btn in self._buttons:
            btn.set_count(visible_counts.get(btn._level, 0))
            btn.set_active(btn._level not in disabled_levels)


class BottomBar(QWidget):
    """Horizontal bar: command input (left) + level buttons (right)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.command_input = CommandInput()
        self.command_input.setFrame(False)
        pal = self.command_input.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(_t("slate")))
        self.command_input.setPalette(pal)
        layout.addWidget(self.command_input, stretch=1)

        self.level_bar = LevelBar()
        layout.addWidget(self.level_bar)

        self.setFixedHeight(32)

        self.setStyleSheet(
            f"""
            BottomBar {{
                background-color: {_t('canvas')};
                border-top: 1px solid {_t('silver_mist')};
            }}
            QLineEdit {{
                color: {_t('ink')};
                background-color: {_t('card')};
                border: 1px solid {_t('silver_mist')};
                border-radius: 8px;
                padding: 3px 10px;
                selection-background-color: {_t('selection_bg')};
                selection-color: {_t('selection_fg')};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {_t('border_focus')};
            }}
            """
        )

    def set_status(self, text: str) -> None:
        """Kept for backward compatibility. No-op — level bar replaces status label."""
        pass

    def activate_command_mode(self) -> None:
        self.command_input.setText(":")
        self.command_input.setFocus()
        self.command_input.setCursorPosition(1)
