"""Highlight pattern dialog.

Ref: docs/specs/global/color-palette.md §10.2
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QColorDialog,
    QDialogButtonBox, QFormLayout, QGroupBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from src.constants.colors import UIColors, HighlightColors


# Default highlight colors (user-selectable, not semantic)
# Ref: docs/audit/HARDCODED_COLORS_AUDIT.md §3
DEFAULT_COLORS = [
    QColor(UIColors.FIND_HIGHLIGHT),  # Yellow
    QColor(HighlightColors.GREEN),     # Green
    QColor(HighlightColors.CYAN),      # Cyan
    QColor(HighlightColors.MAGENTA),   # Magenta
    QColor(HighlightColors.ORANGE),    # Orange
    QColor(HighlightColors.PINK),      # Pink
]


class HighlightDialog(QDialog):
    """Dialog for creating/editing highlight patterns."""

    def __init__(
        self,
        parent=None,
        text: str = "",
        color: QColor | None = None,
        is_regex: bool = False
    ) -> None:
        """Initialize the dialog.

        Args:
            parent: Parent widget.
            text: Initial pattern text (for editing).
            color: Initial color (for editing).
            is_regex: Initial regex state (for editing).
        """
        super().__init__(parent)
        self.setWindowTitle("Highlight Pattern")
        # Ref: docs/specs/global/color-palette.md §10.2.3
        self._color = color if color else QColor(UIColors.FIND_HIGHLIGHT)
        self._setup_ui(text, is_regex)

    def _setup_ui(self, text: str, is_regex: bool) -> None:
        """Set up the dialog UI.

        Args:
            text: Initial text.
            is_regex: Initial regex state.
        """
        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Text input
        self._text_edit = QLineEdit()
        self._text_edit.setText(text)
        self._text_edit.setPlaceholderText("Enter text or pattern to highlight")
        self._text_edit.textChanged.connect(self._update_preview)
        form_layout.addRow("Pattern:", self._text_edit)

        # Color picker
        color_layout = QHBoxLayout()
        self._color_button = QPushButton()
        self._color_button.setFixedSize(60, 30)
        self._color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self._color_button)

        self._color_label = QLabel(self._color.name())
        color_layout.addWidget(self._color_label)
        self._update_color_button()
        color_layout.addStretch()

        form_layout.addRow("Color:", color_layout)

        # Regex checkbox
        self._regex_check = QCheckBox("Regular Expression")
        self._regex_check.setChecked(is_regex)
        self._regex_check.toggled.connect(self._update_preview)
        form_layout.addRow("", self._regex_check)

        layout.addLayout(form_layout)

        # Preview group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_label = QLabel("Enter a pattern to see preview")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("padding: 8px;")
        preview_layout.addWidget(self._preview_label)

        layout.addWidget(preview_group)

        # Quick color buttons
        quick_color_group = QGroupBox("Quick Colors")
        quick_color_layout = QHBoxLayout(quick_color_group)

        for color in DEFAULT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            # Note: #888 is a medium gray for button borders, kept as-is (no semantic equivalent)
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            btn.clicked.connect(lambda checked, c=color: self._set_color(c))
            quick_color_layout.addWidget(btn)

        quick_color_layout.addStretch()
        layout.addWidget(quick_color_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Set initial preview
        self._update_preview()

        # Set minimum size
        self.setMinimumWidth(400)

    def _update_color_button(self) -> None:
        """Update the color button appearance."""
        # Note: #888 is a medium gray for button borders, kept as-is (no semantic equivalent)
        self._color_button.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid #888;"
        )
        self._color_label.setText(self._color.name())

    def _choose_color(self) -> None:
        """Open color picker dialog."""
        color = QColorDialog.getColor(self._color, self, "Choose Highlight Color")
        if color.isValid():
            self._set_color(color)

    def _set_color(self, color: QColor) -> None:
        """Set the current color.

        Args:
            color: The color to set.
        """
        self._color = color
        self._update_color_button()
        self._update_preview()

    def _update_preview(self) -> None:
        """Update the preview label."""
        text = self._text_edit.text().strip()
        if not text:
            self._preview_label.setText("Enter a pattern to see preview")
            self._preview_label.setStyleSheet("padding: 8px;")
            return

        # Show highlighted preview
        is_regex = self._regex_check.isChecked()
        pattern_type = "regex" if is_regex else "text"

        # Create a sample highlighted text
        sample_text = f"Sample text with '{text}' highlighted ({pattern_type} match)"

        # Apply highlight style
        highlight_style = f"background-color: {self._color.name()};"
        self._preview_label.setText(
            f"<span>Sample: </span>"
            f"<span style='{highlight_style}'>{text}</span>"
            f"<span> (highlighted)</span>"
        )
        self._preview_label.setStyleSheet("padding: 8px;")

    def _on_accept(self) -> None:
        """Handle accept button."""
        if not self.get_text().strip():
            self._text_edit.setFocus()
            return
        self.accept()

    def get_text(self) -> str:
        """Get pattern text.

        Returns:
            Pattern text string.
        """
        return self._text_edit.text().strip()

    def get_color(self) -> QColor:
        """Get highlight color.

        Returns:
            QColor for highlighting.
        """
        return self._color

    def is_regex(self) -> bool:
        """Check if pattern is regex.

        Returns:
            True if pattern should be treated as regex.
        """
        return self._regex_check.isChecked()

    def set_text(self, text: str) -> None:
        """Set pattern text.

        Args:
            text: Pattern text.
        """
        self._text_edit.setText(text)

    def set_color(self, color: QColor) -> None:
        """Set highlight color.

        Args:
            color: QColor for highlighting.
        """
        self._set_color(color)

    def set_regex(self, is_regex: bool) -> None:
        """Set regex mode.

        Args:
            is_regex: Whether pattern is regex.
        """
        self._regex_check.setChecked(is_regex)