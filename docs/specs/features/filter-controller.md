# Filter Controller Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The Filter Controller manages filter state and coordinates filter operations between the UI and the Filter Engine. It handles text filters, category filters, and counter filters.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FilterController                           │
│  - Manages filter state                                       │
│  - Coordinates filter types                                   │
│  - Emits filter results                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────────┐   ┌─────────────┐
│ FilterEngine│   │  CategoryTree   │   │FilterState  │
│  (Core)     │   │    (Core)       │   │   (Model)   │
└─────────────┘   └─────────────────┘   └─────────────┘
```

### §2.2 Dependencies

```python
from src.core.filter_engine import FilterEngine, CompiledFilter
from src.core.category_tree import CategoryTree
from src.models.filter_state import FilterState
from src.models.log_entry import LogEntry, LogLevel
```

---

## §3 Responsibilities

### §3.1 Filter State Management

- Maintain current filter text
- Track filter mode (plain, regex, simple)
- Store category visibility states
- Store counter (log level) visibility states

### §3.2 Filter Coordination

- Combine text, category, and counter filters
- Coordinate with `FilterEngine` for compilation
- Apply combined filters to log entries

### §3.3 Signal Emission

- Emit `filter_applied` when filter changes
- Provide filtered entry count

---

## §4 API Reference

### §4.1 Class Definition

```python
class FilterController(QObject):
    """Controller for managing filter state and operations."""
    
    # Signals
    filter_applied = Signal(list)  # List[LogEntry]
    filter_error = Signal(str)     # error_message
    
    @beartype
    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the filter controller.
        
        Args:
            parent: Parent QObject
        """
```

### §4.2 Text Filter Operations

```python
@beartype
def set_filter_text(self, text: str) -> None:
    """
    Set the filter text.
    
    Args:
        text: Filter text (plain text, regex, or simple query)
    """

@beartype
def set_filter_mode(self, mode: str) -> None:
    """
    Set the filter mode.
    
    Args:
        mode: Filter mode ('plain', 'regex', or 'simple')
    """

def get_filter_text(self) -> str:
    """Get the current filter text."""

def get_filter_mode(self) -> str:
    """Get the current filter mode."""

def clear_filter(self) -> None:
    """Clear the text filter."""
```

### §4.3 Category Filter Operations

```python
@beartype
def set_category_tree(self, tree: CategoryTree) -> None:
    """
    Set the category tree for filtering.
    
    Args:
        tree: Category tree with visibility states
    """

@beartype
def toggle_category(self, path: str, checked: bool) -> None:
    """
    Toggle a category's visibility.
    
    Args:
        path: Category path (e.g., "System.Network")
        checked: Whether the category is checked
    """

def get_checked_categories(self) -> set[str]:
    """Get the set of checked category paths."""

def get_category_states(self) -> dict[str, bool]:
    """Get all category checkbox states."""

@beartype
def set_category_states(self, states: dict[str, bool]) -> None:
    """
    Restore category checkbox states.
    
    Args:
        states: Dictionary of path -> checked state
    """

def check_all_categories(self, checked: bool) -> None:
    """Check or uncheck all categories."""
```

### §4.4 Counter Filter Operations

```python
@beartype
def toggle_counter(self, counter_type: str, visible: bool) -> None:
    """
    Toggle a log level's visibility.
    
    Args:
        counter_type: Log level name ('critical', 'error', 'warning', 'msg', 'debug', 'trace')
        visible: Whether logs of this type should be visible
    """

def get_visible_counters(self) -> set[str]:
    """Get the set of visible log level names."""

def get_counter_states(self) -> dict[str, bool]:
    """Get all counter visibility states."""

@beartype
def set_counter_states(self, states: dict[str, bool]) -> None:
    """
    Restore counter visibility states.
    
    Args:
        states: Dictionary of level name -> visible state
    """
```

### §4.5 Filter Application

```python
@beartype
def apply_filter(self, entries: list[LogEntry]) -> list[LogEntry]:
    """
    Apply all active filters to entries.
    
    Args:
        entries: List of log entries to filter
        
    Returns:
        Filtered list of log entries
    """

def get_filter_predicate(self) -> Callable[[LogEntry], bool]:
    """
    Get a filter predicate function.
    
    Returns:
        Function that returns True if entry passes all filters
    """
```

---

## §5 Filter Combination Logic

### §5.1 Filter Types

| Type | Description | Implementation |
|------|-------------|----------------|
| Text | Search in message | `FilterEngine.compile(text, mode)` |
| Category | Category path match | `CategoryTree.is_visible(path)` |
| Counter | Log level match | `FilterState.visible_levels` |

### §5.2 Combination Rule

All filters are combined with **AND** logic:

```
entry passes = text_filter(entry) AND category_filter(entry) AND counter_filter(entry)
```

### §5.3 Filter Application Flow

```
entries → Text Filter → Category Filter → Counter Filter → filtered_entries
              │              │                 │
              ▼              ▼                 ▼
         Compiled      CategoryTree      FilterState
          Filter       is_visible()     visible_levels
```

---

## §6 State Model

### §6.1 FilterState

```python
@dataclass
class FilterState:
    """State model for filters."""
    
    # Text filter
    text: str = ""
    mode: str = "plain"  # 'plain', 'regex', 'simple'
    
    # Category filter
    category_states: dict[str, bool] = field(default_factory=dict)
    
    # Counter filter (log levels)
    counter_states: dict[str, bool] = field(default_factory=lambda: {
        "critical": True,
        "error": True,
        "warning": True,
        "msg": True,
        "debug": True,
        "trace": True,
    })
    
    def is_text_filter_active(self) -> bool:
        """Check if text filter is active."""
        return bool(self.text.strip())
    
    def is_category_filter_active(self) -> bool:
        """Check if category filter is active."""
        return not all(self.category_states.values())
    
    def is_counter_filter_active(self) -> bool:
        """Check if counter filter is active."""
        return not all(self.counter_states.values())
```

---

## §7 Error Handling

### §7.1 Regex Errors

```python
def set_filter_text(self, text: str) -> None:
    if self._state.mode == "regex":
        try:
            re.compile(text)
        except re.error as e:
            self.filter_error.emit(f"Invalid regex: {e}")
            return
    self._state.text = text
```

### §7.2 Simple Query Errors

```python
def set_filter_text(self, text: str) -> None:
    if self._state.mode == "simple":
        try:
            # Validate simple query syntax
            SimpleQueryParser(text).parse()
        except QuerySyntaxError as e:
            self.filter_error.emit(f"Query syntax error: {e}")
            return
    self._state.text = text
```

---

## §8 Performance

### §8.1 Filter Compilation

Text filters are compiled once and cached:

```python
def _compile_filter(self) -> CompiledFilter | None:
    """Compile the text filter if needed."""
    if not self._state.text:
        return None
    
    if self._state.mode == "plain":
        return FilterEngine.compile_plain(self._state.text)
    elif self._state.mode == "regex":
        return FilterEngine.compile_regex(self._state.text)
    elif self._state.mode == "simple":
        return FilterEngine.compile_simple(self._state.text)
```

### §8.2 Filter Application Performance

| Entries | Text Filter | Category Filter | Counter Filter | Total |
|---------|-------------|-----------------|---------------|-------|
| 100K | ~5ms | ~2ms | ~1ms | ~8ms |
| 1M | ~50ms | ~20ms | ~10ms | ~80ms |
| 10M | ~500ms | ~200ms | ~100ms | ~800ms |

---

## §9 Testing

### §9.1 Unit Tests

```python
def test_filter_controller_text_filter(filter_controller):
    """Test text filter application."""
    entries = [
        create_entry("error", message="Error message"),
        create_entry("info", message="Info message"),
    ]
    
    filter_controller.set_filter_text("error")
    filter_controller.set_filter_mode("plain")
    
    filtered = filter_controller.apply_filter(entries)
    
    assert len(filtered) == 1
    assert filtered[0].message == "Error message"

def test_filter_controller_category_filter(filter_controller):
    """Test category filter application."""
    entries = [
        create_entry("info", category="System.Network"),
        create_entry("info", category="System.IO"),
    ]
    
    filter_controller.set_category_states({
        "System": True,
        "System.Network": True,
        "System.IO": False,
    })
    
    filtered = filter_controller.apply_filter(entries)
    
    assert len(filtered) == 1
    assert filtered[0].category == "System.Network"

def test_filter_controller_combined(filter_controller):
    """Test combined filter application."""
    entries = [
        create_entry("error", category="System.Network", message="Error in network"),
        create_entry("error", category="System.IO", message="Error in IO"),
        create_entry("info", category="System.Network", message="Info in network"),
    ]
    
    filter_controller.set_filter_text("network")
    filter_controller.set_category_states({"System.Network": True, "System.IO": False})
    filter_controller.set_counter_states({"error": True, "info": False})
    
    filtered = filter_controller.apply_filter(entries)
    
    assert len(filtered) == 1
    assert filtered[0].category == "System.Network"
    assert filtered[0].level.name == "ERROR"
```

---

## §10 Cross-References

- **Filter Engine:** [filter-engine.md](filter-engine.md)
- **Category Tree:** [category-tree.md](category-tree.md)
- **Main Controller:** [main-controller.md](main-controller.md)
- **Error Handling:** [../global/error-handling.md](../global/error-handling.md)

---

## §11 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial filter controller specification |