"""Side panel with Categories, Filters, Highlights tabs."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QWidget

from log_viewer.gui.category_tree import CategoryTreeWidget
from log_viewer.gui.filter_list import FilterListWidget
from log_viewer.gui.highlight_list import HighlightListWidget


class SidePanel(QTabWidget):
    """Collapsible side panel with three tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.category_tree = CategoryTreeWidget()
        self.filter_list = FilterListWidget()
        self.highlight_list = HighlightListWidget()

        self.addTab(self.category_tree, "Categories")
        self.addTab(self.filter_list, "Filters")
        self.addTab(self.highlight_list, "Highlights")
