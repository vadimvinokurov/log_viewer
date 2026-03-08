"""Reusable counter widget for statistics display.

This module provides a reusable counter widget that can be used across
different views to display statistics with colored backgrounds and icons.

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
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.styles.stylesheet import get_counter_style
from src.constants.dimensions import STATISTICS_ICON_WIDTH


class CounterWidget(QWidget):
    """A single statistics counter with icon and count.
    
    Displays a colored background with an icon character and count number.
    When clicked, emits a signal with the counter type and new visibility state.
    The count always shows the total number of logs, regardless of visibility.
    
    Signals:
        clicked: Emitted when counter is clicked with (counter_type, visible) args.
    """
    
    clicked = Signal(str, bool)  # counter_type, visible
    
    def __init__(
        self,
        counter_type: str,
        icon: str,
        parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the counter widget.
        
        Args:
            counter_type: Type of counter (critical, error, warning, msg, debug, trace).
            icon: Unicode icon character to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._counter_type = counter_type
        self._icon = icon
        self._count = 0
        self._visible = True  # Logs of this type are visible by default
        
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Icon label
        self._icon_label = QLabel(self._icon)
        self._icon_label.setFixedWidth(STATISTICS_ICON_WIDTH)
        self._icon_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        self._icon_label.setFont(font)
        layout.addWidget(self._icon_label)
        
        # Count label
        self._count_label = QLabel("0")
        self._count_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont()
        font.setBold(True)
        self._count_label.setFont(font)
        layout.addWidget(self._count_label)
        
        self.setCursor(Qt.PointingHandCursor)
    
    def _apply_style(self) -> None:
        """Apply the color style based on counter type and visibility state."""
        colors = get_counter_style(self._counter_type)
        
        if self._visible:
            # Active/visible state - full colors
            style = f"""
                CounterWidget {{
                    background-color: {colors['bg']};
                    border: 1px solid {colors['border']};
                    border-radius: 3px;
                }}
                CounterWidget QLabel {{
                    color: {colors['text']};
                    background-color: transparent;
                }}
            """
        else:
            # Inactive/hidden state - muted colors with colored border hint
            style = f"""
                CounterWidget {{
                    background-color: #f5f5f5;
                    border: 2px solid {colors['border']};
                    border-radius: 3px;
                }}
                CounterWidget QLabel {{
                    color: #999999;
                    background-color: transparent;
                }}
            """
        
        self.setStyleSheet(style)
    
    def set_count(self, count: int) -> None:
        """Set the count value.
        
        The count always shows the total number of logs for this level,
        regardless of whether the level is currently visible.
        
        Args:
            count: The count to display.
        """
        self._count = count
        self._count_label.setText(self._format_count(count))
    
    def _format_count(self, count: int) -> str:
        """Format count for display.
        
        Args:
            count: The count to format.
        
        Returns:
            Formatted count string (e.g., "1.2K", "3.5M").
        """
        if count >= 1000000:
            return f"{count / 1000000:.1f}M"
        elif count >= 1000:
            return f"{count / 1000:.1f}K"
        return str(count)
    
    def set_visible_state(self, visible: bool) -> None:
        """Set the visibility state of the counter.
        
        This affects the visual appearance but NOT the count.
        The count always shows total logs.
        
        Args:
            visible: Whether logs of this type should be visible.
        """
        self._visible = visible
        self._apply_style()
    
    def is_visible(self) -> bool:
        """Check if the counter is in visible state.
        
        Returns:
            True if logs of this type should be visible.
        """
        return self._visible
    
    def get_counter_type(self) -> str:
        """Get the counter type.
        
        Returns:
            Counter type string.
        """
        return self._counter_type
    
    def get_count(self) -> int:
        """Get the current count.
        
        Returns:
            Current count value (total logs, not affected by visibility).
        """
        return self._count
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press to toggle visibility.
        
        Args:
            event: Mouse event.
        """
        if event.button() == Qt.LeftButton:
            # Toggle visibility state
            new_state = not self._visible
            self.set_visible_state(new_state)
            # Emit signal with counter type and new visibility
            self.clicked.emit(self._counter_type, new_state)