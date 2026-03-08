# Filter Engine Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)  
**Related:** [category-checkbox-behavior.md](category-checkbox-behavior.md)

---

## §1 Overview

The Filter Engine provides high-performance filtering of log entries based on categories, text patterns, and log levels. It compiles filter criteria into callable functions for efficient repeated evaluation.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FilterController                          │
│  - Manages FilterState                                        │
│  - Coordinates with CategoryTree                              │
│  - Emits signals on filter changes                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FilterEngine                             │
│  - Compiles filters to callable                               │
│  - Caches regex patterns                                      │
│  - Combines category + text + level filters                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Compiled Filter                             │
│  Callable[[LogEntry], bool]                                   │
│  - Fast evaluation (no re-compilation)                        │
│  - Combined AND/OR logic                                      │
└─────────────────────────────────────────────────────────────┘
```

### §2.2 Dependencies

```python
from src.models.filter_state import FilterState, FilterMode
from src.models.log_entry import LogEntry, LogLevel
from src.core.category_tree import CategoryTree
from src.core.simple_query_parser import SimpleQueryParser
from src.utils.settings_manager import CustomCategory
```

---

## §3 Filter Types

### §3.1 Category Filter

Filters log entries by their category path with hierarchical support.

**Visibility Rule (per [category-checkbox-behavior.md](category-checkbox-behavior.md) §4.1):**
```
log_visible(category) = category.checked OR any_ancestor.checked
```

**Implementation:**
```python
def _compile_category_filter(
    self,
    enabled_categories: set[str],
    all_categories: set[str],
    category_tree: CategoryTree | None = None
) -> Callable[[LogEntry], bool] | None:
    """
    Compile category filter.
    
    When category_tree is provided, uses is_category_visible() for
    correct ancestor-based visibility checking.
    
    Returns None if all categories are enabled (no filtering needed).
    """
```

### §3.2 Custom Category Filter

Filters by message content (substring match), not by log category path.

```python
def _compile_custom_category_filter(
    self,
    custom_categories: list[CustomCategory],
    enabled_categories: set[str]
) -> Callable[[LogEntry], bool] | None:
    """
    Compile custom category filter.
    
    Custom categories filter by message content (substring match).
    Parent inheritance: custom category is active only if parent is enabled.
    """
```

### §3.3 Text Filter

Three modes supported:

| Mode | Description | Example |
|------|-------------|---------|
| `PLAIN` | Case-insensitive substring | `"error"` matches "Error: failed" |
| `REGEX` | Regular expression | `"error\d+"` matches "error123" |
| `SIMPLE` | Simple query language | `"\`error\` and not \`warning\`"` |

```python
def _compile_text_filter(
    self,
    text: str,
    mode: FilterMode
) -> Callable[[LogEntry], bool] | None:
    """Compile text filter based on mode."""
```

### §3.4 Level Filter

Filters by log level (CRITICAL, ERROR, WARNING, MSG, DEBUG, TRACE).

```python
def _compile_level_filter(
    self,
    enabled_levels: set[str]
) -> Callable[[LogEntry], bool] | None:
    """
    Compile level filter.
    
    Returns None if all levels are enabled (no filtering needed).
    Returns lambda entry: False if no levels enabled.
    """
```

---

## §4 Filter Combination Logic

### §4.1 Combination Rules

```
Final Filter = (Category OR Custom) AND Text AND Level

