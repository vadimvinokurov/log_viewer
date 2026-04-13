"""FilterListScreen — modal showing active filters.

Triggered by :lsf command.
Format:
    Active filters (2):
      1. :f Some text
      2. :f/cs/Some text
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from log_viewer.core.models import Filter, SearchMode


def _format_filter(f: Filter, index: int) -> str:
    """Format a filter for display."""
    cmd = "f" if f.mode == SearchMode.PLAIN else ("fr" if f.mode == SearchMode.REGEX else "fs")
    if f.case_sensitive:
        return f"  {index}. :{cmd}/cs/{f.pattern}"
    return f"  {index}. :{cmd} {f.pattern}"


class FilterListScreen(ModalScreen[None]):
    """Modal screen showing active filters."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def __init__(self, filters: list[Filter]) -> None:
        super().__init__()
        self._filters = filters

    def compose(self) -> ComposeResult:
        with Vertical(id="filter-list-dialog"):
            if not self._filters:
                yield Label("No active filters")
            else:
                yield Label(f"Active filters ({len(self._filters)}):")
                for i, f in enumerate(self._filters, 1):
                    yield Label(_format_filter(f, i))
            yield Label("[dim]Press Esc to close[/dim]")

    def action_dismiss(self) -> None:
        self.dismiss(None)
