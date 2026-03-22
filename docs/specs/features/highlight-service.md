# Highlight Service Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The Highlight Service manages user-defined highlight patterns for log entries. It coordinates with the Highlight Engine to apply visual highlighting to matching text in the log table.

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    HighlightService                            │
│  - Manage user highlight patterns                             │
│  - Coordinate with HighlightEngine                            │
│  - Persist patterns to settings                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       │                                       │
       ▼                                       ▼
┌─────────────────┐                   ┌─────────────────┐
│  HighlightEngine│                   │ SettingsManager │
│    (Core)       │                   │    (Utils)      │
└─────────────────┘                   └─────────────────┘
```

### §2.2 Service Synchronization Architecture

**Important:** The `LogTableView` maintains its own local `_highlight_service` instance for rendering. When highlight patterns change in the `MainController`'s `HighlightService`, the controller must propagate the changes to `LogTableView` via `set_highlight_engine()`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MainController                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  _highlight_service: HighlightService                            │    │
│  │  - Manages user patterns                                         │    │
│  │  - Provides get_combined_engine()                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ set_highlight_engine(get_combined_engine())
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LogTableView                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  _highlight_service: HighlightService (local copy)               │    │
│  │  - Used by HighlightDelegate for rendering                      │    │
│  │  - Updated via set_highlight_engine()                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
1. `MainController._highlight_service` is the source of truth for highlight patterns
2. `LogTableView._highlight_service` is a local copy used by the delegate
3. Changes must be propagated via `set_highlight_engine()`, not `refresh_highlighting()`
4. `refresh_highlighting()` only triggers a repaint but does NOT update the patterns

### §2.2 Dependencies

```python
from src.core.highlight_engine import HighlightEngine, HighlightPattern
from src.utils.settings_manager import SettingsManager
from PySide6.QtGui import QColor
```

---

## §3 Responsibilities

### §3.1 Pattern Management

- Add, remove, and update highlight patterns
- Store patterns with text, color, and regex flag
- Validate patterns before adding

### §3.2 Engine Coordination

- Sync patterns with `HighlightEngine`
- Provide engine to views for rendering

### §3.3 Persistence

- Load patterns from settings on startup
- Save patterns to settings on changes

---

## §4 API Reference

### §4.1 Class Definition

```python
class HighlightService(QObject):
    """Service for managing highlight patterns."""
    
    # Signals
    patterns_changed = Signal()  # Emitted when patterns change
    
    @beartype
    def __init__(self, settings_manager: SettingsManager | None = None,
                 parent: QObject | None = None) -> None:
        """
        Initialize the highlight service.
        
        Args:
            settings_manager: Optional settings manager for persistence
            parent: Parent QObject
        """
```

### §4.2 Pattern Operations

```python
@beartype
def add_pattern(self, text: str, color: QColor, 
                is_regex: bool = False) -> bool:
    """
    Add a highlight pattern.
    
    Args:
        text: Pattern text (plain text or regex)
        color: Highlight color
        is_regex: Whether text is a regex pattern
        
    Returns:
        True if pattern was added, False if invalid
    """

@beartype
def remove_pattern(self, text: str) -> bool:
    """
    Remove a highlight pattern.
    
    Args:
        text: Pattern text to remove
        
    Returns:
        True if pattern was removed, False if not found
    """

def clear_patterns(self) -> None:
    """Remove all highlight patterns."""

@beartype
def update_pattern(self, old_text: str, new_text: str, 
                   color: QColor, is_regex: bool = False) -> bool:
    """
    Update an existing pattern.
    
    Args:
        old_text: Text of pattern to update
        new_text: New pattern text
        color: New highlight color
        is_regex: Whether new text is a regex pattern
        
    Returns:
        True if pattern was updated, False if not found
    """

def get_patterns(self) -> list[HighlightPattern]:
    """
    Get all highlight patterns.
    
    Returns:
        List of HighlightPattern objects
    """

@beartype
def has_pattern(self, text: str) -> bool:
    """
    Check if a pattern exists.
    
    Args:
        text: Pattern text to check
        
    Returns:
        True if pattern exists
    """
