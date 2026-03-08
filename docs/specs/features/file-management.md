# File Management Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The File Management system handles opening, closing, and monitoring log files. It provides lazy loading for large files and file watching for auto-reload functionality.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FileController                            │
│  - Manages open files (FileInfo)                              │
│  - Coordinates file watching                                  │
│  - Tracks recent files                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│    LogDocument      │       │    FileWatcher      │
│  - Lazy loading     │       │  - File monitoring  │
│  - Byte offset index│       │  - Change detection │
│  - Category extract │       │  - Removal detection│
└─────────────────────┘       └─────────────────────┘
```

### §2.2 Data Flow

```
User Action → MainWindow → MainController → FileController
                                              ↓
                                         LogDocument
                                              ↓
                                         IndexWorker (background)
                                              ↓
                                         MainController._on_index_complete()
                                              ↓
                                         CategoryTree + FilterController
                                              ↓
                                         LogTableView (display)
```

---

## §3 LogDocument

### §3.1 Purpose

`LogDocument` provides lazy loading for large log files. It builds a byte-offset index for efficient random access to lines without loading the entire file into memory.

### §3.2 API Reference

```python
class LogDocument:
    """Document model with lazy loading for large files."""
    
    def __init__(self, filepath: str) -> None:
        """
        Initialize document.
        
        Args:
            filepath: Path to log file
        """
    
    def build_index(
        self,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> None:
        """
        Build byte-offset index for all lines.
        
        Args:
            progress_callback: Optional callback(bytes_read, total_bytes)
        
        Must be called before get_line().
        """
    
    def get_line(self, row: int) -> LogEntry | None:
        """
        Get a single log entry by row index.
        
        Args:
            row: Zero-based row index
        
        Returns:
            LogEntry if valid row, None otherwise
        """
    
    def get_line_count(self) -> int:
        """Return total number of lines."""
    
    def get_categories(self) -> Set[str]:
        """Return all unique categories found."""
    
    def close(self) -> None:
        """Close file handle and release resources."""
    
    def __enter__(self) -> LogDocument:
        """Context manager entry."""
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit."""
```

### §3.3 Indexing Process

```
build_index()
    │
    ├── Open file in binary mode
    │
    ├── For each line:
    │   ├── Record byte offset
    │   ├── Parse line (decode UTF-8)
    │   └── Extract category
    │
    ├── Store line_offsets: List[int]
    ├── Store categories: Set[str]
    │
    └── Seek back to beginning
```

### §3.4 Memory Model

| Component | Memory | Lifetime |
|-----------|--------|----------|
| `_line_offsets` | O(n) where n = lines | File session |
| `_categories` | O(c) where c = categories | File session |
| `_file_handle` | 1 file handle | File session |
| LogEntry | ~200-500 bytes | Per-request (not cached) |

---

## §4 FileController

### §4.1 Purpose

`FileController` manages file operations including opening, closing, and watching files for changes.

### §4.2 API Reference

```python
class FileController(QObject):
    """Controller for file operations."""
    
    # Signals
    file_opened = Signal(object)      # FileInfo
    file_closed = Signal(object)      # Path
    file_changed = Signal(object)     # Path
    file_removed = Signal(object)     # Path
    recent_files_changed = Signal(list)  # list[Path]
    index_progress = Signal(int, int)  # bytes_read, total_bytes
    index_complete = Signal(str)       # filepath
    
    @beartype
    def open_file(self, filepath: str) -> LogDocument | None:
        """
        Open a log file.
        
        Args:
            filepath: Path to the log file.
        
        Returns:
            LogDocument if successful, None otherwise.
        """
    
    @beartype
    def close_file(self, filepath: str) -> bool:
        """
        Close a log file.
        
        Args:
            filepath: Path to the log file.
        
        Returns:
            True if file was closed, False if not found.
        """
    
    def get_document(self, filepath: str) -> LogDocument | None:
        """Get document for a file path."""
    
    def get_current_document(self) -> LogDocument | None:
        """Get the currently active document."""
    
    def get_current_file(self) -> Path | None:
        """Get the currently active file path."""
    
    def get_open_files(self) -> list[Path]:
        """Get list of open file paths."""
    
    def get_recent_files(self) -> list[Path]:
        """Get list of recent files."""
    
    def set_auto_reload(self, enabled: bool) -> None:
        """Enable or disable auto-reload."""
    
    def is_auto_reload_enabled(self) -> bool:
        """Check if auto-reload is enabled."""
    
    def cleanup(self) -> None:
        """Clean up resources."""
```

### §4.3 FileInfo Dataclass

```python
@dataclass
class FileInfo:
    """Information about an open file."""
    path: Path
    document: LogDocument
    is_modified: bool = False
```

---

## §5 FileWatcher

### §5.1 Purpose

`FileWatcher` monitors files for changes on disk and emits signals when files are modified or removed.

### §5.2 Implementation

```python
class FileWatcher(QObject):
    """Watcher for file system changes."""
    
    file_changed = Signal(object)  # Path
    file_removed = Signal(object)  # Path
    
    def watch_file(self, filepath: str) -> None:
        """Start watching a file for changes."""
    
    def stop_watching(self) -> None:
        """Stop watching the current file."""
    
    def get_current_file(self) -> str | None:
        """Get the currently watched file."""
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable watching."""
```

### §5.3 Change Detection

| Event | Signal | User Action |
|-------|--------|--------------|
| File modified | `file_changed` | Prompt to reload |
| File removed | `file_removed` | Show error dialog |

---

## §6 IndexWorker

### §6.1 Purpose

`IndexWorker` performs file indexing in a background thread to avoid blocking the UI.

### §6.2 Implementation

```python
class IndexWorker(QThread):
    """Background worker for file indexing."""
    
    finished = Signal()  # Emitted when indexing complete
    
    def __init__(self, document: LogDocument) -> None:
        super().__init__()
        self._document = document
    
    def run(self) -> None:
        """Run indexing in background thread."""
        self._document.build_index()
        self.finished.emit()
```

### §6.3 Thread Safety

- Runs in background thread
- Emits `finished` signal when complete
- Main thread receives via `Qt.QueuedConnection`
- Document is not accessed during indexing

---

## §7 File Operations Flow

### §7.1 Open File Sequence

```
User: Open file
    │
    ▼
MainController.open_file(filepath)
    │
    ├── Close existing document (if any)
    │
    ├── Create LogDocument(filepath)
    │
    ├── Create IndexWorker(document)
    │
    ├── Connect IndexWorker.finished → _on_index_complete
    │
    └── IndexWorker.start()  [Background thread]
           │
           ▼
        IndexWorker.run()
           │
           ├── document.build_index()
           │
           └── finished.emit()  [Signal to main thread]
                  │
                  ▼
        MainController._on_index_complete()
           │
           ├── Load all entries
           │
           ├── Build category tree
           │
           ├── Update filter controller
           │
           ├── Update category panel
           │
           ├── Start file watcher
           │
           └── Apply initial filter
```

### §7.2 Close File Sequence

```
User: Close file
    │
    ▼
MainController.close_file()
    │
    ├── file_controller.close_file(filepath)
    │       │
    │       ├── Stop file watcher
    │       │
    │       └── document.close()
    │
    ├── Clear data
    │       ├── _all_entries = []
    │       └── _filtered_entries = []
    │
    ├── Clear UI
    │       ├── log_table.clear()
    │       └── category_panel.clear()
    │
    └── Reset filter controller
```

---

## §8 Error Handling

### §8.1 File Errors

| Error | Handling | User Message |
|-------|----------|--------------|
| `FileNotFoundError` | Log + show dialog | "The file '{name}' does not exist." |
| `PermissionError` | Log + show dialog | "Permission denied for '{name}'." |
| `UnicodeDecodeError` | Log + skip line | Line skipped, continue |
| `OSError` | Log + show dialog | "Failed to open file: {error}" |

### §8.2 Recovery

```python
def open_file(self, filepath: str) -> None:
    try:
        self._document = LogDocument(filepath)
        # ... success path
    except FileNotFoundError:
        self._window.show_error("File Not Found", f"The file '{filepath}' does not exist.")
        logger.error(f"File not found: {filepath}")
    except PermissionError:
        self._window.show_error("Access Denied", f"Permission denied for '{filepath}'.")
        logger.error(f"Permission denied: {filepath}")
    except Exception as e:
        self._window.show_error_with_details("Error", str(e), traceback.format_exc())
        logger.exception(f"Failed to open file: {filepath}")
```

---

## §9 Performance

### §9.1 Indexing Performance

| File Size | Lines | Index Time | Memory |
|-----------|-------|------------|--------|
| 10 MB | 100K | ~0.5s | ~10 MB |
| 100 MB | 1M | ~5s | ~100 MB |
| 1 GB | 10M | ~50s | ~1 GB |

### §9.2 Optimization

- **Binary mode reading**: Accurate byte offsets
- **Progress callback**: UI progress bar
- **Background thread**: Non-blocking UI
- **Lazy line loading**: Load on demand

---

## §10 Settings Persistence

### §10.1 Recent Files

```python
# Save
recent_paths = file_controller.get_recent_files_paths()
settings_manager.set_recent_files(recent_paths)

# Load
recent_paths = settings_manager.get_recent_files()
file_controller.load_recent_files(recent_paths)
```

### §10.2 Last File

```python
# Save
if self._document:
    settings_manager.set_last_file(self._document.filepath)

# Load
last_file = settings_manager.get_last_file()
if last_file and Path(last_file).exists():
    self.open_file(last_file)
```

---

## §11 Testing

### §11.1 Unit Tests

```python
def test_log_document_indexing(tmp_path):
    """Test LogDocument builds correct index."""
    log_file = tmp_path / "test.log"
    log_file.write_text("line1\nline2\nline3\n")
    
    with LogDocument(str(log_file)) as doc:
        doc.build_index()
        
        assert doc.get_line_count() == 3
        assert doc.get_line(0) is not None
        assert doc.get_line(3) is None  # Out of bounds

def test_file_controller_open_close(tmp_path):
    """Test FileController open and close."""
    controller = FileController()
    log_file = tmp_path / "test.log"
    log_file.write_text("test\n")
    
    doc = controller.open_file(str(log_file))
    assert doc is not None
    
    assert controller.close_file(str(log_file)) == True
    assert controller.get_document(str(log_file)) is None
```

---

## §12 Cross-References

- **Threading Model:** [../global/threading.md](../global/threading.md)
- **Error Handling:** [../global/error-handling.md](../global/error-handling.md)
- **Memory Model:** [../global/memory-model.md](../global/memory-model.md)
- **Main Controller:** [main-controller.md](main-controller.md)

---

## §13 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial file management specification |