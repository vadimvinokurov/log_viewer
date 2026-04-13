"""Tests for Phase 7 features: themes, clipboard, reload, error display, HTTP."""

import pytest

from log_viewer.core.models import SearchMode
from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.widgets.status_bar import StatusBar


SAMPLE_LINES = [
    "20-03-2026T12:20:42.305 HordeMode LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode LOG_WARNING Missing file",
    "20-03-2026T12:20:42.305 HordeMode LOG_DEBUG Debug info",
]


class TestReloadCommand:
    @pytest.mark.asyncio
    async def test_reload_reloads_file(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LINES))
        app = LogViewerApp(file_path=str(log_file))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.log_store.lines) == 3

            # Modify file
            log_file.write_text("\n".join(SAMPLE_LINES + ["20-03-2026T12:20:42.999 New LOG_INFO Added"]))

            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":reload"
            await cmd_input.action_submit()
            await pilot.pause()

            assert len(app.log_store.lines) == 4

    @pytest.mark.asyncio
    async def test_reload_no_file_shows_error(self, tmp_path):
        app = LogViewerApp()
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":reload"
            await cmd_input.action_submit()
            await pilot.pause()

            status = app.query_one(StatusBar)
            assert status.has_class("error")


class TestThemeCommand:
    @pytest.mark.asyncio
    async def test_theme_persists(self, tmp_path):
        app = LogViewerApp(config_dir=tmp_path / ".logviewer")
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":theme light"
            await cmd_input.action_submit()
            await pilot.pause()

            assert app._config_manager.get("theme") == "light"
            assert app.dark is False

    @pytest.mark.asyncio
    async def test_theme_invalid_shows_error(self, tmp_path):
        app = LogViewerApp(config_dir=tmp_path / ".logviewer")
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":theme invalid"
            await cmd_input.action_submit()
            await pilot.pause()

            status = app.query_one(StatusBar)
            assert status.has_class("error")


class TestErrorDisplay:
    @pytest.mark.asyncio
    async def test_parse_error_shows_error(self, tmp_path):
        app = LogViewerApp(config_dir=tmp_path / ".logviewer")
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":unknowncmd"
            await cmd_input.action_submit()
            await pilot.pause()

            status = app.query_one(StatusBar)
            assert status.has_class("error")

    @pytest.mark.asyncio
    async def test_file_not_found_shows_error(self, tmp_path):
        app = LogViewerApp(config_dir=tmp_path / ".logviewer")
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":open /nonexistent/path.log"
            await cmd_input.action_submit()
            await pilot.pause()
            # Worker is async, give it a moment
            await pilot.pause()

            status = app.query_one(StatusBar)
            assert status.has_class("error")
