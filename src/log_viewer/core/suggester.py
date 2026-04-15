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
        matches = self.get_all_suggestions(value)
        return matches[0] if matches else None

    def get_all_suggestions(self, value: str) -> list[str]:
        """Return all matching completions for Tab cycling."""
        if value.startswith(":open "):
            return self._all_file_suggestions(value)
        if value.startswith(":cate "):
            return self._all_category_suggestions(value, ":cate ")
        if value.startswith(":catd "):
            return self._all_category_suggestions(value, ":catd ")
        return []

    def _all_file_suggestions(self, value: str) -> list[str]:
        prefix = ":open "
        partial = value[len(prefix) :]
        if not partial:
            return []

        expanded = os.path.expanduser(partial)
        parent = os.path.dirname(expanded)
        base = os.path.basename(expanded)
        is_cwd = not parent
        search_dir = parent or "."

        try:
            entries = sorted(os.listdir(search_dir))
        except (OSError, PermissionError):
            return []

        results: list[str] = []
        for entry in entries:
            if entry.startswith(base):
                full = entry if is_cwd else os.path.join(parent, entry)
                if os.path.isdir(os.path.join(search_dir, entry)):
                    full += "/"
                results.append(f":open {full}")
        return results

    def _all_category_suggestions(self, value: str, prefix: str) -> list[str]:
        partial = value[len(prefix) :]
        if not self.log_store:
            return []

        tree = self.log_store.category_tree
        if not tree.children:
            return []

        trailing_slash = partial.endswith("/")
        parts = [p for p in partial.split("/") if p]
        if not parts:
            return [f"{prefix}{name}/" for name in sorted(tree.children)]

        node = tree
        if trailing_slash:
            # "HordeMode/" → all parts are completed, list children of last node
            for part in parts:
                if part not in node.children:
                    return []
                node = node.children[part]
            base = "/".join(parts)
            return [
                f"{prefix}{base}/{name}" + ("/" if node.children[name].children else "")
                for name in sorted(node.children)
            ]

        *completed, last_part = parts
        for part in completed:
            if part not in node.children:
                return []
            node = node.children[part]

        matches = sorted(name for name in node.children if name.startswith(last_part))
        base = "/".join(completed)
        results: list[str] = []
        for name in matches:
            full = f"{base}/{name}" if base else name
            if node.children[name].children:
                full += "/"
            results.append(f"{prefix}{full}")
        return results
