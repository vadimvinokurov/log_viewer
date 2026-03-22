# File Association Specification

**Version**: 1.0  
**Status**: [DRAFT]  
**Created**: 2026-03-21  
**Feature**: "Open with..." file association for macOS and Windows

---

## §1 Overview

### §1.1 Purpose

Enable users to open log files in Log Viewer using the "Open with..." context menu in macOS Finder and Windows Explorer.

### §1.2 Scope

- Command-line argument handling for file paths
- Platform-specific file association registration
- Build system integration for file associations
- Multi-instance handling (open file in existing window vs. new window)

### §1.3 Out of Scope

- Auto-update mechanism
- File type icon customization (future enhancement)
- Drag-and-drop file opening (already supported via Qt)
- Linux file association (future enhancement)

---

## §2 Requirements

### §2.1 User Stories

| ID | Story | Priority |
|----|-------|----------|
| US-1 | As a user, I want to right-click a .log file and select "Open with Log Viewer" to open it | High |
| US-2 | As a user, I want the application to launch and display the file content | High |
| US-3 | As a user, I want to select multiple files and open them in separate windows | Medium |
| US-4 | As a user, I want file associations to be registered during app installation | High |
| US-5 | As a user, I want the app to handle invalid file paths gracefully | High |

### §2.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Application must accept file path as command-line argument | High |
| FR-2 | Application must handle multiple file paths | Medium |
| FR-3 | Application must validate file exists before opening | High |
| FR-4 | Application must show error dialog for invalid files | High |
| FR-5 | Application must register .log file association on macOS | High |
| FR-6 | Application must register .log file association on Windows | High |
| FR-7 | Application must register .txt file association (optional) | Low |
| FR-8 | Application must support custom file extensions via settings | Low |

### §2.3 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Startup time with file argument | < 3 seconds |
| NFR-2 | File validation time | < 100ms |
| NFR-3 | Error dialog display time | < 200ms |
| NFR-4 | Memory overhead for argument handling | < 1 MB |

---

## §3 Architecture

### §3.1 Command-Line Argument Flow

```
User double-clicks file or "Open with..."
    ↓
OS launches application with file path as argument
    ↓
main.py parses sys.argv
    ↓
Application validates file path
    ↓
MainController.open_file(filepath)
    ↓
UI displays file content
```

### §3.2 Multi-Instance Decision

**Current Behavior**: True multi-instance (separate processes).

**Rationale**:
- Complete process isolation
- Crash in one instance doesn't affect others
- Independent memory spaces
- No coordination overhead

**Implementation**: See [multi-window-instance.md](multi-window-instance.md) for full specification.

**Architecture**:
- Each "Open with..." launches NEW process instance
- Each app icon click launches NEW process instance
- Each instance is completely independent
- No shared state between instances

### §3.3 Component Changes

| Component | Change | Impact |
|-----------|--------|--------|
| [`src/main.py`](src/main.py) | Parse command-line arguments | Entry point modification |
| [`src/controllers/main_controller.py`](src/controllers/main_controller.py) | Handle file path from args | Minor addition |
| [`build/logviewer.spec`](build/logviewer.spec) | Register file associations | Build config update |
| [`build/scripts/build-macos.sh`](build/scripts/build-macos.sh) | Add Info.plist entries | Build script update |
| [`build/scripts/build-windows.py`](build/scripts/build-windows.py) | Add registry entries | Build script update |

---

## §4 API Specification

### §4.1 Command-Line Arguments

**Usage**:
```bash
# Single file
LogViewer /path/to/file.log

# Multiple files (separate windows)
LogViewer file1.log file2.log file3.log

# No arguments (empty window)
LogViewer
```

**Argument Parsing**:
```python
def parse_arguments(argv: list[str]) -> list[str]:
    """Parse command-line arguments.
    
    Args:
        argv: Command-line arguments (excluding program name)
    
    Returns:
        List of file paths to open
    
    Behavior:
        - Returns empty list if no arguments
        - Validates each path exists
        - Returns only valid paths
        - Logs warning for invalid paths
    """
```

