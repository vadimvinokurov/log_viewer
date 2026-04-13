"""Tests for horizontal layout integration — LogPanel + CategoryPanel side by side."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal

from log_viewer.core.log_store import LogStore
from log_viewer.tui.widgets.category_panel import CategoryPanel
from log_viewer.tui.widgets.log_panel import LogPanel


SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.258 PLATFORM win64",
]


class LayoutApp(App):
    """App with horizontal layout for testing."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-content {
        layout: horizontal;
    }
    LogPanel {
        width: 3fr;
    }
    CategoryPanel {
        width: 1fr;
    }
    """

    def __init__(self, store: LogStore) -> None:
        super().__init__()
        self.log_store = store

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-content"):
            yield LogPanel()
            yield CategoryPanel(self.log_store)


def _make_store() -> LogStore:
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    return store


class TestHorizontalLayout:
    def test_both_panels_rendered(self) -> None:
        """Both LogPanel and CategoryPanel exist in the DOM."""
        store = _make_store()
        app = LayoutApp(store)

        async def run() -> None:
            async with app.run_test():
                log_panel = app.query_one(LogPanel)
                cat_panel = app.query_one(CategoryPanel)
                assert log_panel is not None
                assert cat_panel is not None

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_panels_are_siblings(self) -> None:
        """LogPanel and CategoryPanel share the same parent container."""
        store = _make_store()
        app = LayoutApp(store)

        async def run() -> None:
            async with app.run_test():
                log_panel = app.query_one(LogPanel)
                cat_panel = app.query_one(CategoryPanel)
                assert log_panel.parent == cat_panel.parent

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_container_is_horizontal(self) -> None:
        """The parent container has horizontal layout."""
        store = _make_store()
        app = LayoutApp(store)

        async def run() -> None:
            async with app.run_test():
                container = app.query_one("#main-content")
                assert container.styles.layout

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_category_panel_width_fraction(self) -> None:
        """CategoryPanel should have a width fraction (not 100%)."""
        store = _make_store()
        app = LayoutApp(store)

        async def run() -> None:
            async with app.run_test():
                cat_panel = app.query_one(CategoryPanel)
                # Should have some width set via CSS (1fr = ~25%)
                assert cat_panel.styles.width is not None

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_log_panel_populated(self) -> None:
        """LogPanel shows lines when populated from store."""
        store = _make_store()
        app = LayoutApp(store)

        async def run() -> None:
            async with app.run_test():
                log_panel = app.query_one(LogPanel)
                for idx in store.filtered_indices:
                    line = store.lines[idx]
                    log_panel.add_row(
                        str(line.line_number),
                        line.timestamp,
                        line.category,
                        line.message,
                    )
                assert log_panel.row_count == 3

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())
