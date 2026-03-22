"""Tests for main window file open dialog behavior.

// Ref: docs/specs/features/file-open-dialog.md §6
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox, QApplication

from src.views.main_window import MainWindow


@pytest.fixture
def main_window(qapp: QApplication) -> Generator[MainWindow, None, None]:
    """Create a MainWindow instance for testing.
    
    Args:
        qapp: QApplication fixture.
    
    Yields:
        MainWindow instance.
    """
    window = MainWindow()
    yield window
    window.deleteLater()


class TestFileOpenDialog:
    """Tests for file open dialog behavior.
    
    // Ref: docs/specs/features/file-open-dialog.md §6.1
    """
    
    def test_dialog_shows_yes_no_buttons(self, main_window: MainWindow, tmp_path: Path) -> None:
        """Test dialog has only Yes and No buttons.
        
        // Ref: docs/specs/features/file-open-dialog.md §6.1
        // FR-2: Dialog must have exactly two buttons: Yes and No
        """
        # Open first file
        test_file1 = str(tmp_path / "test1.log")
        with open(test_file1, 'w') as f:
            f.write("test content 1")
        main_window._open_file(test_file1)
        
        # Try to open second file
        test_file2 = str(tmp_path / "test2.log")
        with open(test_file2, 'w') as f:
            f.write("test content 2")
        
        with patch.object(QMessageBox, 'question') as mock_question:
            mock_question.return_value = QMessageBox.Yes
            
            main_window._handle_file_already_open(test_file2)
            
            # Verify dialog was called with Yes/No buttons only
            call_args = mock_question.call_args
            buttons = call_args[0][3]  # Fourth argument is buttons
            
            # Should have Yes and No buttons only (no Cancel)
            assert buttons == (QMessageBox.Yes | QMessageBox.No)
    
    def test_yes_opens_new_window(self, main_window: MainWindow, tmp_path: Path) -> None:
        """Test Yes button opens file in new window.
        
        // Ref: docs/specs/features/file-open-dialog.md §6.1
        // FR-3: Yes button must open the file in a new window
        """
        # Open first file
        test_file1 = str(tmp_path / "test1.log")
        with open(test_file1, 'w') as f:
            f.write("test content 1")
        main_window._open_file(test_file1)
        
        # Try to open second file
        test_file2 = str(tmp_path / "test2.log")
        with open(test_file2, 'w') as f:
            f.write("test content 2")
        
        with patch.object(QMessageBox, 'question') as mock_question:
            mock_question.return_value = QMessageBox.Yes
            
            main_window._handle_file_already_open(test_file2)
            
            # Verify pending filepath is set
            assert main_window.get_pending_filepath() == test_file2
            
            # Verify current file is unchanged
            assert main_window.get_current_file() == test_file1
    
    def test_no_opens_in_current_window(self, main_window: MainWindow, tmp_path: Path, qtbot) -> None:
        """Test No button opens file in current window.
        
        // Ref: docs/specs/features/file-open-dialog.md §6.1
        // FR-4: No button must open the file in the current window
        
        Note: The view emits signals (file_closed, file_opened) and the controller
        handles setting _current_file. This test verifies the signals are emitted.
        
        Note: file_opened is emitted asynchronously via QTimer.singleShot to allow
        Qt to process close events before opening the new file.
        """
        # Open first file
        test_file1 = str(tmp_path / "test1.log")
        with open(test_file1, 'w') as f:
            f.write("test content 1")
        main_window._open_file(test_file1)
        
        # Try to open second file
        test_file2 = str(tmp_path / "test2.log")
        with open(test_file2, 'w') as f:
            f.write("test content 2")
        
        with patch.object(QMessageBox, 'question') as mock_question:
            mock_question.return_value = QMessageBox.No
            
            # Track signal emissions
            file_closed_emitted = [False]
            file_opened_emitted = [False]
            file_opened_path = [None]
            
            def on_file_closed() -> None:
                file_closed_emitted[0] = True
            
            def on_file_opened(filepath: str) -> None:
                file_opened_emitted[0] = True
                file_opened_path[0] = filepath
            
            main_window.file_closed.connect(on_file_closed)
            main_window.file_opened.connect(on_file_opened)
            
            main_window._handle_file_already_open(test_file2)
            
            # Verify file_closed signal was emitted (synchronous)
            assert file_closed_emitted[0], "file_closed signal should be emitted"
            
            # Wait for the deferred file_opened signal (asynchronous via QTimer.singleShot)
            # Ref: docs/specs/features/file-open-dialog.md §3.1
            qtbot.wait(250)  # Wait slightly longer than the 200ms timer
            
            # Verify file_opened signal was emitted with correct path
            assert file_opened_emitted[0], "file_opened signal should be emitted"
            assert file_opened_path[0] == test_file2, "file_opened should have test_file2 path"
            
            # Verify pending filepath is NOT set (No button doesn't use pending)
            assert main_window.get_pending_filepath() is None
            
            # Note: _current_file is NOT set by the view - controller handles it
            # The view's _current_file remains test_file1 until controller updates it
    
    def test_close_button_cancels(self, main_window: MainWindow, tmp_path: Path) -> None:
        """Test close button (X) cancels the operation.
        
        // Ref: docs/specs/features/file-open-dialog.md §6.1
        // FR-5: Close button (X) must cancel the operation (no action taken)
        """
        # Open first file
        test_file1 = str(tmp_path / "test1.log")
        with open(test_file1, 'w') as f:
            f.write("test content 1")
        main_window._open_file(test_file1)
        
        # Try to open second file
        test_file2 = str(tmp_path / "test2.log")
        with open(test_file2, 'w') as f:
            f.write("test content 2")
        
        # Simulate closing the dialog (returns invalid button)
        # When dialog is closed via X, it returns a value that is neither Yes nor No
        with patch.object(QMessageBox, 'question') as mock_question:
            # Simulate X button (returns 0 or invalid value)
            mock_question.return_value = QMessageBox.StandardButton(0)
            
            main_window._handle_file_already_open(test_file2)
            
            # Verify current file is unchanged
            assert main_window.get_current_file() == test_file1
            
            # Verify pending filepath is NOT set
            assert main_window.get_pending_filepath() is None
    
    def test_dialog_message_text(self, main_window: MainWindow, tmp_path: Path) -> None:
        """Test dialog message text is correct.
        
        // Ref: docs/specs/features/file-open-dialog.md §4.1
        // FR-1: Dialog must show the new filename
        """
        # Open first file
        test_file1 = str(tmp_path / "test1.log")
        with open(test_file1, 'w') as f:
            f.write("test content 1")
        main_window._open_file(test_file1)
        
        # Try to open second file
        test_file2 = str(tmp_path / "test2.log")
        with open(test_file2, 'w') as f:
            f.write("test content 2")
        
        with patch.object(QMessageBox, 'question') as mock_question:
            mock_question.return_value = QMessageBox.Yes
            
            main_window._handle_file_already_open(test_file2)
            
            # Verify dialog message
            call_args = mock_question.call_args
            message = call_args[0][2]  # Third argument is message
            
            # Should show new filename
            assert "test2.log" in message
            
            # Should show simplified message per spec §4.1
            assert "Open 'test2.log' in new windows?" in message
            
            # Should NOT show current filename (removed per spec §3.1)
            assert "test1.log" not in message
            assert "Current file" not in message
            
            # Should NOT have Cancel option in message
            assert "Cancel" not in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])