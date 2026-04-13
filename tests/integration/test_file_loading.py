"""Tests for file loading with worker thread."""

import pytest

from log_viewer.tui.app import LogViewerApp

WORKER_DELAY = 0.5

TEST_FILE = "test_log.log"


@pytest.mark.asyncio
async def test_open_file_via_worker() -> None:
    """Opening a file should load lines via worker thread."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app._open_file_worker(TEST_FILE)
        await pilot.pause(delay=WORKER_DELAY)
        assert len(app.log_store.lines) > 0
        assert app.log_store.current_file == TEST_FILE


@pytest.mark.asyncio
async def test_worker_exclusive() -> None:
    """Opening a new file should cancel previous load."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app._open_file_worker(TEST_FILE)
        await pilot.pause(delay=WORKER_DELAY)
        first_count = len(app.log_store.lines)

        # Open same file again — should replace
        app._open_file_worker(TEST_FILE)
        await pilot.pause(delay=WORKER_DELAY)
        assert len(app.log_store.lines) == first_count


@pytest.mark.asyncio
async def test_open_nonexistent_worker() -> None:
    """Opening nonexistent file via worker should not crash."""
    app = LogViewerApp()
    async with app.run_test() as pilot:
        app._open_file_worker("nonexistent_file.log")
        await pilot.pause(delay=WORKER_DELAY)
        assert len(app.log_store.lines) == 0


@pytest.mark.asyncio
async def test_cli_arg_loads_file_on_start() -> None:
    """Passing a file path to LogViewerApp loads it on mount."""
    app = LogViewerApp(file_path=TEST_FILE)
    async with app.run_test() as pilot:
        await pilot.pause(delay=WORKER_DELAY)
        assert len(app.log_store.lines) > 0
        assert app.log_store.current_file == TEST_FILE


@pytest.mark.asyncio
async def test_cli_arg_nonexistent_no_crash() -> None:
    """Passing nonexistent file path does not crash."""
    app = LogViewerApp(file_path="nonexistent_file.log")
    async with app.run_test() as pilot:
        await pilot.pause(delay=WORKER_DELAY)
        assert len(app.log_store.lines) == 0
