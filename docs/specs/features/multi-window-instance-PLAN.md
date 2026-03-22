# Multi-Instance Implementation Plan

**Version**: 1.0  
**Created**: 2026-03-21  
**Status**: READY FOR IMPLEMENTATION  
**Spec Reference**: [multi-window-instance.md](multi-window-instance.md)

---

## 📋 Overview

This plan breaks down the implementation of true multi-instance behavior (separate processes) for the Log Viewer application into manageable tasks for delegation to spec-coder agents.

**Goal**: Enable multiple independent process instances where each app icon click or "Open with..." launches a NEW process instance.

**Architecture**: Each instance is completely isolated with its own memory space, no shared state, no inter-process communication.

---

## 🎯 Implementation Strategy

### Phase 1: Core Implementation (Code Changes)
- Modify `src/main.py` to support multi-instance
- Update `build/logviewer.spec` for macOS configuration
- Add error handling for process launch failures

### Phase 2: Testing
- Create unit tests for multi-instance behavior
- Create integration tests for macOS and Windows

### Phase 3: Documentation
- Update specification documents
- Document memory implications

---

## 📦 Task Breakdown

### Task T-001: Modify main.py for Multi-Instance Support

**Spec Reference**: §4.1, §4.2  
**Priority**: HIGH  
**Estimated Time**: 2 hours  
**Files**: `src/main.py`

**Scope**:
- Add `_open_in_new_instance()` function to launch new process
- Modify `LogViewerApp.event()` to handle `QFileOpenEvent` by launching new instance
- Modify `main()` to handle multiple files by launching new instances
- Add error handling for subprocess launch failures

**Implementation Details**:

1. **Add `_open_in_new_instance()` function** (after line 133):
```python
def _open_in_new_instance(filepath: Path) -> None:
    """Launch a new instance to open a file.
    
    Args:
        filepath: Path to file to open
    
    Per docs/specs/features/multi-window-instance.md §4.1:
    Each file opens in a separate process instance.
    """
    import subprocess
    
    main_script = Path(sys.argv[0]).absolute()
    
    try:
        if main_script.suffix == '.py':
            # Running as Python script
            subprocess.Popen([sys.executable, str(main_script), str(filepath)])
        else:
            # Running as executable
            subprocess.Popen([str(main_script), str(filepath)])
    except OSError as e:
        logger.error(f"Failed to launch new instance for {filepath}: {e}")
        # Show error dialog
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Instance Launch Failed",
            f"Cannot launch new instance for {filepath}.\n\nError: {e}"
        )
```

2. **Modify `LogViewerApp.event()` method** (lines 50-74):
```python
def event(self, event: QEvent) -> bool:
    """Handle application events including QFileOpenEvent.
    
    Args:
        event: The event to handle
    
    Returns:
        True if event was handled, False otherwise
    
    Per docs/specs/features/multi-window-instance.md §4.2
    """
    if event.type() == QEvent.Type.FileOpen:
        file_event = event
        if hasattr(file_event, 'file'):
            file_path = file_event.file()
            if file_path:
                logger.info(f"Received QFileOpenEvent: {file_path}")
                # Launch NEW instance for this file
                _open_in_new_instance(Path(file_path))
        return True
    return super().event(event)
```

3. **Modify `main()` function** (lines 135-193):
```python
def main() -> None:
    """Application entry point.
    
    Per docs/specs/features/multi-window-instance.md §4.1
    """
    # Debug: Log all arguments received
    logger.debug(f"sys.argv: {sys.argv}")
    logger.debug(f"sys.argv[1:]: {sys.argv[1:]}")
    
    app = LogViewerApp(sys.argv)
    app.setApplicationName("Log Viewer")
    app.setApplicationVersion("0.1.0")
    
    # Parse command-line arguments
    file_paths = parse_arguments(sys.argv[1:])
    logger.info(f"Parsed file paths: {file_paths}")
    
    # Create main window and controller
    window = MainWindow()
    controller = MainController(window)
    
    # Set controller on app to handle QFileOpenEvent
    app.set_controller(controller)
    
    # Show window
    window.show()
    
    # Open files from command-line arguments
    # Per docs/specs/features/multi-window-instance.md §4.1
    if file_paths:
        # Open first file in current instance
        first_file = str(file_paths[0])
        logger.info(f"Opening file: {first_file}")
        
        if not Path(first_file).exists():
            logger.error(f"File does not exist: {first_file}")
        
        QTimer.singleShot(100, lambda: controller.open_file(first_file))
        
        # Launch additional files in NEW instances
        for path in file_paths[1:]:
            _open_in_new_instance(path)
    else:
        # Development mode: auto-open test file
        if DEV_AUTO_OPEN_FILE and DEV_LOG_FILE.exists():
            QTimer.singleShot(100, lambda: controller.open_file(str(DEV_LOG_FILE)))
    
    # Run application
    exit_code = app.exec()
    
    # Clean up
    controller.close()
    
    sys.exit(exit_code)
```

