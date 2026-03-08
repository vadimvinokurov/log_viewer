"""Main window status bar component.

This module provides a custom status bar for the main window with
file information, status messages, and statistics counters.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal

from src.constants.app_constants import STATUS_MESSAGE_TIMEOUT
from src.views.widgets.statistics_bar import StatisticsBar


class MainStatusBar(QStatusBar):
    """Custom status bar for the main window.
    
    Provides:
        - File name display (left)
        - Statistics bar with counters (right)
        - Status messages with timeout
    """
    
    # Signal emitted when a counter is clicked
    counter_clicked = Signal(str, bool)  # counter_type, visible
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the status bar.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up status bar widgets."""
        # File label on the left
        self._file_label = QLabel("No file open")
        self._file_label.setStyleSheet("padding: 0 8px;")
        self.addWidget(self._file_label)
        
        # Stretch in the middle
        self._stretch = QWidget()
        self._stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.addWidget(self._stretch)
        
        # Statistics bar on the right
        self._statistics_bar = StatisticsBar()
        self.addPermanentWidget(self._statistics_bar)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._statistics_bar.counter_clicked.connect(self.counter_clicked)
    
    def set_file(self, filename: str | None) -> None:
        """Set current file name.
        
        Args:
            filename: File name to display, or None to show "No file open".
        """
        if filename:
            self._file_label.setText(filename)
        else:
            self._file_label.setText("No file open")
    
    def show_status(self, message: str, timeout: int = STATUS_MESSAGE_TIMEOUT) -> None:
        """Show a temporary status message.
        
        Args:
            message: Status message to display.
            timeout: Timeout in milliseconds.
        """
        self.showMessage(message, timeout)
    
    def clear_status(self) -> None:
        """Clear the status message."""
        self.clearMessage()
    
    def update_statistics(self, stats: dict[str, int]) -> None:
        """Update the statistics counters.
        
        Args:
            stats: Dictionary mapping counter types to counts.
        """
        self._statistics_bar.update_counters(stats)
    
    def set_counter_visible(self, counter_type: str, visible: bool) -> None:
        """Set the visibility state of a counter.
        
        Args:
            counter_type: Type of counter.
            visible: Whether logs of this type should be visible.
        """
        self._statistics_bar.set_counter_visible(counter_type, visible)
    
    def is_counter_visible(self, counter_type: str) -> bool:
        """Check if a counter is in visible state.
        
        Args:
            counter_type: Type of counter.
        
        Returns:
            True if visible.
        """
        return self._statistics_bar.is_counter_visible(counter_type)
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self._statistics_bar.reset_counters()
    
    def get_visible_types(self) -> list[str]:
        """Get list of visible counter types.
        
        Returns:
            List of visible counter type strings.
        """
        return self._statistics_bar.get_visible_types()
    
    def get_hidden_types(self) -> list[str]:
        """Get list of hidden counter types.
        
        Returns:
            List of hidden counter type strings.
        """
        return self._statistics_bar.get_hidden_types()