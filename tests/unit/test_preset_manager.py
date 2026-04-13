"""Tests for PresetManager."""

from pathlib import Path

import pytest

from log_viewer.core.config import ConfigManager
from log_viewer.core.models import Filter, Highlight, SearchMode
from log_viewer.core.preset_manager import PresetManager


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / ".logviewer"


@pytest.fixture
def cm(config_dir: Path) -> ConfigManager:
    manager = ConfigManager(config_dir=config_dir)
    manager.load()
    # Point presets_path to temp dir so tests are isolated
    manager.set("presets_path", str(config_dir / "presets"))
    return manager


@pytest.fixture
def pm(cm: ConfigManager) -> PresetManager:
    return PresetManager(cm)


def _make_store_state(
    filters: list[Filter] | None = None,
    highlights: list[Highlight] | None = None,
    disabled_categories: list[str] | None = None,
) -> dict:
    return {
        "filters": filters or [],
        "highlights": highlights or [],
        "disabled_categories": disabled_categories or [],
    }


class TestPresetSave:
    def test_save_creates_yaml_file(self, pm: PresetManager, config_dir: Path):
        state = _make_store_state(
            filters=[Filter("error", SearchMode.PLAIN)],
            highlights=[Highlight("fail", SearchMode.PLAIN, color="red")],
            disabled_categories=["http"],
        )
        pm.save("my-debug", state)
        preset_path = config_dir / "presets" / "my-debug.yaml"
        assert preset_path.exists()

    def test_save_overwrites_existing(self, pm: PresetManager):
        state1 = _make_store_state(filters=[Filter("a", SearchMode.PLAIN)])
        state2 = _make_store_state(filters=[Filter("b", SearchMode.PLAIN)])
        pm.save("test", state1)
        pm.save("test", state2)
        loaded = pm.load("test")
        assert len(loaded["filters"]) == 1
        assert loaded["filters"][0]["pattern"] == "b"


class TestPresetLoad:
    def test_load_returns_saved_data(self, pm: PresetManager):
        state = _make_store_state(
            filters=[Filter("error", SearchMode.PLAIN)],
            highlights=[Highlight("fail", SearchMode.PLAIN, color="red")],
            disabled_categories=["http"],
        )
        pm.save("my-debug", state)
        loaded = pm.load("my-debug")
        assert len(loaded["filters"]) == 1
        assert loaded["filters"][0]["pattern"] == "error"
        assert len(loaded["highlights"]) == 1
        assert loaded["highlights"][0]["color"] == "red"
        assert "http" in loaded["disabled_categories"]

    def test_load_nonexistent_raises(self, pm: PresetManager):
        with pytest.raises(FileNotFoundError):
            pm.load("nonexistent")


class TestPresetDelete:
    def test_delete_removes_file(self, pm: PresetManager):
        state = _make_store_state()
        pm.save("to-delete", state)
        assert pm.exists("to-delete")
        pm.delete("to-delete")
        assert not pm.exists("to-delete")

    def test_delete_nonexistent_raises(self, pm: PresetManager):
        with pytest.raises(FileNotFoundError):
            pm.delete("nonexistent")


class TestPresetList:
    def test_list_empty(self, pm: PresetManager):
        assert pm.list_presets() == []

    def test_list_returns_names(self, pm: PresetManager):
        for name in ["alpha", "beta", "gamma"]:
            pm.save(name, _make_store_state())
        names = pm.list_presets()
        assert sorted(names) == ["alpha", "beta", "gamma"]

    def test_list_excludes_non_yaml(self, pm: PresetManager):
        pm.save("valid", _make_store_state())
        presets_dir = pm._presets_dir()
        presets_dir.mkdir(parents=True, exist_ok=True)
        (presets_dir / "readme.txt").write_text("not a preset")
        names = pm.list_presets()
        assert names == ["valid"]


class TestPresetExists:
    def test_exists_true(self, pm: PresetManager):
        pm.save("yes", _make_store_state())
        assert pm.exists("yes")

    def test_exists_false(self, pm: PresetManager):
        assert not pm.exists("no")
