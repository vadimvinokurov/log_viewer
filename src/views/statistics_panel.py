"""Statistics panel with interactive level filter buttons."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal

from src.core.statistics import LogStatistics


class LevelButton(QPushButton):
    """Button for toggling log level visibility."""

    def __init__(self, level: str, color: str, parent=None) -> None:
        """Initialize the level button.

        Args:
            level: Level name (ERROR, WARNING, INFO)
            color: CSS color string for the button
            parent: Parent widget
        """
        super().__init__(parent)
        self._level = level
        self._color = color
        self._count = 0
        self._enabled = True

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the button UI."""
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"Click to hide/show {self._level} logs")
        self._update_style()

    def _update_style(self) -> None:
        """Update button style based on enabled state."""
        if self._enabled:
            # Enabled state - full color
            self.setStyleSheet(f"""
                QPushButton {{
                    color: {self._color};
                    background-color: transparent;
                    border: 1px solid {self._color};
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self._color}22;
                }}
                QPushButton:focus {{
                    outline: 2px solid {self._color};
                    outline-offset: 1px;
                }}
            """)
        else:
            # Disabled state - muted/grayed
            self.setStyleSheet("""
                QPushButton {
                    color: #999;
                    background-color: transparent;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
                QPushButton:focus {
                    outline: 2px solid #999;
                    outline-offset: 1px;
                }
            """)

    def set_count(self, count: int) -> None:
        """Set the count for this level.

        Args:
            count: Number of log entries at this level
        """
        self._count = count
        self._update_text()

    def _update_text(self) -> None:
        """Update button text."""
        count_str = f"{self._count:,}"
        self.setText(f"{self._level} {count_str}")

    def set_enabled_state(self, enabled: bool) -> None:
        """Set the enabled state of the level filter.

        Args:
            enabled: True if level is visible, False if hidden
        """
        self._enabled = enabled
        self._update_style()
        self.setToolTip(
            f"Click to {'hide' if enabled else 'show'} {self._level} logs"
        )

    def is_level_enabled(self) -> bool:
        """Check if level is enabled.

        Returns:
            True if level is enabled (visible)
        """
        return self._enabled

    def get_level(self) -> str:
        """Get the level name.

        Returns:
            Level name string
        """
        return self._level


class StatisticsPanel(QWidget):
    """Panel for displaying log statistics with level filter buttons."""

    # Signal emitted when a level is toggled
    level_toggled = Signal(str, bool)  # level_name, enabled_state

    def __init__(self, parent=None) -> None:
        """Initialize the statistics panel."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(10)

        # Total lines
        self._total_label = QLabel("Total: 0")
        self._total_label.setToolTip("Total lines in file")
        main_layout.addWidget(self._total_label)

        # Separator
        main_layout.addWidget(self._create_separator())

        # Matching/shown lines
        self._shown_label = QLabel("Shown: 0")
        self._shown_label.setToolTip("Lines matching current filters")
        main_layout.addWidget(self._shown_label)

        # Separator
        main_layout.addWidget(self._create_separator())

        # Error count button
        self._error_button = LevelButton("ERROR", "#CC0000")
        self._error_button.clicked.connect(self._on_error_clicked)
        main_layout.addWidget(self._error_button)

        # Separator
        main_layout.addWidget(self._create_separator())

        # Warning count button
        self._warning_button = LevelButton("WARNING", "#CC7700")
        self._warning_button.clicked.connect(self._on_warning_clicked)
        main_layout.addWidget(self._warning_button)

        # Separator
        main_layout.addWidget(self._create_separator())

        # Info count button
        self._info_button = LevelButton("INFO", "#007700")
        self._info_button.clicked.connect(self._on_info_clicked)
        main_layout.addWidget(self._info_button)

        # Stretch at end
        main_layout.addStretch()

    def _create_separator(self) -> QLabel:
        """Create a separator label."""
        separator = QLabel("|")
        separator.setStyleSheet("color: #999;")
        return separator

    def _on_error_clicked(self) -> None:
        """Handle ERROR button click."""
        self._toggle_level(self._error_button)

    def _on_warning_clicked(self) -> None:
        """Handle WARNING button click."""
        self._toggle_level(self._warning_button)

    def _on_info_clicked(self) -> None:
        """Handle INFO button click."""
        self._toggle_level(self._info_button)

    def _toggle_level(self, button: LevelButton) -> None:
        """Toggle a level button and emit signal.

        Args:
            button: The button that was clicked
        """
        new_state = not button.is_level_enabled()
        button.set_enabled_state(new_state)
        self.level_toggled.emit(button.get_level(), new_state)

    def update_stats(self, total: int, shown: int, errors: int, warnings: int, info: int = 0) -> None:
        """Update displayed statistics.

        Args:
            total: Total number of lines in file
            shown: Number of lines currently displayed
            errors: Number of ERROR level entries
            warnings: Number of WARNING level entries
            info: Number of INFO level entries
        """
        self._total_label.setText(f"Total: {self._format_number(total)}")
        self._shown_label.setText(f"Shown: {self._format_number(shown)}")
        self._error_button.set_count(errors)
        self._warning_button.set_count(warnings)
        self._info_button.set_count(info)

    def update_from_statistics(self, stats: LogStatistics) -> None:
        """Update from LogStatistics object.

        Args:
            stats: LogStatistics object with all statistics.
        """
        self.update_stats(
            total=stats.total_lines,
            shown=stats.shown_lines,
            errors=stats.error_count,
            warnings=stats.warning_count,
            info=stats.info_count
        )

    def _format_number(self, value: int) -> str:
        """Format a number with thousand separators.

        Args:
            value: The number to format

        Returns:
            Formatted string with thousand separators
        """
        return f"{value:,}"

    def clear(self) -> None:
        """Clear all statistics."""
        self.update_stats(0, 0, 0, 0, 0)

    def set_loading(self, is_loading: bool) -> None:
        """Show loading state.

        Args:
            is_loading: True if loading, False otherwise
        """
        if is_loading:
            self._total_label.setText("Total: Loading...")
            self._shown_label.setText("Shown: -")
            self._error_button.set_count(0)
            self._warning_button.set_count(0)
            self._info_button.set_count(0)
        else:
            self.clear()

    def set_level_enabled(self, level: str, enabled: bool) -> None:
        """Set the enabled state of a level button.

        Args:
            level: Level name (ERROR, WARNING, INFO)
            enabled: True if level should be visible
        """
        if level == "ERROR":
            self._error_button.set_enabled_state(enabled)
        elif level == "WARNING":
            self._warning_button.set_enabled_state(enabled)
        elif level == "INFO":
            self._info_button.set_enabled_state(enabled)

    def is_level_enabled(self, level: str) -> bool:
        """Check if a level is enabled.

        Args:
            level: Level name (ERROR, WARNING, INFO)

        Returns:
            True if level is enabled
        """
        if level == "ERROR":
            return self._error_button.is_level_enabled()
        elif level == "WARNING":
            return self._warning_button.is_level_enabled()
        elif level == "INFO":
            return self._info_button.is_level_enabled()
        return True

    def reset_level_buttons(self) -> None:
        """Reset all level buttons to enabled state."""
        self._error_button.set_enabled_state(True)
        self._warning_button.set_enabled_state(True)
        self._info_button.set_enabled_state(True)