### §4.2 Main Entry Point Changes

**File**: [`src/main.py`](src/main.py)

**Current Implementation** (lines 23-47):
```python
def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Log Viewer")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    controller = MainController(window)

    window.show()

    # Auto-open test log file in development mode
    if DEV_AUTO_OPEN_FILE and DEV_LOG_FILE.exists():
        QTimer.singleShot(100, lambda: controller.open_file(str(DEV_LOG_FILE)))

    exit_code = app.exec()
    controller.close()
    sys.exit(exit_code)
```

**New Implementation**:
```python
from __future__ import annotations
from beartype import beartype
import argparse
from pathlib import Path

@beartype
def parse_arguments(argv: list[str]) -> list[Path]:
    """Parse command-line arguments.
    
    Args:
        argv: Command-line arguments (sys.argv[1:])
    
    Returns:
        List of valid file paths to open
    
    Example:
        >>> parse_arguments(["/path/to/file.log"])
        [PosixPath('/path/to/file.log')]
        
        >>> parse_arguments(["/nonexistent.log"])
        []
    """
    valid_paths: list[Path] = []
    
    for arg in argv:
        # Skip flags (future: --version, --help, etc.)
        if arg.startswith('-'):
            continue
        
        path = Path(arg)
        if path.exists() and path.is_file():
            valid_paths.append(path)
        else:
            logger.warning(f"File not found: {arg}")
    
    return valid_paths


def main() -> None:
    """Application entry point.
    
    Per docs/specs/features/multi-window-instance.md §4.1
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Log Viewer")
    app.setApplicationVersion("0.1.0")

    # Parse command-line arguments
    file_paths = parse_arguments(sys.argv[1:])

    window = MainWindow()
    controller = MainController(window)

    window.show()

    # Open files from command-line arguments
    # Per docs/specs/features/file-association.md §4.2
    if file_paths:
        # Open first file in current instance
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
        filepath: Path to the file to open
    
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

### §4.3 Error Handling

**File Not Found**:
```python
# In main.py, after QApplication initialization
if file_paths:
    for path in file_paths:
        if not path.exists():
            # Show error dialog
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Warning)
            error_dialog.setWindowTitle("File Not Found")
            error_dialog.setText(f"Cannot find file: {path}")
            error_dialog.setInformativeText("The file may have been moved or deleted.")
            error_dialog.exec()
```

**Permission Denied**:
```python
# In MainController.open_file()
try:
    self._document = LogDocument(filepath)
except PermissionError:
    self._window.show_error(
        "Permission Denied",
        f"Cannot open file: {filepath}\nYou may not have permission to read this file."
    )
