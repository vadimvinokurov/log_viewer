"""Tests for StatusBar widget."""

import pytest

from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.status_bar import StatusBar


@pytest.mark.asyncio
async def test_status_bar_shows_empty_stats() -> None:
    """StatusBar should show 0/0 with zero counts when no file loaded."""
    app = LogViewerApp()
    async with app.run_test():
        status = app.query_one(StatusBar)
        rendered = str(status.render())
        assert "0/0" in rendered


@pytest.mark.asyncio
async def test_status_bar_updates_with_file() -> None:
    """StatusBar should reflect file stats after loading."""
    app = LogViewerApp()
    async with app.run_test():
        app.log_store.load_lines(
            [
                "20-03-2026T12:20:42.305 Cat LOG_ERROR Failed",
                "20-03-2026T12:20:42.305 Cat LOG_ERROR Again",
                "20-03-2026T12:20:42.258 PLATFORM win64",
            ],
            file_path="test.log",
        )
        app.refresh_log_panel()
        status = app.query_one(StatusBar)
        rendered = str(status.render())
        assert "3/3" in rendered
        assert "test.log" in rendered


@pytest.mark.asyncio
async def test_status_bar_level_counts() -> None:
    """StatusBar should show level emoji counts."""
    app = LogViewerApp()
    async with app.run_test():
        app.log_store.load_lines(
            [
                "20-03-2026T12:20:42.305 Cat LOG_ERROR Failed",
                "20-03-2026T12:20:42.305 Cat LOG_WARNING Warn",
                "20-03-2026T12:20:42.258 PLATFORM win64",
            ]
        )
        app.refresh_log_panel()
        status = app.query_one(StatusBar)
        rendered = str(status.render())
        assert "\u27151" in rendered  # ✕1 = 1 ERROR


@pytest.mark.asyncio
async def test_status_bar_shows_search_match() -> None:
    """StatusBar should show match position when search is active."""
    from log_viewer.core.models import SearchDirection, SearchMode

    app = LogViewerApp()
    async with app.run_test():
        app.log_store.load_lines(
            [
                "20-03-2026T12:20:42.305 Cat LOG_ERROR Failed",
                "20-03-2026T12:20:42.305 Cat LOG_ERROR Again failed",
                "20-03-2026T12:20:42.258 PLATFORM win64",
            ]
        )
        app.refresh_log_panel()
        app.log_store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        app._update_status()
        status = app.query_one(StatusBar)
        rendered = str(status.render())
        assert "match 1/2" in rendered


@pytest.mark.asyncio
async def test_status_bar_no_match_when_no_search() -> None:
    """StatusBar should not show match info when no search is active."""
    app = LogViewerApp()
    async with app.run_test():
        app.log_store.load_lines(
            ["20-03-2026T12:20:42.305 Cat LOG_ERROR Failed"]
        )
        app.refresh_log_panel()
        status = app.query_one(StatusBar)
        rendered = str(status.render())
        assert "match" not in rendered
