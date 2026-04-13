"""LogPanel widget — DataTable for displaying parsed log lines."""

from __future__ import annotations

from log_viewer.tui.key_bindings import VimDataTable


class LogPanel(VimDataTable):
    """DataTable for log lines with columns: Line, Timestamp, Level, Category, Message."""

    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()

    def on_mount(self) -> None:
        self.add_column("Line", width=6)
        self.add_column("Timestamp", width=13)
        self.add_column("Category", width=20)
        self.add_column("Message", width=200)
