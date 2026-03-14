# Memory Model Specification

**Version:** 1.1
**Last Updated:** 2026-03-14
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This document defines memory management patterns and ownership semantics for the Log Viewer application. As a Python application with Qt GUI, memory management follows Python's reference counting with Qt's parent-child ownership model.

---

## §2 Ownership Models

### §2.1 Qt Parent-Child Ownership

Qt widgets use parent-child ownership for automatic memory management:

```
MainWindow (parent)
├── SearchToolbarWithStats (child)
├── LogTableView (child)
├── CategoryPanel (child)
└── MainStatusBar (child)
```

**Rule:** When a parent widget is destroyed, all children are automatically destroyed.

**Implementation Pattern:**
```python
# Correct: Parent owns child
self._log_table = LogTableView(self)  # 'self' becomes parent

# Incorrect: Orphan widget (memory leak potential)
self._log_table = LogTableView()  # No parent
```

### §2.2 Python Reference Counting

Python uses reference counting with garbage collection for cyclic references:

**Strong References:**
- Controller references to services: `self._statistics_service = StatisticsService()`
- Model references to data: `self._all_entries: list[LogEntry] = []`

**Weak References:**
- Use `weakref` for circular references to prevent memory leaks
- Qt signals use weak references internally

---

## §3 Data Structure Ownership

### §3.1 LogEntry (Immutable Dataclass)

```python
@dataclass(frozen=True)
class LogEntry:
    row_index: int
    timestamp: str
    category: str
    raw_message: str
    display_message: str
    level: LogLevel
    file_offset: int
    raw_line: str
```

**Ownership:** 
- Created by: [`LogDocument.get_line()`](../../src/models/log_document.py:87)
- Stored in: `list[LogEntry]` owned by `MainController._all_entries`
- Lifetime: Session-scoped (cleared on file close)

**Memory Budget:** 
- Max entries: ~10 million (configurable)
- Entry size: ~200-500 bytes
- Max memory: ~5GB for largest files

### §3.2 LogDocument (Lazy Loading)

```python
class LogDocument:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._line_offsets: List[int] = []
        self._file_handle = None  # Owned resource
```

**Ownership:**
- Created by: `MainController.open_file()`
- Must call: `document.close()` to release file handle
- Context manager support: `with LogDocument(path) as doc: ...`

**Resource Management:**
- File handle: Must be explicitly closed
- Line offsets: Loaded once during `build_index()`
- Categories: Cached in `_categories: Set[str]`

### §3.3 CategoryTree (Mutable Tree)

```python
class CategoryTree:
    def __init__(self):
        self._root = CategoryNode(name="", full_path="")
        self._nodes: dict[str, CategoryNode] = {}
```

**Ownership:**
- Created by: `MainController._on_index_complete()`
- Owned by: `MainController._category_tree`
- Nodes: Stored in `_nodes` dict for O(1) lookup

**Lifetime:** Rebuilt on each file load.

---

## §4 Controller Ownership

### §4.1 MainController

```python
class MainController(QObject):
    def __init__(self, window: MainWindow):
        self._window = window  # Reference, not owned
        self._document: LogDocument | None = None  # Owned
        self._filter_controller = FilterController(self)  # Owned (Qt parent)
        self._statistics_service = StatisticsService()  # Owned
        self._highlight_service = HighlightService()  # Owned
```

**Ownership Rules:**
| Component | Ownership | Lifetime |
|-----------|-----------|----------|
| `_window` | Reference | Application |
| `_document` | Owned | File session |
| `_filter_controller` | Owned (Qt child) | Application |
| `_statistics_service` | Owned | Application |
| `_highlight_service` | Owned | Application |
| `_all_entries` | Owned | File session |
| `_category_tree` | Owned | File session |

### §4.2 FilterController

```python
class FilterController(QObject):
    def __init__(self, parent: QObject | None = None):
        self._state = FilterState()  # Owned
        self._engine = FilterEngine()  # Owned
        self._category_tree = CategoryTree()  # Owned
        self._compiled_filter: Callable | None = None  # Owned reference
```

---

## §5 Service Ownership

### §5.1 StatisticsService

