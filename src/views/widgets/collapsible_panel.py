"""Collapsible panel widget with toggle strip.

This module provides a collapsible container widget with a thin interactive
strip containing an arrow indicator for toggling visibility.
"""
from __future__ import annotations

from typing import Optional
from beartype import beartype

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor


class ToggleStrip(QWidget):
    """Thin interactive strip with arrow indicator for toggling panel visibility.
    
    Features:
    - Full-width thin strip (always visible)
    - Centered arrow indicator
    - Hover effect to indicate interactivity
    - Arrow rotates 180 degrees based on collapsed state
    """
    
    # Signal emitted when clicked
    clicked = Signal()
    
    # Arrow direction constants
    ARROW_DOWN = "▼"
    ARROW_UP = "▲"
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the toggle strip.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._is_collapsed = False
        self._is_hovered = False
        self._arrow_rotation = 0  # 0 = expanded (down), 180 = collapsed (up)
        
        self._setup_ui()
        self._setup_animation()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Very thin strip - only 6px height
        self.setFixedHeight(6)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to toggle panel visibility")
        
        # Use horizontal layout to center the arrow
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add stretch on both sides to center the arrow
        layout.addStretch()
        
        self._arrow_label = QLabel(self.ARROW_DOWN)
        self._arrow_label.setAlignment(Qt.AlignCenter)
        self._arrow_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 6pt;
                background-color: transparent;
            }
        """)
        layout.addWidget(self._arrow_label)
        
        # Add stretch after arrow to center it
        layout.addStretch()
    
    def _setup_animation(self) -> None:
        """Set up the rotation animation for the arrow."""
        self._rotation_animation = QPropertyAnimation(self, b"arrowRotation")
        self._rotation_animation.setDuration(150)  # 150ms animation
        self._rotation_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def isCollapsed(self) -> bool:
        """Check if the panel is collapsed.
        
        Returns:
            True if collapsed, False if expanded.
        """
        return self._is_collapsed
    
    def setCollapsed(self, collapsed: bool) -> None:
        """Set the collapsed state.
        
        Args:
            collapsed: True to collapse, False to expand.
        """
        if self._is_collapsed == collapsed:
            return
        
        self._is_collapsed = collapsed
        self._animate_arrow()
    
    def _animate_arrow(self) -> None:
        """Animate the arrow rotation."""
        target_rotation = 180 if self._is_collapsed else 0
        self._rotation_animation.setStartValue(self._arrow_rotation)
        self._rotation_animation.setEndValue(target_rotation)
        self._rotation_animation.start()
    
    def getArrowRotation(self) -> int:
        """Get the current arrow rotation value.
        
        Returns:
            Current rotation in degrees.
        """
        return self._arrow_rotation
    
    def setArrowRotation(self, rotation: int) -> None:
        """Set the arrow rotation value (for animation).
        
        Args:
            rotation: Rotation value in degrees.
        """
        self._arrow_rotation = rotation
        self._update_arrow_display()
    
    # Define Qt property for animation
    arrowRotation = Property(int, getArrowRotation, setArrowRotation)
    
    def _update_arrow_display(self) -> None:
        """Update the arrow display based on rotation."""
        # Use appropriate arrow based on rotation
        if self._arrow_rotation < 90:
            self._arrow_label.setText(self.ARROW_DOWN)
        else:
            self._arrow_label.setText(self.ARROW_UP)
    
    def toggle(self) -> None:
        """Toggle the collapsed state."""
        self.setCollapsed(not self._is_collapsed)
        self.clicked.emit()
    
    def enterEvent(self, event) -> None:
        """Handle mouse enter event for hover effect."""
        self._is_hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event) -> None:
        """Handle mouse leave event to remove hover effect."""
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press to toggle panel."""
        if event.button() == Qt.LeftButton:
            self.toggle()
        super().mousePressEvent(event)
    
    def paintEvent(self, event) -> None:
        """Paint the toggle strip with hover effect."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background color based on hover state
        if self._is_hovered:
            bg_color = QColor("#e8e8e8")
            border_color = QColor("#a0a0a0")
        else:
            bg_color = QColor("#f0f0f0")
            border_color = QColor("#c0c0c0")
        
        # Draw background
        painter.fillRect(self.rect(), bg_color)
        
        # Draw top border (line above the strip)
        painter.setPen(border_color)
        painter.drawLine(0, 0, self.width(), 0)


class CollapsiblePanel(QWidget):
    """Container widget that can collapse/expand with a toggle strip.
    
    Features:
    - Toggle strip at the BOTTOM with arrow indicator
    - Content area that can be shown/hidden
    - Full-width thin strip (always visible)
    - Hover effect on toggle strip
    """
    
    # Signal emitted when panel is toggled
    toggled = Signal(bool)  # collapsed state
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the collapsible panel.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._content_widget: Optional[QWidget] = None
        self._is_collapsed = False
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # Content area (will hold the actual widget) - comes FIRST
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._main_layout.addWidget(self._content_container)
        
        # Toggle strip at the BOTTOM - comes LAST
        self._toggle_strip = ToggleStrip(self)
        self._toggle_strip.clicked.connect(self._on_toggle_clicked)
        self._main_layout.addWidget(self._toggle_strip)
    
    def _on_toggle_clicked(self) -> None:
        """Handle toggle strip click."""
        self.toggle()
    
    def setContent(self, widget: QWidget) -> None:
        """Set the content widget.
        
        Args:
            widget: Widget to display in the content area.
        """
        # Remove existing content if any
        if self._content_widget is not None:
            self._content_layout.removeWidget(self._content_widget)
            self._content_widget.setParent(None)
        
        self._content_widget = widget
        self._content_layout.addWidget(widget)
        
        # Apply collapsed state if needed
        if self._is_collapsed:
            self._content_container.hide()
    
    def getContent(self) -> QWidget | None:
        """Get the content widget.
        
        Returns:
            Content widget or None if not set.
        """
        return self._content_widget
    
    def isCollapsed(self) -> bool:
        """Check if the panel is collapsed.
        
        Returns:
            True if collapsed, False if expanded.
        """
        return self._is_collapsed
    
    @beartype
    def setCollapsed(self, collapsed: bool) -> None:
        """Set the collapsed state.
        
        Args:
            collapsed: True to collapse, False to expand.
        """
        if self._is_collapsed == collapsed:
            return
        
        self._is_collapsed = collapsed
        self._toggle_strip.setCollapsed(collapsed)
        
        if collapsed:
            self._content_container.hide()
        else:
            self._content_container.show()
        
        self.toggled.emit(collapsed)
    
    def toggle(self) -> None:
        """Toggle the collapsed state."""
        self.setCollapsed(not self._is_collapsed)
    
    def getToggleStrip(self) -> ToggleStrip:
        """Get the toggle strip widget.
        
        Returns:
            Toggle strip widget.
        """
        return self._toggle_strip