```

### §4.3 Engine Access

```python
def get_engine(self) -> HighlightEngine:
    """
    Get the highlight engine.
    
    Returns:
        The HighlightEngine instance
    """

def get_highlighter(self) -> callable:
    """
    Get a highlighter function for use in delegates.
    
    Returns:
        Function that takes text and returns list of highlight ranges
    """
```

### §4.4 Persistence

```python
def load_from_settings(self) -> None:
    """Load patterns from settings manager."""

def save_to_settings(self) -> None:
    """Save patterns to settings manager."""
```

---

## §5 Pattern Model

### §5.1 HighlightPattern

```python
@dataclass
class HighlightPattern:
    """A highlight pattern for log entries."""
    
    text: str              # Pattern text
    color: QColor          # Highlight color
    is_regex: bool = False # Whether text is a regex
    
    @beartype
    def __post_init__(self) -> None:
        """Validate pattern after initialization."""
        if not self.text:
            raise ValueError("Pattern text cannot be empty")
        
        if self.is_regex:
            try:
                re.compile(self.text)
            except re.error as e:
                raise ValueError(f"Invalid regex: {e}")
    
    def matches(self, text: str) -> bool:
        """
        Check if pattern matches text.
        
        Args:
            text: Text to check
            
        Returns:
            True if pattern matches
        """
        if self.is_regex:
            return bool(re.search(self.text, text))
        return self.text in text
    
    def get_ranges(self, text: str) -> list[tuple[int, int]]:
        """
        Get highlight ranges for text.
        
        Args:
            text: Text to search
            
        Returns:
            List of (start, end) tuples for matches
        """
```

### §5.2 Pattern Data for Persistence

```python
@dataclass
class PatternData:
    """Pattern data for serialization."""
    text: str
    color: str      # Hex color string
    is_regex: bool
    
    @classmethod
    def from_pattern(cls, pattern: HighlightPattern) -> PatternData:
        """Create from HighlightPattern."""
        return cls(
            text=pattern.text,
            color=pattern.color.name(),
            is_regex=pattern.is_regex,
        )
    
    def to_pattern(self) -> HighlightPattern:
        """Convert to HighlightPattern."""
        return HighlightPattern(
            text=self.text,
            color=QColor(self.color),
            is_regex=self.is_regex,
        )
```

---

## §6 Highlight Engine

### §6.1 Engine Interface

```python
class HighlightEngine:
    """Engine for applying highlights to text."""
    
    def __init__(self) -> None:
        """Initialize the engine."""
        self._patterns: list[HighlightPattern] = []
        self._compiled: dict[str, re.Pattern] = {}
    
    @beartype
    def add_pattern(self, pattern: HighlightPattern) -> None:
        """Add a highlight pattern."""
        self._patterns.append(pattern)
        if pattern.is_regex:
            self._compiled[pattern.text] = re.compile(pattern.text)
    
    @beartype
    def remove_pattern(self, text: str) -> bool:
        """Remove a pattern by text."""
        for i, p in enumerate(self._patterns):
            if p.text == text:
                self._patterns.pop(i)
                self._compiled.pop(text, None)
                return True
        return False
    
    def clear_patterns(self) -> None:
        """Clear all patterns."""
        self._patterns.clear()
        self._compiled.clear()
    
    @beartype
    def highlight(self, text: str) -> list[tuple[int, int, QColor]]:
        """
        Get highlight ranges for text.
        
        Args:
            text: Text to highlight
            
        Returns:
            List of (start, end, color) tuples
        """
        ranges = []
        for pattern in self._patterns:
            if pattern.is_regex:
                regex = self._compiled[pattern.text]
                for match in regex.finditer(text):
                    ranges.append((match.start(), match.end(), pattern.color))
            else:
                start = 0
                while True:
                    pos = text.find(pattern.text, start)
                    if pos == -1:
                        break
                    ranges.append((pos, pos + len(pattern.text), pattern.color))
                    start = pos + 1
        return ranges
