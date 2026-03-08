"""File watcher for auto-reload."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QFileSystemWatcher

logger = logging.getLogger(__name__)


class FileWatcher(QObject):
    """Watches log file for changes.

    Monitors a log file for changes on disk and emits signals when
    the file is modified or removed. Supports enabling/disabling
    auto-reload functionality.
    """

    # Signals
    file_changed = Signal(str)  # filepath
    file_removed = Signal(str)  # filepath

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the file watcher.

        Args:
            parent: Parent object.
        """
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._current_file: str | None = None
        self._enabled = True
        self._setup_connections()

    def _setup_connections(self) -> None:
        """Connect watcher signals."""
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

    def watch_file(self, filepath: str) -> None:
        """Start watching a file.

        Args:
            filepath: Path to the file to watch.
        """
        # Stop watching current file if any
        self.stop_watching()

        if not Path(filepath).exists():
            logger.warning(f"File does not exist: {filepath}")
            return

        self._current_file = filepath

        # Watch the file itself
        self._watcher.addPath(filepath)

        # Also watch the parent directory to detect file deletion
        parent_dir = str(Path(filepath).parent)
        if parent_dir:
            self._watcher.addPath(parent_dir)

        logger.info(f"Started watching file: {filepath}")

    def stop_watching(self) -> None:
        """Stop watching current file."""
        if self._current_file:
            # Remove file from watcher
            if self._watcher.files():
                self._watcher.removePaths(self._watcher.files())

            # Remove directory from watcher
            if self._watcher.directories():
                self._watcher.removePaths(self._watcher.directories())

            logger.info(f"Stopped watching file: {self._current_file}")
            self._current_file = None

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-reload.

        Args:
            enabled: True to enable, False to disable.
        """
        self._enabled = enabled
        logger.debug(f"File watcher enabled: {enabled}")

    def is_enabled(self) -> bool:
        """Check if file watcher is enabled.

        Returns:
            True if enabled, False otherwise.
        """
        return self._enabled

    def get_current_file(self) -> str | None:
        """Get the currently watched file.

        Returns:
            The current file path or None.
        """
        return self._current_file

    def _on_file_changed(self, path: str) -> None:
        """Handle file change event.

        Args:
            path: Path to the changed file.
        """
        if not self._enabled:
            return

        if path == self._current_file:
            logger.info(f"File changed: {path}")
            self.file_changed.emit(path)

    def _on_directory_changed(self, path: str) -> None:
        """Handle directory change event (file deleted).

        Args:
            path: Path to the changed directory.
        """
        if not self._enabled:
            return

        if self._current_file:
            # Check if the current file still exists
            if not Path(self._current_file).exists():
                logger.info(f"File removed: {self._current_file}")
                self.file_removed.emit(self._current_file)
                self.stop_watching()

    def is_watching(self) -> bool:
        """Check if currently watching a file.

        Returns:
            True if watching a file, False otherwise.
        """
        return self._current_file is not None