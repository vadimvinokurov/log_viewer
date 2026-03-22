"""Tests for HighlightsTabContent with native QListWidgetItem.

// Ref: docs/specs/features/highlight-panel.md §10
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.highlight_engine import HighlightPattern
from src.views.components.highlights_tab import (
    HighlightsTabContent,
    _get_color_emoji,
)


class TestGetColorEmoji:
    """Tests for _get_color_emoji helper function.
    
    // Ref: docs/specs/features/highlight-panel.md §10.1
    """
    
    def test_red_color(self) -> None:
        """Test red color returns red circle emoji."""
        color = QColor(255, 0, 0)  # Pure red
        emoji = _get_color_emoji(color)
        assert emoji == "🔴"
    
    def test_yellow_color(self) -> None:
        """Test yellow color returns yellow circle emoji."""
        color = QColor(255, 255, 0)  # Pure yellow
        emoji = _get_color_emoji(color)
        assert emoji == "🟡"
    
    def test_green_color(self) -> None:
        """Test green color returns green circle emoji."""
        color = QColor(0, 255, 0)  # Pure green
        emoji = _get_color_emoji(color)
        assert emoji == "🟢"
    
    def test_blue_color(self) -> None:
        """Test blue color returns blue circle emoji."""
        color = QColor(0, 0, 255)  # Pure blue
        emoji = _get_color_emoji(color)
        assert emoji == "🔵"
    
    def test_purple_color(self) -> None:
        """Test purple color returns purple circle emoji."""
        color = QColor(128, 0, 255)  # Purple
        emoji = _get_color_emoji(color)
        assert emoji == "🟣"
    
    def test_orange_color(self) -> None:
        """Test orange color returns orange circle emoji."""
        color = QColor(255, 128, 0)  # Orange
        emoji = _get_color_emoji(color)
        assert emoji == "🟠"
    
    def test_dark_color(self) -> None:
        """Test dark/low value color returns black circle."""
        color = QColor(30, 30, 30)  # Very dark
        emoji = _get_color_emoji(color)
        assert emoji == "⚫"
    
    def test_light_color(self) -> None:
        """Test light/low saturation color returns white circle."""
        color = QColor(250, 250, 250)  # Very light
        emoji = _get_color_emoji(color)
        assert emoji == "⚪"


class TestHighlightsTabContent:
    """Tests for HighlightsTabContent widget.
    
    // Ref: docs/specs/features/highlight-panel.md §10.1
    """
    
    def test_creation(self, qtbot) -> None:
        """Test creating HighlightsTabContent.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_creation
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Verify initial state (empty list)
        assert content._pattern_list.count() == 0
        assert len(content._pattern_items) == 0
        
        # Verify buttons disabled
        assert not content._edit_button.isEnabled()
        assert not content._delete_button.isEnabled()
        
        # Add button should be enabled
        assert content._add_button.isEnabled()
    
    def test_add_pattern(self, qtbot) -> None:
        """Test adding a pattern.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_add_pattern
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Create pattern
        color = QColor(255, 255, 0)
        pattern = HighlightPattern(
            text="error",
            color=color,
            is_regex=False,
            enabled=True
        )
        
        # Add pattern
        content.add_pattern(pattern)
        
        # Verify pattern appears in list
        assert content._pattern_list.count() == 1
        assert "error" in content._pattern_items
        
        # Verify pattern_added signal NOT emitted (only emitted from dialog)
        # This is per spec: add_pattern() does not emit signal, only dialog does
    
    def test_add_pattern_with_checkbox(self, qtbot) -> None:
        """Test that added pattern has correct checkbox state."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Create enabled pattern
        pattern_enabled = HighlightPattern(
            text="enabled",
            color=QColor(255, 0, 0),
            is_regex=False,
            enabled=True
        )
        
        content.add_pattern(pattern_enabled)
        
        # Verify checkbox is checked
        item = content._pattern_items["enabled"]
        assert item.checkState() == Qt.CheckState.Checked
        
        # Create disabled pattern
        pattern_disabled = HighlightPattern(
            text="disabled",
            color=QColor(0, 255, 0),
            is_regex=False,
            enabled=False
        )
        
        content.add_pattern(pattern_disabled)
        
        # Verify checkbox is unchecked
        item = content._pattern_items["disabled"]
        assert item.checkState() == Qt.CheckState.Unchecked
    
    def test_add_pattern_display_text(self, qtbot) -> None:
        """Test that pattern display text includes emoji and type."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Create text pattern
        pattern_text = HighlightPattern(
            text="error",
            color=QColor(255, 255, 0),  # Yellow
            is_regex=False,
            enabled=True
        )
        
        content.add_pattern(pattern_text)
        
        item = content._pattern_items["error"]
        text = item.text()
        
        # Should contain emoji, pattern text, and type indicator
        assert "🟡" in text  # Yellow emoji
        assert "error" in text
        assert "(text)" in text
        
        # Create regex pattern
        pattern_regex = HighlightPattern(
            text=r"\d+",
            color=QColor(255, 0, 0),  # Red
            is_regex=True,
            enabled=True
        )
        
        content.add_pattern(pattern_regex)
        
        item = content._pattern_items[r"\d+"]
        text = item.text()
        
        # Should contain regex type indicator
        assert "🔴" in text  # Red emoji
        assert r"\d+" in text
        assert "(regex)" in text
    
    def test_set_patterns(self, qtbot) -> None:
        """Test setting multiple patterns.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_set_patterns
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Create patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0), is_regex=False, enabled=True),
            HighlightPattern(text="warning", color=QColor(255, 255, 0), is_regex=False, enabled=True),
            HighlightPattern(text=r"\d+", color=QColor(0, 255, 0), is_regex=True, enabled=False),
        ]
        
        # Set patterns
        content.set_patterns(patterns)
        
        # Verify all patterns appear in list
        assert content._pattern_list.count() == 3
        
        # Verify correct count
        assert len(content._pattern_items) == 3
        assert "error" in content._pattern_items
        assert "warning" in content._pattern_items
        assert r"\d+" in content._pattern_items
    
    def test_set_patterns_clears_existing(self, qtbot) -> None:
        """Test that set_patterns clears existing items."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add initial patterns
        patterns1 = [
            HighlightPattern(text="error", color=QColor(255, 0, 0)),
        ]
        content.set_patterns(patterns1)
        
        assert content._pattern_list.count() == 1
        
        # Set new patterns
        patterns2 = [
            HighlightPattern(text="warning", color=QColor(255, 255, 0)),
            HighlightPattern(text="info", color=QColor(0, 255, 0)),
        ]
        content.set_patterns(patterns2)
        
        # Verify old items cleared
        assert content._pattern_list.count() == 2
        assert "error" not in content._pattern_items
        assert "warning" in content._pattern_items
        assert "info" in content._pattern_items
    
    def test_enable_disable(self, qtbot) -> None:
        """Test enabling/disabling patterns.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_enable_disable
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Set patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0), enabled=True),
        ]
        content.set_patterns(patterns)
        
        # Track signal emissions
        signal_data = []
        def on_enabled_changed(text: str, enabled: bool):
            signal_data.append((text, enabled))
        
        content.pattern_enabled_changed.connect(on_enabled_changed)
        
        # Get the pattern item
        item = content._pattern_items["error"]
        
        # Toggle checkbox to disable
        item.setCheckState(Qt.CheckState.Unchecked)
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify pattern_enabled_changed signal emitted with correct args
        assert len(signal_data) == 1
        assert signal_data[0] == ("error", False)
    
    def test_edit_pattern(self, qtbot) -> None:
        """Test editing a pattern.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_edit_pattern
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Set patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0), is_regex=False, enabled=True),
        ]
        content.set_patterns(patterns)
        
        # Select pattern
        content._pattern_list.setCurrentRow(0)
        
        # Track signal emissions
        signal_data = []
        def on_edited(old_text: str, new_text: str, color: QColor, is_regex: bool):
            signal_data.append((old_text, new_text, color, is_regex))
        
        content.pattern_edited.connect(on_edited)
        
        # Mock the dialog to return accepted with new values
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 1  # QDialog.DialogCode.Accepted
            dialog_instance.get_text.return_value = "warning"
            dialog_instance.get_color.return_value = QColor(0, 255, 0)
            dialog_instance.is_regex.return_value = True
            MockDialog.return_value = dialog_instance
            
            # Click edit button
            content._edit_button.click()
            
            # Wait for signal
            qtbot.wait(10)
        
        # Verify edit_requested signal emitted (pattern_edited)
        assert len(signal_data) == 1
        assert signal_data[0][0] == "error"  # old_text
        assert signal_data[0][1] == "warning"  # new_text
    
    def test_edit_pattern_double_click(self, qtbot) -> None:
        """Test editing a pattern via double-click."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Set patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0), is_regex=False, enabled=True),
        ]
        content.set_patterns(patterns)
        
        # Track signal emissions
        signal_data = []
        def on_edited(old_text: str, new_text: str, color: QColor, is_regex: bool):
            signal_data.append((old_text, new_text, color, is_regex))
        
        content.pattern_edited.connect(on_edited)
        
        # Mock the dialog
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 1  # QDialog.DialogCode.Accepted
            dialog_instance.get_text.return_value = "edited"
            dialog_instance.get_color.return_value = QColor(255, 0, 0)
            dialog_instance.is_regex.return_value = False
            MockDialog.return_value = dialog_instance
            
            # Double-click the item
            item = content._pattern_items["error"]
            content._pattern_list.itemDoubleClicked.emit(item)
            
            # Wait for signal
            qtbot.wait(10)
        
        # Verify edit signal emitted
        assert len(signal_data) == 1
        assert signal_data[0][0] == "error"
        assert signal_data[0][1] == "edited"
    
    def test_delete_pattern(self, qtbot) -> None:
        """Test deleting a pattern.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_delete_pattern
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Set patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0), enabled=True),
        ]
        content.set_patterns(patterns)
        
        # Select pattern
        content._pattern_list.setCurrentRow(0)
        
        # Track signal emissions
        signal_data = []
        def on_removed(text: str):
            signal_data.append(text)
        
        content.pattern_removed.connect(on_removed)
        
        # Click delete button (no confirmation dialog)
        content._delete_button.click()
        
        # Wait for signal
        qtbot.wait(10)
        
        # Verify pattern_removed signal emitted
        assert len(signal_data) == 1
        assert signal_data[0] == "error"
    
    def test_get_patterns(self, qtbot) -> None:
        """Test getting all patterns.
        
        // Ref: docs/specs/features/highlight-panel.md §10.1 - test_highlights_tab_content_get_patterns
        """
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Create patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0), is_regex=False, enabled=True),
            HighlightPattern(text="warning", color=QColor(255, 255, 0), is_regex=False, enabled=False),
            HighlightPattern(text=r"\d+", color=QColor(0, 255, 0), is_regex=True, enabled=True),
        ]
        
        # Set patterns
        content.set_patterns(patterns)
        
        # Get patterns
        result = content.get_patterns()
        
        # Verify returned list matches input
        assert len(result) == 3
        
        # Check each pattern
        result_dict = {p.text: p for p in result}
        assert "error" in result_dict
        assert result_dict["error"].is_regex is False
        assert result_dict["error"].enabled is True
        
        assert "warning" in result_dict
        assert result_dict["warning"].enabled is False
        
        assert r"\d+" in result_dict
        assert result_dict[r"\d+"].is_regex is True
    
    def test_get_patterns_empty(self, qtbot) -> None:
        """Test getting patterns when empty."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        result = content.get_patterns()
        
        assert result == []
    
    def test_clear(self, qtbot) -> None:
        """Test clearing all patterns."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0)),
            HighlightPattern(text="warning", color=QColor(255, 255, 0)),
        ]
        content.set_patterns(patterns)
        
        assert content._pattern_list.count() == 2
        
        # Clear
        content.clear()
        
        # Verify cleared
        assert content._pattern_list.count() == 0
        assert len(content._pattern_items) == 0
    
    def test_button_states_no_selection(self, qtbot) -> None:
        """Test that buttons are disabled when no selection."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add patterns
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0)),
        ]
        content.set_patterns(patterns)
        
        # No selection - buttons should be disabled
        assert not content._edit_button.isEnabled()
        assert not content._delete_button.isEnabled()
        
        # Select item - buttons should be enabled
        content._pattern_list.setCurrentRow(0)
        assert content._edit_button.isEnabled()
        assert content._delete_button.isEnabled()
        
        # Clear selection - buttons should be disabled again
        content._pattern_list.setCurrentItem(None)
        assert not content._edit_button.isEnabled()
        assert not content._delete_button.isEnabled()
    
    def test_add_button_opens_dialog(self, qtbot) -> None:
        """Test that Add button opens dialog and emits signal on accept."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Track signal emissions
        signal_data = []
        def on_added(text: str, color: QColor, is_regex: bool):
            signal_data.append((text, color, is_regex))
        
        content.pattern_added.connect(on_added)
        
        # Mock the dialog
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 1  # QDialog.DialogCode.Accepted
            dialog_instance.get_text.return_value = "new_pattern"
            dialog_instance.get_color.return_value = QColor(255, 0, 255)
            dialog_instance.is_regex.return_value = True
            MockDialog.return_value = dialog_instance
            
            # Click add button
            content._add_button.click()
            
            # Wait for signal
            qtbot.wait(10)
        
        # Verify dialog was created
        assert MockDialog.called
        
        # Verify signal emitted
        assert len(signal_data) == 1
        assert signal_data[0][0] == "new_pattern"
        assert signal_data[0][2] is True  # is_regex
    
    def test_add_button_cancelled(self, qtbot) -> None:
        """Test that Add button doesn't emit signal when dialog is cancelled."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Track signal emissions
        signal_count = [0]
        def on_added(text: str, color: QColor, is_regex: bool):
            signal_count[0] += 1
        
        content.pattern_added.connect(on_added)
        
        # Mock the dialog to return cancelled
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 0  # QDialog.DialogCode.Rejected
            MockDialog.return_value = dialog_instance
            
            # Click add button
            content._add_button.click()
            
            # Wait for signal
            qtbot.wait(10)
        
        # Verify no signal emitted
        assert signal_count[0] == 0
    
    def test_pattern_data_stored_in_item(self, qtbot) -> None:
        """Test that full pattern data is stored in QListWidgetItem."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Create pattern with all fields
        pattern = HighlightPattern(
            text="test_pattern",
            color=QColor(255, 128, 0),
            is_regex=True,
            enabled=False
        )
        
        content.add_pattern(pattern)
        
        # Get item and retrieve stored data
        item = content._pattern_items["test_pattern"]
        stored_pattern = item.data(Qt.ItemDataRole.UserRole)
        
        # Verify all fields preserved
        assert isinstance(stored_pattern, HighlightPattern)
        assert stored_pattern.text == "test_pattern"
        assert stored_pattern.color == QColor(255, 128, 0)
        assert stored_pattern.is_regex is True
        assert stored_pattern.enabled is False


class TestHighlightsTabContentTypeSafety:
    """Tests for type safety with beartype decorator.
    
    // Ref: docs/SPEC.md §1 (beartype requirement)
    """
    
    def test_set_patterns_with_valid_list(self, qtbot) -> None:
        """Verify set_patterns accepts list[HighlightPattern]."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        patterns = [
            HighlightPattern(text="error", color=QColor(255, 0, 0)),
        ]
        
        # Should work without errors
        content.set_patterns(patterns)
        assert content._pattern_list.count() == 1
    
    def test_add_pattern_with_valid_pattern(self, qtbot) -> None:
        """Verify add_pattern accepts HighlightPattern."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        pattern = HighlightPattern(text="error", color=QColor(255, 0, 0))
        
        # Should work without errors
        content.add_pattern(pattern)
        assert content._pattern_list.count() == 1
    
    def test_get_patterns_returns_list(self, qtbot) -> None:
        """Verify get_patterns returns list[HighlightPattern]."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        pattern = HighlightPattern(text="error", color=QColor(255, 0, 0))
        content.add_pattern(pattern)
        
        result = content.get_patterns()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], HighlightPattern)