```

---

## §5 Platform-Specific Configuration

### §5.1 macOS File Association

**File**: [`build/logviewer.spec`](build/logviewer.spec) (Info.plist section)

**Info.plist Entries** (add to existing `info_plist` dict):

```python
info_plist={
    # ... existing entries ...
    
    # File association configuration
    # Per docs/specs/features/file-association.md §5.1
    'CFBundleDocumentTypes': [
        {
            'CFBundleTypeName': 'Log File',
            'CFBundleTypeRole': 'Viewer',
            'LSItemContentTypes': [
                'public.log',           # System log UTI
                'public.plain-text',    # Plain text files
            ],
            'LSHandlerRank': 'Alternate',  # Not default, but available
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
}
```

**UTI (Uniform Type Identifier) Details**:

| Property | Value | Description |
|----------|-------|-------------|
| `CFBundleTypeName` | `'Log File'` | Display name in Finder |
| `CFBundleTypeRole` | `'Viewer'` | Application can view files |
| `LSHandlerRank` | `'Alternate'` | Not default, available in "Open with..." |
| `LSItemContentTypes` | `['public.log', 'public.plain-text']` | System UTIs for log files |
| `CFBundleTypeExtensions` | `['log', 'txt']` | File extensions |

**Behavior**:
- `.log` files appear in "Open with..." menu
- `.txt` files appear in "Open with..." menu
- Application is not the default handler (user can set manually)

### §5.2 Windows File Association

**File**: [`build/scripts/build-windows.py`](build/scripts/build-windows.py)

**Registry Entries** (add to build script):

```python
def register_file_associations() -> None:
    """Register file associations in Windows Registry.
    
    Per docs/specs/features/file-association.md §5.2
    
    Note: This is called during installation, not at runtime.
    For portable executables, user must manually associate files.
    """
    import winreg
    
    # Application ID
    app_id = "LogViewer"
    app_path = Path("dist/LogViewer.exe")
    
    # Register application
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\{app_id}") as key:
        winreg.SetValue(key, None, winreg.REG_SZ, "Log Viewer")
        with winreg.CreateKey(key, "Capabilities") as cap_key:
            # Register for .log files
            winreg.SetValue(cap_key, "FileAssociations", winreg.REG_SZ, ".log")
            
    # Register .log file type
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.log") as key:
        winreg.SetValue(key, None, winreg.REG_SZ, "LogViewer.log")
        
    # Register LogViewer.log ProgID
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\LogViewer.log") as key:
        winreg.SetValue(key, None, winreg.REG_SZ, "Log File")
        
        # Set default icon
        with winreg.CreateKey(key, "DefaultIcon") as icon_key:
            winreg.SetValue(icon_key, None, winreg.REG_SZ, f'"{app_path}",0')
        
        # Set open command
        with winreg.CreateKey(key, "shell\\open\\command") as cmd_key:
            winreg.SetValue(cmd_key, None, winreg.REG_SZ, f'"{app_path}" "%1"')
    
    # Register for "Open with..." menu
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                          "Software\\Classes\\Applications\\LogViewer.exe") as key:
        winreg.SetValue(key, None, winreg.REG_SZ, "Log Viewer")
        
        # Supported file types
        with winreg.CreateKey(key, "SupportedTypes") as types_key:
            winreg.SetValue(types_key, ".log", winreg.REG_SZ, "")
            winreg.SetValue(types_key, ".txt", winreg.REG_SZ, "")
        
        # Open command
        with winreg.CreateKey(key, "shell\\open\\command") as cmd_key:
            winreg.SetValue(cmd_key, None, winreg.REG_SZ, f'"{app_path}" "%1"')
```

**Installer Integration** (future enhancement):

For proper file association, use an installer (Inno Setup or NSIS):

```nsis
; Inno Setup script snippet
[Registry]
Root: HKCR; Subkey: ".log"; ValueType: string; ValueName: ""; ValueData: "LogViewer.log"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "LogViewer.log"; ValueType: string; ValueName: ""; ValueData: "Log File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "LogViewer.log\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\LogViewer.exe"" ""%1"""
```

**Portable Executable Behavior**:
- No automatic file association
- User must manually associate via "Open with..." → "Choose another app"
- Once associated, appears in "Open with..." menu

### §5.3 Build Script Updates

**macOS Build Script** ([`build/scripts/build-macos.sh`](build/scripts/build-macos.sh)):

No changes needed - Info.plist is already configured in `logviewer.spec`.

**Windows Build Script** ([`build/scripts/build-windows.py`](build/scripts/build-windows.py)):

Add file association registration (optional, for installer builds):

```python
def build_windows():
    """Build Windows executable with file association support."""
    print("Building Log Viewer for Windows...")
    
    # ... existing build code ...
    
    # Note: File associations are registered by installer, not build script
    # For portable builds, user must manually associate files
    
    print("Build complete: dist/LogViewer-0.1.0-windows.exe")
    print("Note: For file association, use installer or manually associate via 'Open with...'")
```

---

## §6 Testing

### §6.1 Unit Tests

**File**: `tests/test_file_association.py`

```python
"""Tests for file association functionality.

// Ref: docs/specs/features/file-association.md §6
"""
from __future__ import annotations
from beartype import beartype
from pathlib import Path
import tempfile
import pytest
from src.main import parse_arguments


class TestParseArguments:
    """Tests for parse_arguments function."""
    
    @beartype
    def test_no_arguments(self) -> None:
        """Test with no arguments."""
        result = parse_arguments([])
        assert result == []
    
    @beartype
    def test_single_valid_file(self, tmp_path: Path) -> None:
        """Test with single valid file."""
        test_file = tmp_path / "test.log"
        test_file.write_text("test content")
        
        result = parse_arguments([str(test_file)])
        assert len(result) == 1
        assert result[0] == test_file
    
    @beartype
    def test_multiple_valid_files(self, tmp_path: Path) -> None:
        """Test with multiple valid files."""
        files = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.log"
            test_file.write_text(f"content {i}")
            files.append(str(test_file))
        
        result = parse_arguments(files)
        assert len(result) == 3
    
    @beartype
    def test_nonexistent_file(self, caplog) -> None:
        """Test with nonexistent file."""
        result = parse_arguments(["/nonexistent/file.log"])
        assert result == []
        assert "File not found" in caplog.text
    
    @beartype
    def test_directory_argument(self, tmp_path: Path) -> None:
        """Test with directory instead of file."""
        result = parse_arguments([str(tmp_path)])
        assert result == []
    
    @beartype
    def test_mixed_valid_invalid(self, tmp_path: Path) -> None:
        """Test with mix of valid and invalid paths."""
        valid_file = tmp_path / "valid.log"
        valid_file.write_text("content")
        
        result = parse_arguments([str(valid_file), "/nonexistent.log"])
        assert len(result) == 1
        assert result[0] == valid_file
    
    @beartype
    def test_skip_flags(self, tmp_path: Path) -> None:
        """Test that flags are skipped."""
        test_file = tmp_path / "test.log"
        test_file.write_text("content")
        
        result = parse_arguments(["--flag", str(test_file), "-v"])
        assert len(result) == 1
        assert result[0] == test_file
```

### §6.2 Integration Tests

**Manual Test Checklist**:

| Platform | Test | Expected Result |
|----------|------|-----------------|
| macOS | Right-click .log file → Open with → Log Viewer | App launches, file opens |
| macOS | Double-click .log file (if associated) | App launches, file opens |
| macOS | Open multiple files | Each opens in separate window |
| macOS | Open nonexistent file | Error dialog shown |
| Windows | Right-click .log file → Open with → Log Viewer | App launches, file opens |
| Windows | Open multiple files | Each opens in separate window |
| Windows | Open nonexistent file | Error dialog shown |

### §6.3 Platform Testing Matrix

| Platform | Version | Architecture | Test Status |
|----------|---------|--------------|-------------|
| macOS | 10.15+ | x86_64 | [ ] Pending |
| macOS | 11+ | arm64 | [ ] Pending |
| Windows | 10 | x64 | [ ] Pending |
| Windows | 11 | x64 | [ ] Pending |

---

## §7 Error Handling

### §7.1 Error Scenarios

| Error | Cause | Recovery |
|-------|-------|----------|
| File not found | File deleted/moved | Show error dialog, open empty window |
| Permission denied | Insufficient permissions | Show error dialog with details |
| Invalid encoding | Binary file | Show warning, attempt to open |
| File locked | File in use by another process | Show error dialog, suggest retry |
| Too many files | > 10 files passed | Open first 10, show warning |

### §7.2 Error Dialog Specification

**File Not Found Dialog**:
```
Title: "File Not Found"
Message: "Cannot find file: {filename}"
Informative Text: "The file may have been moved or deleted."
Buttons: [OK]
Icon: Warning
```

**Permission Denied Dialog**:
```
Title: "Permission Denied"
Message: "Cannot open file: {filename}"
Informative Text: "You may not have permission to read this file."
Buttons: [OK]
Icon: Warning
```

**File Locked Dialog**:
```
Title: "File Locked"
Message: "Cannot open file: {filename}"
Informative Text: "The file is being used by another program."
Buttons: [Retry] [Cancel]
Icon: Warning
```

---

## §8 Performance Considerations

### §8.1 Startup Performance

| Operation | Budget | Notes |
|-----------|--------|-------|
| Argument parsing | < 10ms | Simple path validation |
| File validation | < 100ms | File exists check |
| Error dialog display | < 200ms | Qt dialog creation |
| Total startup | < 3s | Including file load |

### §8.2 Memory Impact

| Component | Memory | Notes |
|-----------|--------|-------|
| Argument list | < 1 KB | List of Path objects |
| Error dialog | < 1 MB | Transient, GC'd after display |
| Total overhead | < 1 MB | Negligible |

---

## §9 Security Considerations

### §9.1 Path Validation

**Risks**:
- Path traversal attacks
- Symbolic link attacks
- Large file paths

**Mitigations**:
```python
@beartype
def validate_path(path: Path) -> Path | None:
    """Validate file path for security.
    
    Args:
        path: Path to validate
    
    Returns:
        Validated path or None if invalid
    
    Security checks:
        - Path exists
        - Path is file (not directory)
        - Path is not symbolic link (optional)
        - Path length < 4096 characters
    """
    # Check path length
    if len(str(path)) > 4096:
        logger.warning(f"Path too long: {path}")
        return None
    
    # Resolve symbolic links
    resolved = path.resolve()
    
    # Check exists and is file
    if not resolved.exists():
        logger.warning(f"Path does not exist: {path}")
        return None
    
    if not resolved.is_file():
        logger.warning(f"Path is not a file: {path}")
        return None
    
    return resolved
```

### §9.2 Command Injection Prevention

**Risk**: Malicious file paths with special characters

**Mitigation**:
- Use `subprocess.Popen` with list arguments (not shell string)
- Validate paths before passing to subprocess
- Quote paths in error messages (prevent log injection)

---

## §10 Documentation

### §10.1 User Documentation

**Location**: `README.md` or `docs/FILE_ASSOCIATION.md`

**Contents**:
- How to associate .log files with Log Viewer
- How to use "Open with..." menu
- Troubleshooting file associations
- Platform-specific instructions

### §10.2 Developer Documentation

**Location**: `docs/DEVELOPMENT.md`

**Contents**:
- How to test file associations
- How to modify supported extensions
- Build system integration
- Registry/plist configuration

---

## §11 Future Enhancements

### §11.1 Short-term (v0.2.0)

- [ ] Custom file icon for .log files
- [ ] Support additional extensions (.txt, .out, .err)
- [ ] Single-instance mode (open files in existing window)

### §11.2 Long-term (v1.0+)

- [ ] Custom file extension registration (.logviewer)
- [ ] Drag-and-drop file association
- [ ] Recent files from command-line
- [ ] Linux file association (.desktop file)

---

## §12 Implementation Checklist

### §12.1 Code Changes

- [ ] Update [`src/main.py`](src/main.py) with argument parsing
- [ ] Add error handling for invalid files
- [ ] Create `ApplicationManager` class (see [multi-window-instance.md](multi-window-instance.md))
- [ ] Update [`build/logviewer.spec`](build/logviewer.spec) with Info.plist entries
- [ ] Add file association tests to `tests/test_file_association.py`

### §12.2 Build Changes

- [ ] Test macOS Info.plist generation
- [ ] Test Windows executable with file argument
- [ ] Document manual file association steps

### §12.3 Documentation Changes

- [ ] Update [`docs/SPEC.md`](docs/SPEC.md) with feature reference
- [ ] Update [`docs/SPEC-INDEX.md`](docs/SPEC-INDEX.md) with feature link
- [ ] Add user documentation for file association

---

## §13 Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Spec Author | [Author] | 2026-03-21 | [DRAFT] |
| Spec Reviewer | [Reviewer] | [Date] | [PENDING] |

---

**End of Specification**