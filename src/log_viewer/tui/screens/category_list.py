"""CategoryListScreen — modal showing the full category tree with enable/disable state.

Triggered by :lscat command.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import CategoryNode


def _format_tree(node: CategoryNode, indent: int = 0) -> list[str]:
    """Format category tree as indented lines with icons and counts."""
    lines: list[str] = []
    prefix = "  " * indent
    for name, child in sorted(node.children.items()):
        icon = "✅" if child.enabled else "❌"
        lines.append(f"{prefix}{icon} {name} ({child.line_count})")
        if child.children:
            lines.extend(_format_tree(child, indent + 1))
    return lines


class CategoryListScreen(ModalScreen[None]):
    """Modal screen showing the full category tree with enable/disable state."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def __init__(self, store: LogStore) -> None:
        super().__init__()
        self._store = store

    def compose(self) -> ComposeResult:
        with Vertical(id="category-list-dialog"):
            yield Label(f"Categories ({len(self._store.category_counts)}):")
            tree_lines = _format_tree(self._store.category_tree)
            if tree_lines:
                for line in tree_lines:
                    yield Label(line)
            else:
                yield Label("No categories loaded")
            yield Label("[dim]Press Esc to close[/dim]")

    def action_dismiss(self) -> None:
        self.dismiss(None)
