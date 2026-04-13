"""Tests for vim-style keyboard mode switching."""

from __future__ import annotations

import pytest

from log_viewer.core.models import InputMode
from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.widgets.log_panel import LogPanel

SAMPLE_LINES = [f"20-03-2026T12:20:42.{i:03d} Cat LOG_INFO Line {i}" for i in range(20)]


@pytest.mark.asyncio
async def test_initial_focus_on_log_panel() -> None:
    """App should start with LogPanel focused, not CommandInput."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        assert isinstance(app.focused, LogPanel)


@pytest.mark.asyncio
async def test_colon_switches_to_command_input() -> None:
    """Pressing : should focus CommandInput with : prefix."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.query_one(LogPanel).focus()
        await pilot.pause()

        await pilot.press("colon")
        await pilot.pause()

        cmd_input = app.query_one(CommandInput)
        assert isinstance(app.focused, CommandInput)
        assert cmd_input.value == ":"


@pytest.mark.asyncio
async def test_slash_switches_to_command_input() -> None:
    """Pressing / should focus CommandInput with / prefix."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.query_one(LogPanel).focus()
        await pilot.pause()

        await pilot.press("slash")
        await pilot.pause()

        cmd_input = app.query_one(CommandInput)
        assert isinstance(app.focused, CommandInput)
        assert cmd_input.value == "/"


@pytest.mark.asyncio
async def test_enter_returns_focus_to_log_panel() -> None:
    """After submitting command, focus should return to LogPanel."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.query_one(LogPanel).focus()
        await pilot.pause()

        await pilot.press("colon")
        await pilot.pause()

        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":q"
        await cmd_input.action_submit()
        await pilot.pause()

        assert isinstance(app.focused, LogPanel)
        assert cmd_input.value == ""


@pytest.mark.asyncio
async def test_escape_cancels_and_returns_focus() -> None:
    """Esc should clear input and return focus to LogPanel."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.query_one(LogPanel).focus()
        await pilot.pause()

        await pilot.press("colon")
        await pilot.pause()

        cmd_input = app.query_one(CommandInput)
        assert cmd_input.value == ":"

        await pilot.press("escape")
        await pilot.pause()

        assert isinstance(app.focused, LogPanel)
        assert cmd_input.value == ""


@pytest.mark.asyncio
async def test_q_quits_in_normal_mode() -> None:
    """q key should quit the app when LogPanel is focused."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.query_one(LogPanel).focus()
        await pilot.pause()

        await pilot.press("q")
        await pilot.pause()

        assert app._exit


@pytest.mark.asyncio
async def test_vim_navigation_in_normal_mode() -> None:
    """Vim navigation keys should work when LogPanel is focused."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(LogPanel)
        table.focus()
        await pilot.pause()

        await pilot.press("j")
        await pilot.pause()
        assert table.cursor_row == 1


@pytest.mark.asyncio
async def test_quit_with_colon_prefix() -> None:
    """:q command should still work with colon prefix."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":q"
        await cmd_input.action_submit()
        await pilot.pause()
        assert app._exit


@pytest.mark.asyncio
async def test_open_with_colon_prefix() -> None:
    """:open command should work with colon prefix."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":open test_log.log"
        await cmd_input.action_submit()
        await pilot.pause(delay=0.5)
        assert len(app.log_store.lines) > 0


class TestInputModeStateMachine:
    """Test InputMode enum transitions in the app."""

    @pytest.mark.asyncio
    async def test_initial_mode_is_normal(self) -> None:
        app = LogViewerApp()
        async with app.run_test() as pilot:
            assert app.input_mode == InputMode.NORMAL

    @pytest.mark.asyncio
    async def test_colon_enters_command_mode(self) -> None:
        app = LogViewerApp()
        async with app.run_test() as pilot:
            app.query_one(LogPanel).focus()
            await pilot.pause()
            await pilot.press("colon")
            await pilot.pause()
            assert app.input_mode == InputMode.COMMAND

    @pytest.mark.asyncio
    async def test_slash_enters_search_forward(self) -> None:
        app = LogViewerApp()
        async with app.run_test() as pilot:
            app.query_one(LogPanel).focus()
            await pilot.pause()
            await pilot.press("slash")
            await pilot.pause()
            assert app.input_mode == InputMode.SEARCH_FORWARD

    @pytest.mark.asyncio
    async def test_question_mark_enters_search_backward(self) -> None:
        app = LogViewerApp()
        async with app.run_test() as pilot:
            app.query_one(LogPanel).focus()
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()
            cmd_input = app.query_one(CommandInput)
            assert app.input_mode == InputMode.SEARCH_BACKWARD
            assert cmd_input.value == "?"

    @pytest.mark.asyncio
    async def test_escape_returns_to_normal(self) -> None:
        app = LogViewerApp()
        async with app.run_test() as pilot:
            app.query_one(LogPanel).focus()
            await pilot.pause()
            await pilot.press("slash")
            await pilot.pause()
            assert app.input_mode == InputMode.SEARCH_FORWARD
            await pilot.press("escape")
            await pilot.pause()
            assert app.input_mode == InputMode.NORMAL

    @pytest.mark.asyncio
    async def test_submit_returns_to_normal(self) -> None:
        app = LogViewerApp()
        async with app.run_test() as pilot:
            app.query_one(LogPanel).focus()
            await pilot.pause()
            await pilot.press("colon")
            await pilot.pause()
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":q"
            await cmd_input.action_submit()
            await pilot.pause()
            assert app.input_mode == InputMode.NORMAL
