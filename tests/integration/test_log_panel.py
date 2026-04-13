"""Tests for LogPanel widget."""

import pytest

from textual.widgets import DataTable

from log_viewer.tui.app import LogViewerApp

SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.258 PLATFORM win64",
]


@pytest.mark.asyncio
async def test_log_panel_populates_on_load() -> None:
    """LogPanel should populate rows when lines are loaded."""
    app = LogViewerApp()
    async with app.run_test():
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        assert table.row_count == 3


@pytest.mark.asyncio
async def test_log_panel_columns() -> None:
    """LogPanel should have 4 columns (Line, Timestamp, Category, Message)."""
    app = LogViewerApp()
    async with app.run_test():
        table = app.query_one(DataTable)
        assert len(table.columns) == 4


@pytest.mark.asyncio
async def test_log_panel_empty() -> None:
    """LogPanel should be empty on start."""
    app = LogViewerApp()
    async with app.run_test():
        table = app.query_one(DataTable)
        assert table.row_count == 0


@pytest.mark.asyncio
async def test_log_panel_highlights_search_match() -> None:
    """LogPanel should highlight the current search match row."""
    from log_viewer.core.models import SearchDirection, SearchMode

    app = LogViewerApp()
    async with app.run_test():
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        # Search for "Failed" — matches line index 1 (raw line 2)
        app.log_store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        app._update_search_highlight()
        table = app.query_one(DataTable)
        # The row at the match position should be highlighted
        assert table.row_count == 3
        # Row key for the matched line should have the search-match class
        highlighted = table.get_row_at(1)
        assert highlighted is not None
