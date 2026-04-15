"""Tests for Tab-autocomplete cycling in CommandInput."""

from __future__ import annotations

from pathlib import Path

import pytest

from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput


@pytest.fixture
def tmp_tree(tmp_path: Path) -> Path:
    (tmp_path / "hello.log").write_text("line1")
    (tmp_path / "hello.txt").write_text("line2")
    return tmp_path


@pytest.mark.asyncio
async def test_tab_accepts_first_match(tmp_tree: Path) -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.focus()
        cmd_input.value = f":open {tmp_tree}/hel"
        cmd_input.cursor_position = len(cmd_input.value)
        await pilot.pause()

        await pilot.press("tab")
        await pilot.pause()

        assert cmd_input.value == f":open {tmp_tree}/hello.log"


@pytest.mark.asyncio
async def test_tab_cycles_through_matches(tmp_tree: Path) -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.focus()
        cmd_input.value = f":open {tmp_tree}/hel"
        cmd_input.cursor_position = len(cmd_input.value)
        await pilot.pause()

        # First Tab — first match
        await pilot.press("tab")
        await pilot.pause()
        assert cmd_input.value == f":open {tmp_tree}/hello.log"

        # Second Tab — second match
        await pilot.press("tab")
        await pilot.pause()
        assert cmd_input.value == f":open {tmp_tree}/hello.txt"

        # Third Tab — cycles back to first
        await pilot.press("tab")
        await pilot.pause()
        assert cmd_input.value == f":open {tmp_tree}/hello.log"


@pytest.mark.asyncio
async def test_tab_does_nothing_without_suggestion() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.focus()
        cmd_input.value = ":open /nonexistent_zzz_path"
        cmd_input.cursor_position = len(cmd_input.value)
        await pilot.pause()

        await pilot.press("tab")
        await pilot.pause()

        assert cmd_input.value == ":open /nonexistent_zzz_path"
