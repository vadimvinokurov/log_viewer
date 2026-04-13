"""Tests for CategoryListScreen modal."""

from __future__ import annotations

from textual.app import App, ComposeResult

from log_viewer.core.log_store import LogStore
from log_viewer.tui.screens.category_list import CategoryListScreen


SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
    "20-03-2026T12:20:42.258 PLATFORM win64",
]


def _make_store() -> LogStore:
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    return store


class ModalApp(App):
    """Test app for modal screens."""

    def compose(self) -> ComposeResult:
        from textual.widgets import Label
        yield Label("Main content")


class TestCategoryListScreen:
    async def test_modal_shows_categories(self) -> None:
        """Modal shows all category paths with enabled state."""
        store = _make_store()
        app = ModalApp()
        async with app.run_test() as pilot:
            screen = CategoryListScreen(store)
            app.push_screen(screen)
            await pilot.pause()
            labels = app.screen.query("Label")
            texts = [str(l.visual) for l in labels]
            assert any("HordeMode" in t for t in texts)
            assert any("LEECH" in t for t in texts)

    async def test_modal_shows_enabled_icon(self) -> None:
        """Enabled categories show ✅ in the modal."""
        store = _make_store()
        app = ModalApp()
        async with app.run_test() as pilot:
            screen = CategoryListScreen(store)
            app.push_screen(screen)
            await pilot.pause()
            labels = app.screen.query("Label")
            texts = [str(l.visual) for l in labels]
            assert any("✅" in t for t in texts)

    async def test_modal_shows_disabled_icon(self) -> None:
        """Disabled categories show ❌ in the modal."""
        store = _make_store()
        store.disable_category("HordeMode")
        app = ModalApp()
        async with app.run_test() as pilot:
            screen = CategoryListScreen(store)
            app.push_screen(screen)
            await pilot.pause()
            labels = app.screen.query("Label")
            texts = [str(l.visual) for l in labels]
            assert any("❌" in t for t in texts)

    async def test_modal_escape_closes(self) -> None:
        """Pressing escape dismisses the modal."""
        store = _make_store()
        app = ModalApp()
        async with app.run_test() as pilot:
            screen = CategoryListScreen(store)
            app.push_screen(screen)
            await pilot.pause()
            assert isinstance(app.screen, CategoryListScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, CategoryListScreen)

    async def test_modal_shows_line_counts(self) -> None:
        """Categories show their line counts."""
        store = _make_store()
        app = ModalApp()
        async with app.run_test() as pilot:
            screen = CategoryListScreen(store)
            app.push_screen(screen)
            await pilot.pause()
            labels = app.screen.query("Label")
            texts = [str(l.visual) for l in labels]
            # HordeMode has 2 lines in the sample
            assert any("(2)" in t for t in texts)
