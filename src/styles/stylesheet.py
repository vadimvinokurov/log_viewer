"""Centralized QSS stylesheet for Log Viewer application.

This module provides cross-platform compatible styles for all UI components.
Uses Qt's system default fonts for native look-and-feel.

Ref: docs/specs/features/typography-system.md §4.1
Ref: docs/specs/features/ui-design-system.md §2.2
"""
from __future__ import annotations

from src.constants.colors import (
    BaseColors,
    PaletteColors,
    StatsColors,
    UIColors,
)
from src.constants.typography import Typography


# =============================================================================
# Shared Style Constants for Panel Content
# =============================================================================

# Ref: docs/specs/features/panel-content-unified-styles.md §3.2
# These colors are used by both QTreeView (Categories) and QListWidget (Filters/Highlights)
# to ensure consistent styling across all panel content tabs.
# Ref: docs/specs/global/color-palette.md §10.3
PANEL_CONTENT_BG = UIColors.BACKGROUND_SECONDARY       # Background Secondary
PANEL_CONTENT_HOVER = UIColors.BACKGROUND_HOVER        # Background Hover
PANEL_CONTENT_SELECTION = UIColors.BACKGROUND_SELECTED  # Selection Highlight
PANEL_CONTENT_TEXT = UIColors.TEXT_SELECTED            # Selected text color


def get_application_stylesheet() -> str:
    """Get the main application stylesheet.
    
    Uses system default font family. Qt uses the application font
    automatically for sizing.
    
    Ref: docs/specs/features/typography-system.md §4.1
    Ref: docs/specs/features/ui-design-system.md §2.2
    Ref: docs/specs/global/color-palette.md §10.3
    
    Returns:
        QSS stylesheet string for the entire application.
    """
    return f"""
        /* Main Application */
        QMainWindow {{
            background-color: {UIColors.BACKGROUND_TERTIARY};
        }}
        
        /* Global Widget Styling */
        QWidget {{
            font-family: {Typography.PRIMARY};
            color: {UIColors.TEXT_PRIMARY};
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {UIColors.BACKGROUND_SECONDARY};
            border-bottom: 1px solid {UIColors.BORDER_DEFAULT};
            padding: 2px;
        }}
        
        QMenuBar::item {{
            padding: 4px 8px;
            background-color: transparent;
        }}
        
        QMenuBar::item:selected {{
            background-color: {UIColors.BACKGROUND_HOVER};
        }}
        
        QMenu {{
            background-color: {UIColors.BACKGROUND_PRIMARY};
            border: 1px solid {UIColors.BORDER_DEFAULT};
        }}
        
        QMenu::item {{
            padding: 4px 24px 4px 8px;
        }}
        
        QMenu::item:selected {{
            background-color: {UIColors.BACKGROUND_SELECTED};
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {UIColors.BACKGROUND_SECONDARY};
            border-top: 1px solid {UIColors.BORDER_DEFAULT};
            min-height: 24px;
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: {UIColors.TOOLTIP_BACKGROUND};
            color: {UIColors.TOOLTIP_TEXT};
            border: 1px solid {UIColors.TOOLTIP_BORDER};
            padding: 4px;
            border-radius: 2px;
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: {UIColors.BACKGROUND_TERTIARY};
            width: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {UIColors.BORDER_DEFAULT};
            min-height: 20px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {UIColors.BORDER_HOVER};
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
            background-color: {UIColors.BACKGROUND_PRIMARY};
            border: 1px solid {UIColors.BORDER_DEFAULT};
            border-radius: 3px;
            padding: 4px 6px;
            selection-background-color: {UIColors.BACKGROUND_SELECTED};
        }}
        
        QLineEdit:focus {{
            border: 1px solid {UIColors.BORDER_FOCUS};
        }}
        
        QLineEdit:disabled {{
            background-color: {UIColors.BACKGROUND_SECONDARY};
            color: {UIColors.TEXT_DISABLED};
        }}
        
        /* Push Button */
        QPushButton {{
            background-color: {UIColors.BACKGROUND_SECONDARY};
            border: 1px solid {UIColors.BORDER_DEFAULT};
            border-radius: 3px;
            padding: 4px 12px;
            min-width: 60px;
        }}
        
        QPushButton:hover {{
            background-color: {UIColors.BACKGROUND_HOVER};
            border: 1px solid {UIColors.BORDER_HOVER};
        }}
        
        QPushButton:pressed {{
            background-color: {UIColors.BACKGROUND_ACTIVE};
        }}
        
        QPushButton:disabled {{
            background-color: {UIColors.BACKGROUND_SECONDARY};
            color: {UIColors.TEXT_DISABLED};
            border: 1px solid {UIColors.BORDER_DISABLED};
        }}
        
        /* Combo Box */
        QComboBox {{
            background-color: {UIColors.BACKGROUND_PRIMARY};
            border: 1px solid {UIColors.BORDER_DEFAULT};
            border-radius: 3px;
            padding: 4px 8px;
            min-width: 80px;
        }}
        
        QComboBox:hover {{
            border: 1px solid {UIColors.BORDER_HOVER};
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
            background-color: {UIColors.BACKGROUND_PRIMARY};
            border: 1px solid {UIColors.BORDER_DEFAULT};
            selection-background-color: {UIColors.BACKGROUND_SELECTED};
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: {UIColors.BORDER_DEFAULT};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {UIColors.BORDER_FOCUS};
        }}
    """


