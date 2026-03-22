"""Tests for settings manager."""
from __future__ import annotations

import json
import os
import platform
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from PySide6.QtCore import QByteArray

from src.utils.settings_manager import (
    SettingsManager,
    AppSettings,
    HighlightPatternData,
)


class TestHighlightPatternData:
    """Tests for HighlightPatternData class."""
    
    def test_pattern_data_creation(self) -> None:
        """Test creating highlight pattern data."""
        pattern = HighlightPatternData(
            text="error",
            color_hex="#FF0000",
            is_regex=False,
            enabled=True
        )
        
        assert pattern.text == "error"
        assert pattern.color_hex == "#FF0000"
        assert pattern.is_regex is False
        assert pattern.enabled is True
    
    def test_pattern_data_defaults(self) -> None:
        """Test highlight pattern data defaults."""
        pattern = HighlightPatternData(
            text="error",
            color_hex="#FFFF00"
        )
        
        assert pattern.is_regex is False
        assert pattern.enabled is True
    
    def test_pattern_data_to_dict(self) -> None:
        """Test converting pattern data to dictionary."""
        pattern = HighlightPatternData(
            text="error",
            color_hex="#FF0000",
            is_regex=True,
            enabled=False
        )
        
        data = pattern.to_dict()
        
        assert data["text"] == "error"
        assert data["color_hex"] == "#FF0000"
        assert data["is_regex"] is True
        assert data["enabled"] is False
    
    def test_pattern_data_from_dict(self) -> None:
        """Test creating pattern data from dictionary."""
        data = {
            "text": "error",
            "color_hex": "#FF0000",
            "is_regex": True,
            "enabled": False
        }
        
        pattern = HighlightPatternData.from_dict(data)
        
        assert pattern.text == "error"
        assert pattern.color_hex == "#FF0000"
        assert pattern.is_regex is True
        assert pattern.enabled is False
    
    def test_pattern_data_from_dict_defaults(self) -> None:
        """Test creating pattern data from dictionary with defaults."""
        data = {"text": "error"}
        
        pattern = HighlightPatternData.from_dict(data)
        
        assert pattern.text == "error"
        assert pattern.color_hex == "#FFFF00"  # Default yellow
        assert pattern.is_regex is False
        assert pattern.enabled is True


