"""Context menu handler for log table view.

This module provides a context menu handler that can be attached
to a log table view to provide standard context menu actions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QWidget
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from src.views.log_table_view import LogTableView


class TableContextMenu:
    """Context menu handler for log table.
    
    This class handles the creation and display of context menus
    for the log table view, including copy, select all, and find actions.
    """
    
    def __init__(self, parent: QWidget, table_view: LogTableView) -> None:
        """Initialize the context menu handler.
        
        Args:
            parent: Parent widget for the menu.
            table_view: The log table view to operate on.
        """
        self._parent = parent
        self._table_view = table_view
    
    def show(self, position) -> None:
        """Show context menu at position.
        
        Args:
            position: Global position to show menu at.
        """
        menu = QMenu(self._parent)
        
        # Copy action
        copy_action = QAction("Copy", self._parent)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._table_view.copy_selected)
        menu.addAction(copy_action)
        
        # Select All action
        select_all_action = QAction("Select All", self._parent)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self._table_view.selectAll)
        menu.addAction(select_all_action)
        
        menu.addSeparator()
        
        # Find action
        find_action = QAction("Find in Results...", self._parent)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self._table_view.find_requested)
        menu.addAction(find_action)
        
        menu.exec(position)