Where:
- Category filter: enabled categories with ancestor visibility
- Custom filter: substring match on message content
- Text filter: plain/regex/simple search
- Level filter: enabled log levels
```

### §4.2 Special Cases

| Category | Custom | Text | Level | Result |
|----------|--------|------|-------|--------|
| All enabled | None | None | All | Match all (no filter) |
| None enabled | None | None | All | Match none |
| None enabled | Active | None | All | Match custom only |
| All enabled | Active | None | All | Match all (category OR custom) |
| Partial | None | Active | All | (Category) AND (Text) |
| Partial | Active | Active | Partial | (Category OR Custom) AND (Text) AND (Level) |

### §4.3 Implementation

```python
def compile_filter(
    self,
    state: FilterState,
    category_tree: CategoryTree | None = None
) -> Callable[[LogEntry], bool]:
    """
    Compile a filter from state.
    
    Combines:
    1. Category filter (with visibility-based logic)
    2. Custom category filter (OR with category)
    3. Text filter (AND with category/custom)
    4. Level filter (AND with others)
    """
    # Build individual filters
    category_filter = self._compile_category_filter(...)
    custom_filter = self._compile_custom_category_filter(...)
    text_filter = self._compile_text_filter(...)
    level_filter = self._compile_level_filter(...)
    
    # Combine with OR for category/custom
    # Combine with AND for text/level
    # ...
```

---

## §5 Performance

### §5.1 Regex Caching

```python
class FilterEngine:
    def __init__(self):
        self._regex_cache: dict[str, re.Pattern] = {}
    
    def _compile_regex_filter(self, pattern: str) -> Callable[[LogEntry], bool]:
        # Check cache
        if pattern in self._regex_cache:
            compiled = self._regex_cache[pattern]
        else:
            compiled = re.compile(pattern)
            self._regex_cache[pattern] = compiled
        # ...
    
    def clear_cache(self) -> None:
        """Clear regex cache."""
        self._regex_cache.clear()
    
    def get_cache_size(self) -> int:
        """Get number of cached patterns."""
        return len(self._regex_cache)
```

**Cache Limits:**
- Default: Unlimited (clear manually)
- Recommended: Clear on file close

### §5.2 Filter Compilation

**Cost:** O(n) where n = number of filter criteria  
**Benefit:** Compiled filter is O(1) per call

```python
# Expensive: Compile once
filter_func = engine.compile_filter(state, category_tree)

# Cheap: Evaluate many times
for entry in entries:
    if filter_func(entry):
        filtered.append(entry)
```

### §5.3 Memory Budget

| Component | Memory | Notes |
|-----------|--------|-------|
| Regex cache | ~1KB per pattern | Clear on file close |
| Compiled filter | ~1KB | Lambda closure |
| Category tree | ~100 bytes per category | Owned by controller |

---

## §6 API Reference

### §6.1 FilterEngine

```python
class FilterEngine:
    def __init__(self) -> None:
        """Initialize filter engine with empty cache."""
    
    @beartype
    def compile_filter(
        self,
        state: FilterState,
        category_tree: CategoryTree | None = None
    ) -> Callable[[LogEntry], bool]:
        """
        Compile a filter from state.
        
        Args:
            state: Filter state with enabled categories, filter text, mode, levels
            category_tree: Optional CategoryTree for visibility-based filtering
        
        Returns:
            Callable that returns True if entry matches filter
        """
    
    @beartype
    def validate_filter(
        self,
        text: str,
        mode: FilterMode
    ) -> tuple[bool, str]:
        """
        Validate a filter without compiling.
        
        Args:
            text: Filter text
            mode: Filter mode
        
        Returns:
            Tuple of (is_valid, error_message)
        """
    
    def clear_cache(self) -> None:
        """Clear regex pattern cache."""
    
    def get_cache_size(self) -> int:
        """Get number of cached regex patterns."""
```

### §6.2 FilterState

```python
@dataclass
class FilterState:
    """Mutable filter state."""
    enabled_categories: Set[str] = field(default_factory=set)
    filter_text: str = ""
    filter_mode: FilterMode = FilterMode.PLAIN
    custom_categories: List[CustomCategory] = field(default_factory=list)
    all_categories: Set[str] = field(default_factory=set)
    enabled_levels: Set[str] = field(default_factory=lambda: {
        "LOG_CRITICAL", "LOG_ERROR", "LOG_WARNING", "LOG_MSG", "LOG_DEBUG", "LOG_TRACE"
    })