**Tests Required**:
- Verify `_open_in_new_instance()` launches subprocess correctly
- Verify `LogViewerApp.event()` handles `QFileOpenEvent` correctly
- Verify `main()` handles multiple files correctly
- Verify error handling for subprocess failures

**Dependencies**: None

---

### Task T-002: Update Info.plist for macOS Multi-Instance

**Spec Reference**: §8.1, §8.3  
**Priority**: HIGH  
**Estimated Time**: 30 minutes  
**Files**: `build/logviewer.spec`

**Scope**:
- Add `LSMultipleInstances: True` to Info.plist
- Add `NSAppleScriptEnabled: True` to Info.plist
- Add comment explaining multi-instance configuration

**Implementation Details**:

Modify `build/logviewer.spec` (lines 93-129):

```python
app = BUNDLE(
    coll,
    name='Log Viewer.app',
    bundle_identifier=BUNDLE_ID,
    version=APP_VERSION,
    icon=str(project_root / 'build' / 'icons' / 'app.icns'),
    info_plist={
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleVersion': APP_VERSION,
        'CFBundleShortVersionString': APP_VERSION,
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        
        # File association configuration
        # Per docs/specs/features/file-association.md §5.1
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Log File',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': [
                    'public.log',
                    'public.plain-text',
                ],
                'LSHandlerRank': 'Alternate',
                'CFBundleTypeExtensions': [
                    'log',
                    'txt',
                ],
                'CFBundleTypeIconFile': 'app.icns',
            },
        ],
        'UTExportedTypeDeclarations': [
            {
                'UTTypeIdentifier': 'com.logviewer.log',
                'UTTypeDescription': 'Log File',
                'UTTypeConformsTo': ['public.plain-text'],
                'UTTypeTagSpecification': {
                    'public.filename-extension': ['log'],
                },
            },
        ],
        
        # Multi-instance configuration
        # Per docs/specs/features/multi-window-instance.md §8.1
        'LSMultipleInstances': True,  # Allow multiple instances
        'NSAppleScriptEnabled': True,  # Enable AppleScript control
    },
)
```

**Tests Required**:
- Verify Info.plist contains `LSMultipleInstances: True`
- Verify Info.plist contains `NSAppleScriptEnabled: True`
- Test on macOS that multiple instances can be launched

**Dependencies**: None

---

### Task T-003: Create Multi-Instance Tests

**Spec Reference**: §10.1, §10.2  
**Priority**: MEDIUM  
**Estimated Time**: 2 hours  
**Files**: `tests/test_multi_instance.py` (NEW)

**Scope**:
- Create unit tests for `_open_in_new_instance()` function
- Create unit tests for subprocess launch behavior
- Create integration test checklist

**Implementation Details**:

Create `tests/test_multi_instance.py`:

```python
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
    
    @beartype
    @patch('subprocess.Popen')
    def test_launch_python_script(self, mock_popen: Mock) -> None:
        """Test launching new instance as Python script."""
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
    
    @beartype
    @patch('subprocess.Popen')
    def test_launch_executable(self, mock_popen: Mock) -> None:
        """Test launching new instance as executable."""
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
    
    @beartype
    @patch('subprocess.Popen')
    @patch('PySide6.QtWidgets.QMessageBox.critical')
    def test_launch_failure_shows_error(self, mock_messagebox: Mock, mock_popen: Mock) -> None:
        """Test that launch failure shows error dialog."""
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
    
    @beartype
    def test_launch_new_instance_subprocess(self) -> None:
        """Test launching new instance via subprocess."""
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
    
    @beartype
    def test_launch_new_instance_with_file(self) -> None:
        """Test launching new instance with file argument."""
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
```

