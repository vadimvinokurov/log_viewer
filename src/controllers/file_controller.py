"""Controller for file operations.

This module provides the FileController class for managing file operations
including opening, closing, and watching log files.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal

from beartype import beartype

from src.models.log_document import LogDocument
from src.controllers.file_watcher import FileWatcher

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about an open file.
    
    Attributes:
        path: Path to the log file.
        document: The log document instance.
        is_modified: Whether the file has been modified.
    """
    path: Path
    document: LogDocument
    is_modified: bool = False


class FileController(QObject):
    """Controller for file operations.

    Handles:
    - Opening and closing log files
    - Managing recent files
    - File watching for changes
    - Tab management for open files

    Signals:
        file_opened: Emitted when a file is opened (FileInfo)
        file_closed: Emitted when a file is closed (Path)
        file_changed: Emitted when a file changes on disk (Path)
        file_removed: Emitted when a file is removed from disk (Path)
        recent_files_changed: Emitted when recent files list changes
        index_progress: Emitted during indexing (bytes_read, total_bytes)
        index_complete: Emitted when indexing is complete (filepath)
    """

    file_opened = Signal(object)  # FileInfo
    file_closed = Signal(object)  # Path
    file_changed = Signal(object)  # Path
    file_removed = Signal(object)  # Path
    recent_files_changed = Signal(list)  # list[Path]
    index_progress = Signal(int, int)  # bytes_read, total_bytes
    index_complete = Signal(str)  # filepath

    MAX_RECENT_FILES = 10

    @beartype
    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the file controller.

        Args:
            parent: Parent object.
        """
        super().__init__(parent)

        self._open_files: list[FileInfo] = []
        self._recent_files: list[Path] = []
        self._file_watcher = FileWatcher(self)
        self._current_file: Path | None = None
        self._auto_reload_enabled = True

        self._setup_file_watcher()

    def _setup_file_watcher(self) -> None:
        """Set up file watcher connections."""
        self._file_watcher.file_changed.connect(self._on_file_changed)
        self._file_watcher.file_removed.connect(self._on_file_removed)

    @beartype
    def open_file(self, filepath: str) -> LogDocument | None:
        """Open a log file.

        Args:
            filepath: Path to the log file.

        Returns:
            LogDocument if successful, None otherwise.
        """
        path = Path(filepath)

        # Check if already open
        for file_info in self._open_files:
            if file_info.path == path:
                self._current_file = path
                self.file_opened.emit(file_info)
                return file_info.document

        # Load file
        try:
            document = LogDocument(str(path))
        except Exception as e:
            logger.error(f"Failed to open file {filepath}: {e}")
            return None

        # Add to open files
        file_info = FileInfo(path=path, document=document)
        self._open_files.append(file_info)
        self._current_file = path

        # Add to recent files
        self._add_recent_file(path)

        # Start watching
        self._file_watcher.watch_file(str(path))

        # Emit signal
        self.file_opened.emit(file_info)

        logger.info(f"Opened file: {filepath}")
        return document

    @beartype
    def close_file(self, filepath: str) -> bool:
        """Close a log file.

        Args:
            filepath: Path to the log file.

        Returns:
            True if file was closed, False if not found.
        """
        path = Path(filepath)

        for i, file_info in enumerate(self._open_files):
            if file_info.path == path:
                # Stop watching
                if self._file_watcher.get_current_file() == str(path):
                    self._file_watcher.stop_watching()

                # Close document
                file_info.document.close()

                # Remove from open files
                self._open_files.pop(i)

                # Update current file
                if self._current_file == path:
                    self._current_file = None

                # Emit signal
                self.file_closed.emit(path)
                logger.info(f"Closed file: {filepath}")
                return True

        return False

    def close_current_file(self) -> bool:
        """Close the currently active file.

        Returns:
            True if file was closed, False if no current file.
        """
        if self._current_file:
            return self.close_file(str(self._current_file))
        return False

    @beartype
    def get_document(self, filepath: str) -> LogDocument | None:
        """Get document for a file path.

        Args:
            filepath: Path to the log file.

        Returns:
            LogDocument if open, None otherwise.
        """
        path = Path(filepath)
        for file_info in self._open_files:
            if file_info.path == path:
                return file_info.document
        return None

    def get_current_document(self) -> LogDocument | None:
        """Get the currently active document.

        Returns:
            Current LogDocument or None.
        """
        if self._current_file:
            return self.get_document(str(self._current_file))
        return None

    def get_current_file(self) -> Path | None:
        """Get the currently active file path.

        Returns:
            Current file path or None.
        """
        return self._current_file

    @beartype
    def set_current_file(self, filepath: str) -> None:
        """Set the currently active file.

        Args:
            filepath: Path to set as current.
        """
        self._current_file = Path(filepath)

    def get_open_files(self) -> list[Path]:
        """Get list of open file paths.

        Returns:
            List of open file paths.
        """
        return [f.path for f in self._open_files]

    def get_recent_files(self) -> list[Path]:
        """Get list of recent files.

        Returns:
            List of recent file paths.
        """
        return self._recent_files.copy()

    @beartype
    def load_recent_files(self, paths: list[str]) -> None:
        """Load recent files from settings.

        Args:
            paths: List of file path strings.
        """
        self._recent_files = [
            Path(p) for p in paths if Path(p).exists()
        ]
        self.recent_files_changed.emit(self._recent_files)

    def get_recent_files_paths(self) -> list[str]:
        """Get recent files as string paths for saving.

        Returns:
            List of file path strings.
        """
        return [str(p) for p in self._recent_files]

    def set_auto_reload(self, enabled: bool) -> None:
        """Enable or disable auto-reload.

        Args:
            enabled: Whether auto-reload is enabled.
        """
        self._auto_reload_enabled = enabled
        self._file_watcher.set_enabled(enabled)
        logger.debug(f"Auto-reload {'enabled' if enabled else 'disabled'}")

    def is_auto_reload_enabled(self) -> bool:
        """Check if auto-reload is enabled.

        Returns:
            True if auto-reload is enabled.
        """
        return self._auto_reload_enabled

    def is_file_open(self, filepath: str) -> bool:
        """Check if a file is currently open.

        Args:
            filepath: Path to check.

        Returns:
            True if file is open, False otherwise.
        """
        path = Path(filepath)
        return any(f.path == path for f in self._open_files)

    def has_open_files(self) -> bool:
        """Check if there are any open files.

        Returns:
            True if there are open files.
        """
        return len(self._open_files) > 0

    def build_index(
        self,
        filepath: str,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> None:
        """Build index for a document.

        Args:
            filepath: Path to the file.
            progress_callback: Optional callback for progress updates.
        """
        document = self.get_document(filepath)
        if document:
            document.build_index(progress_callback)
            self.index_complete.emit(filepath)

    def _add_recent_file(self, path: Path) -> None:
        """Add a file to recent files list.

        Args:
            path: Path to add.
        """
        # Remove if already exists
        if path in self._recent_files:
            self._recent_files.remove(path)

        # Add to front
        self._recent_files.insert(0, path)

        # Trim to max
        if len(self._recent_files) > self.MAX_RECENT_FILES:
            self._recent_files = self._recent_files[:self.MAX_RECENT_FILES]

        self.recent_files_changed.emit(self._recent_files)

    def _on_file_changed(self, filepath: str) -> None:
        """Handle file change event from watcher.

        Args:
            filepath: Path to changed file.
        """
        if not self._auto_reload_enabled:
            return

        path = Path(filepath)
        self.file_changed.emit(path)

    def _on_file_removed(self, filepath: str) -> None:
        """Handle file removal event from watcher.

        Args:
            filepath: Path to removed file.
        """
        path = Path(filepath)
        self.file_removed.emit(path)

    def stop_watching(self) -> None:
        """Stop watching the current file."""
        self._file_watcher.stop_watching()

    def cleanup(self) -> None:
        """Clean up resources.

        Closes all open files and stops file watching.
        """
        # Stop watching
        self._file_watcher.stop_watching()

        # Close all open files
        for file_info in self._open_files:
            try:
                file_info.document.close()
            except Exception as e:
                logger.warning(f"Error closing file {file_info.path}: {e}")

        self._open_files.clear()
        self._current_file = None

        logger.info("FileController cleaned up")