"""Tests for preset command integration in TUI."""

import pytest

from log_viewer.core.models import Filter, SearchMode
from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput


@pytest.fixture
def app(tmp_path):
    """Create a LogViewerApp with temp config dir."""
    return LogViewerApp(file_path=None, config_dir=tmp_path / ".logviewer")


SAMPLE_LINES = [
    "20-03-2026T12:20:42.305 HordeMode LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode LOG_WARNING Missing file",
    "20-03-2026T12:20:42.305 HordeMode LOG_DEBUG Debug info",
]


class TestPresetSaveCommand:
    @pytest.mark.asyncio
    async def test_preset_save(self, app, tmp_path):
        async with app.run_test() as pilot:
            app.log_store.load_lines(SAMPLE_LINES, file_path="test.log")
            app.refresh_log_panel()
            app.log_store.add_filter(Filter("error", SearchMode.PLAIN))

            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":preset save my-filter"
            await cmd_input.action_submit()
            await pilot.pause()

            pm = app._preset_manager
            assert pm.exists("my-filter")
            data = pm.load("my-filter")
            assert len(data["filters"]) == 1
            assert data["filters"][0]["pattern"] == "error"


class TestPresetLoadCommand:
    @pytest.mark.asyncio
    async def test_preset_load(self, app, tmp_path):
        async with app.run_test() as pilot:
            app.log_store.load_lines(SAMPLE_LINES, file_path="test.log")
            app.refresh_log_panel()

            pm = app._preset_manager
            pm.save(
                "debug",
                {
                    "filters": [{"pattern": "fail", "mode": "plain", "case_sensitive": False}],
                    "highlights": [],
                    "disabled_categories": [],
                },
            )

            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":preset load debug"
            await cmd_input.action_submit()
            await pilot.pause()

            assert len(app.log_store.filters) == 1
            assert app.log_store.filters[0].pattern == "fail"

    @pytest.mark.asyncio
    async def test_preset_load_nonexistent(self, app, tmp_path):
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":preset load nonexistent"
            await cmd_input.action_submit()
            await pilot.pause()
            # Should not crash, no filters added
            assert len(app.log_store.filters) == 0


class TestPresetDeleteCommand:
    @pytest.mark.asyncio
    async def test_rmpreset(self, app, tmp_path):
        async with app.run_test() as pilot:
            pm = app._preset_manager
            pm.save("to-delete", {"filters": [], "highlights": [], "disabled_categories": []})

            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":rmpreset to-delete"
            await cmd_input.action_submit()
            await pilot.pause()

            assert not pm.exists("to-delete")


class TestCommandHistory:
    @pytest.mark.asyncio
    async def test_history_persists(self, app, tmp_path):
        async with app.run_test() as pilot:
            cmd_input = app.query_one(CommandInput)
            cmd_input.value = ":f error"
            await cmd_input.action_submit()
            await pilot.pause()

            assert len(app._command_history.commands) == 1
            assert app._command_history.commands[0] == ":f error"
