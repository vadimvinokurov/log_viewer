"""Custom category dialog."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QDialogButtonBox,
    QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt


class CustomCategoryDialog(QDialog):
    """Dialog for creating/editing custom categories."""

    def __init__(
        self,
        parent=None,
        categories: Optional[list[str]] = None,
        name: str = "",
        pattern: str = "",
        parent_category: Optional[str] = None
    ) -> None:
        """Initialize the dialog.

        Args:
            parent: Parent widget.
            categories: List of available parent categories.
            name: Initial category name (for editing).
            pattern: Initial pattern (for editing).
            parent_category: Initial parent category selection.
        """
        super().__init__(parent)
        self.setWindowTitle("Custom Category")
        self._categories = categories or []
        self._setup_ui(name, pattern, parent_category)

    def _setup_ui(
        self,
        name: str,
        pattern: str,
        parent_category: Optional[str]
    ) -> None:
        """Set up the dialog UI.

        Args:
            name: Initial name.
            pattern: Initial pattern.
            parent_category: Initial parent selection.
        """
        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Name input
        self._name_edit = QLineEdit()
        self._name_edit.setText(name)
        self._name_edit.setPlaceholderText("Enter category name")
        form_layout.addRow("Name:", self._name_edit)

        # Pattern input
        self._pattern_edit = QLineEdit()
        self._pattern_edit.setText(pattern)
        self._pattern_edit.setPlaceholderText("Enter pattern to match in message")
        self._pattern_edit.textChanged.connect(self._update_preview)
        form_layout.addRow("Pattern:", self._pattern_edit)

        # Parent category dropdown
        self._parent_combo = QComboBox()
        self._parent_combo.addItem("(None)", None)  # No parent option
        for category in sorted(self._categories):
            self._parent_combo.addItem(category, category)

        # Select initial parent if provided
        if parent_category:
            index = self._parent_combo.findData(parent_category)
            if index >= 0:
                self._parent_combo.setCurrentIndex(index)

        form_layout.addRow("Parent:", self._parent_combo)

        layout.addLayout(form_layout)

        # Preview group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_label = QLabel("Enter a pattern to see preview")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("padding: 8px; background-color: #f0f0f0;")
        preview_layout.addWidget(self._preview_label)

        layout.addWidget(preview_group)

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

    def _update_preview(self) -> None:
        """Update the preview label."""
        pattern = self._pattern_edit.text().strip()
        if not pattern:
            self._preview_label.setText("Enter a pattern to see preview")
            self._preview_label.setStyleSheet("padding: 8px; background-color: #f0f0f0;")
            return

        # Show example match
        example_text = f"Example: Messages containing '{pattern}' will be categorized under this category"
        self._preview_label.setText(example_text)
        self._preview_label.setStyleSheet("padding: 8px; background-color: #e8f5e9;")

    def _on_accept(self) -> None:
        """Handle accept button."""
        if not self.get_name().strip():
            self._name_edit.setFocus()
            return
        if not self.get_pattern().strip():
            self._pattern_edit.setFocus()
            return
        self.accept()

    def get_name(self) -> str:
        """Get category name.

        Returns:
            Category name string.
        """
        return self._name_edit.text().strip()

    def get_pattern(self) -> str:
        """Get pattern string.

        Returns:
            Pattern string.
        """
        return self._pattern_edit.text().strip()

    def get_parent(self) -> Optional[str]:
        """Get parent category path.

        Returns:
            Parent category path or None if no parent selected.
        """
        data = self._parent_combo.currentData()
        return data if isinstance(data, str) else None

    def set_name(self, name: str) -> None:
        """Set category name.

        Args:
            name: Category name.
        """
        self._name_edit.setText(name)

    def set_pattern(self, pattern: str) -> None:
        """Set pattern string.

        Args:
            pattern: Pattern string.
        """
        self._pattern_edit.setText(pattern)

    def set_parent(self, parent: Optional[str]) -> None:
        """Set parent category.

        Args:
            parent: Parent category path or None.
        """
        if parent is None:
            self._parent_combo.setCurrentIndex(0)
        else:
            index = self._parent_combo.findData(parent)
            if index >= 0:
                self._parent_combo.setCurrentIndex(index)