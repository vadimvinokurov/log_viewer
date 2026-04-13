"""Tests for vim-style navigation."""

import pytest

from textual.widgets import DataTable

from log_viewer.tui.app import LogViewerApp

SAMPLE_LINES = [f"20-03-2026T12:20:42.{i:03d} Cat LOG_INFO Line {i}" for i in range(20)]


@pytest.mark.asyncio
async def test_j_moves_down() -> None:
    """j key should move cursor down one row."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        # Move cursor down with j
        await pilot.press("j")
        await pilot.pause()
        assert table.cursor_row == 1


@pytest.mark.asyncio
async def test_k_moves_up() -> None:
    """k key should move cursor up one row."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        # Move down first, then up
        await pilot.press("j")
        await pilot.press("k")
        await pilot.pause()
        assert table.cursor_row == 0


@pytest.mark.asyncio
async def test_gg_goes_to_first_line() -> None:
    """gg should move cursor to first line."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        # Go to bottom first
        await pilot.press("end")
        await pilot.pause()

        # Then gg to go to top
        await pilot.press("g")
        await pilot.press("g")
        await pilot.pause()
        assert table.cursor_row == 0


@pytest.mark.asyncio
async def test_G_goes_to_last_line() -> None:
    """G (capital G, as real terminal sends) should move cursor to last line."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        await pilot.press("shift+g")
        await pilot.pause()
        assert table.cursor_row == 19


@pytest.mark.asyncio
async def test_capital_G_goes_to_last_line() -> None:
    """Uppercase G (key='G') — how real terminals send it — should go to last line."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        # Simulate real terminal: press "G" (uppercase letter)
        await pilot.press("G")
        await pilot.pause()
        assert table.cursor_row == 19


@pytest.mark.asyncio
async def test_number_G_goes_to_specific_line() -> None:
    """42G should move cursor to row index 41 (0-based)."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        # Type digits then G
        for ch in "5":
            await pilot.press(ch)
        await pilot.press("G")
        await pilot.pause()
        assert table.cursor_row == 4  # 0-based: line 5 → index 4


@pytest.mark.asyncio
async def test_ctrl_d_half_page_down() -> None:
    """Ctrl+D should scroll half page down."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        await pilot.press("ctrl+d")
        await pilot.pause()
        assert table.cursor_row > 0
