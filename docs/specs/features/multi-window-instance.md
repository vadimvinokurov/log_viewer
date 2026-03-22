# Multi-Instance Specification

**Version**: 1.0  
**Status**: [DRAFT]  
**Created**: 2026-03-21  
**Feature**: True multi-instance behavior with isolated processes for macOS and Windows

**Note**: This specification describes TRUE MULTI-INSTANCE (separate processes), not multi-window single-instance.

---

## §1 Overview

### §1.1 Purpose

Enable the Log Viewer application to run multiple independent process instances, where:
- Each app icon click launches a NEW process instance
- Each "Open with..." launches a NEW process instance
- Each instance is completely isolated with its own memory and state
- No shared state between instances

### §1.2 Problem Statement

**Current Behavior** (undesirable):
- macOS activates existing app instance when app icon is clicked
- "Open with..." redirects to already-open window instead of opening new window
- Users cannot view multiple log files simultaneously in separate windows

**Desired Behavior**:
- App icon click → launches NEW process instance (new window)
- "Open with..." → launches NEW process instance (new window)
- Each instance is completely independent
- If one instance crashes, others remain unaffected

### §1.3 Scope

- Multi-process instance management
- macOS single-instance prevention
- Windows single-instance prevention
- Process isolation and independence
- Command-line argument handling

### §1.4 Out of Scope

- Multi-window single-instance (rejected approach)
- Inter-process communication (IPC)
- Instance coordination/locking
- Tabbed interface (future enhancement)
- Session restoration (future enhancement)

---

## §2 Requirements

### §2.1 User Stories

