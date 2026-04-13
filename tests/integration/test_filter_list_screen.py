"""Tests for FilterListScreen modal — RED phase."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.screen import ModalScreen

from log_viewer.core.models import Filter, SearchMode
from log_viewer.core.log_store import LogStore
from log_viewer.tui.screens.filter_list import FilterListScreen


SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
]


class _TestApp(App):
    """Minimal app to test screen pushing."""

    def __init__(self) -> None:
        super().__init__()
        self.log_store = LogStore()

    def compose(self) -> ComposeResult:
        yield from []


async def test_filter_list_shows_filters() -> None:
    app = _TestApp()
    async with app.run_test() as pilot:
        store = app.log_store
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="ERROR", mode=SearchMode.PLAIN))
        store.add_filter(Filter(pattern="timeout", mode=SearchMode.REGEX))

        screen = FilterListScreen(store.filters)
        app.push_screen(screen)

        await pilot.pause()

        # Screen should be mounted
        assert isinstance(app.screen, FilterListScreen)
        # Should dismiss on Escape
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, FilterListScreen)


async def test_filter_list_empty() -> None:
    app = _TestApp()
    async with app.run_test() as pilot:
        store = app.log_store
        store.load_lines(SAMPLE_LINES)

        screen = FilterListScreen(store.filters)
        app.push_screen(screen)
        await pilot.pause()

        assert isinstance(app.screen, FilterListScreen)
        await pilot.press("escape")


async def test_filter_list_displays_content() -> None:
    app = _TestApp()
    async with app.run_test() as pilot:
        store = app.log_store
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="ERROR", mode=SearchMode.PLAIN))

        screen = FilterListScreen(store.filters)
        app.push_screen(screen)
        await pilot.pause()

        # Verify screen is a modal
        assert isinstance(app.screen, ModalScreen)
