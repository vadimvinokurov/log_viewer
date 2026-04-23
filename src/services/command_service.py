"""CommandService: routes ParsedCommand objects to the correct service calls."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QColor

from src.core.command_parser import ParsedCommand
from src.models.filter_state import FilterMode

_MODE_MAP: dict[str, FilterMode] = {
    "plain": FilterMode.PLAIN,
    "regex": FilterMode.REGEX,
    "simple": FilterMode.SIMPLE,
}


class CommandService:
    """Thin router that dispatches a ParsedCommand to the right service."""

    def __init__(
        self,
        filter_controller: object,
        highlight_service: object,
        log_table: object,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._filter_controller = filter_controller
        self._highlight_service = highlight_service
        self._log_table = log_table
        self._status_callback = status_callback
        self._direction: str = "forward"

    @property
    def direction(self) -> str:
        return self._direction

    def execute(self, cmd: ParsedCommand) -> None:
        _handlers: dict[str, Callable[[ParsedCommand], None]] = {
            "s": self._handle_search,
            "f": self._handle_filter,
            "h": self._handle_highlight,
            "rmf": self._handle_remove_filter,
            "rmh": self._handle_remove_highlight,
            "n": self._handle_next,
            "N": self._handle_prev,
        }
        handler = _handlers.get(cmd.action)
        if handler is not None:
            handler(cmd)

    # -- handlers --

    def _handle_search(self, cmd: ParsedCommand) -> None:
        self._direction = cmd.direction
        count = self._log_table.find_text(cmd.text, cmd.case_sensitive)
        if self._status_callback is not None:
            self._status_callback(f"{count} matches")

    def _handle_filter(self, cmd: ParsedCommand) -> None:
        mode = _MODE_MAP[cmd.mode]
        self._filter_controller.set_filter_text(cmd.text)
        self._filter_controller.set_filter_mode(mode)
        self._filter_controller.apply_filter()

    def _handle_highlight(self, cmd: ParsedCommand) -> None:
        color = QColor(cmd.color) if cmd.color else QColor("red")
        is_regex = cmd.mode == "regex"
        self._highlight_service.add_user_pattern(cmd.text, color, is_regex=is_regex)
        self._log_table.set_highlight_engine(
            self._highlight_service.get_combined_engine()
        )

    def _handle_remove_filter(self, cmd: ParsedCommand) -> None:
        if cmd.text:
            self._filter_controller.set_filter_text("")
            self._filter_controller.apply_filter()
        else:
            self._filter_controller.clear_filter()

    def _handle_remove_highlight(self, cmd: ParsedCommand) -> None:
        if cmd.text:
            self._highlight_service.remove_user_pattern(cmd.text)
        else:
            self._highlight_service.clear_all()
        self._log_table.set_highlight_engine(
            self._highlight_service.get_combined_engine()
        )

    def _handle_next(self, cmd: ParsedCommand) -> None:
        if self._direction == "forward":
            self._log_table.find_next()
        else:
            self._log_table.find_previous()

    def _handle_prev(self, cmd: ParsedCommand) -> None:
        if self._direction == "forward":
            self._log_table.find_previous()
        else:
            self._log_table.find_next()
