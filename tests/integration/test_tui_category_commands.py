"""Tests for category command integration in TUI — RED phase."""

from __future__ import annotations

import pytest

from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.screens.category_list import CategoryListScreen


SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
    "20-03-2026T12:20:42.258 PLATFORM win64",
]


async def _load_and_prep(app: LogViewerApp) -> None:
    """Load sample data and refresh panel."""
    app.log_store.load_lines(SAMPLE_LINES, file_path="test.log")
    app.refresh_log_panel()


@pytest.mark.asyncio
async def test_catd_disables_category() -> None:
    """:catd HordeMode disables the HordeMode category."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        assert len(app.log_store.filtered_indices) == 4

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":catd HordeMode"
        await cmd_input.action_submit()
        await pilot.pause()

        # HordeMode has 2 lines — they should be filtered out
        assert len(app.log_store.filtered_indices) == 2


@pytest.mark.asyncio
async def test_cate_enables_category() -> None:
    """:cate HordeMode re-enables a disabled category."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        app.log_store.disable_category("HordeMode")
        app.refresh_log_panel()
        assert len(app.log_store.filtered_indices) == 2

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":cate HordeMode"
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filtered_indices) == 4


@pytest.mark.asyncio
async def test_cate_without_args_enables_all_categories() -> None:
    """:cate without args enables all categories."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        app.log_store.disable_category("HordeMode")
        app.refresh_log_panel()
        assert len(app.log_store.filtered_indices) == 2

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":cate"
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filtered_indices) == 4


@pytest.mark.asyncio
async def test_catd_without_args_disables_all_categories() -> None:
    """:catd without args disables all categories."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        assert len(app.log_store.filtered_indices) == 4

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":catd"
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filtered_indices) == 0


@pytest.mark.asyncio
async def test_lscat_shows_category_list_screen() -> None:
    """:lscat opens the CategoryListScreen modal."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":lscat"
        await cmd_input.action_submit()
        await pilot.pause()

        assert isinstance(app.screen, CategoryListScreen)


@pytest.mark.asyncio
async def test_catd_updates_category_panel() -> None:
    """:catd also refreshes the CategoryPanel."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":catd HordeMode"
        await cmd_input.action_submit()
        await pilot.pause()

        from log_viewer.tui.widgets.category_panel import CategoryPanel
        cat_panel = app.query_one(CategoryPanel)
        cat_panel.root.expand()
        children = list(cat_panel.root.children)
        horde_nodes = [c for c in children if "HordeMode" in str(c.label)]
        assert "❌" in str(horde_nodes[0].label)