class TestPatternPersistence:
    """Integration tests for pattern persistence.
    
    // Ref: docs/specs/features/highlight-panel.md §10.1 - test_pattern_persistence
    """
    
    def test_pattern_persistence_via_settings_manager(self, qtbot, tmp_path) -> None:
        """Test that patterns persist via SettingsManager."""
        from src.utils.settings_manager import SettingsManager, HighlightPatternData
        
        settings_file = str(tmp_path / "test_settings.json")
        
        # Create settings manager
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Add highlight patterns
        patterns = [
            HighlightPatternData(text="error", color_hex="#FF0000", is_regex=False, enabled=True),
            HighlightPatternData(text="warning", color_hex="#FFFF00", is_regex=False, enabled=True),
        ]
        settings_manager.settings.highlight_patterns = patterns
        settings_manager.save()
        
        # Create new settings manager (simulates app restart)
        settings_manager2 = SettingsManager(filepath=settings_file)
        settings_manager2.load()
        
        # Verify patterns loaded
        loaded_patterns = settings_manager2.settings.highlight_patterns
        assert len(loaded_patterns) == 2
        assert loaded_patterns[0].text == "error"
        assert loaded_patterns[0].color_hex == "#FF0000"
        assert loaded_patterns[1].text == "warning"
        assert loaded_patterns[1].enabled is True
    
    def test_pattern_persistence_disabled_state(self, qtbot, tmp_path) -> None:
        """Test that disabled state persists."""
        from src.utils.settings_manager import SettingsManager, HighlightPatternData
        
        settings_file = str(tmp_path / "test_settings.json")
        
        # Create settings manager
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Add pattern with enabled=False
        patterns = [
            HighlightPatternData(text="debug", color_hex="#00FF00", is_regex=False, enabled=False),
        ]
        settings_manager.settings.highlight_patterns = patterns
        settings_manager.save()
        
        # Create new settings manager
        settings_manager2 = SettingsManager(filepath=settings_file)
        settings_manager2.load()
        
        # Verify disabled state persisted
        loaded_patterns = settings_manager2.settings.highlight_patterns
        assert len(loaded_patterns) == 1
        assert loaded_patterns[0].enabled is False
    
    def test_pattern_persistence_regex_flag(self, qtbot, tmp_path) -> None:
        """Test that regex flag persists."""
        from src.utils.settings_manager import SettingsManager, HighlightPatternData
        
        settings_file = str(tmp_path / "test_settings.json")
        
        # Create settings manager
        settings_manager = SettingsManager(filepath=settings_file)
        settings_manager.load()
        
        # Add regex pattern
        patterns = [
            HighlightPatternData(text=r"\d+", color_hex="#FF00FF", is_regex=True, enabled=True),
        ]
        settings_manager.settings.highlight_patterns = patterns
        settings_manager.save()
        
        # Create new settings manager
        settings_manager2 = SettingsManager(filepath=settings_file)
        settings_manager2.load()
        
        # Verify regex flag persisted
        loaded_patterns = settings_manager2.settings.highlight_patterns
        assert len(loaded_patterns) == 1
        assert loaded_patterns[0].is_regex is True


