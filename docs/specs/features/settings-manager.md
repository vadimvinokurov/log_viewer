# Settings Manager Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The Settings Manager handles persistent application settings including window geometry, column widths, highlight patterns, category states, and recent files.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SettingsManager                            │
│  - Load/save application settings                             │
│  - Manage QSettings wrapper                                   │
│  - Provide typed access to settings                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  QSettings  │
                    │  (Qt)       │
                    └─────────────┘
```

### §2.2 Dependencies

```python
from PySide6.QtCore import QSettings
from typing import Any
from pathlib import Path
```

---

## §3 Responsibilities

### §3.1 Settings Categories

| Category | Description |
|----------|-------------|
| Window | Geometry, state, position |
| Columns | Table column widths |
| Highlights | User highlight patterns |
| Categories | Category checkbox states |
| Files | Recent files, last opened |
| Filters | Filter history |

### §3.2 Storage Location

Settings are stored in platform-specific locations:
- **Windows**: `HKEY_CURRENT_USER\Software\CompanyName\AppName`
- **macOS**: `~/Library/Preferences/com.company.app.plist`
- **Linux**: `~/.config/CompanyName/AppName.conf`

---

## §4 API Reference

### §4.1 Class Definition

```python
class SettingsManager:
    """Manager for application settings."""
    
    # Settings keys
    KEY_GEOMETRY = "geometry"
    KEY_WINDOW_STATE = "windowState"
    KEY_COLUMN_WIDTHS = "columnWidths"
    KEY_HIGHLIGHT_PATTERNS = "highlightPatterns"
    KEY_CATEGORY_STATES = "categoryStates"
    KEY_LAST_FILE = "lastFile"
    KEY_RECENT_FILES = "recentFiles"
    KEY_FILTER_HISTORY = "filterHistory"
    KEY_COUNTER_STATES = "counterStates"
    
    @beartype
    def __init__(self, organization: str = "LogViewer", 
                 application: str = "LogViewer") -> None:
        """
        Initialize the settings manager.
        
        Args:
            organization: Organization name for QSettings
            application: Application name for QSettings
        """
```

### §4.2 Window Settings

```python
@beartype
def save_geometry(self, geometry: bytes) -> None:
    """
    Save window geometry.
    
    Args:
        geometry: Serialized geometry from QWidget.saveGeometry()
    """

def load_geometry(self) -> bytes | None:
    """
    Load window geometry.
    
    Returns:
        Serialized geometry or None if not set
    """

@beartype
def save_window_state(self, state: bytes) -> None:
    """
    Save window state.
    
    Args:
        state: Serialized state from QMainWindow.saveState()
    """

def load_window_state(self) -> bytes | None:
    """
    Load window state.
    
    Returns:
        Serialized state or None if not set
    """
```

### §4.3 Column Settings

```python
@beartype
def save_column_widths(self, widths: dict[str, int]) -> None:
    """
    Save table column widths.
    
    Args:
        widths: Dictionary of column name -> width
    """

def load_column_widths(self) -> dict[str, int]:
    """
    Load table column widths.
    
    Returns:
        Dictionary of column name -> width
    """
```

### §4.4 Highlight Settings

```python
@beartype
def save_highlight_patterns(self, patterns: list[dict[str, Any]]) -> None:
    """
    Save highlight patterns.
    
    Args:
        patterns: List of pattern dictionaries with keys:
            - text: str
            - color: str (hex color)
            - is_regex: bool
    """

def load_highlight_patterns(self) -> list[dict[str, Any]]:
    """
    Load highlight patterns.
    
    Returns:
        List of pattern dictionaries
    """
```

### §4.5 Category Settings

```python
@beartype
def save_category_states(self, states: dict[str, bool]) -> None:
    """
    Save category checkbox states.
    
    Args:
        states: Dictionary of category path -> checked state
    """

def load_category_states(self) -> dict[str, bool]:
    """
    Load category checkbox states.
    
    Returns:
        Dictionary of category path -> checked state
    """
```

### §4.6 File Settings

```python
@beartype
def save_last_file(self, filepath: str) -> None:
    """
    Save the last opened file path.
    
    Args:
        filepath: Path to the last opened file
    """

def load_last_file(self) -> str | None:
    """
    Load the last opened file path.
    
    Returns:
        File path or None if not set
    """

@beartype
def save_recent_files(self, files: list[str]) -> None:
    """
    Save recent files list.
    
    Args:
        files: List of recent file paths
    """

def load_recent_files(self) -> list[str]:
    """
    Load recent files list.
    
    Returns:
        List of recent file paths
    """

@beartype
def add_recent_file(self, filepath: str) -> None:
    """
    Add a file to recent files.
    
    Args:
        filepath: Path to add
    """
```

### §4.7 Filter Settings

```python
@beartype
def save_filter_history(self, history: list[str]) -> None:
    """
    Save filter history.
    
    Args:
        history: List of recent filter texts
    """

def load_filter_history(self) -> list[str]:
    """
    Load filter history.
    
    Returns:
        List of recent filter texts
    """

@beartype
def add_filter_history(self, text: str) -> None:
    """
    Add a filter to history.
    
    Args:
        text: Filter text to add
    """