class TestAppSettings:
    """Tests for AppSettings class."""
    
    def test_default_settings(self) -> None:
        """Test default settings."""
        settings = AppSettings()
        
        assert settings.highlight_patterns == []
        assert settings.last_file is None
        assert settings.window_geometry is None
        assert settings.column_widths == {}
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1
        assert settings.category_states_by_file == {}
        assert settings.current_file is None
    
    def test_settings_to_dict(self) -> None:
        """Test converting settings to dictionary."""
        settings = AppSettings(
            highlight_patterns=[HighlightPatternData("error", "#FF0000")],
            last_file="/path/to/file.log",
            column_widths={"timestamp": 150, "message": 500}
        )
        
        data = settings.to_dict()
        
        assert len(data["highlight_patterns"]) == 1
        assert data["last_file"] == "/path/to/file.log"
        assert data["column_widths"] == {"timestamp": 150, "message": 500}
    
    def test_settings_from_dict(self) -> None:
        """Test creating settings from dictionary."""
        data = {
            "highlight_patterns": [
                {"text": "error", "color_hex": "#FF0000", "is_regex": False, "enabled": True}
            ],
            "last_file": "/path/to/file.log",
            "column_widths": {"timestamp": 150}
        }
        
        settings = AppSettings.from_dict(data)
        
        assert len(settings.highlight_patterns) == 1
        assert settings.highlight_patterns[0].text == "error"
        assert settings.last_file == "/path/to/file.log"
        assert settings.column_widths == {"timestamp": 150}
    
    def test_settings_from_dict_empty(self) -> None:
        """Test creating settings from empty dictionary."""
        settings = AppSettings.from_dict({})
        
        assert settings.highlight_patterns == []
        assert settings.last_file is None
        assert settings.window_geometry is None
        assert settings.column_widths == {}
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1
        assert settings.category_states_by_file == {}
        assert settings.current_file is None
    
    def test_settings_with_category_states_by_file(self) -> None:
        """Test settings with per-file category states."""
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1
        settings = AppSettings(
            category_states_by_file={
                "/path/to/file1.log": {"app": True, "app.network": False, "system": True},
                "/path/to/file2.log": {"app": False, "system": True}
            }
        )
        
        assert settings.category_states_by_file == {
            "/path/to/file1.log": {"app": True, "app.network": False, "system": True},
            "/path/to/file2.log": {"app": False, "system": True}
        }
    
    def test_settings_category_states_by_file_to_dict(self) -> None:
        """Test converting settings with per-file category states to dictionary."""
        settings = AppSettings(
            category_states_by_file={
                "/path/to/file.log": {"app": True, "system": False}
            }
        )
        
        data = settings.to_dict()
        
        assert "category_states_by_file" in data
        assert data["category_states_by_file"] == {"/path/to/file.log": {"app": True, "system": False}}
    
    def test_settings_category_states_by_file_from_dict(self) -> None:
        """Test creating settings from dictionary with per-file category states."""
        data = {
            "highlight_patterns": [],
            "category_states_by_file": {
                "/path/to/file.log": {"app": True, "app.network": False, "system": True}
            }
        }
        
        settings = AppSettings.from_dict(data)
        
        assert settings.category_states_by_file == {
            "/path/to/file.log": {"app": True, "app.network": False, "system": True}
        }
    
    def test_window_geometry_serialization(self) -> None:
        """Test window geometry serialization."""
        geometry = QByteArray(b"test_geometry_data")
        settings = AppSettings(window_geometry=bytes(geometry))
        
        data = settings.to_dict()
        
        assert data["window_geometry"] == "746573745f67656f6d657472795f64617461"
        
        # Deserialize
        loaded = AppSettings.from_dict(data)
        assert loaded.window_geometry == b"test_geometry_data"


