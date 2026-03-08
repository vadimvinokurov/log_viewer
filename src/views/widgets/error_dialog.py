"""Error dialog for displaying errors."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


class ErrorDialog(QDialog):
    """Dialog for displaying error messages.

    Provides a user-friendly error dialog with an expandable details
    section for showing stack traces and technical information.
    """

    def __init__(
        self,
        title: str,
        message: str,
        details: str = "",
        parent: QWidget | None = None
    ) -> None:
        """Initialize the error dialog.

        Args:
            title: Dialog window title.
            message: User-friendly error message.
            details: Technical details/stack trace (optional).
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self._message = message
        self._details = details
        self._details_visible = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Set dialog properties
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Error icon and message
        message_layout = QHBoxLayout()

        # Error icon (using standard icon)
        icon_label = QLabel()
        icon = QGuiApplication.style().standardIcon(
            QGuiApplication.style().StandardPixmap.SP_MessageBoxCritical
        )
        icon_label.setPixmap(icon.pixmap(32, 32))
        message_layout.addWidget(icon_label, 0, Qt.AlignTop)

        # Error message
        message_label = QLabel(self._message)
        message_label.setWordWrap(True)
        message_layout.addWidget(message_label, 1)

        layout.addLayout(message_layout)

        # Details section (collapsible)
        if self._details:
            self._details_widget = QWidget()
            details_layout = QVBoxLayout(self._details_widget)
            details_layout.setContentsMargins(0, 0, 0, 0)

            # Details text
            self._details_text = QTextEdit()
            self._details_text.setPlainText(self._details)
            self._details_text.setReadOnly(True)
            self._details_text.setMaximumHeight(150)
            # Disable horizontal scrollbar - wrap text instead
            self._details_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._details_text.setLineWrapMode(QTextEdit.WidgetWidth)
            details_layout.addWidget(self._details_text)

            # Copy details button
            copy_btn = QPushButton("Copy Details")
            copy_btn.clicked.connect(self._copy_details)
            details_layout.addWidget(copy_btn, 0, Qt.AlignRight)

            self._details_widget.setVisible(False)
            layout.addWidget(self._details_widget)

            # Show/Hide details button
            self._toggle_btn = QPushButton("Show Details")
            self._toggle_btn.clicked.connect(self._toggle_details)
            layout.addWidget(self._toggle_btn)

        # OK button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

    def _toggle_details(self) -> None:
        """Toggle the visibility of the details section."""
        self._details_visible = not self._details_visible
        self._details_widget.setVisible(self._details_visible)
        self._toggle_btn.setText(
            "Hide Details" if self._details_visible else "Show Details"
        )

        # Adjust dialog size
        self.adjustSize()

    def _copy_details(self) -> None:
        """Copy error details to clipboard."""
        if self._details:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self._details)

    @staticmethod
    def show_error(
        title: str,
        message: str,
        details: str = "",
        parent: QWidget | None = None
    ) -> None:
        """Show an error dialog.

        Args:
            title: Dialog window title.
            message: User-friendly error message.
            details: Technical details/stack trace (optional).
            parent: Parent widget.
        """
        dialog = ErrorDialog(title, message, details, parent)
        dialog.exec()