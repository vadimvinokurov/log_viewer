"""File tabs widget for managing open files.

This module provides a tab widget for displaying open files
with close buttons and icons.
"""
from __future__ import annotations

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QTabWidget, QTabBar
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from src.styles.stylesheet import get_tab_stylesheet


class FileTab(QWidget):
    """A single file tab with icon, name, and close button.
    
    This widget is used as the tab title in the FileTabsWidget.
    """
    
    # Signal emitted when close button is clicked
    close_clicked = Signal()
    
    def __init__(
        self,
        filename: str,
        filepath: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the file tab.
        
        Args:
            filename: Display name for the tab.
            filepath: Full file path (optional).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._filename = filename
        self._filepath = filepath
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # File icon (using text for now, can be replaced with actual icon)
        self._icon_label = QLabel("📄")
        self._icon_label.setFixedWidth(16)
        layout.addWidget(self._icon_label)
        
        # Filename label
        self._name_label = QLabel(self._filename)
        self._name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._name_label)
        
        # Close button
        self._close_button = QPushButton("×")
        self._close_button.setFixedSize(16, 16)
        self._close_button.setFlat(True)
        self._close_button.setCursor(Qt.PointingHandCursor)
        self._close_button.setToolTip("Close tab")
        self._close_button.clicked.connect(self.close_clicked)
        layout.addWidget(self._close_button)
    
    def set_modified(self, modified: bool) -> None:
        """Set the modified indicator.
        
        Args:
            modified: Whether the file has been modified.
        """
        if modified:
            self._name_label.setText(f"{self._filename} *")
        else:
            self._name_label.setText(self._filename)
    
    def get_filename(self) -> str:
        """Get the filename.
        
        Returns:
            The filename string.
        """
        return self._filename
    
    def get_filepath(self) -> Optional[str]:
        """Get the file path.
        
        Returns:
            The file path or None.
        """
        return self._filepath


class FileTabsWidget(QWidget):
    """Tab widget for managing open files.
    
    Provides a tab bar with:
    - Default "Log Viewer" home tab
    - File tabs with close buttons
    - Active tab styling with underline
    """
    
    # Signals
    tab_close_requested = Signal(int)  # tab_index
    current_tab_changed = Signal(int)  # tab_index
    file_opened = Signal(str)  # filepath
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the file tabs widget.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._file_paths: dict[int, str] = {}  # tab_index -> filepath
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setStyleSheet(get_tab_stylesheet())
        
        # Connect signals
        self._tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tab_widget.currentChanged.connect(self._on_current_changed)
        
        # Add default home tab
        self._add_home_tab()
        
        layout.addWidget(self._tab_widget)
    
    def _add_home_tab(self) -> None:
        """Add the default home tab."""
        home_widget = QWidget()
        self._tab_widget.addTab(home_widget, "Log Viewer")
        # Don't show close button for home tab
        self._tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
    
    def add_file_tab(self, filepath: str) -> int:
        """Add a new file tab.
        
        Args:
            filepath: Path to the file.
        
        Returns:
            Index of the new tab.
        """
        # Check if file is already open
        for index, path in self._file_paths.items():
            if path == filepath:
                self._tab_widget.setCurrentIndex(index)
                return index
        
        # Create new tab
        filename = Path(filepath).name
        content_widget = QWidget()  # Placeholder for actual content
        
        # Create custom tab title
        tab_title = FileTab(filename, filepath)
        tab_title.close_clicked.connect(lambda: self._on_tab_close_requested(self._tab_widget.indexOf(content_widget)))
        
        # Add tab
        index = self._tab_widget.addTab(content_widget, "")
        self._tab_widget.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, tab_title)
        
        # Store filepath
        self._file_paths[index] = filepath
        
        # Set as current
        self._tab_widget.setCurrentIndex(index)
        
        self.file_opened.emit(filepath)
        
        return index
    
    def remove_tab(self, index: int) -> None:
        """Remove a tab by index.
        
        Args:
            index: Tab index to remove.
        """
        if index == 0:
            # Don't remove home tab
            return
        
        self._file_paths.pop(index, None)
        self._tab_widget.removeTab(index)
        
        # Reindex file paths
        new_paths: dict[int, str] = {}
        for old_index, path in sorted(self._file_paths.items()):
            new_index = old_index - 1 if old_index > index else old_index
            new_paths[new_index] = path
        self._file_paths = new_paths
    
    def set_current_tab(self, index: int) -> None:
        """Set the current tab by index.
        
        Args:
            index: Tab index to set as current.
        """
        self._tab_widget.setCurrentIndex(index)
    
    def get_current_tab_index(self) -> int:
        """Get the current tab index.
        
        Returns:
            Current tab index.
        """
        return self._tab_widget.currentIndex()
    
    def get_tab_count(self) -> int:
        """Get the total number of tabs.
        
        Returns:
            Number of tabs.
        """
        return self._tab_widget.count()
    
    def get_file_path(self, index: int) -> Optional[str]:
        """Get the file path for a tab.
        
        Args:
            index: Tab index.
        
        Returns:
            File path or None if not a file tab.
        """
        return self._file_paths.get(index)
    
    def get_current_file_path(self) -> Optional[str]:
        """Get the file path of the current tab.
        
        Returns:
            Current file path or None.
        """
        return self._file_paths.get(self._tab_widget.currentIndex())
    
    def _on_tab_close_requested(self, index: int) -> None:
        """Handle tab close request.
        
        Args:
            index: Tab index to close.
        """
        if index == 0:
            # Don't close home tab
            return
        
        self.tab_close_requested.emit(index)
    
    def _on_current_changed(self, index: int) -> None:
        """Handle current tab change.
        
        Args:
            index: New current tab index.
        """
        self.current_tab_changed.emit(index)
    
    def clear_all_tabs(self) -> None:
        """Clear all tabs except the home tab."""
        # Remove all tabs except home
        while self._tab_widget.count() > 1:
            self._tab_widget.removeTab(1)
        self._file_paths.clear()
    
    def set_tab_modified(self, index: int, modified: bool) -> None:
        """Set the modified state of a tab.
        
        Args:
            index: Tab index.
            modified: Whether the file has been modified.
        """
        if index <= 0 or index >= self._tab_widget.count():
            return
        
        tab_button = self._tab_widget.tabBar().tabButton(index, QTabBar.ButtonPosition.LeftSide)
        if isinstance(tab_button, FileTab):
            tab_button.set_modified(modified)