"""File path suggester for the :open command."""

from __future__ import annotations

import os

from textual.suggester import Suggester


class FilePathSuggester(Suggester):
    """Suggest file/directory completions for the `:open` command."""

    def __init__(self) -> None:
        super().__init__(use_cache=False, case_sensitive=True)

    async def get_suggestion(self, value: str) -> str | None:
        prefix = ":open "
        if not value.startswith(prefix):
            return None

        partial = value[len(prefix) :]
        if not partial:
            return None

        expanded = os.path.expanduser(partial)
        parent = os.path.dirname(expanded) or "."
        base = os.path.basename(expanded)

        try:
            entries = sorted(os.listdir(parent))
        except (OSError, PermissionError):
            return None

        for entry in entries:
            if entry.startswith(base):
                full = os.path.join(parent, entry)
                if os.path.isdir(full):
                    full += "/"
                return f":open {full}"

        return None