def get_table_stylesheet() -> str:
    """Get the stylesheet for log table view.
    
    Uses system default fonts. Font for message column is set via
    Qt.FontRole in LogTableModel.data(), not via QSS.
    
    Ref: docs/specs/features/typography-system.md §4.1
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    Ref: docs/specs/features/table-unified-styles.md §8
    Ref: docs/specs/global/color-palette.md §10.3
    
    Returns:
        QSS stylesheet string for QTableWidget.
    """
    return f"""
        /* Table View Container */
        QTableWidget {{
            background-color: {PaletteColors.GRAY_2};
            border: 1px solid {UIColors.BORDER_DEFAULT};
            gridline-color: {UIColors.BACKGROUND_HOVER};
            selection-background-color: {UIColors.BACKGROUND_SELECTED};
            selection-color: {UIColors.TEXT_SELECTED};
        }}
        
        /* Table Rows */
        QTableWidget::item {{
            padding: 0;
            background-color: {PaletteColors.GRAY_2};
            border: none;
            border-bottom: 1px solid {UIColors.BACKGROUND_HOVER};
        }}
        
        /* Hover State - same as default (no visual change) */
        QTableWidget::item:hover {{
            background-color: {PaletteColors.GRAY_2};
        }}
        
        /* Selected State */
        QTableWidget::item:selected {{
            background-color: {UIColors.BACKGROUND_SELECTED};
            color: {UIColors.TEXT_SELECTED};
        }}
        
        /* Selected + Hover */
        QTableWidget::item:selected:hover {{
            background-color: {UIColors.BACKGROUND_SELECTED};
        }}
        
        /* Table Header - Unified with Row Style */
        QHeaderView::section {{
            font-family: {Typography.PRIMARY};
            font-weight: normal;
            font-size: inherit;
            padding: 0;
            background-color: {UIColors.BACKGROUND_SECONDARY};
            border: none;
            border-bottom: 1px solid {UIColors.BORDER_DEFAULT};
            border-right: 1px solid {UIColors.BACKGROUND_HOVER};
            text-align: center;
        }}
        
        /* Last column - no right border */
        QHeaderView::section:last {{
            border-right: none;
        }}
    """


def get_tab_stylesheet() -> str:
    """Get the stylesheet for tab widgets.
    
    Ref: docs/specs/global/color-palette.md §10.3
    
    Returns:
        QSS stylesheet string for QTabWidget.
    """
    return f"""
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {UIColors.BORDER_DEFAULT};
            background-color: {UIColors.BACKGROUND_PRIMARY};
        }}
        
        /* Tab Bar */
        QTabBar::tab {{
            background-color: {UIColors.BACKGROUND_HOVER};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 6px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {UIColors.BACKGROUND_TERTIARY};
            border-bottom: 2px solid {UIColors.BORDER_FOCUS};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {UIColors.BACKGROUND_TERTIARY};
        }}
        
        /* Close button on tabs */
        QTabBar::close-button {{
            image: none;
            subcontrol-position: right;
            margin-right: 4px;
        }}
        
        QTabBar::close-button:hover {{
            background-color: {UIColors.BACKGROUND_HOVER};
            border-radius: 2px;
        }}
    """


