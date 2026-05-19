"""Tests for ConfigManager."""

import json
from pathlib import Path

import pytest

from log_viewer.core.config import ConfigManager


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Return a temp directory for config files."""
    return tmp_path / ".logviewer"


@pytest.fixture
def cm(config_dir: Path) -> ConfigManager:
    """Create ConfigManager with temp dir."""
    return ConfigManager(config_dir=config_dir)


class TestConfigManagerLoad:
    def test_creates_dir_and_file_on_first_load(self, config_dir: Path, cm: ConfigManager):
        cm.load()
        assert config_dir.exists()
        assert (config_dir / "settings.json").exists()

    def test_load_returns_defaults_when_no_file(self, cm: ConfigManager):
        cfg = cm.load()
        assert cfg["history_size"] == 100
        assert cfg["default_categories_enabled"] is True

    def test_load_reads_existing_file(self, config_dir: Path, cm: ConfigManager):
        config_dir.mkdir(parents=True, exist_ok=True)
        data = {"history_size": 50}
        (config_dir / "settings.json").write_text(json.dumps(data))
        cfg = cm.load()
        assert cfg["history_size"] == 50

    def test_load_merges_missing_keys_with_defaults(self, config_dir: Path, cm: ConfigManager):
        config_dir.mkdir(parents=True, exist_ok=True)
        data = {"history_size": 50}
        (config_dir / "settings.json").write_text(json.dumps(data))
        cfg = cm.load()
        assert cfg["history_size"] == 50
        assert cfg["default_categories_enabled"] is True  # default preserved


class TestConfigManagerSave:
    def test_save_writes_file(self, config_dir: Path, cm: ConfigManager):
        cm.load()
        cm.set("history_size", 200)
        cm.save()
        raw = (config_dir / "settings.json").read_text()
        data = json.loads(raw)
        assert data["history_size"] == 200

    def test_save_preserves_all_keys(self, config_dir: Path, cm: ConfigManager):
        cm.load()
        cm.set("history_size", 200)
        cm.save()
        raw = (config_dir / "settings.json").read_text()
        data = json.loads(raw)
        assert data["history_size"] == 200
        assert data["default_categories_enabled"] is True


class TestConfigManagerGetSet:
    def test_get_after_load(self, cm: ConfigManager):
        cm.load()
        assert cm.get("history_size") == 100

    def test_set_and_get(self, cm: ConfigManager):
        cm.load()
        cm.set("history_size", 200)
        assert cm.get("history_size") == 200

    def test_get_returns_default_for_unknown_key(self, cm: ConfigManager):
        cm.load()
        assert cm.get("nonexistent") is None

    def test_get_returns_custom_default(self, cm: ConfigManager):
        cm.load()
        assert cm.get("nonexistent", "fallback") == "fallback"

    def test_last_open_dir_defaults_to_empty(self, cm: ConfigManager):
        cm.load()
        assert cm.get("last_open_dir") == ""
