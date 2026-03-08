"""Find in results dialog."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QWidget
)
from PySide6.QtCore import Signal, Qt


class FindDialog(QDialog):
    """Dialog for finding text in results."""

    # Signals
    find_requested = Signal(str, bool)  # text, case_sensitive
    find_next = Signal()
    find_previous = Signal()
    highlight_all = Signal(str, bool)  # text, case_sensitive
    clear_highlights = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the find dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Find in Results")
        self._current_match = 0
        self._total_matches = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Set dialog properties
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Search input row
        input_layout = QHBoxLayout()

        search_label = QLabel("Find:")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Enter search text...")
        self._search_input.setMinimumWidth(250)

        input_layout.addWidget(search_label)
        input_layout.addWidget(self._search_input, 1)

        layout.addLayout(input_layout)

        # Options row
        options_layout = QHBoxLayout()

        self._case_sensitive_check = QCheckBox("Case sensitive")
        options_layout.addWidget(self._case_sensitive_check)

        options_layout.addStretch()

        # Match count label
        self._match_label = QLabel("No matches")
        options_layout.addWidget(self._match_label)

        layout.addLayout(options_layout)

        # Buttons row
        buttons_layout = QHBoxLayout()

        self._find_previous_btn = QPushButton("Previous")
        self._find_previous_btn.setToolTip("Find previous match (Shift+Enter)")
        self._find_next_btn = QPushButton("Next")
        self._find_next_btn.setToolTip("Find next match (Enter)")
        self._highlight_all_btn = QPushButton("Highlight All")
        self._close_btn = QPushButton("Close")

        self._find_previous_btn.setEnabled(False)
        self._find_next_btn.setEnabled(False)

        buttons_layout.addWidget(self._highlight_all_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self._find_previous_btn)
        buttons_layout.addWidget(self._find_next_btn)
        buttons_layout.addWidget(self._close_btn)

        layout.addLayout(buttons_layout)

        # Set focus to search input
        self._search_input.setFocus()

    def _connect_signals(self) -> None:
        """Connect button signals."""
        self._find_next_btn.clicked.connect(self._on_find_next)
        self._find_previous_btn.clicked.connect(self._on_find_previous)
        self._highlight_all_btn.clicked.connect(self._on_highlight_all)
        self._close_btn.clicked.connect(self.close)

        # Enable/disable buttons based on text
        self._search_input.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str) -> None:
        """Handle text change in search input.

        Args:
            text: The new text.
        """
        has_text = bool(text)
        self._find_next_btn.setEnabled(has_text)
        self._find_previous_btn.setEnabled(has_text)
        self._highlight_all_btn.setEnabled(has_text)

        if not has_text:
            self.clear_highlights.emit()
            self._update_match_count(0, 0)

    def _on_find_next(self) -> None:
        """Handle find next button click."""
        text = self._search_input.text()
        if text:
            case_sensitive = self._case_sensitive_check.isChecked()
            self.find_requested.emit(text, case_sensitive)
            self.find_next.emit()

    def _on_find_previous(self) -> None:
        """Handle find previous button click."""
        text = self._search_input.text()
        if text:
            case_sensitive = self._case_sensitive_check.isChecked()
            self.find_requested.emit(text, case_sensitive)
            self.find_previous.emit()

    def _on_highlight_all(self) -> None:
        """Handle highlight all button click."""
        text = self._search_input.text()
        if text:
            case_sensitive = self._case_sensitive_check.isChecked()
            self.highlight_all.emit(text, case_sensitive)

    def keyPressEvent(self, event) -> None:
        """Handle key press events.

        Args:
            event: Key event.
        """
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            # Enter: find next
            # Shift+Enter: find previous
            if event.modifiers() & Qt.ShiftModifier:
                self._on_find_previous()
            else:
                self._on_find_next()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.clear_highlights.emit()
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def update_match_count(self, current: int, total: int) -> None:
        """Update displayed match count.

        Args:
            current: Current match index (1-based).
            total: Total number of matches.
        """
        self._current_match = current
        self._total_matches = total
        self._update_match_label()

    def _update_match_count(self, current: int, total: int) -> None:
        """Update displayed match count (internal method).

        Args:
            current: Current match index (1-based).
            total: Total number of matches.
        """
        self._current_match = current
        self._total_matches = total
        self._update_match_label()

    def _update_match_label(self) -> None:
        """Update the match label text."""
        if self._total_matches == 0:
            self._match_label.setText("No matches")
        else:
            self._match_label.setText(f"{self._current_match} of {self._total_matches}")

    def get_search_text(self) -> str:
        """Get the current search text.

        Returns:
            The search text.
        """
        return self._search_input.text()

    def is_case_sensitive(self) -> bool:
        """Check if case-sensitive search is enabled.

        Returns:
            True if case-sensitive, False otherwise.
        """
        return self._case_sensitive_check.isChecked()

    def set_search_text(self, text: str) -> None:
        """Set the search text.

        Args:
            text: The text to search for.
        """
        self._search_input.setText(text)

    def clear_search(self) -> None:
        """Clear the search input and highlights."""
        self._search_input.clear()
        self.clear_highlights.emit()
        self._update_match_count(0, 0)