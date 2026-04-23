"""Main window status bar component.

This module provides a custom status bar for the main window with
file information, status messages, and statistics counters.

// Ref: docs/specs/features/panel-toggle-button.md §4.1
// Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
// Thread: Main thread only (Qt UI component per docs/specs/global/threading.md §8.1)
// Memory: Qt parent-child ownership (parent: MainWindow)
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QSizePolicy, QPushButton
from PySide6.QtCore import Qt, Signal

from src.constants.app_constants import STATUS_MESSAGE_TIMEOUT
from src.views.widgets.command_bar import CommandBar
from src.views.widgets.statistics_bar import StatisticsBar


class MainStatusBar(QStatusBar):
    """Custom status bar for the main window.

    Provides:
        - File name display (left)
        - Statistics bar with counters (right)
        - Panel toggle button (rightmost)
        - Embedded command bar input (replaces normal content when active)
        - Status messages with timeout

    // Ref: docs/specs/features/panel-toggle-button.md §4.1
    """

    # Signal emitted when a counter is clicked
    counter_clicked = Signal(str, bool)  # counter_type, visible

    # Signal emitted when panel toggle button is clicked
    # Ref: docs/specs/features/panel-toggle-button.md §4.1
    panels_toggled = Signal(bool)  # panels_visible

    # Command bar signals (forwarded from CommandBar callbacks)
    command_submitted = Signal(str, str)  # text (without prefix), prefix
    command_cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the status bar.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        # Instance variables for panel toggle
        # Ref: docs/specs/features/panel-toggle-button.md §4.1
        self._panels_visible: bool = True  # Default: panels visible
        self._toggle_button: QPushButton  # Set in _setup_ui

        # Command bar (logic class, widgets embedded here)
        self._command_bar = CommandBar()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up status bar widgets.

        // Ref: docs/specs/features/panel-toggle-button.md §6.2
        """
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

        # Panel toggle button (NEW) - rightmost position
        # Ref: docs/specs/features/panel-toggle-button.md §6.2
        self._toggle_button = QPushButton("\U0001f441\ufe0f")
        self._toggle_button.setFlat(True)
        self._toggle_button.setToolTip("Hide panels (Ctrl+Shift+P)")
        self._toggle_button.clicked.connect(self._on_toggle_clicked)
        self.addPermanentWidget(self._toggle_button)

        # Command bar widgets (hidden by default)
        self._cmd_prefix_label = self._command_bar.prefix_label
        self._cmd_input = self._command_bar.input
        self._cmd_prefix_label.hide()
        self._cmd_input.hide()
        self.addWidget(self._cmd_prefix_label)
        self.addWidget(self._cmd_input)
        # Install event filter on input so we can delegate to CommandBar
        self._cmd_input.installEventFilter(self)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._statistics_bar.counter_clicked.connect(self.counter_clicked)
        # Wire CommandBar callbacks to our signals + UI restoration
        self._command_bar.set_callbacks(
            on_submitted=self._on_command_submitted,
            on_cancelled=self._on_command_cancelled,
        )

    def _on_command_submitted(self, text: str, prefix: str) -> None:
        """Forward command submission and restore normal content."""
        self.deactivate_command_bar()
        self.command_submitted.emit(text, prefix)

    def _on_command_cancelled(self) -> None:
        """Restore normal content on cancel."""
        self.deactivate_command_bar()
        self.command_cancelled.emit()
    
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
    
    # Panel toggle methods
    # Ref: docs/specs/features/panel-toggle-button.md §4.1
    
    def _on_toggle_clicked(self) -> None:
        """Handle toggle button click.
        
        Emits panels_toggled signal with current visibility state.
        The signal argument is the NEW state (opposite of current).
        
        // Ref: docs/specs/features/panel-toggle-button.md §6.2
        """
        # Emit the opposite of current state (toggle)
        new_state = not self._panels_visible
        self.panels_toggled.emit(new_state)
    
    def set_panels_visible(self, visible: bool) -> None:
        """Set the panels visibility state.
        
        Updates the toggle button icon and tooltip to reflect current state.
        
        Args:
            visible: True if panels are visible, False if hidden.
        
        // Ref: docs/specs/features/panel-toggle-button.md §4.1
        """
        self._panels_visible = visible
        if visible:
            self._toggle_button.setText("👁️")
            self._toggle_button.setToolTip("Hide panels (Ctrl+Shift+P)")
        else:
            self._toggle_button.setText("👁️‍🗨️")
            self._toggle_button.setToolTip("Show panels (Ctrl+Shift+P)")
    
    def is_panels_visible(self) -> bool:
        """Check if panels are currently visible.

        Returns:
            True if panels are visible, False if hidden.

        // Ref: docs/specs/features/panel-toggle-button.md §4.1
        """
        return self._panels_visible

    # Command bar methods

    def get_command_bar(self) -> CommandBar:
        """Return the embedded command bar."""
        return self._command_bar

    def activate_command_bar(self, prefix: str) -> None:
        """Show command input in the status bar, hiding normal content."""
        self._command_bar.activate(prefix)
        # Hide normal status bar content
        self._file_label.hide()
        self._stretch.hide()
        # Show command widgets
        self._cmd_prefix_label.show()
        self._cmd_input.show()
        self._cmd_input.setFocus()

    def deactivate_command_bar(self) -> None:
        """Restore normal status bar content, hiding command input."""
        self._command_bar.deactivate()
        # Hide command widgets
        self._cmd_prefix_label.hide()
        self._cmd_input.hide()
        # Restore normal content
        self._file_label.show()
        self._stretch.show()

    def eventFilter(self, obj: object, event: object) -> bool:
        """Delegate key events on command input to CommandBar."""
        if obj is self._cmd_input:
            return self._command_bar.eventFilter(obj, event)
        return super().eventFilter(obj, event)