| ID | Story | Priority |
|----|-------|----------|
| US-1 | As a user, I want to click the app icon and get a NEW process instance (new window) | High |
| US-2 | As a user, I want "Open with..." to launch a NEW process instance for each file | High |
| US-3 | As a user, I want each instance to have completely independent state (no shared memory) | High |
| US-4 | As a user, I want closing one instance to NOT affect other instances | High |
| US-5 | As a user, I want each instance to be isolated (crash in one doesn't affect others) | High |

### §2.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Application must allow multiple simultaneous process instances | High |
| FR-2 | App icon click must launch new process instance | High |
| FR-3 | "Open with..." must launch new process instance for each file | High |
| FR-4 | Each instance must have independent memory space | High |
| FR-5 | Each instance must have independent LogDocument | High |
| FR-6 | Each instance must have independent settings (in-memory) | High |
| FR-7 | Closing one instance must not affect other instances | High |
| FR-8 | No inter-process communication required | High |
| FR-9 | macOS single-instance enforcement must be disabled | High |
| FR-10 | Windows single-instance enforcement must be disabled | High |

### §2.3 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Instance startup time | < 3 seconds |
| NFR-2 | Memory per instance | ~80-120 MB (base Qt/Python) |
| NFR-3 | No shared state between instances | 100% isolation |
| NFR-4 | Crash isolation | One crash doesn't affect others |

---

## §3 Architecture

### §3.1 Current Architecture (Single Instance)

```
macOS/Windows launches app
    ↓
QApplication (single instance)
    ↓
MainWindow (single instance)
    ↓
MainController (single instance)
    ↓
LogDocument (single instance)
```

**Problem**: macOS/Windows enforces single-instance by default, reusing existing process.

### §3.2 New Architecture (Multi-Instance)

```
User Action (app icon click / Open with...)
    ↓
macOS/Windows launches NEW process
    ↓
Process 1: QApplication → MainWindow → MainController → LogDocument
Process 2: QApplication → MainWindow → MainController → LogDocument
Process N: QApplication → MainWindow → MainController → LogDocument
```

**Key Changes**:
- Each instance is completely independent
- No shared state between instances
- No inter-process communication
- Each instance has its own memory space

### §3.3 Implementation Strategy

**macOS**: Disable single-instance enforcement in Info.plist
**Windows**: No single-instance enforcement by default (already allows multiple instances)

**No ApplicationManager needed**: Each instance is independent, no coordination required.

---

## §4 API Specification

### §4.1 No New Classes Required

**Rationale**: Multi-instance architecture requires NO coordination between instances. Each instance is completely independent.

**Current Implementation** (unchanged):
```python
# src/main.py
def main() -> None:
    """Application entry point.
    
    Per docs/specs/features/multi-window-instance.md §4.1
    
    Each call to main() creates a NEW process instance.
    """
    app = LogViewerApp(sys.argv)
    app.setApplicationName("Log Viewer")
    app.setApplicationVersion("0.1.0")
    
    window = MainWindow()
    controller = MainController(window)
    
    window.show()
    
    # Parse command-line arguments
    file_paths = parse_arguments(sys.argv[1:])
    
    if file_paths:
        # Open first file in this instance
        first_file = str(file_paths[0])
        QTimer.singleShot(100, lambda: controller.open_file(first_file))
        
        # Launch additional files in NEW instances
        for path in file_paths[1:]:
            _open_in_new_instance(path)
    else:
        # Development mode: auto-open test file
        if DEV_AUTO_OPEN_FILE and DEV_LOG_FILE.exists():
            QTimer.singleShot(100, lambda: controller.open_file(str(DEV_LOG_FILE)))
    
    exit_code = app.exec()
    controller.close()
    sys.exit(exit_code)


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
    except Exception as e:
        logger.error(f"Failed to launch new instance for {filepath}: {e}")
```

### §4.2 LogViewerApp Changes

**File**: `src/main.py` (MODIFIED)

**Current Implementation** (lines 28-75):
```python
class LogViewerApp(QApplication):
    """Custom QApplication to handle macOS file open events."""
    
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._controller: MainController | None = None
    
    def set_controller(self, controller: MainController) -> None:
        self._controller = controller
    
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FileOpen:
            # ... handle file open ...
        return super().event(event)
```

**New Implementation**:
```python
class LogViewerApp(QApplication):
    """Custom QApplication to handle macOS file open events.
    
    Per docs/specs/features/multi-window-instance.md §4.2
    
    Each QFileOpenEvent launches a NEW process instance.
    """
    
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._controller: MainController | None = None
    
    def set_controller(self, controller: MainController) -> None:
        """Set the controller to handle file open events.
        
        Args:
            controller: MainController instance
        """
        self._controller = controller
    
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

---

## §5 Instance Lifecycle

### §5.1 Instance Creation Flow

```
User Action (app icon click / Open with...)
    ↓
macOS/Windows launches NEW process
    ↓
main() called in NEW process
    ↓
QApplication created
    ↓
MainWindow created
    ↓
MainController created
    ↓
LogDocument created (if file provided)
    ↓
Window shown
    ↓
Process runs independently
```

### §5.2 Instance Closure Flow

```
User closes window (⌘+W / Alt+F4)
    ↓
MainWindow.closeEvent()
    ↓
MainController.close()
    ↓
LogDocument closed
    ↓
Process exits
    ↓
Other instances unaffected
```

### §5.3 Multiple Files Flow

```
User selects multiple files in "Open with..."
    ↓
macOS/Windows launches Process 1 with file1.log
    ↓
Process 1: main() → open file1.log
    ↓
main() launches Process 2 with file2.log
    ↓
Process 2: main() → open file2.log
    ↓
main() launches Process 3 with file3.log
    ↓
Process 3: main() → open file3.log
    ↓
Each process runs independently
```

---

## §6 Memory Management

### §6.1 Memory Ownership

| Object | Owner | Lifetime |
|--------|-------|----------|
| `QApplication` | Process | Process lifetime |
| `MainWindow` | `QApplication` | Process lifetime |
| `MainController` | `MainWindow` | Process lifetime |
| `LogDocument` | `MainController` | Process lifetime |

### §6.2 Memory Budget

| Component | Memory | Notes |
|-----------|--------|-------|
| Qt Application | ~80-120 MB | Base Qt/Python overhead |
| MainWindow | ~2 MB | UI widgets |
| MainController | ~1 MB | Logic state |
| LogDocument | ~5-50 MB | Depends on file size |
| **Total (per instance)** | ~88-173 MB | Independent per instance |

**Memory Impact**:
- 1 instance: ~88-173 MB
- 5 instances: ~440-865 MB
- 10 instances: ~880-1730 MB

### §6.3 Memory Isolation

**Each instance has**:
- Independent Python interpreter
- Independent Qt application
- Independent memory heap
- Independent garbage collector

**No shared state**:
- No shared memory between instances
- No inter-process communication
- No coordination overhead

---

## §7 Thread Safety

### §7.1 Thread Model

**Each instance has its own threads**:
- Main thread: UI operations
- Background threads: File indexing, filtering (per instance)

**No cross-instance communication**:
- No locks needed between instances
- No shared resources
- Complete isolation

### §7.2 Concurrency Requirements

| Operation | Thread | Lock Required |
|-----------|--------|----------------|
| Create instance | OS process | No |
| Close instance | OS process | No |
| File operations | Per-instance | Per-instance lock |
| UI updates | Per-instance main thread | No |

**Rationale**: Each instance is a separate OS process with its own memory space.

---

## §8 Platform-Specific Behavior

### §8.1 macOS Behavior

**Problem**: macOS enforces single-instance by default.

**Current Behavior** (undesirable):
- Clicking app icon activates existing instance
- "Open with..." redirects to existing instance
- No way to launch second instance from Dock

**Solution**: Disable single-instance enforcement in Info.plist

**Implementation**:
```python
# build/logviewer.spec (Info.plist section)
info_plist={
    # ... existing entries ...
    
    # CRITICAL: Disable single-instance enforcement
    # Per docs/specs/features/multi-window-instance.md §8.1
    'LSMultipleInstances': True,  # Allow multiple instances
    'NSAppleScriptEnabled': True,  # Enable AppleScript control
    
    # Note: LSMultipleInstances is deprecated but still works
    # Modern approach: Use NSApplicationActivationPolicyRegular
    'NSApplicationActivationPolicy': 'NSApplicationActivationPolicyRegular',
}
```

**Alternative Approach** (if LSMultipleInstances doesn't work):
```python
# Use subprocess.Popen to launch new instances
# In LogViewerApp.event() for QFileOpenEvent:
def event(self, event: QEvent) -> bool:
    if event.type() == QEvent.Type.FileOpen:
        file_path = event.file()
        if file_path:
            # Launch NEW instance instead of opening in existing
            import subprocess
            import sys
            from pathlib import Path
            
            main_script = Path(sys.argv[0]).absolute()
            if main_script.suffix == '.py':
                subprocess.Popen([sys.executable, str(main_script), file_path])
            else:
                subprocess.Popen([str(main_script), file_path])
        return True
    return super().event(event)
```

**Testing**:
```bash
# Test 1: Click app icon multiple times
# Expected: Each click launches new instance

# Test 2: Open with... multiple files
# Expected: Each file opens in new instance

# Test 3: Close one instance
# Expected: Other instances remain running
```

### §8.2 Windows Behavior

**Default Behavior**: Windows allows multiple instances by default.

**No changes needed**: Windows doesn't enforce single-instance.

**Implementation**:
```python
# No special handling needed for Windows
# Each "Open with..." launches new process by default
```

**Testing**:
```powershell
# Test 1: Double-click app icon multiple times
# Expected: Each double-click launches new instance

# Test 2: Open with... multiple files
# Expected: Each file opens in new instance

# Test 3: Close one instance
# Expected: Other instances remain running
```

### §8.3 Info.plist Configuration

**File**: `build/logviewer.spec` (MODIFIED)

**Add to Info.plist**:
```python
info_plist={
    # ... existing entries ...
    
    # Allow multiple instances (macOS)
    # Per docs/specs/features/multi-window-instance.md §8.1
    'LSMultipleInstances': True,
    'NSAppleScriptEnabled': True,
}
```

**Note**: `LSMultipleInstances` is deprecated in modern macOS but still functional. Alternative is to handle `QFileOpenEvent` and launch new process.

---

## §9 User Interface

### §9.1 No Window Menu Needed

**Rationale**: Each instance is independent, no coordination needed.

**Current Implementation** (unchanged):
- No Window menu required
- Each instance has its own menu bar
- ⌘+N / Ctrl+N not needed (launch new instance instead)

**Alternative**: If user wants to open new empty window:
- macOS: Right-click Dock icon → "New Window" (requires NSApplication delegate)
- Windows: Not applicable (multiple instances by default)

### §9.2 Keyboard Shortcuts

| Action | macOS | Windows/Linux |
|--------|-------|---------------|
| Close Window | ⌘+W | Ctrl+W |
| Quit Application | ⌘+Q | Alt+F4 |
| Open File | ⌘+O | Ctrl+O |

**Note**: No "New Window" shortcut needed (launch new instance instead).

---

## §10 Testing

### §10.1 Unit Tests

**File**: `tests/test_multi_instance.py` (NEW)

```python
"""Tests for multi-instance behavior.

// Ref: docs/specs/features/multi-window-instance.md §10
"""
from __future__ import annotations
from beartype import beartype
import pytest
import subprocess
import sys
from pathlib import Path


class TestMultiInstance:
    """Tests for multi-instance behavior."""
    
    @beartype
    def test_launch_new_instance(self) -> None:
        """Test launching new instance via subprocess."""
        # This test verifies that subprocess.Popen launches new instance
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
    def test_open_file_in_new_instance(self, tmp_path: Path) -> None:
        """Test opening file in new instance."""
        test_file = tmp_path / "test.log"
        test_file.write_text("test content")
        
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
```

### §10.2 Integration Tests

**Manual Test Checklist**:

| Platform | Test | Expected Result |
|----------|------|-----------------|
| macOS | Click app icon (first time) | Opens empty window (Process 1) |
| macOS | Click app icon (second time) | Opens NEW empty window (Process 2) |
| macOS | Open with file.log | Opens file in NEW instance (Process 3) |
| macOS | Open with file2.log | Opens file in NEW instance (Process 4) |
| macOS | Close one instance | Other instances remain running |
| macOS | ⌘+Q in one instance | Only that instance quits |
| macOS | Activity Monitor | Shows multiple "Log Viewer" processes |
| Windows | Double-click app icon (first time) | Opens empty window (Process 1) |
| Windows | Double-click app icon (second time) | Opens NEW empty window (Process 2) |
| Windows | Open with file.log | Opens file in NEW instance (Process 3) |
| Windows | Close one instance | Other instances remain running |
| Windows | Task Manager | Shows multiple "LogViewer.exe" processes |

### §10.3 Performance Tests

| Test | Target | Measurement |
|------|--------|-------------|
| Launch 5 instances | < 15 seconds | Time to launch 5 instances |
| Memory per instance | ~80-120 MB | Memory usage per instance |
| Instance startup time | < 3 seconds | Time to create single instance |
| 10 instances memory | < 1.5 GB | Total memory with 10 instances |

---

## §11 Error Handling

### §11.1 Error Scenarios

| Error | Cause | Recovery |
|-------|-------|----------|
| Instance launch failed | Memory exhausted | Show error dialog, close app |
| File open failed | Invalid file | Show error dialog, keep instance running |
| Process creation failed | OS limits | Show error dialog, log error |
| Subprocess.Popen failed | Permission denied | Show error dialog, log error |

### §11.2 Error Dialog Specification

**Instance Launch Failed**:
```
Title: "Instance Launch Failed"
Message: "Cannot launch new instance"
Informative Text: "The system may be low on memory or resources. Try closing some applications."
Buttons: [OK]
Icon: Critical
```

**Process Creation Failed**:
```python
def _open_in_new_instance(filepath: Path) -> None:
    """Launch a new instance to open a file."""
    import subprocess
    
    main_script = Path(sys.argv[0]).absolute()
    
    try:
        if main_script.suffix == '.py':
            subprocess.Popen([sys.executable, str(main_script), str(filepath)])
        else:
            subprocess.Popen([str(main_script), str(filepath)])
    except OSError as e:
        logger.error(f"Failed to launch new instance for {filepath}: {e}")
        # Show error dialog
        QMessageBox.critical(
            None,
            "Instance Launch Failed",
            f"Cannot launch new instance for {filepath}.\n\nError: {e}"
        )
```

---

## §12 Implementation Checklist

### §12.1 Code Changes

- [ ] Modify `src/main.py` to use `_open_in_new_instance()` for multiple files
- [ ] Modify `LogViewerApp.event()` to launch new instance for `QFileOpenEvent`
- [ ] Update `build/logviewer.spec` Info.plist with `LSMultipleInstances: True`
- [ ] Add error handling for subprocess launch failures
- [ ] Test macOS single-instance prevention bypass

### §12.2 Test Changes

- [ ] Create `tests/test_multi_instance.py`
- [ ] Add integration tests for multi-instance behavior
- [ ] Add performance tests for instance creation

### §12.3 Documentation Changes

- [ ] Update `docs/SPEC.md` with feature reference
- [ ] Update `docs/SPEC-INDEX.md` with feature link
- [ ] Update `docs/specs/features/file-association.md` to reference multi-instance behavior
- [ ] Document memory implications of multiple instances

---

## §13 References

- Qt QMainWindow Documentation: https://doc.qt.io/qt-6/qmainwindow.html
- Qt QApplication Documentation: https://doc.qt.io/qt-6/qapplication.html
- macOS App Architecture: https://developer.apple.com/library/archive/documentation/General/Conceptual/MOSXAppProgrammingGuide/AppArchitecture/AppArchitecture.html
- Windows Application Development: https://docs.microsoft.com/en-us/windows/win32/learnwin32/overview-of-the-windows-programming-model

---

## §14 Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Spec Author | [Author] | 2026-03-21 | [DRAFT] |
| Spec Reviewer | [Reviewer] | [Date] | [PENDING] |

---

**End of Specification**