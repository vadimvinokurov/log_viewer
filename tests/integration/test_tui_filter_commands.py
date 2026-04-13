"""Tests for filter command integration in TUI — RED phase."""

from __future__ import annotations

import pytest

from log_viewer.core.models import SearchMode
from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.screens.filter_list import FilterListScreen


SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_WARNING Missing file",
    "20-03-2026T12:20:42.258 PLATFORM win64",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_DEBUG Debug info",
]


async def _load_and_prep(app: LogViewerApp) -> None:
    """Load sample data and refresh panel."""
    app.log_store.load_lines(SAMPLE_LINES, file_path="test.log")
    app.refresh_log_panel()


@pytest.mark.asyncio
async def test_f_command_filters_lines() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        assert len(app.log_store.filtered_indices) == 6

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":f LOG_ERROR"
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filters) == 1
        assert len(app.log_store.filtered_indices) == 2


@pytest.mark.asyncio
async def test_fr_command_regex_filter() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":fr LOG_ERROR"
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filters) == 1
        assert app.log_store.filters[0].mode == SearchMode.REGEX


@pytest.mark.asyncio
async def test_fs_command_simple_query() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ':fs "Failed" AND "open"'
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filters) == 1
        assert app.log_store.filters[0].mode == SearchMode.SIMPLE
        assert len(app.log_store.filtered_indices) == 1


@pytest.mark.asyncio
async def test_rmf_removes_filter() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":f LOG_ERROR"
        await cmd_input.action_submit()
        await pilot.pause()
        assert len(app.log_store.filters) == 1

        cmd_input.value = ":rmf LOG_ERROR"
        await cmd_input.action_submit()
        await pilot.pause()
        assert len(app.log_store.filters) == 0
        assert len(app.log_store.filtered_indices) == 6


@pytest.mark.asyncio
async def test_rmf_clears_all() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":f LOG_ERROR"
        await cmd_input.action_submit()
        await pilot.pause()

        cmd_input.value = ":f Debug"
        await cmd_input.action_submit()
        await pilot.pause()
        assert len(app.log_store.filters) == 2

        cmd_input.value = ":rmf"
        await cmd_input.action_submit()
        await pilot.pause()
        assert len(app.log_store.filters) == 0
        assert len(app.log_store.filtered_indices) == 6


@pytest.mark.asyncio
async def test_lsf_shows_filter_list_screen() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":f LOG_ERROR"
        await cmd_input.action_submit()
        await pilot.pause()

        cmd_input.value = ":lsf"
        await cmd_input.action_submit()
        await pilot.pause()

        assert isinstance(app.screen, FilterListScreen)


@pytest.mark.asyncio
async def test_f_with_case_sensitive_flag() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":f/cs/Failed"
        await cmd_input.action_submit()
        await pilot.pause()

        assert len(app.log_store.filters) == 1
        assert app.log_store.filters[0].case_sensitive is True
