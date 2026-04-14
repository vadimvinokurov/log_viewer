"""Command suggester — file path completion for :open, category completion for :cate/:catd."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from textual.suggester import Suggester

if TYPE_CHECKING:
    from log_viewer.core.log_store import LogStore


class CommandSuggester(Suggester):
    """Suggest completions for commands: file paths for :open, categories for :cate/:catd."""

    def __init__(self) -> None:
        super().__init__(use_cache=False, case_sensitive=True)
        self.log_store: Optional[LogStore] = None

    async def get_suggestion(self, value: str) -> str | None:
        if value.startswith(":open "):
            return self._suggest_file(value)
        if value.startswith(":cate "):
            return self._suggest_category(value, ":cate ")
        if value.startswith(":catd "):
            return self._suggest_category(value, ":catd ")
        return None

    def _suggest_file(self, value: str) -> str | None:
        prefix = ":open "
        partial = value[len(prefix) :]
        if not partial:
            return None

        expanded = os.path.expanduser(partial)
        parent = os.path.dirname(expanded)
        base = os.path.basename(expanded)
        is_cwd = not parent
        search_dir = parent or "."

        try:
            entries = sorted(os.listdir(search_dir))
        except (OSError, PermissionError):
            return None

        for entry in entries:
            if entry.startswith(base):
                full = entry if is_cwd else os.path.join(parent, entry)
                if os.path.isdir(os.path.join(search_dir, entry)):
                    full += "/"
                return f":open {full}"

        return None

    def _suggest_category(self, value: str, prefix: str) -> str | None:
        partial = value[len(prefix) :]
        if not self.log_store:
            return None

        tree = self.log_store.category_tree
        if not tree.children:
            return None

        # Navigate to the deepest matching node based on typed partial path
        parts = [p for p in partial.split("/") if p]
        if not parts:
            # No partial segment yet — suggest from top-level children
            children = sorted(tree.children)
            if children:
                return f"{prefix}{children[0]}/"
            return None

        # The last part may be incomplete — find matches at its level
        *completed, last_part = parts
        node = tree
        for part in completed:
            if part not in node.children:
                return None
            node = node.children[part]

        # Find children of current node that start with last_part
        matches = sorted(name for name in node.children if name.startswith(last_part))
        if not matches:
            return None

        base = "/".join(completed)
        chosen = matches[0]
        full = f"{base}/{chosen}" if base else chosen
        child_node = node.children[chosen]
        if child_node.children:
            full += "/"
        return f"{prefix}{full}"
