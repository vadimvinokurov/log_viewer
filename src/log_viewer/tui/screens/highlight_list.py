"""HighlightListScreen — modal showing active highlights.

Triggered by :lsh command.
Format:
    Active highlights (2):
      1. :h ERROR [red]
      2. :h/color=yellow/WARNING
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from log_viewer.core.models import Highlight, SearchMode


def _format_highlight(h: Highlight, index: int) -> str:
    """Format a highlight for display."""
    cmd = "h" if h.mode == SearchMode.PLAIN else ("hr" if h.mode == SearchMode.REGEX else "hs")
    color = h.color
    if h.case_sensitive and color != "red":
        return f"  {index}. :{cmd}/cs,color={color}/{h.pattern}"
    elif h.case_sensitive:
        return f"  {index}. :{cmd}/cs/{h.pattern}"
    elif color != "red":
        return f"  {index}. :{cmd}/color={color}/{h.pattern}"
    else:
        return f"  {index}. :{cmd} {h.pattern}"


class HighlightListScreen(ModalScreen[None]):
    """Modal screen showing active highlights."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def __init__(self, highlights: list[Highlight]) -> None:
        super().__init__()
        self._highlights = highlights

    def compose(self) -> ComposeResult:
        with Vertical(id="highlight-list-dialog"):
            if not self._highlights:
                yield Label("No active highlights")
            else:
                yield Label(f"Active highlights ({len(self._highlights)}):")
                for i, h in enumerate(self._highlights, 1):
                    yield Label(_format_highlight(h, i))
            yield Label("[dim]Press Esc to close[/dim]")

    def action_dismiss(self) -> None:
        self.dismiss(None)