```python
class StatisticsService:
    def __init__(self):
        self._calculator = StatisticsCalculator()  # Owned
        self._cached_stats: Optional[LogStatistics] = None  # Owned
```

**Caching Strategy:**
- Cache key: `hash(tuple(id(e) for e in entries))`
- Cache invalidation: On file close, on filter change
- Memory: O(1) for cached stats

### §5.2 HighlightService

```python
class HighlightService:
    def __init__(self):
        self._user_engine = HighlightEngine()  # Owned
        self._find_engine = HighlightEngine()  # Owned
        self._combined_engine = HighlightEngine()  # Owned
        self._user_patterns: List[HighlightPattern] = []  # Owned
```

---

## §6 View Ownership

### §6.1 MainWindow

```python
class MainWindow(QMainWindow):
    def _create_components(self):
        self._search_toolbar = SearchToolbarWithStats()  # Owned (Qt child)
        self._log_table = LogTableView()  # Owned (Qt child)
        self._category_panel = CategoryPanel()  # Owned (Qt child)
        self._status_bar = MainStatusBar()  # Owned (Qt child)
```

### §6.2 CategoryPanel

```python
class CategoryPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        self._model: Optional[QStandardItemModel] = None  # Owned
        self._category_items: dict[str, QStandardItem] = {}  # Owned references
```

---

## §7 Memory Budgets

### §7.1 File Loading

| File Size | Line Count | Memory Usage | Strategy |
|-----------|------------|--------------|----------|
| < 100 MB | < 1M lines | < 500 MB | Full load |
| 100 MB - 1 GB | 1M - 10M lines | 500 MB - 5 GB | Lazy load |
| > 1 GB | > 10M lines | > 5 GB | Stream + index |

### §7.2 Filter Engine Cache

```python
class FilterEngine:
    def __init__(self):
        self._regex_cache: dict[str, re.Pattern] = {}  # Bounded cache
```

**Cache Limits:**
- Max patterns: 100 (configurable)
- Cache eviction: LRU or manual clear via `clear_cache()`

### §7.3 Statistics Cache

- Single `LogStatistics` object cached
- Hash-based invalidation
- Memory: O(1)

---

## §8 Resource Cleanup

### §8.1 File Handles

```python
# Must close on file change or app exit
if self._document is not None:
    self._document.close()
    self._document = None
```

### §8.2 Qt Connections

```python
# Qt automatically disconnects on object destruction
# Explicit disconnect for early cleanup:
self._filter_controller.filter_applied.disconnect(self._on_filter_applied)
```

### §8.3 Background Threads

```python
# IndexWorker cleanup
if self._index_worker is not None:
    self._index_worker.wait()  # Wait for thread to finish
    self._index_worker = None
```

---

## §9 Thread Safety

### §9.1 Main Thread Only (Qt GUI)

- All UI operations must run on main thread
- Signal/slot connections use `Qt.QueuedConnection` for cross-thread

### §9.2 Background Threads

- `IndexWorker`: File indexing in background
- Must not access Qt objects directly
- Use signals to communicate results

### §9.3 Shared State

```python
# Thread-safe via Qt signals
class IndexWorker(QThread):
    finished = Signal()  # Cross-thread communication
```

---

## §10 Best Practices

### §10.1 Do

✅ Use Qt parent-child for widget ownership  
✅ Close file handles explicitly  
✅ Use context managers for `LogDocument`  
✅ Clear caches on file close  
✅ Use weak references for circular dependencies  

### §10.2 Don't

❌ Create widgets without parents  
❌ Store raw file handles in long-lived objects  
❌ Accumulate compiled regex patterns without limit  
❌ Access Qt objects from background threads  

---

## §11 Cross-References

- **Threading Model:** [threading.md](threading.md)
- **Error Handling:** [error-handling.md](error-handling.md)
- **Category Tree Spec:** [../features/category-checkbox-behavior.md](../features/category-checkbox-behavior.md)
- **Filter Engine:** [../features/filter-engine.md](../features/filter-engine.md)

---

## §12 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-14 | Removed custom categories from CategoryPanel |
| 1.0 | 2026-03-13 | Initial memory model specification |