# Log Viewer - Master Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Type:** Python Tooling (Desktop Application)

---

## §1 Project Overview

### §1.1 Purpose

Log Viewer is a desktop application for viewing, filtering, and analyzing log files. It provides:
- Hierarchical category tree for organizing log entries
- Multiple filter modes (plain text, regex, simple query)
- Real-time file watching and auto-reload
- Custom highlight patterns
- Statistics and log level counters

### §1.2 Technology Stack

- **Language:** Python 3.12+
- **GUI Framework:** PySide6 (Qt)
- **Type Safety:** beartype + mypy/pyright
- **Package Manager:** uv
- **Testing:** pytest

### §1.3 Architecture

```
src/
├── constants/      # Application constants, colors, dimensions
│   ├── app_constants.py
│   ├── colors.py
│   ├── dimensions.py
│   └── log_levels.py
├── controllers/   # Business logic controllers
│   ├── main_controller.py      # Central coordinator
│   ├── filter_controller.py    # Filter state management
│   ├── file_controller.py      # File operations
│   ├── file_watcher.py         # File system monitoring
│   └── index_worker.py         # Background indexing
├── core/          # Core domain logic
│   ├── category_tree.py        # Hierarchical category structure
│   ├── filter_engine.py       # Filter compilation and matching
│   ├── highlight_engine.py    # Text highlighting
│   ├── parser.py              # Log line parsing
│   ├── simple_query_parser.py # Query language parser
│   └── statistics.py          # Log statistics
├── models/        # Data models
│   ├── log_entry.py           # Single log entry
│   ├── log_document.py        # Log file document
│   ├── filter_state.py        # Filter state model
│   └── system_node.py         # Category tree node
├── services/      # Application services
│   ├── find_service.py        # Find in logs
│   ├── highlight_service.py   # Highlight management
│   └── statistics_service.py  # Statistics computation
├── styles/        # Qt stylesheets
│   └── stylesheet.py
├── utils/         # Utilities
│   ├── clipboard.py           # Clipboard operations
│   └── settings_manager.py   # Persistent settings
└── views/         # Qt views and widgets
    ├── main_window.py         # Main application window
    ├── log_table_view.py      # Log entry table
    ├── category_panel.py      # Category filter panel
    ├── filter_toolbar.py      # Filter input toolbar
    ├── find_dialog.py         # Find dialog
    ├── statistics_panel.py   # Statistics panel
    ├── table_context_menu.py # Context menu
    ├── components/            # Reusable components
    │   ├── base_panel.py
    │   ├── counter_widget.py
    │   └── search_input.py
    └── widgets/              # Custom widgets
        ├── collapsible_panel.py
        ├── custom_category_dialog.py
        ├── error_dialog.py
        ├── file_tabs.py
        ├── highlight_dialog.py
        ├── main_status_bar.py
        ├── search_toolbar.py
        └── statistics_bar.py
```

---

## §2 Feature Index

| Feature | Spec Document | Status |
|---------|---------------|--------|
| Category Checkbox Behavior | [specs/features/category-checkbox-behavior.md](specs/features/category-checkbox-behavior.md) | v1.0 |
| Filter Engine | [specs/features/filter-engine.md](specs/features/filter-engine.md) | v1.0 |
| Category Tree | [specs/features/category-tree.md](specs/features/category-tree.md) | v1.0 |
| File Management | [specs/features/file-management.md](specs/features/file-management.md) | v1.0 |
| Main Controller | [specs/features/main-controller.md](specs/features/main-controller.md) | v1.0 |
| UI Components | [specs/features/ui-components.md](specs/features/ui-components.md) | v1.0 |
| Filter Controller | [specs/features/filter-controller.md](specs/features/filter-controller.md) | v1.0 |
| Settings Manager | [specs/features/settings-manager.md](specs/features/settings-manager.md) | v1.0 |
| Highlight Service | [specs/features/highlight-service.md](specs/features/highlight-service.md) | v1.0 |

---

## §3 Global Specifications

### §3.1 Memory Model

Per [specs/global/memory-model.md](specs/global/memory-model.md):

- Qt parent-child ownership for widgets
- Python reference counting for models
- Context managers for `LogDocument`
- No manual memory management needed

### §3.2 Threading Model

Per [specs/global/threading.md](specs/global/threading.md):

- **Main Thread:** All GUI operations
- **Background Threads:** File indexing (`IndexWorker`), file watching (`FileWatcher`)
- **Signal/Slot:** Cross-thread communication via Qt signals with `Qt.QueuedConnection`
- **Thread Safety:** Models are not thread-safe; use signals for updates

### §3.3 Error Handling

Per [specs/global/error-handling.md](specs/global/error-handling.md):

- **Critical Errors:** Show dialog, offer recovery options
- **Recoverable Errors:** Log warning, continue operation
- **User Input Errors:** Show inline error, prevent action
- **File Errors:** Show error dialog with details

---

## §4 Global Conventions

### §4.1 Code Style

```python
# Every file starts with:
from __future__ import annotations
from beartype import beartype

# Use modern type hints:
def function(items: list[str]) -> dict[str, int]:
    ...

# Use X | None instead of Optional[X]:
def get_entry(index: int) -> LogEntry | None:
    ...

# All public functions decorated with @beartype:
@beartype
def public_function(name: str, count: int) -> list[str]:
    ...
```

