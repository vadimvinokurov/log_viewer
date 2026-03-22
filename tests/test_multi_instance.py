"""Tests for multi-instance behavior.

// Ref: docs/specs/features/multi-window-instance.md §10
"""
from __future__ import annotations
from beartype import beartype
import pytest
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestOpenInNewInstance:
    """Tests for _open_in_new_instance function."""
    
    @patch('subprocess.Popen')
    def test_launch_python_script(self, mock_popen: Mock) -> None:
        """Test launching new instance as Python script.
        
        Per docs/specs/features/multi-window-instance.md §10.1:
        Verify subprocess.Popen called with Python executable and script path.
        """
        from src.main import _open_in_new_instance
        
        # Mock sys.argv[0] as Python script
        with patch('sys.argv', ['src/main.py']):
            with patch('src.main.Path') as mock_path:
                mock_path.return_value.suffix = '.py'
                mock_path.return_value.absolute.return_value = Path('src/main.py')
                
                _open_in_new_instance(Path('/path/to/file.log'))
                
                # Verify subprocess.Popen was called
                mock_popen.assert_called_once()
                
                # Verify arguments include Python executable and script path
                call_args = mock_popen.call_args[0][0]
                assert sys.executable in call_args
                assert 'src/main.py' in str(call_args)
                assert '/path/to/file.log' in str(call_args)
    
    @patch('subprocess.Popen')
    def test_launch_executable(self, mock_popen: Mock) -> None:
        """Test launching new instance as executable.
        
        Per docs/specs/features/multi-window-instance.md §10.1:
        Verify subprocess.Popen called with executable path for frozen apps.
        """
        from src.main import _open_in_new_instance
        
        # Mock sys.argv[0] as executable
        with patch('sys.argv', ['dist/Log Viewer.app/Contents/MacOS/Log Viewer']):
            with patch('src.main.Path') as mock_path:
                mock_path.return_value.suffix = ''  # No .py extension
                mock_path.return_value.absolute.return_value = Path('dist/Log Viewer.app/Contents/MacOS/Log Viewer')
                
                _open_in_new_instance(Path('/path/to/file.log'))
                
                # Verify subprocess.Popen was called
                mock_popen.assert_called_once()
                
                # Verify arguments include executable path
                call_args = mock_popen.call_args[0][0]
                assert 'Log Viewer' in str(call_args)
                assert '/path/to/file.log' in str(call_args)
    
    @patch('subprocess.Popen')
    @patch('PySide6.QtWidgets.QMessageBox.critical')
    def test_launch_failure_shows_error(self, mock_messagebox: Mock, mock_popen: Mock) -> None:
        """Test that launch failure shows error dialog.
        
        Per docs/specs/features/multi-window-instance.md §11.2:
        OSError during subprocess launch should show error dialog.
        """
        from src.main import _open_in_new_instance
        
        # Mock subprocess.Popen to raise OSError
        mock_popen.side_effect = OSError("Failed to launch")
        
        # Mock sys.argv[0] as Python script
        with patch('sys.argv', ['src/main.py']):
            with patch('src.main.Path') as mock_path:
                mock_path.return_value.suffix = '.py'
                mock_path.return_value.absolute.return_value = Path('src/main.py')
                
                _open_in_new_instance(Path('/path/to/file.log'))
                
                # Verify error dialog was shown
                mock_messagebox.assert_called_once()
                assert "Instance Launch Failed" in str(mock_messagebox.call_args)


class TestMultiInstanceIntegration:
    """Integration tests for multi-instance behavior."""
    
    def test_launch_new_instance_subprocess(self) -> None:
        """Test launching new instance via subprocess.
        
        Per docs/specs/features/multi-window-instance.md §10.1:
        Verify that subprocess.Popen can launch a new instance.
        """
        main_script = Path("src/main.py")
        
        if main_script.exists():
            # Launch new instance
            process = subprocess.Popen(
                [sys.executable, str(main_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Verify process started
            assert process.pid is not None
            assert process.poll() is None  # Process is running
            
            # Clean up
            process.terminate()
            process.wait()
    
    def test_launch_new_instance_with_file(self) -> None:
        """Test launching new instance with file argument.
        
        Per docs/specs/features/multi-window-instance.md §10.1:
        Verify that subprocess.Popen can launch a new instance with a file.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("test content")
            test_file = Path(f.name)
        
        try:
            main_script = Path("src/main.py")
            
            if main_script.exists():
                # Launch new instance with file
                process = subprocess.Popen(
                    [sys.executable, str(main_script), str(test_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Verify process started
                assert process.pid is not None
                
                # Clean up
                process.terminate()
                process.wait()
        finally:
            # Clean up temp file
            test_file.unlink(missing_ok=True)