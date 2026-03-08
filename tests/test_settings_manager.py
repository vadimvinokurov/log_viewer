"""Tests for settings manager."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from PySide6.QtCore import QByteArray

from src.utils.settings_manager import (
    SettingsManager,
    AppSettings,
    CustomCategory,
    HighlightPatternData,
)


class TestCustomCategory:
    """Tests for CustomCategory class."""
    
    def test_custom_category_creation(self) -> None:
        """Test creating a custom category."""
        category = CustomCategory(
            name="errors",
            pattern=r"\[ERROR\]",
            parent="app"
        )
        
        assert category.name == "errors"
        assert category.pattern == r"\[ERROR\]"
        assert category.parent == "app"
    
    def test_custom_category_no_parent(self) -> None:
        """Test creating a custom category without parent."""
        category = CustomCategory(
            name="errors",
            pattern=r"\[ERROR\]"
        )
        
        assert category.name == "errors"
        assert category.parent is None
    
    def test_custom_category_to_dict(self) -> None:
        """Test converting custom category to dictionary."""
        category = CustomCategory(
            name="errors",
            pattern=r"\[ERROR\]",
            parent="app"
        )
        
        data = category.to_dict()
        
        assert data["name"] == "errors"
        assert data["pattern"] == r"\[ERROR\]"
        assert data["parent"] == "app"
    
    def test_custom_category_from_dict(self) -> None:
        """Test creating custom category from dictionary."""
        data = {
            "name": "errors",
            "pattern": r"\[ERROR\]",
            "parent": "app"
        }
        
        category = CustomCategory.from_dict(data)
        
        assert category.name == "errors"
        assert category.pattern == r"\[ERROR\]"
        assert category.parent == "app"
    
    def test_custom_category_from_dict_missing_fields(self) -> None:
        """Test creating custom category from dictionary with missing fields."""
        data = {}
        
        category = CustomCategory.from_dict(data)
        
        assert category.name == ""
        assert category.pattern == ""
        assert category.parent is None


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
        
        assert settings.custom_categories == []
        assert settings.highlight_patterns == []
        assert settings.last_file is None
        assert settings.window_geometry is None
        assert settings.column_widths == {}
        assert settings.category_states == {}
    
    def test_settings_to_dict(self) -> None:
        """Test converting settings to dictionary."""
        settings = AppSettings(
            custom_categories=[CustomCategory("errors", r"\[ERROR\]")],
            highlight_patterns=[HighlightPatternData("error", "#FF0000")],
            last_file="/path/to/file.log",
            column_widths={"timestamp": 150, "message": 500}
        )
        
        data = settings.to_dict()
        
        assert len(data["custom_categories"]) == 1
        assert len(data["highlight_patterns"]) == 1
        assert data["last_file"] == "/path/to/file.log"
        assert data["column_widths"] == {"timestamp": 150, "message": 500}
    
    def test_settings_from_dict(self) -> None:
        """Test creating settings from dictionary."""
        data = {
            "custom_categories": [
                {"name": "errors", "pattern": r"\[ERROR\]", "parent": None}
            ],
            "highlight_patterns": [
                {"text": "error", "color_hex": "#FF0000", "is_regex": False, "enabled": True}
            ],
            "last_file": "/path/to/file.log",
            "column_widths": {"timestamp": 150}
        }
        
        settings = AppSettings.from_dict(data)
        
        assert len(settings.custom_categories) == 1
        assert settings.custom_categories[0].name == "errors"
        assert len(settings.highlight_patterns) == 1
        assert settings.highlight_patterns[0].text == "error"
        assert settings.last_file == "/path/to/file.log"
        assert settings.column_widths == {"timestamp": 150}
    
    def test_settings_from_dict_empty(self) -> None:
        """Test creating settings from empty dictionary."""
        settings = AppSettings.from_dict({})
        
        assert settings.custom_categories == []
        assert settings.highlight_patterns == []
        assert settings.last_file is None
        assert settings.window_geometry is None
        assert settings.column_widths == {}
        assert settings.category_states == {}
    
    def test_settings_with_category_states(self) -> None:
        """Test settings with category states."""
        settings = AppSettings(
            category_states={"app": True, "app.network": False, "system": True}
        )
        
        assert settings.category_states == {"app": True, "app.network": False, "system": True}
    
    def test_settings_category_states_to_dict(self) -> None:
        """Test converting settings with category states to dictionary."""
        settings = AppSettings(
            custom_categories=[CustomCategory("errors", r"\[ERROR\]")],
            category_states={"app": True, "system": False}
        )
        
        data = settings.to_dict()
        
        assert "category_states" in data
        assert data["category_states"] == {"app": True, "system": False}
    
    def test_settings_category_states_from_dict(self) -> None:
        """Test creating settings from dictionary with category states."""
        data = {
            "custom_categories": [],
            "highlight_patterns": [],
            "category_states": {"app": True, "app.network": False, "system": True}
        }
        
        settings = AppSettings.from_dict(data)
        
        assert settings.category_states == {"app": True, "app.network": False, "system": True}
    
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
        
        assert settings.custom_categories == []
        assert settings.highlight_patterns == []
        assert settings.last_file is None
    
    def test_save_and_load_settings(self, temp_settings_file: str) -> None:
        """Test saving and loading settings."""
        manager = SettingsManager(temp_settings_file)
        
        # Add some settings
        manager.add_custom_category(CustomCategory("errors", r"\[ERROR\]"))
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
        manager.set_last_file("/path/to/file.log")
        
        # Save
        manager.save()
        
        # Create new manager and load
        manager2 = SettingsManager(temp_settings_file)
        settings = manager2.load()
        
        assert len(settings.custom_categories) == 1
        assert settings.custom_categories[0].name == "errors"
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
        assert settings.custom_categories == []
        assert settings.highlight_patterns == []
    
    def test_add_custom_category(self, temp_settings_file: str) -> None:
        """Test adding custom category."""
        manager = SettingsManager(temp_settings_file)
        
        category = CustomCategory("errors", r"\[ERROR\]", parent="app")
        manager.add_custom_category(category)
        
        categories = manager.get_custom_categories()
        
        assert len(categories) == 1
        assert categories[0].name == "errors"
        assert categories[0].pattern == r"\[ERROR\]"
        assert categories[0].parent == "app"
    
    def test_remove_custom_category(self, temp_settings_file: str) -> None:
        """Test removing custom category."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_custom_category(CustomCategory("errors", r"\[ERROR\]"))
        manager.add_custom_category(CustomCategory("warnings", r"\[WARN\]"))
        
        result = manager.remove_custom_category("errors")
        
        assert result is True
        categories = manager.get_custom_categories()
        assert len(categories) == 1
        assert categories[0].name == "warnings"
    
    def test_remove_custom_category_not_found(self, temp_settings_file: str) -> None:
        """Test removing non-existent custom category."""
        manager = SettingsManager(temp_settings_file)
        
        result = manager.remove_custom_category("nonexistent")
        
        assert result is False
    
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
            
            manager.add_custom_category(CustomCategory("test", "pattern"))
            manager.save()
            
            assert os.path.exists(filepath)
    
    def test_multiple_custom_categories(self, temp_settings_file: str) -> None:
        """Test multiple custom categories."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_custom_category(CustomCategory("errors", r"\[ERROR\]"))
        manager.add_custom_category(CustomCategory("warnings", r"\[WARN\]"))
        manager.add_custom_category(CustomCategory("info", r"\[INFO\]"))
        
        categories = manager.get_custom_categories()
        
        assert len(categories) == 3
        names = [c.name for c in categories]
        assert "errors" in names
        assert "warnings" in names
        assert "info" in names
    
    def test_multiple_highlight_patterns(self, temp_settings_file: str) -> None:
        """Test multiple highlight patterns."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_highlight_pattern(HighlightPatternData("error", "#FF0000"))
        manager.add_highlight_pattern(HighlightPatternData("warning", "#FFFF00"))
        manager.add_highlight_pattern(HighlightPatternData("info", "#00FF00"))
        
        patterns = manager.get_highlight_patterns()
        
        assert len(patterns) == 3
    
    def test_set_category_states(self, temp_settings_file: str) -> None:
        """Test setting category states."""
        manager = SettingsManager(temp_settings_file)
        
        states = {"app": True, "app.network": False, "system": True}
        manager.set_category_states(states)
        
        result = manager.get_category_states()
        assert result == states
    
    def test_get_category_states_copy(self, temp_settings_file: str) -> None:
        """Test that get_category_states returns a copy."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_category_states({"app": True})
        
        states = manager.get_category_states()
        states["new"] = False
        
        # Original should be unchanged
        assert "new" not in manager.get_category_states()
    
    def test_category_states_default_empty(self, temp_settings_file: str) -> None:
        """Test that category states default to empty dict."""
        manager = SettingsManager(temp_settings_file)
        
        result = manager.get_category_states()
        assert result == {}


class TestSettingsManagerPersistence:
    """Tests for settings persistence."""
    
    def test_persist_custom_categories(self, temp_settings_file: str) -> None:
        """Test persisting custom categories."""
        manager = SettingsManager(temp_settings_file)
        
        manager.add_custom_category(CustomCategory("errors", r"\[ERROR\]", "app"))
        manager.add_custom_category(CustomCategory("warnings", r"\[WARN\]"))
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        categories = manager2.get_custom_categories()
        assert len(categories) == 2
    
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
    
    def test_persist_category_states(self, temp_settings_file: str) -> None:
        """Test persisting category states."""
        manager = SettingsManager(temp_settings_file)
        
        states = {"app": True, "app.network": False, "system": True}
        manager.set_category_states(states)
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        loaded_states = manager2.get_category_states()
        assert loaded_states == states
    
    def test_persist_category_states_empty(self, temp_settings_file: str) -> None:
        """Test persisting empty category states."""
        manager = SettingsManager(temp_settings_file)
        
        manager.set_category_states({})
        manager.save()
        
        # Load in new manager
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        loaded_states = manager2.get_category_states()
        assert loaded_states == {}
    
    def test_category_states_with_corrupted_data(self, temp_settings_file: str) -> None:
        """Test category states with corrupted data resets to default."""
        # Write invalid JSON
        with open(temp_settings_file, "w") as f:
            f.write("{ invalid json }")
        
        manager = SettingsManager(temp_settings_file)
        settings = manager.load()
        
        # Should return default settings with empty category_states
        assert settings.category_states == {}


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
    
    def test_unicode_in_settings(self, temp_settings_file: str) -> None:
        """Test with unicode characters in settings."""
        manager = SettingsManager(temp_settings_file)
        
        # Unicode category name
        manager.add_custom_category(CustomCategory("ошибки", r"\[ОШИБКА\]"))
        manager.save()
        
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        categories = manager2.get_custom_categories()
        assert categories[0].name == "ошибки"
    
    def test_concurrent_modifications(self, temp_settings_file: str) -> None:
        """Test concurrent modifications to settings."""
        manager = SettingsManager(temp_settings_file)
        
        # Add category
        manager.add_custom_category(CustomCategory("errors", r"\[ERROR\]"))
        
        # Get categories and modify returned list
        categories = manager.get_custom_categories()
        categories.append(CustomCategory("new", "pattern"))
        
        # Original should be unchanged
        assert len(manager.get_custom_categories()) == 1
    
    def test_large_settings(self, temp_settings_file: str) -> None:
        """Test with large settings."""
        manager = SettingsManager(temp_settings_file)
        
        # Add many categories and patterns
        for i in range(100):
            manager.add_custom_category(CustomCategory(f"category{i}", f"pattern{i}"))
            manager.add_highlight_pattern(HighlightPatternData(f"text{i}", "#FF0000"))
        
        manager.save()
        
        # Load and verify
        manager2 = SettingsManager(temp_settings_file)
        manager2.load()
        
        assert len(manager2.get_custom_categories()) == 100
        assert len(manager2.get_highlight_patterns()) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])