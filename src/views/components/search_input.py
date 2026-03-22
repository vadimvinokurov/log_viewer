"""Reusable search input widget with placeholder icon."""
from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget, QLineEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from src.styles.stylesheet import get_search_input_stylesheet


class SearchInput(QLineEdit):
    """Search input field with placeholder icon.
    
    A QLineEdit styled for search input with a placeholder icon.
    Emits signals on text change and return pressed.
    
    Signals:
        text_changed: Emitted when text changes (str)
        return_pressed: Emitted when Enter is pressed
        escape_pressed: Emitted when Escape is pressed
    """
    
    text_changed = Signal(str)
    escape_pressed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the search input.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setPlaceholderText("Search logs...")
        self.setMinimumWidth(200)
        # No maximum width - allows the input to stretch
        self.setStyleSheet(get_search_input_stylesheet())
        
        # Minimal left margin for text
        self.setTextMargins(4, 0, 0, 0)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.
        
        Emits return_pressed on Enter key.
        Emits escape_pressed on Escape key.
        
        Args:
            event: Key event.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.returnPressed.emit()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.escape_pressed.emit()
            self.clear()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def set_search_text(self, text: str) -> None:
        """Set the search text.
        
        Args:
            text: Text to set.
        """
        self.setText(text)
    
    def get_search_text(self) -> str:
        """Get the current search text.
        
        Returns:
            Current search text.
        """
        return self.text()
    
    def clear_search(self) -> None:
        """Clear the search input."""
        self.clear()
    
    def select_all_text(self) -> None:
        """Select all text in the search input."""
        self.selectAll()