class TestHighlightsTabContentSignals:
    """Tests for HighlightsTabContent signal emissions."""
    
    def test_pattern_added_signal_parameters(self, qtbot) -> None:
        """Test pattern_added signal has correct parameters."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Track signal parameters
        signal_params = []
        def on_added(text: str, color: QColor, is_regex: bool):
            signal_params.append((text, color, is_regex))
        
        content.pattern_added.connect(on_added)
        
        # Mock dialog and emit signal
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 1
            dialog_instance.get_text.return_value = "test_pattern"
            dialog_instance.get_color.return_value = QColor(255, 128, 0)
            dialog_instance.is_regex.return_value = True
            MockDialog.return_value = dialog_instance
            
            content._add_button.click()
            qtbot.wait(10)
        
        assert len(signal_params) == 1
        text, color, is_regex = signal_params[0]
        assert text == "test_pattern"
        assert color == QColor(255, 128, 0)
        assert is_regex is True
    
    def test_pattern_removed_signal_parameters(self, qtbot) -> None:
        """Test pattern_removed signal has correct parameters."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add pattern
        pattern = HighlightPattern(text="error", color=QColor(255, 0, 0))
        content.add_pattern(pattern)
        
        # Select and track signal
        content._pattern_list.setCurrentRow(0)
        
        signal_params = []
        def on_removed(text: str):
            signal_params.append(text)
        
        content.pattern_removed.connect(on_removed)
        
        # Click delete button (no confirmation dialog)
        content._delete_button.click()
        qtbot.wait(10)
        
        assert len(signal_params) == 1
        assert signal_params[0] == "error"
    
    def test_pattern_edited_signal_parameters(self, qtbot) -> None:
        """Test pattern_edited signal has correct parameters."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add pattern
        pattern = HighlightPattern(text="old_text", color=QColor(255, 0, 0), is_regex=False)
        content.add_pattern(pattern)
        content._pattern_list.setCurrentRow(0)
        
        # Track signal
        signal_params = []
        def on_edited(old_text: str, new_text: str, color: QColor, is_regex: bool):
            signal_params.append((old_text, new_text, color, is_regex))
        
        content.pattern_edited.connect(on_edited)
        
        # Mock dialog
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 1
            dialog_instance.get_text.return_value = "new_text"
            dialog_instance.get_color.return_value = QColor(0, 255, 0)
            dialog_instance.is_regex.return_value = True
            MockDialog.return_value = dialog_instance
            
            content._edit_button.click()
            qtbot.wait(10)
        
        assert len(signal_params) == 1
        old_text, new_text, color, is_regex = signal_params[0]
        assert old_text == "old_text"
        assert new_text == "new_text"
        assert color == QColor(0, 255, 0)
        assert is_regex is True
    
    def test_pattern_enabled_changed_signal_parameters(self, qtbot) -> None:
        """Test pattern_enabled_changed signal has correct parameters."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add pattern
        pattern = HighlightPattern(text="test", color=QColor(255, 0, 0), enabled=True)
        content.add_pattern(pattern)
        
        # Track signal
        signal_params = []
        def on_enabled_changed(text: str, enabled: bool):
            signal_params.append((text, enabled))
        
        content.pattern_enabled_changed.connect(on_enabled_changed)
        
        # Toggle checkbox
        item = content._pattern_items["test"]
        item.setCheckState(Qt.CheckState.Unchecked)
        qtbot.wait(10)
        
        assert len(signal_params) == 1
        assert signal_params[0] == ("test", False)


class TestEditPatternTextChange:
    """Tests for editing patterns with text changes."""
    
    def test_edit_pattern_updates_dictionary_key(self, qtbot) -> None:
        """Test that editing pattern text updates dictionary key."""
        content = HighlightsTabContent()
        qtbot.addWidget(content)
        
        # Add pattern
        pattern = HighlightPattern(text="old_text", color=QColor(255, 0, 0))
        content.add_pattern(pattern)
        
        # Verify old key exists
        assert "old_text" in content._pattern_items
        
        # Select and edit
        content._pattern_list.setCurrentRow(0)
        
        # Mock dialog
        with patch('src.views.components.highlights_tab.HighlightDialog') as MockDialog:
            dialog_instance = MagicMock()
            dialog_instance.exec.return_value = 1
            dialog_instance.get_text.return_value = "new_text"
            dialog_instance.get_color.return_value = QColor(255, 0, 0)
            dialog_instance.is_regex.return_value = False
            MockDialog.return_value = dialog_instance
            
            content._edit_button.click()
            qtbot.wait(10)
        
        # Verify old key removed, new key added
        assert "old_text" not in content._pattern_items
        assert "new_text" in content._pattern_items


if __name__ == "__main__":
    pytest.main([__file__, "-v"])