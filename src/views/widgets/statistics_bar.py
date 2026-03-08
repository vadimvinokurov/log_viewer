"""Statistics bar with colored counters for log levels.

This module provides a widget that displays log statistics as a row
of colored counters with icons and counts.

Counter Types:
    critical: ⛔ Light Red (#FF4444) - Critical errors
    error: 🛑 Red (#CC0000) - Error messages
    warning: ⚠️ Orange (#FFAA00) - Warning messages
    msg: ℹ️ Blue (#0066CC) - Informational messages
    debug: 🟪 Purple (#8844AA) - Debug messages
    trace: 🟩 Green (#00AA00) - Trace messages
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Signal

from src.views.components.counter_widget import CounterWidget
from src.constants.log_levels import LogLevel, LOG_LEVEL_CONFIGS


# Counter order for display (from most to least severe)
COUNTER_ORDER: list[LogLevel] = [
    LogLevel.CRITICAL,
    LogLevel.ERROR,
    LogLevel.WARNING,
    LogLevel.MSG,
    LogLevel.DEBUG,
    LogLevel.TRACE,
]

# Mapping from LogLevel to counter type string (for get_counter_style)
LEVEL_TO_COUNTER_TYPE: dict[LogLevel, str] = {
    LogLevel.CRITICAL: "critical",
    LogLevel.ERROR: "error",
    LogLevel.WARNING: "warning",
    LogLevel.MSG: "msg",
    LogLevel.DEBUG: "debug",
    LogLevel.TRACE: "trace",
}


class StatisticsBar(QWidget):
    """A bar displaying multiple statistics counters.
    
    Displays a row of colored counters for different log levels.
    Clicking a counter toggles visibility of that log level in the table.
    The count always shows the total number of logs for each level.
    
    Counter order (left to right):
        - critical: ⛔ Critical errors
        - error: 🛑 Errors
        - warning: ⚠️ Warnings
        - msg: ℹ️ Informational messages
        - debug: 🟪 Debug messages
        - trace: 🟩 Trace messages
    """
    
    # Signal emitted when a counter is clicked
    # Parameters: counter_type (str), visible (bool)
    counter_clicked = Signal(str, bool)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the statistics bar.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._counters: dict[str, CounterWidget] = {}
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Create counters in specified order using LOG_LEVEL_CONFIGS
        for level in COUNTER_ORDER:
            config = LOG_LEVEL_CONFIGS[level]
            counter_type = LEVEL_TO_COUNTER_TYPE[level]
            counter = CounterWidget(counter_type, config.icon)
            counter.setToolTip(f"{config.tooltip} (click to toggle visibility)")
            # Connect to CounterWidget's clicked signal
            counter.clicked.connect(lambda ct, v: self._on_counter_clicked(ct, v))
            self._counters[counter_type] = counter
            layout.addWidget(counter)
        
        # Add stretch at the end
        layout.addStretch()
    
    def _on_counter_clicked(self, counter_type: str, visible: bool) -> None:
        """Handle counter click - emit signal with visibility state.
        
        Args:
            counter_type: The type of counter that was clicked.
            visible: The new visibility state from the counter.
        """
        # Emit signal with counter type and new visibility
        self.counter_clicked.emit(counter_type, visible)
    
    def update_counters(self, stats: dict[str, int]) -> None:
        """Update all counter values.
        
        The count always shows total logs, regardless of visibility state.
        
        Args:
            stats: Dictionary mapping counter types to counts.
        """
        for counter_type, count in stats.items():
            if counter_type in self._counters:
                self._counters[counter_type].set_count(count)
    
    def set_counter_visible(self, counter_type: str, visible: bool) -> None:
        """Set the visibility state of a specific counter.
        
        Args:
            counter_type: Type of counter.
            visible: Whether logs of this type should be visible.
        """
        if counter_type in self._counters:
            self._counters[counter_type].set_visible_state(visible)
    
    def is_counter_visible(self, counter_type: str) -> bool:
        """Check if a counter is in visible state.
        
        Args:
            counter_type: Type of counter.
        
        Returns:
            True if visible.
        """
        if counter_type in self._counters:
            return self._counters[counter_type].is_visible()
        return True
    
    def reset_counters(self) -> None:
        """Reset all counters to zero and visible state."""
        for counter in self._counters.values():
            counter.set_count(0)
            counter.set_visible_state(True)
    
    def get_visible_types(self) -> list[str]:
        """Get list of counter types that are currently visible.
        
        Returns:
            List of visible counter type strings.
        """
        return [
            counter_type
            for counter_type, counter in self._counters.items()
            if counter.is_visible()
        ]
    
    def get_hidden_types(self) -> list[str]:
        """Get list of counter types that are currently hidden.
        
        Returns:
            List of hidden counter type strings.
        """
        return [
            counter_type
            for counter_type, counter in self._counters.items()
            if not counter.is_visible()
        ]