class TestSettingsManager:
    """Tests for SettingsManager class."""
    
    def test_default_settings(self, temp_settings_file: str) -> None:
        """Test default settings when file doesn't exist."""
        manager = SettingsManager(temp_settings_file)
        
        # Delete the file if it exists
        Path(temp_settings_file).unlink(missing_ok=True)
        
        settings = manager.load()
        
        assert settings.highlight_patterns == []
        assert settings.last_file is None
    
    def test_save_and_load_settings(self, temp_settings_file: str) -> None:
        """Test saving and loading settings."""
        manager = SettingsManager(temp_settings_file)
        
        # Add some settings
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
        manager.set_last_file("/path/to/file.log")
        
        # Save
        manager.save()
        
        # Create new manager and load
        manager2 = SettingsManager(temp_settings_file)
        settings = manager2.load()
        
        assert len(settings.highlight_patterns) == 1
        assert settings.last_file == "/path/to/file.log"
    
    def test_corrupt_settings_file(self, temp_settings_file: str) -> None:
        """Test handling corrupt settings file."""
        # Write invalid JSON
        with open(temp_settings_file, "w") as f:
            f.write("{ invalid json }")
        
        manager = SettingsManager(temp_settings_file)
        settings = manager.load()
        
        # Should return default settings
        assert settings.highlight_patterns == []
    
    def test_add_highlight_pattern(self, temp_settings_file: str) -> None:
        """Test adding highlight pattern."""
        manager = SettingsManager(temp_settings_file)
        
        pattern = HighlightPatternData("error", "#FF0000", is_regex=True)
        manager.add_highlight_pattern(pattern)
        
        patterns = manager.get_highlight_patterns()
        
        assert len(patterns) == 1
        assert patterns[0].text == "error"
        assert patterns[0].color_hex == "#FF0000"
        assert patterns[0].is_regex is True
    
    def test_remove_highlight_pattern(self, temp_settings_file: str) -> None:
        """Test removing highlight pattern."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
        manager.add_highlight_pattern(HighlightPatternData("warning", "#FFFF00"))
        
        result = manager.remove_highlight_pattern(0)
        
        assert result is True
        patterns = manager.get_highlight_patterns()
        assert len(patterns) == 1
        assert patterns[0].text == "warning"
    
    def test_remove_highlight_pattern_invalid_index(self, temp_settings_file: str) -> None:
        """Test removing highlight pattern with invalid index."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
        
        result = manager.remove_highlight_pattern(10)
        
        assert result is False
    
    def test_set_last_file(self, temp_settings_file: str) -> None:
        """Test setting last file."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_last_file("/path/to/file.log")
        
        assert manager.settings.last_file == "/path/to/file.log"
    
    def test_set_window_geometry(self, temp_settings_file: str) -> None:
        """Test setting window geometry."""
        manager = SettingsManager(temp_settings_file)
        
        geometry = QByteArray(b"test_geometry")
        manager.set_window_geometry(geometry)
        
        result = manager.get_window_geometry()
        
        assert result is not None
        assert bytes(result) == b"test_geometry"
    
    def test_get_window_geometry_none(self, temp_settings_file: str) -> None:
        """Test getting window geometry when not set."""
        manager = SettingsManager(temp_settings_file)
        
        result = manager.get_window_geometry()
        
        assert result is None
    
    def test_set_column_widths(self, temp_settings_file: str) -> None:
        """Test setting column widths."""
        manager = SettingsManager(temp_settings_file)
        
        widths = {"timestamp": 150, "category": 200, "message": 500}
        manager.set_column_widths(widths)
        
        result = manager.get_column_widths()
        
        assert result == widths
    
    def test_get_column_widths_copy(self, temp_settings_file: str) -> None:
        """Test that get_column_widths returns a copy."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_column_widths({"timestamp": 150})
        
        widths = manager.get_column_widths()
        widths["new"] = 100
        
        # Original should be unchanged
        assert "new" not in manager.get_column_widths()
    
    def test_settings_property(self, temp_settings_file: str) -> None:
        """Test settings property."""
        manager = SettingsManager(temp_settings_file)
        
        settings = manager.settings
        
        assert isinstance(settings, AppSettings)
    
    def test_save_creates_directory(self) -> None:
        """Test that save creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "settings.json")
            manager = SettingsManager(filepath)
            
            manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
            manager.save()
            
            assert os.path.exists(filepath)
    
    def test_multiple_highlight_patterns(self, temp_settings_file: str) -> None:
        """Test multiple highlight patterns."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
        manager.add_highlight_pattern(HighlightPatternData("warning", "#FFFF00"))
        manager.add_highlight_pattern(HighlightPatternData("info", "#00FF00"))
        
        patterns = manager.get_highlight_patterns()
        
        assert len(patterns) == 3
    
    def test_set_category_states(self, temp_settings_file: str) -> None:
        """Test setting category states for a file."""
        manager = SettingsManager(temp_settings_file)
        
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1, §5.2
        states = {"app": True, "app.network": False, "system": True}
        manager.set_category_states("/path/to/file.log", states)
        
        result = manager.get_category_states("/path/to/file.log")
        assert result == states
    
    def test_get_category_states_copy(self, temp_settings_file: str) -> None:
        """Test that get_category_states returns a copy."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_category_states("/path/to/file.log", {"app": True})
        
        states = manager.get_category_states("/path/to/file.log")
        states["new"] = False
        
        # Original should be unchanged
        assert "new" not in manager.get_category_states("/path/to/file.log")
    
    def test_category_states_default_empty(self, temp_settings_file: str) -> None:
        """Test that category states default to empty dict for new files."""
        manager = SettingsManager(temp_settings_file)
        
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.3
        # New files should return empty dict (all categories default to checked)
        result = manager.get_category_states("/new/file.log")
        assert result == {}
    
    def test_category_states_per_file(self, temp_settings_file: str) -> None:
        """Test that category states are stored per file."""
        manager = SettingsManager(temp_settings_file)
        
        # Set different states for different files
        manager.set_category_states("/path/to/file1.log", {"app": True, "system": False})
        manager.set_category_states("/path/to/file2.log", {"app": False, "network": True})
        
        # Verify each file has its own state
        assert manager.get_category_states("/path/to/file1.log") == {"app": True, "system": False}
        assert manager.get_category_states("/path/to/file2.log") == {"app": False, "network": True}
        assert manager.get_category_states("/path/to/other.log") == {}


class TestSettingsManagerPersistence:
    """Tests for settings persistence."""
    
    def test_persist_highlight_patterns(self, temp_settings_file: str) -> None:
        """Test persisting highlight patterns."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000", is_regex=True))
        manager.add_highlight_pattern(HighlightPatternData("warning", "#FFFF00", enabled=False))
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        patterns = manager2.get_highlight_patterns()
        assert len(patterns) == 2
        assert patterns[0].is_regex is True
        assert patterns[1].enabled is False
    
    def test_persist_column_widths(self, temp_settings_file: str) -> None:
        """Test persisting column widths."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_column_widths({"timestamp": 150, "message": 500})
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        widths = manager2.get_column_widths()
        assert widths == {"timestamp": 150, "message": 500}
    
    def test_persist_last_file(self, temp_settings_file: str) -> None:
        """Test persisting last file."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_last_file("/path/to/file.log")
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        assert manager2.settings.last_file == "/path/to/file.log"
    
    def test_persist_category_states_by_file(self, temp_settings_file: str) -> None:
        """Test persisting per-file category states."""
        manager = SettingsManager(temp_settings_file)
        
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1, §5.2
        states = {"app": True, "app.network": False, "system": True}
        manager.set_category_states("/path/to/file.log", states)
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        loaded_states = manager2.get_category_states("/path/to/file.log")
        assert loaded_states == states
    
    def test_persist_category_states_empty(self, temp_settings_file: str) -> None:
        """Test persisting empty category states for a file."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_category_states("/path/to/file.log", {})
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        loaded_states = manager2.get_category_states("/path/to/file.log")
        assert loaded_states == {}
    
    def test_category_states_with_corrupted_data(self, temp_settings_file: str) -> None:
        """Test category states with corrupted data resets to default."""
        # Write invalid JSON
        with open(temp_settings_file, "w") as f:
            f.write("{ invalid json }")
        
        manager = SettingsManager(temp_settings_file)
        settings = manager.load()
        
        # Should return default settings with empty category_states_by_file
        assert settings.category_states_by_file == {}
    
    def test_migrate_old_category_states_format(self, temp_settings_file: str) -> None:
        """Test migration from old category_states format to new category_states_by_file format."""
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.3
        # Write old format settings
        old_format_data = {
            "highlight_patterns": [],
            "last_file": "/path/to/old_file.log",
            "category_states": {"app": True, "app.network": False, "system": True}
        }
        with open(temp_settings_file, "w") as f:
            json.dump(old_format_data, f)
        
        # Load and verify migration
        manager = SettingsManager(temp_settings_file)
        settings = manager.load()
        
        # Old category_states should be migrated to category_states_by_file
        assert settings.category_states_by_file == {
            "/path/to/old_file.log": {"app": True, "app.network": False, "system": True}
        }
    
    def test_migrate_old_category_states_no_last_file(self, temp_settings_file: str) -> None:
        """Test migration when old format has no last_file."""
        # Write old format without last_file
        old_format_data = {
            "highlight_patterns": [],
            "category_states": {"app": True, "system": False}
        }
        with open(temp_settings_file, "w") as f:
            json.dump(old_format_data, f)
        
        # Load and verify migration
        manager = SettingsManager(temp_settings_file)
        settings = manager.load()
        
        # Without last_file, migration should result in empty dict
        assert settings.category_states_by_file == {}
    
    def test_new_format_takes_precedence(self, temp_settings_file: str) -> None:
        """Test that new format takes precedence over old format."""
        # Write both old and new format
        mixed_format_data = {
            "highlight_patterns": [],
            "last_file": "/path/to/old_file.log",
            "category_states": {"app": True, "system": False},
            "category_states_by_file": {
                "/path/to/new_file.log": {"app": False, "network": True}
            }
        }
        with open(temp_settings_file, "w") as f:
            json.dump(mixed_format_data, f)
        
        # Load and verify new format is used
        manager = SettingsManager(temp_settings_file)
        settings = manager.load()
        
        # New format should take precedence
        assert settings.category_states_by_file == {
            "/path/to/new_file.log": {"app": False, "network": True}
        }


class TestSettingsManagerEdgeCases:
    """Edge case tests for SettingsManager."""
    
    def test_empty_file_path(self) -> None:
        """Test with empty file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "settings.json")
            manager = SettingsManager(filepath)
            
            # Should work with valid path
            settings = manager.load()
            assert isinstance(settings, AppSettings)
    
    def test_special_characters_in_path(self, temp_settings_file: str) -> None:
        """Test with special characters in last file path."""
        manager = SettingsManager(temp_settings_file)
        
        # Path with special characters
        special_path = "/path/with spaces/and'quotes/file.log"
        manager.set_last_file(special_path)
        manager.save()
        
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        assert manager2.settings.last_file == special_path
    
    def test_large_settings(self, temp_settings_file: str) -> None:
        """Test with large settings."""
        manager = SettingsManager(temp_settings_file)
        
        # Add many patterns
        for i in range(100):
            manager.add_highlight_pattern(HighlightPatternData(f"text{i}", "#FF0000"))
        
        manager.save()
        
        # Load and verify
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        assert len(manager2.get_highlight_patterns()) == 100


