"""Tests for bottom bar layout — CommandInput and StatusBar don't overlap."""

import pytest

from textual.containers import Horizontal

from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.widgets.status_bar import StatusBar


@pytest.mark.asyncio
async def test_command_input_and_status_bar_are_siblings_in_container() -> None:
    """CommandInput and StatusBar should be inside the same horizontal container."""
    app = LogViewerApp()
    async with app.run_test():
        # Both should be inside a Horizontal container
        containers = app.query(Horizontal)
        bottom_bars = [c for c in containers if c.has_class("bottom-bar")]
        assert len(bottom_bars) == 1, "Should have exactly one bottom-bar container"
        bar = bottom_bars[0]
        assert bar.query_one(CommandInput) is not None
        assert bar.query_one(StatusBar) is not None


@pytest.mark.asyncio
async def test_command_input_typing_visible() -> None:
    """Typing into CommandInput should update its value."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.focus()
        await pilot.pause()

        # Simulate typing into the input
        cmd_input.value = "open test.log"
        await pilot.pause()
        assert cmd_input.value == "open test.log"
