"""Highlights tab content for the CategoryPanel.

// Ref: docs/specs/features/highlight-panel.md §3.1, §3.2, §4.1, §4.2
// Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
// Thread: Main thread only (Qt UI component per docs/specs/global/threading.md §8.1)
// Memory: Qt parent-child ownership (parent: CategoryPanel)
// Perf: List load < 50ms for 100 patterns per §9.1
"""
from __future__ import annotations

from beartype import beartype
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from src.core.highlight_engine import HighlightPattern
from src.styles.stylesheet import get_panel_list_stylesheet
from src.views.widgets.highlight_dialog import HighlightDialog


# Color to Unicode emoji mapping for display
# Using colored circle emojis for visual indicator
# Ref: docs/specs/features/panel-content-unified-styles.md §3.6
def _get_color_emoji(color: QColor) -> str:
    """Get Unicode emoji for a color.
    
    Maps QColor to the closest colored circle emoji.
    
    Args:
        color: The highlight color.
    
    Returns:
        Unicode emoji string representing the color.
    """
    # Get HSV values for color matching
    h, s, v, _ = color.getHsv()
    
    # Check for light/white colors first (high value, low saturation)
    if v > 240 and s < 30:
        return "⚪"  # White circle for light/white
    
    # Check for dark/gray colors (low saturation or low value)
    if s < 20 or v < 20:
        return "⚫"  # Black circle for dark/gray
    
    # Map hue to colored circles (hue is 0-359)
    # Red: 0-30, Orange: 30-60, Yellow: 60-90, Green: 90-150
    # Cyan: 150-210, Blue: 210-270, Purple: 270-330, Red: 330-360
    if h < 30 or h >= 330:
        return "🔴"  # Red circle
    elif h < 60:
        return "🟠"  # Orange circle
    elif h < 90:
        return "🟡"  # Yellow circle
    elif h < 150:
        return "🟢"  # Green circle
    elif h < 210:
        return "🔵"  # Blue circle (cyan range)
    elif h < 270:
        return "🔵"  # Blue circle
    else:
        return "🟣"  # Purple circle


