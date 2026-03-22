"""Worker thread for loading documents.

This module provides a QThread-based worker for loading documents
in the background without blocking the UI.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from beartype import beartype

from src.models.log_document import LogDocument


class IndexWorker(QThread):
    """Worker thread for loading documents."""

    progress = Signal(int, int)  # bytes_read, total_bytes
    finished = Signal()

    @beartype
    def __init__(self, document: LogDocument) -> None:
        """Initialize the worker.

        Args:
            document: The document to load
        """
        super().__init__()
        self._document = document

    def run(self) -> None:
        """Run the loading process."""
        self._document.load(self._on_progress)
        self.finished.emit()

    @beartype
    def _on_progress(self, bytes_read: int, total_bytes: int) -> None:
        """Report progress.

        Args:
            bytes_read: Number of bytes read so far
            total_bytes: Total bytes to read
        """
        self.progress.emit(bytes_read, total_bytes)