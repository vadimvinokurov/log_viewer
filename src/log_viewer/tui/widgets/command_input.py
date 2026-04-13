"""CommandInput widget — minimal command bar for :open and :q."""

from __future__ import annotations

from textual.widgets import Input


class CommandInput(Input):
    """Input field for entering commands like :open and :q."""

    DEFAULT_CSS = """
    CommandInput, CommandInput:focus, CommandInput:hover {
        border: none;
        height: 1;
        width: 1fr;
        padding: 0;
        background: $surface;
    }
    """

    def __init__(self) -> None:
        super().__init__(select_on_focus=False)

    def key_escape(self) -> None:
        """Cancel input and return focus to LogPanel."""
        self.value = ""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            app._return_to_log_panel()

    def key_up(self) -> None:
        """Navigate command history up."""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            cmd = app._command_history.navigate_up()
            if cmd:
                self.value = cmd
                self.cursor_position = len(cmd)

    def key_down(self) -> None:
        """Navigate command history down."""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            cmd = app._command_history.navigate_down()
            self.value = cmd
            self.cursor_position = len(cmd)