class TestPlatformSettingsPath:
    """Tests for platform-specific settings path resolution.
    
    Ref: docs/specs/features/settings-persistence-fix.md §3.1
    """
    
    def test_platform_settings_path_macos(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test macOS settings path."""
        # Mock platform.system to return "Darwin"
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "Users" / "test")
        
        # Create the home directory
        (tmp_path / "Users" / "test").mkdir(parents=True, exist_ok=True)
        
        path = SettingsManager._get_platform_settings_path()
        
        expected = tmp_path / "Users" / "test" / "Library" / "Application Support" / "Log Viewer" / "settings.json"
        assert path == expected
    
    def test_platform_settings_path_windows(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test Windows settings path."""
        # Mock platform.system to return "Windows"
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        
        # Mock APPDATA environment variable
        appdata_path = tmp_path / "Users" / "test" / "AppData" / "Roaming"
        monkeypatch.setattr(os, "environ", {"APPDATA": str(appdata_path)})
        
        path = SettingsManager._get_platform_settings_path()
        
        expected = appdata_path / "LogViewer" / "settings.json"
        assert path == expected
    
    def test_platform_settings_path_windows_no_appdata(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test Windows settings path when APPDATA is not set."""
        # Mock platform.system to return "Windows"
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        
        # Mock no APPDATA environment variable
        monkeypatch.setattr(os, "environ", {})
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "Users" / "test")
        
        # Create the home directory
        (tmp_path / "Users" / "test").mkdir(parents=True, exist_ok=True)
        
        path = SettingsManager._get_platform_settings_path()
        
        expected = tmp_path / "Users" / "test" / "AppData" / "Roaming" / "LogViewer" / "settings.json"
        assert path == expected
    
    def test_platform_settings_path_linux(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test Linux settings path."""
        # Mock platform.system to return "Linux"
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home" / "test")
        
        # Create the home directory
        (tmp_path / "home" / "test").mkdir(parents=True, exist_ok=True)
        
        path = SettingsManager._get_platform_settings_path()
        
        expected = tmp_path / "home" / "test" / ".config" / "LogViewer" / "settings.json"
        assert path == expected
    
    def test_platform_settings_path_creates_directory(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that platform settings directory is created if it doesn't exist."""
        # Mock platform.system to return "Linux"
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home" / "test")
        
        # Create the home directory
        (tmp_path / "home" / "test").mkdir(parents=True, exist_ok=True)
        
        # Directory should not exist yet
        config_dir = tmp_path / "home" / "test" / ".config" / "LogViewer"
        assert not config_dir.exists()
        
        # Call _get_platform_settings_path
        path = SettingsManager._get_platform_settings_path()
        
        # Directory should now exist
        assert config_dir.exists()
        assert path.parent == config_dir
    
    def test_settings_manager_default_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that SettingsManager uses platform-specific path by default."""
        # Mock platform.system to return "Linux"
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home" / "test")
        
        # Create the home directory
        (tmp_path / "home" / "test").mkdir(parents=True, exist_ok=True)
        
        # Create manager without filepath argument
        manager = SettingsManager()
        
        # Should use platform-specific path
        expected = tmp_path / "home" / "test" / ".config" / "LogViewer" / "settings.json"
        assert manager.filepath == expected
    
    def test_settings_manager_custom_path(self, temp_settings_file: str) -> None:
        """Test that SettingsManager can still use custom path."""
        manager = SettingsManager(temp_settings_file)
        
        assert manager.filepath == Path(temp_settings_file)


class TestSettingsMigration:
    """Tests for settings migration from old location.
    
    Ref: docs/specs/features/settings-persistence-fix.md §2.3
    """
    
    def test_migrate_from_old_location(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test migration from old settings.json location."""
        # Mock platform.system to return "Linux"
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home" / "test")
        
        # Create the home directory
        (tmp_path / "home" / "test").mkdir(parents=True, exist_ok=True)
        
        # Create old settings.json in current directory
        old_settings = {
            "highlight_patterns": [{"text": "error", "color_hex": "#FF0000"}],
            "last_file": "/old/path/file.log"
        }
        old_path = Path("settings.json")
        with open(old_path, "w") as f:
            json.dump(old_settings, f)
        
        try:
            # Create manager (should migrate)
            manager = SettingsManager()
            
            # New settings file should exist
            assert manager.filepath.exists()
            
            # Load and verify settings were migrated
            settings = manager.load()
            assert len(settings.highlight_patterns) == 1
            assert settings.last_file == "/old/path/file.log"
        finally:
            # Clean up old settings file
            old_path.unlink(missing_ok=True)
    
    def test_no_migration_when_new_exists(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that migration doesn't happen when new settings already exist."""
        # Mock platform.system to return "Linux"
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home" / "test")
        
        # Create the home directory
        (tmp_path / "home" / "test").mkdir(parents=True, exist_ok=True)
        
        # Create new settings file
        new_settings_path = tmp_path / "home" / "test" / ".config" / "LogViewer" / "settings.json"
        new_settings_path.parent.mkdir(parents=True, exist_ok=True)
        new_settings = {
            "highlight_patterns": [{"text": "warning", "color_hex": "#FFFF00"}],
            "last_file": "/new/path/file.log"
        }
        with open(new_settings_path, "w") as f:
            json.dump(new_settings, f)
        
        # Create old settings.json in current directory
        old_settings = {
            "highlight_patterns": [{"text": "error", "color_hex": "#FF0000"}],
            "last_file": "/old/path/file.log"
        }
        old_path = Path("settings.json")
        with open(old_path, "w") as f:
            json.dump(old_settings, f)
        
        try:
            # Create manager (should NOT migrate)
            manager = SettingsManager()
            
            # Load and verify new settings are preserved
            settings = manager.load()
            assert len(settings.highlight_patterns) == 1
            assert settings.highlight_patterns[0].text == "warning"
            assert settings.last_file == "/new/path/file.log"
        finally:
            # Clean up old settings file
            old_path.unlink(missing_ok=True)
    
    def test_no_migration_when_no_old_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that migration doesn't happen when no old settings file exists."""
        # Mock platform.system to return "Linux"
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home" / "test")
        
        # Create the home directory
        (tmp_path / "home" / "test").mkdir(parents=True, exist_ok=True)
        
        # Create manager (no old file to migrate)
        manager = SettingsManager()
        
        # New settings file should not exist yet (not loaded)
        # But the directory should be created
        assert manager.filepath.parent.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])