class HighlightsTabContent(QWidget):
    """Widget for managing highlight patterns.
    
    Uses native QListWidgetItem for visual consistency with other tabs.
    
    // Ref: docs/specs/features/highlight-panel.md §3.1, §4.1
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    // Thread: Main thread only (Qt UI component per docs/specs/global/threading.md §8.1)
    """
    
    # Signals
    pattern_added = Signal(str, QColor, bool)      # text, color, is_regex
    pattern_removed = Signal(str)                   # text
    pattern_enabled_changed = Signal(str, bool)    # text, enabled
    pattern_edited = Signal(str, str, QColor, bool)  # old_text, new_text, color, is_regex
    
    @beartype
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the highlights tab content.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._pattern_items: dict[str, QListWidgetItem] = {}
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Pattern list - unified styling with tree view
        # Ref: docs/specs/features/panel-content-unified-styles.md §3.4
        self._pattern_list = QListWidget()
        self._pattern_list.setStyleSheet(get_panel_list_stylesheet())
        self._pattern_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._pattern_list.itemChanged.connect(self._on_item_changed)
        self._pattern_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._pattern_list)
        
        # Button bar
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        self._add_button = QPushButton("Add")
        self._add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self._add_button)
        
        self._edit_button = QPushButton("Edit")
        self._edit_button.setEnabled(False)
        self._edit_button.clicked.connect(self._on_edit_clicked)
        button_layout.addWidget(self._edit_button)
        
        self._delete_button = QPushButton("Delete")
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self._delete_button)
        
        layout.addLayout(button_layout)
    
    @beartype
    def _format_item_text(self, pattern: HighlightPattern) -> str:
        """Format the display text for a pattern item.
        
        Args:
            pattern: The highlight pattern.
        
        Returns:
            Formatted display string with color emoji and type indicator.
        """
        color_emoji = _get_color_emoji(pattern.color)
        type_text = "regex" if pattern.is_regex else "text"
        return f"{color_emoji} {pattern.text} ({type_text})"
    
    @beartype
    def set_patterns(self, patterns: list[HighlightPattern]) -> None:
        """Set the list of highlight patterns.
        
        Args:
            patterns: List of HighlightPattern objects.
        """
        # Block signals during batch update
        self._pattern_list.blockSignals(True)
        
        # Clear existing items
        self._pattern_list.clear()
        self._pattern_items.clear()
        
        # Unblock signals before adding items
        self._pattern_list.blockSignals(False)
        
        # Add each pattern
        for pattern in patterns:
            self.add_pattern(pattern)
    
    @beartype
    def get_patterns(self) -> list[HighlightPattern]:
        """Get all highlight patterns.
        
        Returns:
            List of HighlightPattern objects.
        """
        patterns: list[HighlightPattern] = []
        for i in range(self._pattern_list.count()):
            item = self._pattern_list.item(i)
            if item:
                pattern = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(pattern, HighlightPattern):
                    patterns.append(pattern)
        return patterns
    
    @beartype
    def add_pattern(self, pattern: HighlightPattern) -> None:
        """Add a single pattern to the list.
        
        Args:
            pattern: HighlightPattern to add.
        """
        # Block signals while setting up the item to prevent
        # spurious itemChanged signals during initialization
        self._pattern_list.blockSignals(True)
        
        # Create list item
        item = QListWidgetItem(self._pattern_list)
        
        # Store full pattern data
        item.setData(Qt.ItemDataRole.UserRole, pattern)
        
        # Set checkbox state
        item.setCheckState(Qt.CheckState.Checked if pattern.enabled else Qt.CheckState.Unchecked)
        
        # Set display text with color emoji and type indicator
        item.setText(self._format_item_text(pattern))
        
        # Unblock signals after setup
        self._pattern_list.blockSignals(False)
        
        # Store in dictionary for O(1) lookup
        self._pattern_items[pattern.text] = item
    
    def clear(self) -> None:
        """Clear all patterns from the list."""
        self._pattern_list.clear()
        self._pattern_items.clear()
    
    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Handle item checkbox change.
        
        Args:
            item: The changed item.
        """
        pattern = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(pattern, HighlightPattern):
            return
        
        enabled = item.checkState() == Qt.CheckState.Checked
        
        # Only update and emit if state actually changed
        if pattern.enabled != enabled:
            # Block signals to prevent recursion when updating data
            self._pattern_list.blockSignals(True)
            
            # Update pattern data with new enabled state
            updated_pattern = HighlightPattern(
                text=pattern.text,
                color=pattern.color,
                is_regex=pattern.is_regex,
                enabled=enabled
            )
            item.setData(Qt.ItemDataRole.UserRole, updated_pattern)
            
            # Unblock signals
            self._pattern_list.blockSignals(False)
            
            # Emit signal
            self.pattern_enabled_changed.emit(pattern.text, enabled)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in the list."""
        selected = self._pattern_list.currentItem() is not None
        self._edit_button.setEnabled(selected)
        self._delete_button.setEnabled(selected)
    
    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on list item.
        
        Args:
            item: The double-clicked item.
        """
        self._edit_pattern(item)
    
    def _on_add_clicked(self) -> None:
        """Handle Add button click."""
        dialog = HighlightDialog(self)
        if dialog.exec():
            text = dialog.get_text()
            color = dialog.get_color()
            is_regex = dialog.is_regex()
            
            if text:
                # Add to list widget
                pattern = HighlightPattern(
                    text=text,
                    color=color,
                    is_regex=is_regex,
                    enabled=True
                )
                self.add_pattern(pattern)
                # Emit signal for controller
                self.pattern_added.emit(text, color, is_regex)
    
    def _on_edit_clicked(self) -> None:
        """Handle Edit button click."""
        item = self._pattern_list.currentItem()
        if item:
            self._edit_pattern(item)
    
    def _edit_pattern(self, item: QListWidgetItem) -> None:
        """Edit the selected pattern.
        
        Args:
            item: The item to edit.
        """
        pattern = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(pattern, HighlightPattern):
            return
        
        old_text = pattern.text
        
        # Open dialog with current values
        dialog = HighlightDialog(
            self,
            text=old_text,
            color=pattern.color,
            is_regex=pattern.is_regex
        )
        
        if dialog.exec():
            new_text = dialog.get_text()
            color = dialog.get_color()
            is_regex = dialog.is_regex()
            
            if new_text:
                # Block signals during update
                self._pattern_list.blockSignals(True)
                
                # Update pattern data
                updated_pattern = HighlightPattern(
                    text=new_text,
                    color=color,
                    is_regex=is_regex,
                    enabled=pattern.enabled
                )
                item.setData(Qt.ItemDataRole.UserRole, updated_pattern)
                
                # Update display text
                item.setText(self._format_item_text(updated_pattern))
                
                # Update dictionary key if text changed
                if new_text != old_text:
                    if old_text in self._pattern_items:
                        del self._pattern_items[old_text]
                    self._pattern_items[new_text] = item
                
                # Unblock signals
                self._pattern_list.blockSignals(False)
                
                # Emit signal for controller
                self.pattern_edited.emit(old_text, new_text, color, is_regex)
    
    def _on_delete_clicked(self) -> None:
        """Handle Delete button click."""
        item = self._pattern_list.currentItem()
        if not item:
            return
        
        pattern = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(pattern, HighlightPattern):
            return
        
        text = pattern.text
        
        # Emit signal for controller to update service
        self.pattern_removed.emit(text)
        
        # Remove from list widget
        row = self._pattern_list.row(item)
        self._pattern_list.takeItem(row)
        
        # Remove from dictionary
        if text in self._pattern_items:
            del self._pattern_items[text]