def get_tree_stylesheet() -> str:
    """Get the stylesheet for tree views.
    
    Uses shared panel content colors for consistency with list widgets.
    
    Ref: docs/specs/features/panel-content-unified-styles.md §3.3
    
    Returns:
        QSS stylesheet string for QTreeView.
    """
    return f"""
        /* Tree View */
        QTreeView {{
            background-color: {PANEL_CONTENT_BG};
            border: none;
            selection-background-color: {PANEL_CONTENT_SELECTION};
            selection-color: {PANEL_CONTENT_TEXT};
        }}
        
        /* Ref: docs/specs/features/category-tree-row-unification.md §6.2 */
        /* Padding: 0 for visual consistency with table rows */
        QTreeView::item {{
            padding: 0;
            border: none;
        }}
        
        QTreeView::item:selected {{
            background-color: {PANEL_CONTENT_SELECTION};
            color: {PANEL_CONTENT_TEXT};
        }}
        
        QTreeView::item:hover {{
            background-color: {PANEL_CONTENT_HOVER};
        }}
        
        /* Branch indicators - indentation controlled via QTreeView.setIndentation() */
        /* Ref: docs/specs/features/category-panel-styles.md §7.3.1 */
        /* Note: QSS width on QTreeView::branch does not work - use setIndentation() instead */
    """


def get_panel_list_stylesheet() -> str:
    """Get the stylesheet for panel content list widgets.
    
    Used by Filters and Highlights tabs to ensure consistent
    styling with the Categories tree view.
    
    Uses shared panel content colors for consistency with tree views.
    
    Ref: docs/specs/features/panel-content-unified-styles.md §3.4
    
    Returns:
        QSS stylesheet string for QListWidget.
    """
    return f"""
        /* Panel Content List - unified with tree view styling */
        QListWidget {{
            background-color: {PANEL_CONTENT_BG};
            border: none;
        }}
        
        /* List Items - unified with tree items */
        QListWidget::item {{
            padding: 0;
            border: none;
        }}
        
        QListWidget::item:hover {{
            background-color: {PANEL_CONTENT_HOVER};
        }}
        
        QListWidget::item:selected {{
            background-color: {PANEL_CONTENT_SELECTION};
            color: {PANEL_CONTENT_TEXT};
        }}
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
    
    Ref: docs/specs/global/color-palette.md §10.3
    
    Returns:
        QSS stylesheet string for search input.
    """
    return f"""
        SearchInput {{
            background-color: {UIColors.BACKGROUND_PRIMARY};
            border: 1px solid {UIColors.BORDER_DEFAULT};
            border-radius: 3px;
            padding: 4px 6px;
        }}
        
        SearchInput:focus {{
            border: 1px solid {UIColors.BORDER_FOCUS};
        }}
        
        SearchInput QLabel {{
            background-color: transparent;
            color: {UIColors.TEXT_SECONDARY};
        }}
    """


def get_toolbar_stylesheet() -> str:
    """Get the stylesheet for toolbar areas.
    
    Ref: docs/specs/global/color-palette.md §10.3
    
    Returns:
        QSS stylesheet string for toolbar.
    """
    return f"""
        /* Toolbar */
        QToolBar {{
            background-color: {UIColors.BACKGROUND_SECONDARY};
            border: none;
            border-bottom: 1px solid {UIColors.BORDER_DEFAULT};
            padding: 4px;
            spacing: 4px;
        }}
        
        QToolBar::separator {{
            background-color: {UIColors.BORDER_DEFAULT};
            width: 1px;
            margin: 4px 8px;
        }}
        
        QToolBar QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 3px;
            padding: 4px;
        }}
        
        QToolBar QToolButton:hover {{
            background-color: {UIColors.BACKGROUND_HOVER};
            border: 1px solid {UIColors.BORDER_DEFAULT};
        }}
        
        QToolBar QToolButton:pressed {{
            background-color: {UIColors.BACKGROUND_ACTIVE};
        }}
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


def get_expand_collapse_button_stylesheet() -> str:
    """Get stylesheet for expand/collapse button.
    
    Returns:
        QSS stylesheet string for the expand/collapse button.
    
    // Ref: docs/specs/features/category-tree-expand-collapse.md §6.3
    """
    return """
QPushButton#expandCollapseButton {
    background-color: #F5F5F5;
    border: 1px solid #C0C0C0;
    border-radius: 3px;
    padding: 4px;
    min-width: 32px;
    max-width: 32px;
    color: #333333;
}

QPushButton#expandCollapseButton:hover {
    background-color: #E8E8E8;
    border: 1px solid #A0A0A0;
}

QPushButton#expandCollapseButton:pressed {
    background-color: #D0D0D0;
}

QPushButton#expandCollapseButton:focus {
    border: 1px solid #0066CC;
}
"""