```

### §4.8 Counter Settings

```python
@beartype
def save_counter_states(self, states: dict[str, bool]) -> None:
    """
    Save counter visibility states.
    
    Args:
        states: Dictionary of level name -> visible state
    """

def load_counter_states(self) -> dict[str, bool]:
    """
    Load counter visibility states.
    
    Returns:
        Dictionary of level name -> visible state
    """
```

### §4.9 General Operations

```python
def clear(self) -> None:
    """Clear all settings."""

def sync(self) -> None:
    """Sync settings to disk."""

@beartype
def save(self) -> None:
    """Save all pending settings."""

@beartype
def load(self) -> None:
    """Load all settings into memory."""
```

---

## §5 Data Model

### §5.1 Settings Data Class

```python
@dataclass
class AppSettings:
    """Application settings data."""
    
    # Window
    geometry: bytes | None = None
    window_state: bytes | None = None
    
    # Columns
    column_widths: dict[str, int] = field(default_factory=lambda: {
        "time": 50,
        "category": 100,
        "type": 40,
        "message": -1,  # stretch
    })
    
    # Highlights
    highlight_patterns: list[HighlightPatternData] = field(default_factory=list)
    
    # Categories
    category_states: dict[str, bool] = field(default_factory=dict)
    
    # Files
    last_file: str | None = None
    recent_files: list[str] = field(default_factory=list)
    
    # Filters
    filter_history: list[str] = field(default_factory=list)
    
    # Counters
    counter_states: dict[str, bool] = field(default_factory=lambda: {
        "critical": True,
        "error": True,
        "warning": True,
        "msg": True,
        "debug": True,
        "trace": True,
    })


@dataclass
class HighlightPatternData:
    """Highlight pattern data."""
    text: str
    color: str  # hex color
    is_regex: bool = False
```

---

## §6 Settings File Format

### §6.1 QSettings Format

Settings are stored using QSettings, which uses platform-specific formats:

**Windows (Registry):**
```
HKEY_CURRENT_USER\Software\LogViewer\LogViewer\
    geometry = <hex>
    windowState = <hex>
    columnWidths = <JSON>
    highlightPatterns = <JSON>
    ...
```

**Linux (INI format):**
```ini
[General]
geometry=@ByteArray(...)
windowState=@ByteArray(...)
columnWidths=@Variant(...)
...
```

### §6.2 JSON Serialization

Complex types are serialized as JSON:

```python
def _serialize_patterns(self, patterns: list[dict]) -> str:
    """Serialize patterns to JSON."""
    return json.dumps(patterns)

def _deserialize_patterns(self, data: str) -> list[dict]:
    """Deserialize patterns from JSON."""
    if not data:
        return []
    return json.loads(data)
```

---

## §7 Error Handling

### §7.1 Settings Load Errors

```python
def load_highlight_patterns(self) -> list[dict]:
    """Load highlight patterns with error handling."""
    try:
        data = self._settings.value(self.KEY_HIGHLIGHT_PATTERNS, "[]")
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to load highlight patterns: {e}")
        return []
```

### §7.2 Settings Save Errors

```python
def save_highlight_patterns(self, patterns: list[dict]) -> None:
    """Save highlight patterns with error handling."""
    try:
        data = json.dumps(patterns)
        self._settings.setValue(self.KEY_HIGHLIGHT_PATTERNS, data)
    except (TypeError, json.JSONEncodeError) as e:
        logger.error(f"Failed to save highlight patterns: {e}")
```

---

## §8 Performance

### §8.1 Load Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Load geometry | <1ms | Binary data |
| Load patterns | <5ms | JSON parse |
| Load all settings | <20ms | All categories |

### §8.2 Save Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Save geometry | <1ms | Binary data |
| Save patterns | <5ms | JSON serialize |
| Save all settings | <20ms | All categories |

---

## §9 Testing

### §9.1 Unit Tests

```python
def test_settings_manager_geometry(settings_manager, tmp_path):
    """Test geometry save/load."""
    geometry = b"test_geometry_data"
    
    settings_manager.save_geometry(geometry)
    loaded = settings_manager.load_geometry()
    
    assert loaded == geometry

def test_settings_manager_patterns(settings_manager):
    """Test highlight patterns save/load."""
    patterns = [
        {"text": "error", "color": "#ff0000", "is_regex": False},
        {"text": "warning", "color": "#ffff00", "is_regex": False},
    ]
    
    settings_manager.save_highlight_patterns(patterns)
    loaded = settings_manager.load_highlight_patterns()
    
    assert loaded == patterns

def test_settings_manager_recent_files(settings_manager):
    """Test recent files management."""
    settings_manager.add_recent_file("/path/to/file1.log")
    settings_manager.add_recent_file("/path/to/file2.log")
    
    recent = settings_manager.load_recent_files()
    
    assert len(recent) == 2
    assert recent[0] == "/path/to/file2.log"  # Most recent first
```

---

## §10 Cross-References

- **Main Controller:** [main-controller.md](main-controller.md)
- **Error Handling:** [../global/error-handling.md](../global/error-handling.md)

---

## §11 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial settings manager specification |