# Main Controller Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The Main Controller is the central coordinator for the Log Viewer application. It manages the interaction between views, models, and services, handling file operations, filtering, and UI updates.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     MainController                            │
│  - Coordinates all operations                                  │
│  - Owns services and controllers                              │
│  - Manages application state                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────────┐   ┌─────────────┐
│ MainWindow  │   │ FilterController│   │ FileController│
│  (View)     │   │  (Sub-controller)│   │  (Sub-controller)│
└─────────────┘   └─────────────────┘   └─────────────┘
       │                   │                   │
       │                   ▼                   ▼
       │           ┌─────────────┐   ┌─────────────┐
       │           │ FilterEngine│   │ FileWatcher │
       │           └─────────────┘   └─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                     Services                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │StatisticsService│  │ HighlightService│  │SettingsManager│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### §2.2 Dependencies

```python
from src.models.log_document import LogDocument
from src.models.log_entry import LogEntry, LogLevel
from src.views.main_window import MainWindow
from src.controllers.filter_controller import FilterController
from src.controllers.file_controller import FileController
from src.controllers.index_worker import IndexWorker
from src.core.category_tree import CategoryTree, build_category_display_nodes
from src.services.statistics_service import StatisticsService
from src.services.highlight_service import HighlightService
from src.utils.settings_manager import SettingsManager
```

---

## §3 Responsibilities

### §3.1 File Management

- Open and close log files
- Coordinate with `FileController` for file operations
- Manage `LogDocument` lifecycle
- Handle file change notifications

### §3.2 Filter Management

- Coordinate with `FilterController` for filter operations
- Apply filters to log entries
- Update UI with filtered results

### §3.3 Category Management

- Build and maintain `CategoryTree`
- Sync category states with `CategoryPanel`
- Persist category states to settings

### §3.4 UI Coordination

- Update `MainWindow` with data
- Handle user actions from views
- Show status messages and errors

### §3.5 Settings Management

- Load settings on startup
- Save settings on shutdown
- Restore UI state (geometry, column widths, category states)

---

## §4 API Reference

### §4.1 Initialization

```python
class MainController(QObject):
    """Main controller for the application."""
    
    # Signals
    statistics_updated = Signal(dict)  # stats dict
    
    @beartype
    def __init__(self, window: MainWindow) -> None:
        """
        Initialize the controller.
        
        Args:
            window: The main application window
        """
```

### §4.2 File Operations

```python
@beartype
def open_file(self, filepath: str) -> None:
    """
    Open a log file.
    
    Args:
        filepath: Path to the log file
    """

def refresh(self) -> None:
    """Refresh current file."""

def close_file(self) -> None:
    """Close current file and clear UI."""
```

### §4.3 Filter Operations

```python
@beartype
def _on_filter_applied_from_ui(self, text: str, mode: str) -> None:
    """
    Handle filter applied from UI.
    
    Args:
        text: Filter text
        mode: Filter mode ('plain', 'regex', or 'simple')
    """

@beartype
def _on_category_toggled(self, category_path: str, checked: bool) -> None:
    """
    Handle category toggle from category panel.
    
    Args:
        category_path: Category path
        checked: Whether it's checked
    """

@beartype
def _on_counter_toggled(self, counter_type: str, visible: bool) -> None:
    """
    Handle counter toggle from statistics bar.
    
    Args:
        counter_type: Counter type (critical, error, warning, msg, debug, trace)
        visible: Whether logs of this type should be visible
    """
```

### §4.4 Highlight Operations

```python
def get_highlight_engine(self) -> HighlightEngine:
    """Get the highlight engine."""

def add_highlight_pattern(
    self,
    text: str,
    color: QColor,
    is_regex: bool = False
) -> None:
    """Add a highlight pattern."""

def remove_highlight_pattern(self, pattern: str) -> None:
    """Remove a highlight pattern."""

def clear_highlight_patterns(self) -> None:
    """Clear all highlight patterns."""
```

### §4.5 Lifecycle

```python
def close(self) -> None:
    """Clean up resources."""
```

---

## §5 Signal Flow

### §5.1 File Open Flow

```
MainWindow.file_opened
    │
    ▼
MainController.open_file(filepath)
    │
    ├── Close existing document
    │
    ├── Create LogDocument
    │
    ├── Create IndexWorker
    │
    └── IndexWorker.start()
           │
           ▼
        IndexWorker.finished
           │
           ▼
        MainController._on_index_complete()
           │
           ├── Load entries
           │
           ├── Build category tree
           │
           ├── Update FilterController
           │
           ├── Update CategoryPanel
           │
           ├── Start FileWatcher
           │
           └── Apply initial filter
```

### §5.2 Filter Flow

```
MainWindow.filter_applied(text, mode)
    │
    ▼
MainController._on_filter_applied_from_ui()
    │
    ├── Update FilterController
    │
    └── FilterController.apply_filter()
           │
           ▼
        FilterController.filter_applied
           │
           ▼
        MainController._on_filter_applied()
           │
           └── _apply_filters()
                  │
                  ├── Get compiled filter
                  │
                  ├── Filter entries
                  │
                  └── Update LogTableView
```

### §5.3 Category Toggle Flow

