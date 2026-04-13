"""StatusBar widget — displays file stats and level counts."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """Status bar showing visible/total lines and level breakdown."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        width: auto;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    StatusBar.error {
        background: $error;
        color: white;
    }
    """

    def update_stats(
        self,
        visible: int,
        total: int,
        level_counts: dict,
        filename: str | None = None,
        match_info: str | None = None,
    ) -> None:
        self.remove_class("error")
        parts: list[str] = []
        if filename:
            parts.append(filename)
        if match_info:
            parts.append(match_info)
        parts.append(f"{visible}/{total}")

        from log_viewer.core.models import LogLevel

        for level in [
            LogLevel.CRITICAL,
            LogLevel.ERROR,
            LogLevel.WARNING,
            LogLevel.INFO,
            LogLevel.DEBUG,
            LogLevel.TRACE,
        ]:
            count = level_counts.get(level.name, 0)
            parts.append(f"{level.icon_plain}{count}")

        self.update(" \u2502 ".join(parts))

    def show_error(self, msg: str) -> None:
        """Show an error message in red, auto-clears after 3 seconds."""
        self.add_class("error")
        self.update(f"\u274c {msg}")
        self.set_timer(3.0, self._clear_error)

    def _clear_error(self) -> None:
        """Clear error state. Caller should re-run update_stats."""
        self.remove_class("error")
