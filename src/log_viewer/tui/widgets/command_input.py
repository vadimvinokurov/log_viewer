"""CommandInput widget — command bar with file path autocomplete for :open."""

from __future__ import annotations

from textual.widgets import Input

from log_viewer.core.suggester import FilePathSuggester


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
        super().__init__(
            select_on_focus=False,
            suggester=FilePathSuggester(),
        )

    def key_escape(self) -> None:
        """Cancel input and return focus to LogPanel."""
        self.value = ""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            app._return_to_log_panel()

    def check_consume_key(self, key: str, character: str | None) -> bool:
        """Consume Tab when a suggestion is available to prevent focus cycling."""
        if key == "tab":
            return True
        return super().check_consume_key(key, character)

    def key_tab(self) -> None:
        """Accept the current suggestion, if any."""
        if self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)

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
