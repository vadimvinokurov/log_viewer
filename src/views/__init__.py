"""Views package."""
from src.views.category_panel import CategoryPanel
from src.views.filter_toolbar import FilterToolbar
from src.views.statistics_panel import StatisticsPanel
from src.views.find_dialog import FindDialog

# Main views
from src.views.main_window import MainWindow
from src.views.log_table_view import LogTableView, LogTableModel, LogEntry, LogEntryDisplay

# Widgets
from src.views.widgets.search_toolbar import SearchToolbar, SearchInput, SearchToolbarWithStats
from src.views.widgets.statistics_bar import StatisticsBar

# Components
from src.views.components import CounterWidget

__all__ = [
    # Main classes
    "MainWindow",
    "LogTableView",
    "LogTableModel",
    "LogEntry",
    "LogEntryDisplay",
    
    # Widgets
    "SearchToolbar",
    "SearchInput",
    "SearchToolbarWithStats",
    "StatisticsBar",
    "CounterWidget",
    
    # Other views
    "CategoryPanel",
    "FilterToolbar",
    "StatisticsPanel",
    "FindDialog",
]