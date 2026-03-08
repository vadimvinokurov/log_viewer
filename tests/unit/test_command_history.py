"""Tests for CommandHistory."""

import json
from pathlib import Path

import pytest

from log_viewer.core.command_history import CommandHistory
from log_viewer.core.config import ConfigManager


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / ".logviewer"


@pytest.fixture
def cm(config_dir: Path) -> ConfigManager:
    manager = ConfigManager(config_dir=config_dir)
    manager.load()
    return manager


@pytest.fixture
def history(cm: ConfigManager) -> CommandHistory:
    return CommandHistory(cm)


class TestCommandHistoryAdd:
    def test_add_creates_history_file(self, history: CommandHistory, config_dir: Path):
        history.add(":f error")
        assert (config_dir / "history.json").exists()

    def test_add_stores_command(self, history: CommandHistory):
        history.add(":f error")
        assert history.commands == [":f error"]

    def test_add_multiple(self, history: CommandHistory):
        history.add(":f error")
        history.add(":h fail")
        assert history.commands == [":f error", ":h fail"]

    def test_add_consecutive_duplicate_removed(self, history: CommandHistory):
        history.add(":f error")
        history.add(":f error")
        assert history.commands == [":f error"]

    def test_add_non_consecutive_duplicate_kept(self, history: CommandHistory):
        history.add(":f error")
        history.add(":h fail")
        history.add(":f error")
        assert history.commands == [":f error", ":h fail", ":f error"]

    def test_add_respects_max_size(self, cm: ConfigManager):
        cm.set("history_size", 3)
        history = CommandHistory(cm)
        for i in range(5):
            history.add(f":cmd{i}")
        assert len(history.commands) == 3
        assert history.commands[0] == ":cmd2"


class TestCommandHistoryNavigate:
    def test_navigate_up_from_end(self, history: CommandHistory):
        history.add(":a")
        history.add(":b")
        history.add(":c")
        assert history.navigate_up() == ":c"

    def test_navigate_up_twice(self, history: CommandHistory):
        history.add(":a")
        history.add(":b")
        history.add(":c")
        history.navigate_up()
        assert history.navigate_up() == ":b"

    def test_navigate_up_past_beginning_returns_oldest(self, history: CommandHistory):
        history.add(":a")
        history.add(":b")
        history.navigate_up()
        history.navigate_up()
        result = history.navigate_up()
        assert result == ":a"

    def test_navigate_down_after_up(self, history: CommandHistory):
        history.add(":a")
        history.add(":b")
        history.add(":c")
        # up: pos 3->2 (":c"), up: pos 2->1 (":b")
        history.navigate_up()
        history.navigate_up()
        # down: pos 1->2 (":c")
        assert history.navigate_down() == ":c"

    def test_navigate_down_past_end_returns_empty(self, history: CommandHistory):
        history.add(":a")
        history.navigate_up()
        assert history.navigate_down() == ""

    def test_navigate_resets_on_add(self, history: CommandHistory):
        history.add(":a")
        history.add(":b")
        history.navigate_up()
        history.add(":c")
        # After add, position resets — next up should show latest
        assert history.navigate_up() == ":c"

    def test_navigate_empty_history(self, history: CommandHistory):
        assert history.navigate_up() == ""
        assert history.navigate_down() == ""


class TestCommandHistoryPersist:
    def test_load_existing_history(self, config_dir: Path, cm: ConfigManager):
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "history.json").write_text(json.dumps([":a", ":b"]))
        history = CommandHistory(cm)
        assert history.commands == [":a", ":b"]

    def test_save_on_add(self, config_dir: Path, history: CommandHistory):
        history.add(":test")
        raw = (config_dir / "history.json").read_text()
        data = json.loads(raw)
        assert data == [":test"]
