"""Tests for MainWindow panel toggle functionality.

// Ref: docs/specs/features/panel-toggle-button.md §7.1
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from src.views.main_window import MainWindow


class TestMainWindowPanelToggle:
    """Tests for MainWindow panel toggle functionality.
    
    // Ref: docs/specs/features/panel-toggle-button.md §7.1
    """
    
    def test_initial_panels_visible(self, qtbot: pytest.QtBot) -> None:
        """Test panels start visible by default.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        
        assert window.is_panels_visible() is True
    
    def test_toggle_panels_hides(self, qtbot: pytest.QtBot) -> None:
        """Test toggle_panels hides panels when visible.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        # Initial state: panels visible
        assert window.is_panels_visible() is True
        
        # Toggle to hide
        window.toggle_panels()
        
        assert window.is_panels_visible() is False
        assert window._main_toolbar.isVisible() is False
    
    def test_toggle_panels_shows(self, qtbot: pytest.QtBot) -> None:
        """Test toggle_panels shows panels when hidden.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        # Hide panels first
        window.set_panels_visible(False)
        assert window.is_panels_visible() is False
        
        # Toggle to show
        window.toggle_panels()
        
        assert window.is_panels_visible() is True
        assert window._main_toolbar.isVisible() is True
    
    def test_set_panels_visible_false(self, qtbot: pytest.QtBot) -> None:
        """Test set_panels_visible(False) hides panels.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        window.set_panels_visible(False)
        
        assert window.is_panels_visible() is False
        assert window._main_toolbar.isVisible() is False
        
        # Check splitter sizes
        splitter = window.centralWidget().findChild(QSplitter)
        assert splitter is not None
        sizes = splitter.sizes()
        assert sizes[1] == 0  # Category panel hidden
    
    def test_set_panels_visible_true(self, qtbot: pytest.QtBot) -> None:
        """Test set_panels_visible(True) shows panels.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        # Hide first
        window.set_panels_visible(False)
        assert window.is_panels_visible() is False
        
        # Show again
        window.set_panels_visible(True)
        
        assert window.is_panels_visible() is True
        assert window._main_toolbar.isVisible() is True
        
        # Check splitter sizes are restored
        splitter = window.centralWidget().findChild(QSplitter)
        assert splitter is not None
        sizes = splitter.sizes()
        assert sizes[1] > 0  # Category panel visible
    
    def test_panels_toggled_signal_emitted(self, qtbot: pytest.QtBot) -> None:
        """Test panels_toggled signal is emitted.
        
        // Ref: docs/specs/features/panel-toggle-button.md §7.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        signal_emitted: list[bool] = []
        window.panels_toggled.connect(lambda v: signal_emitted.append(v))
        
        # Toggle to hide
        window.toggle_panels()
        qtbot.wait(10)
        
        assert len(signal_emitted) == 1
        assert signal_emitted[0] is False
        
        # Toggle to show
        window.toggle_panels()
        qtbot.wait(10)
        
        assert len(signal_emitted) == 2
        assert signal_emitted[1] is True
    
    def test_splitter_sizes_stored_and_restored(self, qtbot: pytest.QtBot) -> None:
        """Test splitter sizes are stored when hiding and restored when showing.
        
        // Ref: docs/specs/features/panel-toggle-button.md §5.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        # Resize window to known width
        window.resize(1000, 600)
        qtbot.wait(10)
        
        splitter = window.centralWidget().findChild(QSplitter)
        assert splitter is not None
        
        # Set custom splitter sizes
        splitter.setSizes([700, 300])
        qtbot.wait(10)
        
        # Get actual sizes (Qt may adjust them)
        actual_sizes = list(splitter.sizes())
        
        # Hide panels
        window.set_panels_visible(False)
        assert window._stored_splitter_sizes == actual_sizes
        
        # Show panels
        window.set_panels_visible(True)
        
        # Check sizes are restored
        sizes = splitter.sizes()
        assert sizes[0] == actual_sizes[0]
        assert sizes[1] == actual_sizes[1]
    
    def test_status_bar_updated_on_toggle(self, qtbot: pytest.QtBot) -> None:
        """Test status bar button state is updated on toggle.
        
        // Ref: docs/specs/features/panel-toggle-button.md §5.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        # Initial state
        assert window._status_bar.is_panels_visible() is True
        
        # Hide panels
        window.set_panels_visible(False)
        assert window._status_bar.is_panels_visible() is False
        
        # Show panels
        window.set_panels_visible(True)
        assert window._status_bar.is_panels_visible() is True
    
    def test_no_change_when_same_state(self, qtbot: pytest.QtBot) -> None:
        """Test set_panels_visible does nothing when state unchanged.
        
        // Ref: docs/specs/features/panel-toggle-button.md §5.1
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        signal_count: list[int] = []
        window.panels_toggled.connect(lambda _: signal_count.append(1))
        
        # Set to visible (already visible)
        window.set_panels_visible(True)
        
        # No signal should be emitted
        assert len(signal_count) == 0
        assert window.is_panels_visible() is True


class TestMainWindowPanelToggleKeyboardShortcut:
    """Tests for keyboard shortcut panel toggle.
    
    // Ref: docs/specs/features/panel-toggle-button.md §5.3
    """
    
    def test_keyboard_shortcut_toggles_panels(self, qtbot: pytest.QtBot) -> None:
        """Test Ctrl+Shift+P toggles panels.
        
        // Ref: docs/specs/features/panel-toggle-button.md §5.3
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        # Initial state
        assert window.is_panels_visible() is True
        
        # Press Ctrl+Shift+P
        qtbot.keyPress(window, Qt.Key_P, Qt.ControlModifier | Qt.ShiftModifier)
        qtbot.wait(10)
        
        assert window.is_panels_visible() is False
        
        # Press again
        qtbot.keyPress(window, Qt.Key_P, Qt.ControlModifier | Qt.ShiftModifier)
        qtbot.wait(10)
        
        assert window.is_panels_visible() is True


class TestMainWindowPanelToggleEdgeCases:
    """Edge case tests for panel toggle.
    
    // Ref: docs/specs/features/panel-toggle-button.md §5.4
    """
    
    def test_multiple_toggles(self, qtbot: pytest.QtBot) -> None:
        """Test multiple rapid toggles."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        qtbot.wait(10)
        
        for i in range(10):
            visible = i % 2 == 0
            window.set_panels_visible(visible)
            assert window.is_panels_visible() == visible
    
    def test_toggle_without_show(self, qtbot: pytest.QtBot) -> None:
        """Test toggle works before window is shown."""
        window = MainWindow()
        qtbot.addWidget(window)
        
        # Toggle before show
        window.set_panels_visible(False)
        assert window.is_panels_visible() is False
        
        window.set_panels_visible(True)
        assert window.is_panels_visible() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])