"""Side panel with Categories, Filters, Highlights, Pinned tabs."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QWidget

from log_viewer.core.themes import _t
from log_viewer.gui.category_tree import CategoryTreeWidget
from log_viewer.gui.filter_list import FilterListWidget
from log_viewer.gui.highlight_list import HighlightListWidget
from log_viewer.gui.pinned_list import PinnedListWidget


class SidePanel(QTabWidget):
    """Collapsible side panel with four tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.category_tree = CategoryTreeWidget()
        self.filter_list = FilterListWidget()
        self.highlight_list = HighlightListWidget()
        self.pinned_list = PinnedListWidget()

        self.addTab(self.category_tree, "Categories")
        self.addTab(self.filter_list, "Filters")
        self.addTab(self.highlight_list, "Highlights")
        self.addTab(self.pinned_list, "Pinned")

        self.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: none;
                background-color: {_t('panel')};
            }}
            QTabBar::tab {{
                background-color: {_t('tab_bg')};
                color: {_t('graphite')};
                padding: 6px 14px;
                border: none;
                border-radius: 8px;
                margin-right: 2px;
                font-weight: 500;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background-color: {_t('card')};
                color: {_t('ink')};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {_t('silver_mist')};
                color: {_t('ink')};
            }}
            """
        )
