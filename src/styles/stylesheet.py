"""Centralized QSS stylesheet for Log Viewer application.

This module provides cross-platform compatible styles for all UI components.
Uses Qt's system default fonts for native look-and-feel.

Ref: docs/specs/features/typography-system.md §4.1
Ref: docs/specs/features/ui-design-system.md §2.2
"""
from __future__ import annotations

from src.constants.colors import StatsColors
from src.constants.typography import Typography


def get_application_stylesheet() -> str:
    """Get the main application stylesheet.
    
    Uses system default font family. Qt uses the application font
    automatically for sizing.
    
    Ref: docs/specs/features/typography-system.md §4.1
    Ref: docs/specs/features/ui-design-system.md §2.2
    
    Returns:
        QSS stylesheet string for the entire application.
    """
    return f"""
        /* Main Application */
        QMainWindow {{
            background-color: #f0f0f0;
        }}
        
        /* Global Widget Styling */
        QWidget {{
            font-family: {Typography.PRIMARY};
            color: #333333;
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: #f5f5f5;
            border-bottom: 1px solid #c0c0c0;
            padding: 2px;
        }}
        
        QMenuBar::item {{
            padding: 4px 8px;
            background-color: transparent;
        }}
        
        QMenuBar::item:selected {{
            background-color: #e0e0e0;
        }}
        
        QMenu {{
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
        }}
        
        QMenu::item {{
            padding: 4px 24px 4px 8px;
        }}
        
        QMenu::item:selected {{
            background-color: #dcebf7;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: #f5f5f5;
            border-top: 1px solid #c0c0c0;
            min-height: 24px;
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px;
            border-radius: 2px;
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: #f0f0f0;
            width: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: #c0c0c0;
            min-height: 20px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: #a0a0a0;
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background-color: transparent;
        }}
        
        /* Hide horizontal scrollbars globally */
        QScrollBar:horizontal {{
            height: 0;
            width: 0;
        }}
        
        QScrollBar::handle:horizontal {{
            height: 0;
            width: 0;
        }}
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
            height: 0;
        }}
        
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            height: 0;
            width: 0;
        }}
        
        /* Line Edit */
        QLineEdit {{
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 4px 6px;
            selection-background-color: #dcebf7;
        }}
        
        QLineEdit:focus {{
            border: 1px solid #0066cc;
        }}
        
        QLineEdit:disabled {{
            background-color: #f5f5f5;
            color: #999999;
        }}
        
        /* Push Button */
        QPushButton {{
            background-color: #f5f5f5;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 4px 12px;
            min-width: 60px;
        }}
        
        QPushButton:hover {{
            background-color: #e8e8e8;
            border: 1px solid #a0a0a0;
        }}
        
        QPushButton:pressed {{
            background-color: #d0d0d0;
        }}
        
        QPushButton:disabled {{
            background-color: #f5f5f5;
            color: #999999;
            border: 1px solid #d0d0d0;
        }}
        
        /* Combo Box */
        QComboBox {{
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 4px 8px;
            min-width: 80px;
        }}
        
        QComboBox:hover {{
            border: 1px solid #a0a0a0;
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            selection-background-color: #dcebf7;
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: #c0c0c0;
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: #0066cc;
        }}
    """


def get_table_stylesheet() -> str:
    """Get the stylesheet for log table view.
    
    Uses system default fonts. Font for message column is set via
    Qt.FontRole in LogTableModel.data(), not via QSS.
    
    Ref: docs/specs/features/typography-system.md §4.1
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    
    Returns:
        QSS stylesheet string for QTableWidget.
    """
    return """
        /* Table View */
        QTableWidget {
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            gridline-color: #e0e0e0;
            selection-background-color: #dcebf7;
            selection-color: #000000;
        }
        
        QTableWidget::item {
            padding: 0px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        QTableWidget::item:selected {
            background-color: #dcebf7;
            color: #000000;
        }
        
        /* Table Header */
        QHeaderView::section {
            font-family: """ + Typography.PRIMARY + """;
            font-weight: normal;
            background-color: #f5f5f5;
            border: none;
            border-bottom: 1px solid #c0c0c0;
            border-right: 1px solid #e0e0e0;
            padding: 0px;
            text-align: center;
        }
        
        QHeaderView::section:hover {
            background-color: #e8e8e8;
        }
    """


def get_tab_stylesheet() -> str:
    """Get the stylesheet for tab widgets.
    
    Returns:
        QSS stylesheet string for QTabWidget.
    """
    return """
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: #ffffff;
        }
        
        /* Tab Bar */
        QTabBar::tab {
            background-color: #e8e8e8;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 6px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #f0f0f0;
            border-bottom: 2px solid #0066cc;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #f0f0f0;
        }
        
        /* Close button on tabs */
        QTabBar::close-button {
            image: none;
            subcontrol-position: right;
            margin-right: 4px;
        }
        
        QTabBar::close-button:hover {
            background-color: #e0e0e0;
            border-radius: 2px;
        }
    """


