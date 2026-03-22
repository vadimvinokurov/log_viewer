# Settings Persistence Fix Specification

**Version**: 1.0  
**Status**: [DRAFT]  
**Created**: 2026-03-21  
**Feature**: Fix settings persistence in packed macOS application

---

## §1 Overview

### §1.1 Problem Statement

The application does not persist category selections (and other settings) after restart when running as a packed macOS application bundle. This affects:

- Category checkbox states
- Highlight patterns
- Window geometry
- Column widths
- Saved filters

### §1.2 Root Cause

The `SettingsManager` class uses a relative path `"settings.json"` for the settings file:

```python
# Current implementation (BROKEN)
def __init__(self, filepath: str = "settings.json") -> None:
    self.filepath = Path(filepath)
```

When a packed macOS application is launched from Finder or the Applications folder:
- The current working directory is `/` (root) or an unpredictable location
- The relative path `"settings.json"` resolves to a non-writable location
- Settings cannot be saved or loaded correctly

### §1.3 Solution

Use platform-specific standard locations for settings storage:

| Platform | Standard Location | Example Path |
|----------|-------------------|--------------|
| macOS | `~/Library/Application Support/Log Viewer/` | `/Users/user/Library/Application Support/Log Viewer/settings.json` |
| Windows | `%APPDATA%/LogViewer/` | `C:/Users/user/AppData/Roaming/LogViewer/settings.json` |
| Linux | `~/.config/LogViewer/` | `/home/user/.config/LogViewer/settings.json` |

---

## §2 Implementation Requirements

### §2.1 Platform-Specific Path Resolution

**Location**: `src/utils/settings_manager.py`

**New Method**:

```python
from pathlib import Path
import platform
import os

@staticmethod
def _get_platform_settings_path() -> Path:
    """Get platform-specific settings directory.
    
    Returns:
        Path to the settings directory.
        
    Platform locations:
        - macOS: ~/Library/Application Support/Log Viewer/
        - Windows: %APPDATA%/LogViewer/
        - Linux: ~/.config/LogViewer/
    
    The directory is created if it doesn't exist.
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # ~/Library/Application Support/Log Viewer/
        base = Path.home() / "Library" / "Application Support" / "Log Viewer"
    elif system == "Windows":
        # %APPDATA%/LogViewer/
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "LogViewer"
    else:  # Linux and others
        # ~/.config/LogViewer/
        base = Path.home() / ".config" / "LogViewer"
    
    # Ensure directory exists
    base.mkdir(parents=True, exist_ok=True)
    
    return base / "settings.json"
```

### §2.2 Updated Constructor

```python
def __init__(self, filepath: str | None = None) -> None:
    """Initialize the settings manager.

    Args:
        filepath: Path to the settings file. If None, uses platform-specific default.
    """
    if filepath is None:
        self.filepath = self._get_platform_settings_path()
    else:
        self.filepath = Path(filepath)
    
    self._settings = AppSettings()
```

### §2.3 Backward Compatibility

**Migration Strategy**:

1. On first run with new version, check for old `settings.json` in current directory
2. If found, migrate settings to new location
3. Delete or rename old file

```python
def _migrate_from_old_location(self) -> None:
    """Migrate settings from old location if exists.
    
    Checks for settings.json in current directory (old location)
    and migrates to new platform-specific location.
    """
    old_path = Path("settings.json")
    if old_path.exists() and not self.filepath.exists():
        try:
            # Copy old settings to new location
            import shutil
            shutil.copy2(old_path, self.filepath)
            logger.info(f"Migrated settings from {old_path} to {self.filepath}")
            
            # Optionally remove old file
            # old_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to migrate settings: {e}")
```

---

## §3 Testing Requirements

### §3.1 Unit Tests

**Location**: `tests/test_settings_manager.py`

