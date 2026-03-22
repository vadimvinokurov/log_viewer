# File Management Specification

**Version:** 1.2
**Last Updated:** 2026-03-18
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The File Management system handles opening and closing log files. It loads all file content into memory for fast filtering and search operations. File updates are handled via manual refresh button.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FileController                            │
│  - Manages open files (FileInfo)                              │
│  - Tracks recent files                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────┐
              │    LogDocument      │
              │  - Full load        │
              │  - All entries      │
              │  - Category extract │
              └─────────────────────┘
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

`LogDocument` loads all log file content into memory. All entries are available for fast filtering and search operations.

### §3.2 API Reference

```python
class LogDocument:
    """Document model with full file loading."""
    
    def __init__(self, filepath: str) -> None:
        """
        Initialize document.
        
        Args:
            filepath: Path to log file
        """
    
    def load(
        self,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> None:
        """
        Load all lines into memory.
        
        Args:
            progress_callback: Optional callback(bytes_read, total_bytes)
        
        Must be called before get_all_entries().
        """
    
    def get_all_entries(self) -> list[LogEntry]:
        """Return all loaded log entries."""
    
    def get_line_count(self) -> int:
        """Return total number of lines."""
    
    def get_categories(self) -> set[str]:
        """Return all unique categories found."""

### §3.3 Loading Process

```
load()
    │
    ├── Open file in binary mode
    │
    ├── For each line:
    │   ├── Parse line (decode UTF-8)
    │   ├── Create LogEntry
    │   └── Extract category
    │
    ├── Store entries: list[LogEntry]
    ├── Store categories: set[str]
    │
    └── Close file handle
```

### §3.4 Memory Model

| Component | Memory | Lifetime |
|-----------|--------|----------|
| `_entries` | O(n) where n = lines, ~200-500 bytes each | File session |
| `_categories` | O(c) where c = categories | File session |

**Note:** File handle is closed immediately after loading. No persistent file handle during session.

---

## §4 FileController

### §4.1 Purpose

`FileController` manages file operations including opening and closing files.

### §4.2 API Reference

```python
class FileController(QObject):
    """Controller for file operations."""
    
    # Signals
    file_opened = Signal(object)      # FileInfo
    file_closed = Signal(object)      # Path
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

## §5 IndexWorker

### §5.1 Purpose

`IndexWorker` performs file indexing in a background thread to avoid blocking the UI.

### §5.2 Implementation

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

### §5.3 Thread Safety

- Runs in background thread
- Emits `finished` signal when complete
- Main thread receives via `Qt.QueuedConnection`
- Document is not accessed during indexing

---

## §6 File Operations Flow

### §6.1 Open File Sequence

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
           └── Apply initial filter
```

### §6.2 Close File Sequence

```
User: Close file
    │
    ▼
MainController.close_file()
    │
    ├── file_controller.close_file(filepath)
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

### §9.1 Loading Performance

| File Size | Lines | Load Time | Memory |
|-----------|-------|-----------|--------|
| 10 MB | 100K | ~0.5s | ~50 MB |
| 100 MB | 1M | ~5s | ~500 MB |
| 1 GB | 10M | ~50s | ~5 GB |

### §9.2 Optimization

- **Binary mode reading**: Efficient file I/O
- **Progress callback**: UI progress bar
- **Background thread**: Non-blocking UI
- **Full memory load**: Fast filtering and search

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
| 1.2 | 2026-03-18 | Removed real-time file watching and auto-reload feature |
| 1.1 | 2026-03-18 | Changed to full load model, removed lazy loading |
| 1.0 | 2026-03-13 | Initial file management specification |