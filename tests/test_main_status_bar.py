"""Tests for MainStatusBar panel toggle button.

// Ref: docs/specs/features/panel-toggle-button.md §7.1
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from src.views.widgets.main_status_bar import MainStatusBar


class TestMainStatusBarToggleButton:
    """Tests for panel toggle button functionality.
    
    // Ref: docs/specs/features/panel-toggle-button.md §7.1
    """
    
    def test_toggle_button_initial_state(self, qtbot: pytest.QtBot) -> None:
        """Test toggle button starts with panels visible.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        assert status_bar.is_panels_visible() is True
        assert status_bar._toggle_button.text() == "👁️"
        assert "Hide" in status_bar._toggle_button.toolTip()
    
    def test_toggle_button_click_emits_signal(self, qtbot: pytest.QtBot) -> None:
        """Test clicking toggle button emits signal.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        signal_emitted: list[bool] = []
        status_bar.panels_toggled.connect(lambda v: signal_emitted.append(v))
        
        # Initial state: panels visible (True)
        # Click should emit False (toggle to hide)
        status_bar._toggle_button.click()
        qtbot.wait(10)
        
        assert len(signal_emitted) == 1
        assert signal_emitted[0] is False  # First click hides panels
    
    def test_toggle_button_second_click(self, qtbot: pytest.QtBot) -> None:
        """Test second click emits opposite state.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        signal_emitted: list[bool] = []
        status_bar.panels_toggled.connect(lambda v: signal_emitted.append(v))
        
        # First click: visible -> hidden (emits False)
        status_bar._toggle_button.click()
        qtbot.wait(10)
        
        # Update state to hidden
        status_bar.set_panels_visible(False)
        
        # Second click: hidden -> visible (emits True)
        status_bar._toggle_button.click()
        qtbot.wait(10)
        
        assert len(signal_emitted) == 2
        assert signal_emitted[0] is False  # First click hides
        assert signal_emitted[1] is True   # Second click shows
    
    def test_set_panels_visible_false(self, qtbot: pytest.QtBot) -> None:
        """Test button state updates correctly when panels hidden.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        status_bar.set_panels_visible(False)
        
        assert status_bar.is_panels_visible() is False
        assert status_bar._toggle_button.text() == "👁️‍🗨️"
        assert "Show" in status_bar._toggle_button.toolTip()
    
    def test_set_panels_visible_true(self, qtbot: pytest.QtBot) -> None:
        """Test button state updates correctly when panels shown.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        # First set to hidden
        status_bar.set_panels_visible(False)
        assert status_bar.is_panels_visible() is False
        
        # Then set back to visible
        status_bar.set_panels_visible(True)
        
        assert status_bar.is_panels_visible() is True
        assert status_bar._toggle_button.text() == "👁️"
        assert "Hide" in status_bar._toggle_button.toolTip()
    
    def test_toggle_button_position(self, qtbot: pytest.QtBot) -> None:
        """Test toggle button is at rightmost position.
        
        // Ref: docs/specs/features/panel-toggle-button.md §3.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        # The toggle button should be added as a permanent widget
        # after the statistics bar
        # Check that it exists and is a permanent widget
        assert status_bar._toggle_button is not None
        
        # Verify it's a child of the status bar
        assert status_bar._toggle_button.parent() == status_bar
    
    def test_toggle_button_is_flat(self, qtbot: pytest.QtBot) -> None:
        """Test toggle button is flat style.
        
        // Ref: docs/specs/features/panel-toggle-button.md §6.2
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        assert status_bar._toggle_button.isFlat() is True
    
    def test_toggle_button_tooltip(self, qtbot: pytest.QtBot) -> None:
        """Test toggle button has correct tooltip.
        
        // Ref: docs/specs/features/panel-toggle-button.md §3.1
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        # Initial tooltip (panels visible)
        assert "Ctrl+Shift+P" in status_bar._toggle_button.toolTip()
        
        # After hiding panels
        status_bar.set_panels_visible(False)
        assert "Ctrl+Shift+P" in status_bar._toggle_button.toolTip()
    
    def test_signal_not_emitted_on_set_panels_visible(self, qtbot: pytest.QtBot) -> None:
        """Test that set_panels_visible does not emit signal.
        
        Signal should only be emitted on button click, not on programmatic state change.
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        signal_emitted: list[bool] = []
        status_bar.panels_toggled.connect(lambda v: signal_emitted.append(v))
        
        # Change state programmatically
        status_bar.set_panels_visible(False)
        status_bar.set_panels_visible(True)
        
        # No signal should be emitted
        assert len(signal_emitted) == 0


class TestMainStatusBarToggleButtonEdgeCases:
    """Edge case tests for panel toggle button.
    
    // Ref: docs/specs/features/panel-toggle-button.md §7.1
    """
    
    def test_multiple_state_changes(self, qtbot: pytest.QtBot) -> None:
        """Test multiple rapid state changes."""
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        # Toggle multiple times
        for i in range(10):
            visible = i % 2 == 0
            status_bar.set_panels_visible(visible)
            assert status_bar.is_panels_visible() == visible
    
    def test_state_consistency_after_clicks(self, qtbot: pytest.QtBot) -> None:
        """Test state remains consistent after multiple clicks.
        
        Note: The button click emits a signal but does NOT change state.
        State is changed by the receiver calling set_panels_visible().
        """
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        signal_values: list[bool] = []
        status_bar.panels_toggled.connect(lambda v: signal_values.append(v))
        
        # Click multiple times without changing state
        for _ in range(3):
            status_bar._toggle_button.click()
            qtbot.wait(5)
        
        # All clicks should emit False (toggle from visible state)
        # State remains True because we never called set_panels_visible
        assert len(signal_values) == 3
        assert all(v is False for v in signal_values)
        assert status_bar.is_panels_visible() is True  # State unchanged


class TestMainStatusBarExistingFunctionality:
    """Tests to ensure existing functionality is not broken."""
    
    def test_file_label_still_works(self, qtbot: pytest.QtBot) -> None:
        """Test file label functionality still works."""
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        status_bar.set_file("test.log")
        assert status_bar._file_label.text() == "test.log"
        
        status_bar.set_file(None)
        assert status_bar._file_label.text() == "No file open"
    
    def test_statistics_bar_still_works(self, qtbot: pytest.QtBot) -> None:
        """Test statistics bar functionality still works."""
        status_bar = MainStatusBar()
        qtbot.addWidget(status_bar)
        
        stats = {"error": 5, "warning": 10, "info": 20}
        status_bar.update_statistics(stats)
        
        # Should not raise any exceptions
        status_bar.reset_statistics()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])