def get_tree_stylesheet() -> str:
    """Get the stylesheet for tree views.
    
    Returns:
        QSS stylesheet string for QTreeView.
    """
    return """
        /* Tree View */
        QTreeView {
            background-color: #f5f5f5;
            border: none;
            selection-background-color: #dcebf7;
            selection-color: #000000;
        }
        
        QTreeView::item {
            padding: 2px 4px;
            border: none;
        }
        
        QTreeView::item:selected {
            background-color: #dcebf7;
            color: #000000;
        }
        
        QTreeView::item:hover {
            background-color: #e8e8e8;
        }
        
        /* Branch indicators */
        QTreeView::branch {
            background-color: transparent;
        }
        
        QTreeView::branch:has-children:!has-siblings:closed,
        QTreeView::branch:closed:has-children:has-siblings {
            background-color: transparent;
        }
        
        QTreeView::branch:open:has-children:!has-siblings,
        QTreeView::branch:open:has-children:has-siblings {
            background-color: transparent;
        }
        
        /* Checkbox styling */
        QTreeView::indicator {
            width: 14px;
            height: 14px;
        }
        
        QTreeView::indicator:unchecked {
            border: 1px solid #a0a0a0;
            background-color: #ffffff;
        }
        
        QTreeView::indicator:checked {
            border: 1px solid #0066cc;
            background-color: #0066cc;
        }
    """


def get_statistics_counter_stylesheet(
    bg_color: str,
    text_color: str,
    border_color: str | None = None
) -> str:
    """Get the stylesheet for a statistics counter widget.
    
    Args:
        bg_color: Background color (CSS color string).
        text_color: Text/icon color (CSS color string).
        border_color: Optional border color. Defaults to text_color.
    
    Returns:
        QSS stylesheet string for the counter widget.
    """
    if border_color is None:
        border_color = text_color
    
    return f"""
        StatisticsCounter {{
            background-color: {bg_color};
            border: 1px solid {border_color};
            border-radius: 3px;
            padding: 2px 8px;
        }}
        
        StatisticsCounter QLabel {{
            color: {text_color};
            font-weight: bold;
            background-color: transparent;
        }}
        
        StatisticsCounter:hover {{
            background-color: {bg_color};
            border: 1px solid {text_color};
        }}
    """


def get_search_input_stylesheet() -> str:
    """Get the stylesheet for search input fields.
    
    Returns:
        QSS stylesheet string for search input.
    """
    return """
        SearchInput {
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 4px 6px;
        }
        
        SearchInput:focus {
            border: 1px solid #0066cc;
        }
        
        SearchInput QLabel {
            background-color: transparent;
            color: #666666;
        }
    """


def get_toolbar_stylesheet() -> str:
    """Get the stylesheet for toolbar areas.
    
    Returns:
        QSS stylesheet string for toolbar.
    """
    return """
        /* Toolbar */
        QToolBar {
            background-color: #f5f5f5;
            border: none;
            border-bottom: 1px solid #c0c0c0;
            padding: 4px;
            spacing: 4px;
        }
        
        QToolBar::separator {
            background-color: #c0c0c0;
            width: 1px;
            margin: 4px 8px;
        }
        
        QToolBar QToolButton {
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 3px;
            padding: 4px;
        }
        
        QToolBar QToolButton:hover {
            background-color: #e8e8e8;
            border: 1px solid #c0c0c0;
        }
        
        QToolBar QToolButton:pressed {
            background-color: #d0d0d0;
        }
    """


def get_counter_style(counter_type: str) -> dict[str, str]:
    """Get the color scheme for a statistics counter.
    
    Args:
        counter_type: Type of counter (critical, error, warning, msg, debug, trace).
    
    Returns:
        Dictionary with 'bg', 'text', and 'border' color values.
    """
    # Map counter type strings to StatsColors attributes
    color_map = {
        "critical": {
            "bg": StatsColors.CRITICAL_BG,
            "text": StatsColors.CRITICAL_TEXT,
            "border": StatsColors.CRITICAL_BORDER,
        },
        "error": {
            "bg": StatsColors.ERROR_BG,
            "text": StatsColors.ERROR_TEXT,
            "border": StatsColors.ERROR_BORDER,
        },
        "warning": {
            "bg": StatsColors.WARNING_BG,
            "text": StatsColors.WARNING_TEXT,
            "border": StatsColors.WARNING_BORDER,
        },
        "msg": {
            "bg": StatsColors.MSG_BG,
            "text": StatsColors.MSG_TEXT,
            "border": StatsColors.MSG_BORDER,
        },
        "debug": {
            "bg": StatsColors.DEBUG_BG,
            "text": StatsColors.DEBUG_TEXT,
            "border": StatsColors.DEBUG_BORDER,
        },
        "trace": {
            "bg": StatsColors.TRACE_BG,
            "text": StatsColors.TRACE_TEXT,
            "border": StatsColors.TRACE_BORDER,
        },
    }
    return color_map.get(counter_type, color_map["msg"])


def get_collapsible_panel_stylesheet() -> str:
    """Get the stylesheet for collapsible panel toggle strip.
    
    Returns:
        QSS stylesheet string for the toggle strip.
    """
    return """
        /* Toggle Strip */
        ToggleStrip {
            background-color: #f0f0f0;
            border-top: 1px solid #c0c0c0;
            border-bottom: 1px solid #c0c0c0;
        }
        
        ToggleStrip:hover {
            background-color: #e0e0e0;
            border-top: 1px solid #a0a0a0;
            border-bottom: 1px solid #a0a0a0;
        }
        
        /* Collapsible Panel */
        CollapsiblePanel {
            background-color: transparent;
        }
        
        CollapsiblePanel QWidget {
            background-color: transparent;
        }
    """