```python
def test_platform_settings_path_macos(monkeypatch):
    """Test macOS settings path."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(Path, "home", lambda: Path("/Users/test"))
    
    path = SettingsManager._get_platform_settings_path()
    
    assert path == Path("/Users/test/Library/Application Support/Log Viewer/settings.json")

def test_platform_settings_path_windows(monkeypatch):
    """Test Windows settings path."""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(os.environ, "get", lambda k, d: "C:/Users/test/AppData/Roaming")
    
    path = SettingsManager._get_platform_settings_path()
    
    assert path == Path("C:/Users/test/AppData/Roaming/LogViewer/settings.json")

def test_platform_settings_path_linux(monkeypatch):
    """Test Linux settings path."""
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", lambda: Path("/home/test"))
    
    path = SettingsManager._get_platform_settings_path()
    
    assert path == Path("/home/test/.config/LogViewer/settings.json")

def test_settings_persist_after_save(tmp_path):
    """Test that settings persist after save."""
    settings_file = tmp_path / "settings.json"
    manager = SettingsManager(filepath=str(settings_file))
    
    # Set category states
    manager.set_category_states("/test/file.log", {"CategoryA": True, "CategoryB": False})
    manager.save()
    
    # Create new instance to test persistence
    manager2 = SettingsManager(filepath=str(settings_file))
    manager2.load()
    
    states = manager2.get_category_states("/test/file.log")
    assert states == {"CategoryA": True, "CategoryB": False}
```

### §3.2 Integration Tests

**Manual Testing Checklist**:

- [ ] Run app from source: `uv run python src/main.py` - settings should persist
- [ ] Run packed app from build directory: `./dist/Log Viewer.app/Contents/MacOS/Log Viewer` - settings should persist
- [ ] Run packed app from Finder: Double-click `Log Viewer.app` - settings should persist
- [ ] Run packed app from Applications folder: After copying to `/Applications` - settings should persist
- [ ] Verify settings file location: `~/Library/Application Support/Log Viewer/settings.json` exists on macOS

---

## §4 Affected Components

### §4.1 Files to Modify

| File | Changes |
|------|---------|
| `src/utils/settings_manager.py` | Add platform-specific path resolution, update constructor |
| `tests/test_settings_manager.py` | Add tests for platform paths and persistence |

### §4.2 No Changes Required

| Component | Reason |
|-----------|--------|
| `src/controllers/main_controller.py` | Uses `SettingsManager()` - default behavior will use correct path |
| `src/main.py` | No changes needed |
| Build scripts | No changes needed |

---

## §5 Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Settings persist after app restart when launched from Finder | Manual test on macOS |
| 2 | Settings persist after app restart when launched from Applications folder | Manual test on macOS |
| 3 | Settings file created in platform-specific location | Check `~/Library/Application Support/Log Viewer/settings.json` |
| 4 | Old settings migrated to new location (if exists) | Unit test |
| 5 | No regression in development mode | Run from source, verify settings persist |
| 6 | Works on Windows (if tested) | Manual test on Windows |
| 7 | Works on Linux (if tested) | Manual test on Linux |

---

## §6 Implementation Notes

### §6.1 Why Not QSettings?

The specification mentions using `QSettings`, but the current implementation uses a custom JSON-based approach. While `QSettings` would handle platform-specific paths automatically, migrating to `QSettings` would require:

1. Rewriting all settings logic
2. Converting existing JSON format to Qt's INI/plist format
3. Handling backward compatibility with existing user settings

**Decision**: Keep JSON format but use platform-specific paths. This is a minimal change that preserves existing functionality.

### §6.2 Directory Creation

The settings directory must be created if it doesn't exist:

```python
self.filepath.parent.mkdir(parents=True, exist_ok=True)
```

This is already done in the `save()` method, but should also be done during initialization to ensure the directory exists before any settings operations.

### §6.3 Error Handling

If the platform-specific location is not writable (rare edge case), fall back to a temporary location:

```python
try:
    self.filepath.parent.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Fall back to temp directory
    import tempfile
    self.filepath = Path(tempfile.gettempdir()) / "LogViewer" / "settings.json"
    self.filepath.parent.mkdir(parents=True, exist_ok=True)
    logger.warning(f"Using fallback settings location: {self.filepath}")
```

---

## §7 References

- [docs/specs/features/settings-manager.md](settings-manager.md) - Settings Manager specification
- [docs/specs/features/application-packaging.md](application-packaging.md) - Application packaging specification
- [docs/specs/features/category-checkbox-behavior.md](category-checkbox-behavior.md) §5 - Category state persistence

---

## §8 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial specification for settings persistence fix |