```

### §6.3 FilterMode

```python
class FilterMode(Enum):
    """Filter mode enumeration."""
    PLAIN = "plain"    # Case-insensitive substring
    REGEX = "regex"    # Regular expression
    SIMPLE = "simple"  # Simple query language
```

---

## §7 Simple Query Language

### §7.1 Syntax

```
query      ::= term (operator term)*
operator   ::= "and" | "or" | "not"
term       ::= "`" text "`" | "(" query ")"
```

### §7.2 Examples

| Query | Matches |
|-------|---------|
| `"\`error\`"` | Lines containing "error" |
| `"\`error\` and \`failed\`"` | Lines with both "error" and "failed" |
| `"\`error\` or \`warning\`"` | Lines with "error" or "warning" |
| `"not \`debug\`"` | Lines not containing "debug" |
| `"\`error\` and not \`trace\`"` | Lines with "error" but not "trace" |

### §7.3 Implementation

```python
class SimpleQueryParser:
    def compile(self, query: str) -> Callable[[LogEntry], bool]:
        """
        Compile a simple query to a filter function.
        
        Args:
            query: Query string like "`error` and not `warning`"
        
        Returns:
            Callable that returns True if entry matches query
        
        Raises:
            ValueError: If query is malformed
        """
```

---

## §8 Thread Safety

### §8.1 Thread Safety Guarantees

| Component | Thread-Safe? | Notes |
|-----------|--------------|-------|
| `FilterEngine` | Yes | Immutable after compilation |
| `FilterState` | No | Owned by single thread |
| `CategoryTree` | No | Owned by single thread |
| Compiled filter | Yes | Read-only callable |

### §8.2 Usage Pattern

```python
# Main thread: Compile filter
filter_func = engine.compile_filter(state, category_tree)

# Background thread: Apply filter (safe)
filtered = [e for e in entries if filter_func(e)]

# Main thread: Update UI
self._window.set_entries(filtered)
```

---

## §9 Error Handling

### §9.1 Validation Before Compilation

```python
# Always validate first
is_valid, error_msg = engine.validate_filter(text, mode)

if not is_valid:
    # Show error to user
    self.filter_error.emit(error_msg)
    return False

# Safe to compile
filter_func = engine.compile_filter(state)
```

### §9.2 Error Types

| Error | Cause | Recovery |
|-------|-------|----------|
| `re.error` | Invalid regex pattern | Show error, clear filter |
| `ValueError` | Malformed simple query | Show error, clear filter |
| `TypeError` | Invalid state type | Log error, use defaults |

---

## §10 Testing

### §10.1 Unit Tests

```python
def test_category_filter():
    """Test category filter with ancestor visibility."""
    tree = CategoryTree()
    tree.add_category("HordeMode/scripts/app")
    tree.add_category("HordeMode/scripts/core")
    tree.toggle("HordeMode/scripts", False)  # Disable parent
    
    # Child should still be visible via ancestor
    assert tree.is_category_visible("HordeMode/scripts/app") == False
    assert tree.is_category_visible("HordeMode") == True

def test_text_filter_plain():
    """Test plain text filter."""
    engine = FilterEngine()
    state = FilterState(filter_text="error", filter_mode=FilterMode.PLAIN)
    filter_func = engine.compile_filter(state)
    
    entry = create_entry(message="An error occurred")
    assert filter_func(entry) == True

def test_filter_combination():
    """Test combined filters."""
    # Category OR Custom AND Text AND Level
    pass
```

### §10.2 Integration Tests

See [test_filter_engine.py](../../tests/test_filter_engine.py)

---

## §11 Cross-References

- **Category Tree:** [category-checkbox-behavior.md](category-checkbox-behavior.md)
- **Category Tree API:** [category-tree.md](category-tree.md)
- **Filter Controller:** [filter-controller.md](filter-controller.md)
- **Memory Model:** [../global/memory-model.md](../global/memory-model.md)

---

## §12 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial filter engine specification |