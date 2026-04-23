"""Views package."""
from src.views.category_panel import CategoryPanel

# Components
from src.views.components import CounterWidget
from src.views.find_dialog import FindDialog
from src.views.log_table_view import LogEntry, LogEntryDisplay, LogTableModel, LogTableView

# Main views
from src.views.main_window import MainWindow
from src.views.statistics_panel import StatisticsPanel

# Widgets
from src.views.widgets.statistics_bar import StatisticsBar

__all__ = [
    # Main classes
    "MainWindow",
    "LogTableView",
    "LogTableModel",
    "LogEntry",
    "LogEntryDisplay",

    # Widgets
    "StatisticsBar",
    "CounterWidget",

    # Other views
    "CategoryPanel",
    "StatisticsPanel",
    "FindDialog",
]