```
CategoryPanel.category_toggled(path, checked)
    │
    ▼
MainController._on_category_toggled()
    │
    ├── FilterController.toggle_category()
    │
    ├── FilterController.apply_filter()
    │
    └── Save category states
```

---

## §6 State Management

### §6.1 Controller State

```python
class MainController(QObject):
    def __init__(self, window: MainWindow):
        # Document state
        self._document: LogDocument | None = None
        self._all_entries: list[LogEntry] = []
        self._filtered_entries: list[LogEntry] = []
        
        # Services
        self._statistics_service = StatisticsService()
        self._highlight_service = HighlightService()
        
        # Sub-controllers
        self._filter_controller = FilterController(self)
        self._file_controller = FileController(self)
        
        # Category tree
        self._category_tree = CategoryTree()
        
        # Settings
        self._settings_manager = SettingsManager()
        
        # Background worker
        self._index_worker: IndexWorker | None = None
```

### §6.2 Settings Persistence

```python
def _load_settings(self) -> None:
    """Load application settings."""
    settings = self._settings_manager.load()
    
    # Load highlight patterns
    for pattern_data in settings.highlight_patterns:
        self._highlight_service.add_user_pattern(...)
    
    # Restore window geometry
    geometry = self._settings_manager.get_window_geometry()
    if geometry:
        self._window.restoreGeometry(geometry)
    
    # Restore column widths
    if settings.column_widths:
        self._window.get_log_table().set_column_widths(settings.column_widths)

def _save_settings(self) -> None:
    """Save application settings."""
    # Save highlight patterns
    patterns = [...]
    self._settings_manager.settings.highlight_patterns = patterns
    
    # Save last file
    if self._document:
        self._settings_manager.set_last_file(self._document.filepath)
    
    # Save window geometry
    self._settings_manager.set_window_geometry(self._window.saveGeometry())
    
    # Save column widths
    self._settings_manager.set_column_widths(...)
    
    # Save category states
    self._save_category_states()
    
    self._settings_manager.save()
```

---

## §7 Error Handling

### §7.1 File Errors

```python
def open_file(self, filepath: str) -> None:
    try:
        self._document = LogDocument(filepath)
        # ... success path
    except FileNotFoundError:
        self._window.show_error("File Not Found", f"The file '{filepath}' does not exist.")
    except PermissionError:
        self._window.show_error("Access Denied", f"Permission denied for '{filepath}'.")
    except Exception as e:
        self._window.show_error_with_details("Error", str(e), traceback.format_exc())
```

### §7.2 Filter Errors

```python
def _on_filter_error(self, error_message: str) -> None:
    """Handle filter error from FilterController."""
    self._window.show_error("Filter Error", error_message)
```

---

## §8 Threading

### §8.1 Main Thread Operations

All UI operations must run on main thread:
- Window updates
- Model updates
- Signal emissions to UI

### §8.2 Background Thread Operations

File indexing runs in background:
- `IndexWorker` runs in `QThread`
- Emits `finished` signal when complete
- Main thread receives via `Qt.QueuedConnection`

### §8.3 Thread Safety

| Component | Thread | Notes |
|-----------|--------|-------|
| `MainController` | Main | All operations on main thread |
| `IndexWorker` | Background | File indexing only |
| `FileWatcher` | Background | File system monitoring |
| `LogDocument` | Either | Not thread-safe, use in one thread |

---

## §9 Performance

### §9.1 File Loading

| File Size | Lines | Load Time | Memory |
|-----------|-------|-----------|--------|
| 10 MB | 100K | ~0.5s | ~50 MB |
| 100 MB | 1M | ~5s | ~500 MB |
| 1 GB | 10M | ~50s | ~5 GB |

### §9.2 Filter Application

| Entries | Filter Time | Notes |
|---------|-------------|-------|
| 100K | ~10ms | Compiled filter |
| 1M | ~100ms | Compiled filter |
| 10M | ~1s | Compiled filter |

---

## §10 Testing

### §10.1 Unit Tests

```python
def test_main_controller_open_file(main_controller, tmp_path):
    """Test file opening."""
    log_file = tmp_path / "test.log"
    log_file.write_text("2024-01-01 00:00:00 Category LOG_MSG Test\n")
    
    main_controller.open_file(str(log_file))
    
    # Wait for indexing
    # ... (in real test, use qWait or signal spy)
    
    assert main_controller._document is not None
    assert len(main_controller._all_entries) == 1

def test_main_controller_filter(main_controller):
    """Test filter application."""
    # Set up entries
    main_controller._all_entries = [create_entry("error"), create_entry("info")]
    
    # Apply filter
    main_controller._filter_controller.set_filter_text("error")
    main_controller._filter_controller.apply_filter()
    
    # Check filtered
    assert len(main_controller._filtered_entries) == 1
```

---

## §11 Cross-References

- **Threading Model:** [../global/threading.md](../global/threading.md)
- **Error Handling:** [../global/error-handling.md](../global/error-handling.md)
- **Memory Model:** [../global/memory-model.md](../global/memory-model.md)
- **File Management:** [file-management.md](file-management.md)
- **Filter Controller:** [filter-controller.md](filter-controller.md)
- **Filter Engine:** [filter-engine.md](filter-engine.md)

---

## §12 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-14 | Updated import: build_system_nodes → build_category_display_nodes |
| 1.0 | 2026-03-13 | Initial main controller specification |