### §4.2 Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `LogEntry`, `FilterEngine` |
| Functions | snake_case | `get_entries()`, `apply_filter()` |
| Variables | snake_case | `entry_count`, `filter_text` |
| Constants | UPPER_SNAKE | `MAX_ENTRIES`, `DEFAULT_TIMEOUT` |
| Signals | snake_case | `filter_applied`, `entry_selected` |
| Slots | snake_case with prefix | `_on_filter_applied()`, `_on_entry_clicked()` |
| Private members | Leading underscore | `self._entries`, `self._filter_engine` |

### §4.3 File Organization

```python
# Standard file structure:
from __future__ import annotations
from beartype import beartype

# Standard library imports
import os
import re
from dataclasses import dataclass
from typing import Any

# Third-party imports
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget

# Local imports
from src.models.log_entry import LogEntry
from src.core.filter_engine import FilterEngine

# Constants
MAX_ENTRIES = 100000
DEFAULT_TIMEOUT = 5000

# Classes
class MyClass:
    """Class docstring."""
    
    @beartype
    def __init__(self) -> None:
        """Initialize."""
```

---

## §5 API Reference

See [specs/api/engine-api.yaml](specs/api/engine-api.yaml) for complete API documentation.

### §5.1 Key Classes

| Class | Module | Description |
|-------|--------|-------------|
| `LogEntry` | `models.log_entry` | Single log entry |
| `LogDocument` | `models.log_document` | Log file document |
| `FilterEngine` | `core.filter_engine` | Filter compilation |
| `CategoryTree` | `core.category_tree` | Category hierarchy |
| `MainController` | `controllers.main_controller` | Central coordinator |
| `MainWindow` | `views.main_window` | Main application window |

### §5.2 Key Signals

| Signal | Emitter | When |
|--------|---------|------|
| `filter_applied` | `FilterController` | Filter applied |
| `category_toggled` | `CategoryPanel` | Category checkbox toggled |
| `file_opened` | `FileController` | File opened |
| `file_changed` | `FileWatcher` | File changed on disk |
| `statistics_updated` | `MainController` | Statistics computed |

---

## §6 Data Flow

### §6.1 File Open Flow

```
User → MainWindow.open_file()
     → MainController.open_file()
     → FileController.open_file()
     → LogDocument created
     → IndexWorker.start()
     → IndexWorker.finished
     → MainController._on_index_complete()
     → CategoryTree built
     → FilterController updated
     → CategoryPanel populated
     → LogTableView populated
```

### §6.2 Filter Flow

```
User → MainWindow.filter_applied
     → MainController._on_filter_applied_from_ui()
     → FilterController.apply_filter()
     → FilterEngine.matches()
     → FilterController.filter_applied
     → MainController._on_filter_applied()
     → LogTableView.set_entries()
```

### §6.3 Category Toggle Flow

```
User → CategoryPanel.category_toggled
     → MainController._on_category_toggled()
     → FilterController.toggle_category()
     → FilterController.apply_filter()
     → Filter applied (see §6.2)
```

---

## §7 Performance Requirements

| Operation | Target | Notes |
|-----------|--------|-------|
| File open (10 MB) | < 1s | Background indexing |
| Filter apply (100K entries) | < 50ms | Compiled filter |
| Category toggle | < 10ms | Visibility check |
| UI response | < 16ms | 60 FPS |
| Memory (100 MB file) | < 500 MB | Python overhead |

---

## §8 Testing Requirements

### §8.1 Test Categories

| Category | Location | Coverage Target |
|----------|----------|------------------|
| Unit Tests | `tests/test_*.py` | 80% |
| Integration Tests | `tests/test_integration.py` | Key flows |
| Performance Tests | Manual | Large files |

### §8.2 Test Files

| File | Coverage |
|------|----------|
| `test_category_tree.py` | Category tree operations |
| `test_filter_engine.py` | Filter compilation and matching |
| `test_highlight_engine.py` | Highlight patterns |
| `test_parser.py` | Log line parsing |
| `test_statistics.py` | Statistics computation |
| `test_settings_manager.py` | Settings persistence |
| `test_integration.py` | End-to-end flows |

---

## §9 Navigation

- **Quick Index:** [SPEC-INDEX.md](SPEC-INDEX.md)
- **API Reference:** [specs/api/engine-api.yaml](specs/api/engine-api.yaml)

### §9.1 Global Specs

- [Memory Model](specs/global/memory-model.md)
- [Threading Model](specs/global/threading.md)
- [Error Handling](specs/global/error-handling.md)

### §9.2 Feature Specs

- [Category Checkbox Behavior](specs/features/category-checkbox-behavior.md)
- [Filter Engine](specs/features/filter-engine.md)
- [Category Tree](specs/features/category-tree.md)
- [File Management](specs/features/file-management.md)
- [Main Controller](specs/features/main-controller.md)
- [UI Components](specs/features/ui-components.md)
- [Filter Controller](specs/features/filter-controller.md)
- [Settings Manager](specs/features/settings-manager.md)
- [Highlight Service](specs/features/highlight-service.md)

---

## §10 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial master spec with complete documentation |