**Tests Required**:
- All tests in `test_multi_instance.py` must pass
- Integration tests must verify subprocess launch behavior

**Dependencies**: Task T-001 (requires `_open_in_new_instance()` function)

---

### Task T-004: Update Documentation

**Spec Reference**: §12.3  
**Priority**: LOW  
**Estimated Time**: 30 minutes  
**Files**: `docs/SPEC.md`, `docs/SPEC-INDEX.md`, `docs/specs/features/file-association.md`

**Scope**:
- Update `docs/SPEC.md` with feature reference (already done)
- Update `docs/SPEC-INDEX.md` with feature link (already done)
- Update `docs/specs/features/file-association.md` to reference multi-instance behavior (already done)
- Document memory implications in README or user documentation

**Implementation Details**:

1. **Create user documentation** (optional):
   - Document that each app icon click launches new instance
   - Document that each "Open with..." launches new instance
   - Document memory implications (~80-120 MB per instance)
   - Document that closing one instance doesn't affect others

2. **Update README.md** (if needed):
   - Add note about multi-instance behavior
   - Add note about memory usage

**Tests Required**: None (documentation only)

**Dependencies**: None

---

## 📊 Task Dependency Graph

```
T-001 (main.py modifications)
    ↓
T-003 (create tests)
    
T-002 (Info.plist update) - independent

T-004 (documentation) - independent
```

---

## 🧪 Testing Strategy

### Unit Tests (Task T-003)
- Test `_open_in_new_instance()` function
- Test subprocess launch behavior
- Test error handling

### Integration Tests (Manual)
- Test on macOS: app icon click launches new instance
- Test on macOS: "Open with..." launches new instance
- Test on Windows: app icon click launches new instance
- Test on Windows: "Open with..." launches new instance
- Test closing one instance doesn't affect others
- Test Activity Monitor/Task Manager shows multiple processes

### Performance Tests
- Measure memory per instance (~80-120 MB expected)
- Measure startup time (< 3 seconds expected)
- Test with 5 instances (should work without issues)

---

## 📝 Implementation Notes

### macOS-Specific Notes
- `LSMultipleInstances: True` is deprecated but still functional
- Alternative: Handle `QFileOpenEvent` and launch new process via `subprocess.Popen()`
- Test on macOS 10.15+ (Catalina and later)

### Windows-Specific Notes
- No changes needed (Windows allows multiple instances by default)
- Test on Windows 10/11

### Memory Considerations
- Each instance uses ~80-120 MB base memory
- 5 instances = ~400-600 MB total
- 10 instances = ~800-1200 MB total
- Users should be aware of memory usage

---

## ✅ Acceptance Criteria

### Must Have
- [ ] App icon click launches NEW process instance (not activate existing)
- [ ] "Open with..." launches NEW process instance (not reuse existing)
- [ ] Each instance is completely independent
- [ ] Closing one instance doesn't affect others
- [ ] macOS: `LSMultipleInstances: True` in Info.plist
- [ ] Error handling for subprocess launch failures
- [ ] Unit tests pass
- [ ] Integration tests pass on macOS and Windows

### Should Have
- [ ] Documentation updated
- [ ] Memory usage documented
- [ ] Performance tests pass

### Nice to Have
- [ ] User documentation created
- [ ] README updated with multi-instance notes

---

## 🚀 Ready for Delegation

This plan is ready for delegation to spec-coder agents. Each task has:
- Clear spec reference
- Detailed implementation instructions
- Test requirements
- Dependencies mapped

**Recommended Delegation Order**:
1. T-001 (main.py modifications) - CRITICAL PATH
2. T-002 (Info.plist update) - INDEPENDENT
3. T-003 (create tests) - DEPENDS ON T-001
4. T-004 (documentation) - INDEPENDENT

---

## 📞 Contact

For questions or clarifications about this plan, refer to:
- Spec: [docs/specs/features/multi-window-instance.md](multi-window-instance.md)
- Master Spec: [docs/SPEC.md](../../SPEC.md)
- Spec Index: [docs/SPEC-INDEX.md](../../SPEC-INDEX.md)

---

**End of Implementation Plan**