```

---

## §7 Error Handling

### §7.1 Invalid Pattern

```python
def add_pattern(self, text: str, color: QColor, is_regex: bool = False) -> bool:
    """Add pattern with validation."""
    if not text or not text.strip():
        logger.warning("Cannot add empty pattern")
        return False
    
    if is_regex:
        try:
            re.compile(text)
        except re.error as e:
            logger.warning(f"Invalid regex pattern: {e}")
            return False
    
    pattern = HighlightPattern(text=text, color=color, is_regex=is_regex)
    self._engine.add_pattern(pattern)
    self.patterns_changed.emit()
    return True
```

### §7.2 Duplicate Pattern

```python
def add_pattern(self, text: str, color: QColor, is_regex: bool = False) -> bool:
    """Add pattern with duplicate check."""
    if self.has_pattern(text):
        logger.info(f"Pattern already exists: {text}")
        return False
    
    # ... add pattern
```

---

## §8 Performance

### §8.1 Pattern Matching

| Patterns | Text Length | Match Time |
|----------|-------------|------------|
| 1 | 100 chars | <0.1ms |
| 10 | 100 chars | <0.5ms |
| 100 | 100 chars | <5ms |
| 10 | 10,000 chars | <5ms |

### §8.2 Optimization

- Regex patterns are compiled once and cached
- Plain text patterns use `str.find()` for efficiency
- Highlight ranges are computed on-demand during paint

---

## §9 Testing

### §9.1 Unit Tests

```python
def test_highlight_service_add_pattern(highlight_service):
    """Test adding a pattern."""
    result = highlight_service.add_pattern("error", QColor("red"))
    
    assert result is True
    assert highlight_service.has_pattern("error")

def test_highlight_service_regex_pattern(highlight_service):
    """Test adding a regex pattern."""
    result = highlight_service.add_pattern(
        r"error:\s+\w+", 
        QColor("red"), 
        is_regex=True
    )
    
    assert result is True
    
    engine = highlight_service.get_engine()
    ranges = engine.highlight("error: test message")
    
    assert len(ranges) == 1
    assert ranges[0][0] == 0
    assert ranges[0][1] == 10

def test_highlight_service_invalid_regex(highlight_service):
    """Test adding an invalid regex pattern."""
    result = highlight_service.add_pattern(
        r"error[", 
        QColor("red"), 
        is_regex=True
    )
    
    assert result is False
    assert not highlight_service.has_pattern("error[")

def test_highlight_service_persistence(highlight_service, settings_manager):
    """Test pattern persistence."""
    highlight_service.add_pattern("error", QColor("red"))
    highlight_service.save_to_settings()
    
    # Create new service
    new_service = HighlightService(settings_manager)
    new_service.load_from_settings()
    
    assert new_service.has_pattern("error")
```

---

## §10 Cross-References

- **Main Controller:** [main-controller.md](main-controller.md)
- **Settings Manager:** [settings-manager.md](settings-manager.md)
- **Highlight Panel UI:** [highlight-panel.md](highlight-panel.md)
- **Error Handling:** [../global/error-handling.md](../global/error-handling.md)

---

## §11 Synchronization with LogTableView

### §11.1 Pattern Update Propagation

When highlight patterns change, the `MainController` must propagate the updated engine to `LogTableView`:

```python
# CORRECT: Update the engine reference
self._window.get_log_table().set_highlight_engine(
    self._highlight_service.get_combined_engine()
)

# INCORRECT: Only triggers repaint, patterns not updated
self._window.get_log_table().refresh_highlighting()
```

### §11.2 When to Use Each Method

| Method | Purpose | When to Use |
|--------|---------|-------------|
| `set_highlight_engine()` | Update the highlight engine reference | Pattern add/remove/edit, enabled state change |
| `refresh_highlighting()` | Trigger repaint with existing engine | View refresh, scroll, filter change |

---

## §12 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-17 | Added service synchronization architecture, LogTableView propagation requirements |
| 1.0 | 2026-03-13 | Initial highlight service specification |