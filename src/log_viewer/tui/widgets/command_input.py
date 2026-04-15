"""CommandInput widget — command bar with Tab-cycling autocomplete for :open, :cate, :catd."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Input

from log_viewer.core.suggester import CommandSuggester

if TYPE_CHECKING:
    from log_viewer.core.log_store import LogStore


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
            suggester=CommandSuggester(),
        )
        self._cycle_matches: list[str] = []
        self._cycle_index: int = 0
        self._last_tab_value: str = ""

    def set_log_store(self, store: LogStore) -> None:
        """Provide LogStore reference for category autocomplete."""
        if self.suggester:
            self.suggester.log_store = store

    def key_escape(self) -> None:
        """Cancel input and return focus to LogPanel."""
        self.value = ""
        self._reset_cycle()
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
        """Cycle through all matching completions on repeated Tab presses."""
        if self.value == self._last_tab_value and self._cycle_matches:
            self._cycle_index = (self._cycle_index + 1) % len(self._cycle_matches)
        else:
            matches = self.suggester.get_all_suggestions(self.value)
            if not matches:
                return
            self._cycle_matches = matches
            self._cycle_index = 0

        self.value = self._cycle_matches[self._cycle_index]
        self._last_tab_value = self.value
        self.cursor_position = len(self.value)

    def _reset_cycle(self) -> None:
        self._cycle_matches = []
        self._cycle_index = 0
        self._last_tab_value = ""

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
