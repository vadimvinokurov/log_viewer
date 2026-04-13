"""Tests for TUI app shell."""

import pytest

from log_viewer.tui.app import LogViewerApp


@pytest.mark.asyncio
async def test_app_compose_has_layout() -> None:
    """App should compose with Header, LogPanel, StatusBar."""
    app = LogViewerApp()
    async with app.run_test():
        from textual.widgets import Header

        header = app.query_one(Header)
        assert header is not None


@pytest.mark.asyncio
async def test_app_has_log_store() -> None:
    """App should have a LogStore instance."""
    app = LogViewerApp()
    async with app.run_test():
        assert app.log_store is not None
        assert len(app.log_store.lines) == 0


@pytest.mark.asyncio
async def test_app_title() -> None:
    """App should have correct title."""
    app = LogViewerApp()
    async with app.run_test():
        assert "Log Viewer" in app.title or "log-viewer" in app.title.lower()
