"""Filter toolbar."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent


class FilterInput(QLineEdit):
    """Custom line edit that emits signal only on Enter key."""

    def __init__(self, parent=None) -> None:
        """Initialize the filter input."""
        super().__init__(parent)
        self.setPlaceholderText("Enter filter text...")
        self.setMinimumWidth(300)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.

        Emits returnPressed on Enter key.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.returnPressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class FilterToolbar(QWidget):
    """Toolbar for filtering."""

    # Signals
    filter_changed = Signal(str, str)  # filter_text, mode
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        """Initialize the filter toolbar."""
        super().__init__(parent)
        self._filter_active = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Filter label
        filter_label = QLabel("Filter:")
        layout.addWidget(filter_label)

        # Filter input
        self._filter_input = FilterInput()
        self._filter_input.setToolTip(
            "Enter filter text and press Enter to apply.\n"
            "Use the dropdown to select filter mode."
        )
        self._filter_input.returnPressed.connect(self._on_filter_apply)
        layout.addWidget(self._filter_input)

        # Mode dropdown
        mode_label = QLabel("Mode:")
        layout.addWidget(mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Plain", "plain")
        self._mode_combo.addItem("Regex", "regex")
        self._mode_combo.addItem("Simple", "simple")
        self._mode_combo.setToolTip(
            "Plain: Case-insensitive substring search\n"
            "Regex: Python regular expression\n"
            "Simple: Custom query language (and, or, not)"
        )
        self._mode_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self._mode_combo)

        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.setToolTip("Apply filter (Enter)")
        apply_btn.clicked.connect(self._on_filter_apply)
        apply_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(apply_btn)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip("Clear filter")
        clear_btn.clicked.connect(self._on_filter_clear)
        clear_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(clear_btn)

        # Separator
        layout.addSpacing(16)

        # Refresh button
        refresh_btn = QPushButton("↻")
        refresh_btn.setToolTip("Refresh file (F5)")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self.refresh_requested)
        layout.addWidget(refresh_btn)

        # Filter status indicator
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self._status_label)

        # Stretch at end
        layout.addStretch()

    def _on_filter_apply(self) -> None:
        """Emit filter_changed signal with current values."""
        filter_text = self._filter_input.text()
        mode = self._mode_combo.currentData()
        self._filter_active = bool(filter_text)
        self._update_status()
        self.filter_changed.emit(filter_text, mode)

    def _update_status(self) -> None:
        """Update the filter status indicator."""
        if self._filter_active:
            self._status_label.setText("(filter active)")
            self._status_label.setStyleSheet("color: #0066cc; font-style: italic;")
        else:
            self._status_label.setText("")
            self._status_label.setStyleSheet("color: gray; font-style: italic;")

    def _on_filter_clear(self) -> None:
        """Clear the filter input and apply."""
        self._filter_input.clear()
        self._on_filter_apply()

    def get_filter_text(self) -> str:
        """Return current filter text."""
        return self._filter_input.text()

    def get_filter_mode(self) -> str:
        """Return current filter mode."""
        return self._mode_combo.currentData()

    def set_filter_text(self, text: str) -> None:
        """Set filter text without applying."""
        self._filter_input.setText(text)

    def set_filter_mode(self, mode: str) -> None:
        """Set filter mode by data value."""
        index = self._mode_combo.findData(mode)
        if index >= 0:
            self._mode_combo.setCurrentIndex(index)

    def set_focus(self) -> None:
        """Set focus to the filter input."""
        self._filter_input.setFocus()

    def set_filter_active(self, active: bool) -> None:
        """Set filter status indicator.

        Args:
            active: Whether a filter is active.
        """
        self._filter_active = active
        self._update_status()

    def is_filter_active(self) -> bool:
        """Check if a filter is active.

        Returns:
            True if filter is active.
        """
        return self._filter_active