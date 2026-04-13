"""Tests for search command integration in TUI."""

from __future__ import annotations

import pytest

from log_viewer.core.models import SearchDirection, SearchMode
from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.widgets.log_panel import LogPanel

SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_WARNING Missing file",
    "20-03-2026T12:20:42.258 PLATFORM win64",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_DEBUG Debug info",
]


async def _load_and_prep(app: LogViewerApp) -> None:
    app.log_store.load_lines(SAMPLE_LINES, file_path="test.log")
    app.refresh_log_panel()


@pytest.mark.asyncio
async def test_slash_search_forward() -> None:
    """/text should trigger forward search."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = "/Failed"
        await cmd_input.action_submit()
        await pilot.pause()

        assert app.log_store.search_state is not None
        assert app.log_store.search_state.direction == SearchDirection.FORWARD
        assert app.log_store.search_state.matches == [1, 2]
        assert app.log_store.search_state.current_index == 0


@pytest.mark.asyncio
async def test_question_mark_search_backward() -> None:
    """?text should trigger backward search."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = "?Failed"
        await cmd_input.action_submit()
        await pilot.pause()

        assert app.log_store.search_state is not None
        assert app.log_store.search_state.direction == SearchDirection.BACKWARD
        assert app.log_store.search_state.current_index == 1  # Last match


@pytest.mark.asyncio
async def test_s_command_plain_search() -> None:
    """:s pattern should trigger plain search."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":s Failed"
        await cmd_input.action_submit()
        await pilot.pause()

        assert app.log_store.search_state is not None
        assert app.log_store.search_state.mode == SearchMode.PLAIN
        assert app.log_store.search_state.matches == [1, 2]


@pytest.mark.asyncio
async def test_sr_command_regex_search() -> None:
    """:sr pattern should trigger regex search."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":sr LOG_ERROR|LOG_WARNING"
        await cmd_input.action_submit()
        await pilot.pause()

        assert app.log_store.search_state is not None
        assert app.log_store.search_state.mode == SearchMode.REGEX
        assert app.log_store.search_state.matches == [1, 2, 3]


@pytest.mark.asyncio
async def test_ss_command_simple_search() -> None:
    """:ss pattern should trigger simple query search."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ':ss "Failed" AND "open"'
        await cmd_input.action_submit()
        await pilot.pause()

        assert app.log_store.search_state is not None
        assert app.log_store.search_state.mode == SearchMode.SIMPLE
        assert app.log_store.search_state.matches == [1]


@pytest.mark.asyncio
async def test_s_with_case_sensitive_flag() -> None:
    """:s/cs/pattern should be case-sensitive."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":s/cs/failed"
        await cmd_input.action_submit()
        await pilot.pause()

        assert app.log_store.search_state is not None
        assert app.log_store.search_state.case_sensitive is True
        # Only "Read failed" has lowercase "failed"
        assert app.log_store.search_state.matches == [2]


@pytest.mark.asyncio
async def test_n_navigates_next_match() -> None:
    """n key should go to next search match."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = "/Failed"
        await cmd_input.action_submit()
        await pilot.pause()
        assert app.log_store.search_state.current_index == 0

        # n navigates to next match
        app.query_one(LogPanel).focus()
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()

        assert app.log_store.search_state.current_index == 1


@pytest.mark.asyncio
async def test_shift_n_navigates_prev_match() -> None:
    """N (shift+n) key should go to previous search match."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = "/Failed"
        await cmd_input.action_submit()
        await pilot.pause()
        assert app.log_store.search_state.current_index == 0

        app.query_one(LogPanel).focus()
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert app.log_store.search_state.current_index == 1

        await pilot.press("N")
        await pilot.pause()
        assert app.log_store.search_state.current_index == 0


@pytest.mark.asyncio
async def test_escape_clears_search() -> None:
    """Esc during search mode should clear search state."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        await _load_and_prep(app)
        app.query_one(LogPanel).focus()
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert app.log_store.search_state is None
