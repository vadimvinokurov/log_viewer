# Threading Model Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This document defines the threading model for the Log Viewer application. The application uses Qt's event loop with background threads for file operations.

---

## §2 Threading Architecture

### §2.1 Thread Model

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Thread (GUI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ MainWindow │  │ Controllers │  │ Qt Event Loop       │   │
│  │   (Qt)      │  │             │  │                     │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
│         │                │                    │               │
│         └────────────────┴────────────────────┘               │
│                          │                                    │
│              ┌───────────┴───────────┐                       │
│              │   Signal/Slot Queue    │                       │
│              └─────────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Qt Signals (QueuedConnection)
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                   Background Threads                          │
│  ┌─────────────────┐  ┌─────────────────┐                    │
│  │  IndexWorker    │  │  FileWatcher    │                    │
│  │  (QThread)      │  │  (QThread)      │                    │
│  └─────────────────┘  └─────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### §2.2 Thread Types

| Thread | Purpose | Qt Affinity |
|--------|---------|-------------|
| Main Thread | GUI, event processing, all UI updates | GUI Thread |
| IndexWorker | File indexing, line offset building | Worker Thread |
| FileWatcher | File system monitoring | Worker Thread |

---

## §3 Main Thread Constraints

### §3.1 GUI Operations (Main Thread Only)

**MUST run on main thread:**
- All QWidget operations
- Model/view updates
- Signal emissions to UI
- Dialog display

```python
# Correct: UI operation on main thread
def _on_index_complete(self, filepath: str) -> None:
    # This runs on main thread via signal
    self._window.get_log_table().set_entries(display_entries)
```

### §3.2 Thread Affinity

```python
class MainController(QObject):
    # QObject has thread affinity
    # All slots run on the thread where the object lives
    
    def __init__(self, window: MainWindow):
        super().__init__()  # Lives on main thread
        self._index_worker = IndexWorker(self._document)
        self._index_worker.finished.connect(
            lambda: self._on_index_complete(filepath)
        )  # QueuedConnection by default for cross-thread
```

---

## §4 Background Threads

### §4.1 IndexWorker

**Purpose:** Build line offset index for large files without blocking UI.

```python
class IndexWorker(QThread):
    finished = Signal()  # Cross-thread signal
    
    def __init__(self, document: LogDocument):
        super().__init__()
        self._document = document
    
    def run(self) -> None:
        # Runs on worker thread
        self._document.build_index(self._progress_callback)
        # Signal emission is thread-safe
        self.finished.emit()
```

**Thread Safety:**
- `LogDocument` is owned by worker during indexing
- No concurrent access to document
- Signal emission uses `Qt.QueuedConnection`

### §4.2 FileWatcher

**Purpose:** Monitor file changes on disk.

```python
class FileWatcher(QObject):
    file_changed = Signal(object)  # Path object
    file_removed = Signal(object)  # Path object
    
    def _on_file_changed(self, filepath: str) -> None:
        # Runs on worker thread
        # Signal emission is thread-safe
        self.file_changed.emit(Path(filepath))
```

---

## §5 Signal/Slot Connections

### §5.1 Connection Types

| Type | Use Case | Thread Safety |
|------|----------|---------------|
| `AutoConnection` | Default, auto-selects | Thread-safe |
| `DirectConnection` | Same-thread only | Not thread-safe |
| `QueuedConnection` | Cross-thread to main | Thread-safe |
| `BlockingQueuedConnection` | Cross-thread, blocking | Thread-safe (blocks) |

### §5.2 Cross-Thread Communication

```python
# Worker thread emits signal
class IndexWorker(QThread):
    finished = Signal()  # Signal declaration
    
    def run(self):
        # ... work ...
        self.finished.emit()  # Thread-safe emission

# Main thread receives via slot
class MainController(QObject):
    def __init__(self):
        self._index_worker.finished.connect(
            self._on_index_complete  # Slot runs on main thread
        )  # AutoConnection selects QueuedConnection for cross-thread
```

### §5.3 Signal Emission Rules

**Thread-Safe Operations:**
- Emitting signals from any thread
- Connecting signals across threads
- Using `Qt.QueuedConnection` explicitly

**Not Thread-Safe:**
- Direct method calls across threads
- Accessing QObject from non-owner thread
- Modifying UI from worker thread

---

## §6 Synchronization Primitives

### §6.1 Qt Signals (Primary)

**Use for:**
- Worker → Main thread communication
- Cross-component decoupling
- Event notification

```python
# Worker thread signals
self._index_worker.finished.connect(self._on_index_complete)
self._file_controller.file_changed.connect(self._on_file_changed)
```

### §6.2 Python Locks (Secondary)

**Use for:**
- Protecting shared Python data structures
- Non-Qt state synchronization

```python
import threading

class SharedState:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}
    
    def update(self, key, value):
        with self._lock:
            self._data[key] = value
```

### §6.3 No Mutex Needed

**Qt handles internally:**
- Signal/slot queues
- Event loop synchronization
- QObject thread affinity

---

## §7 Thread-Safe Patterns

### §7.1 Background Task Pattern

```python
class MainController(QObject):
    def open_file(self, filepath: str) -> None:
        # Main thread: UI update
        self._window.show_status("Loading...", 0)
        
        # Create worker thread
        self._index_worker = IndexWorker(self._document)
        
        # Connect signals (thread-safe)
        self._index_worker.finished.connect(
            lambda: self._on_index_complete(filepath)
        )
        
        # Start background work
        self._index_worker.start()
    
    def _on_index_complete(self, filepath: str) -> None:
        # Main thread: UI update
        self._window.show_status(f"Loaded {len(self._all_entries)} entries", 3000)
```

### §7.2 Progress Reporting Pattern

```python
class IndexWorker(QThread):
    progress = Signal(int, int)  # bytes_read, total_bytes
    
    def run(self) -> None:
        self._document.build_index(
            progress_callback=lambda r, t: self.progress.emit(r, t)
        )

class MainController(QObject):
    def __init__(self):
        self._index_worker.progress.connect(self._on_progress)
    
    def _on_progress(self, bytes_read: int, total_bytes: int) -> None:
        # Main thread: Update progress bar
        percent = int(bytes_read / total_bytes * 100)
        self._window.update_progress(percent)
```

---

## §8 Thread-Safe Data Access

### §8.1 Immutable Data (Thread-Safe)

```python
@dataclass(frozen=True)
class LogEntry:
    # Immutable - safe to share across threads
    row_index: int
    timestamp: str
    category: str
    # ...
```

### §8.2 Owned Data (Single Owner)

```python
class FilterController(QObject):
    def __init__(self, parent):
        self._state = FilterState()  # Owned by controller
        self._compiled_filter: Callable | None = None  # Owned
```

**Rule:** Only owner thread can modify. Other threads read via copied data.

### §8.3 Shared State (Requires Synchronization)

```python
# Avoid shared mutable state when possible
# If needed, use Qt signals for updates

class SharedState(QObject):
    state_changed = Signal(dict)
    
    def __init__(self):
        self._state = {}
    
    def update(self, key: str, value: Any) -> None:
        # Main thread only
        self._state[key] = value
        self.state_changed.emit(self._state.copy())
```

---

## §9 File Operations

### §9.1 File Loading Sequence

```
Main Thread                    Worker Thread
    │                               │
    │ open_file()                   │
    │──────────────────────────────>│
    │                               │ build_index()
    │ show_status("Loading...")     │
    │                               │
    │                               │ progress.emit()
    │<──────────────────────────────│
    │ update_progress()             │
    │                               │
    │                               │ finished.emit()
    │<──────────────────────────────│
    │ _on_index_complete()          │
    │ set_entries()                 │
    │                               │
```

### §9.2 File Watching

```python
class FileController(QObject):
    file_changed = Signal(object)  # Path
    
    def __init__(self):
        self._file_watcher = FileWatcher(self)
        self._file_watcher.file_changed.connect(self._on_file_changed)
    
    def _on_file_changed(self, filepath: Path) -> None:
        # Main thread: Prompt user
        if self._auto_reload_enabled:
            self.refresh()
```

---

## §10 Performance Considerations

### §10.1 UI Responsiveness

**Target:** 60 FPS (16ms frame time)

**Guidelines:**
- File operations in background thread
- Batch UI updates (not per-line)
- Use progress signals for long operations

### §10.2 Memory Access

**Thread-Local Cache:**
- Each thread can have local cache
- No synchronization needed for thread-local data

**Shared Cache:**
- Use `threading.Lock` for Python data
- Use Qt signals for state propagation

---

## §11 Debugging Thread Issues

### §11.1 Common Problems

| Problem | Symptom | Solution |
|---------|---------|----------|
| UI freeze | Window not responding | Move work to background thread |
| Race condition | Intermittent crashes | Use signals, not direct calls |
| Deadlock | Application hangs | Avoid blocking queued connections |

### §11.2 Thread Sanitizer

```python
# Enable Qt thread warnings
import os
os.environ['QT_DEBUG_PLUGINS'] = '1'

# Check thread affinity
assert widget.thread() == QThread.currentThread()
```

---

## §12 Best Practices

### §12.1 Do

✅ Use Qt signals for cross-thread communication  
✅ Keep UI operations on main thread  
✅ Use `QThread` for background work  
✅ Emit signals from worker threads  
✅ Use `QueuedConnection` for cross-thread signals  

### §12.2 Don't

❌ Access QWidget from worker thread  
❌ Call UI methods directly from background  
❌ Block main thread for I/O  
❌ Use `BlockingQueuedConnection` unless necessary  
❌ Share mutable state without synchronization  

---

## §13 Cross-References

- **Memory Model:** [memory-model.md](memory-model.md)
- **Error Handling:** [error-handling.md](error-handling.md)
- **File Controller:** [../features/file-management.md](../features/file-management.md)

---

## §14 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial threading specification |