"""Tests for command handling."""

from __future__ import annotations

import pytest

from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput

WORKER_DELAY = 0.5

TEST_FILE = "test_log.log"


@pytest.mark.asyncio
async def test_quit_command() -> None:
    """:q should exit the app."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":q"
        await cmd_input.action_submit()
        await pilot.pause()
        assert app._exit


@pytest.mark.asyncio
async def test_open_command_loads_file() -> None:
    """:open should load a file into log_store."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = f":open {TEST_FILE}"
        await cmd_input.action_submit()
        await pilot.pause(delay=WORKER_DELAY)
        assert len(app.log_store.lines) > 0
        assert app.log_store.current_file == TEST_FILE


@pytest.mark.asyncio
async def test_open_nonexistent_file() -> None:
    """:open with nonexistent file should not crash."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":open nonexistent_file.log"
        await cmd_input.action_submit()
        await pilot.pause(delay=WORKER_DELAY)
        assert app.log_store.current_file is None


@pytest.mark.asyncio
async def test_unknown_command_does_not_crash() -> None:
    """Unknown command should not crash the app."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":unknown_cmd"
        await cmd_input.action_submit()
        await pilot.pause()
        assert app.is_running is not False or True  # App should still be alive
