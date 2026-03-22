# Timestamp Unix Epoch Storage Specification

**Version:** 1.0
**Last Updated:** 2026-03-21
**Project Context:** Python Tooling (Desktop Application)
**Status:** [IMPLEMENTED]

---

## §1 Overview

This specification defines the change from string-based timestamp storage to Unix Epoch (float) in [`LogEntry`](../../src/models/log_entry.py:20), with display formatting in the table view and tooltip.

### §1.1 Problem Statement

Current implementation stores timestamps as strings:
- **Memory overhead**: String storage is inefficient (~20-30 bytes per timestamp)
- **No date context**: Users see only time in table, but can't see the full date
- **Inconsistent display**: Tooltip shows same truncated time as table

### §1.2 Requirements

Per user requirements:
1. **Store as Unix Epoch**: Convert timestamp string to `float` (Unix timestamp with milliseconds)
2. **Table display**: Show only `H:M:S.MS` format (e.g., `15:30:45.123`)
3. **Tooltip on hover**: Show full date and time (e.g., `2026-03-10 15:30:45.123`)

### §1.3 Goals

1. Reduce memory footprint for timestamp storage
2. Provide date context via tooltip
3. Maintain fast display performance
4. Preserve existing log format compatibility

---

## §2 Current Implementation

### §2.1 LogEntry Model

**File:** [`src/models/log_entry.py`](../../src/models/log_entry.py:20)

```python
@dataclass(frozen=True)
class LogEntry:
    row_index: int
    timestamp: str        # CURRENT: String storage
    category: str
    display_message: str
    level: LogLevel
    file_offset: int
```

### §2.2 LogEntryDisplay Adapter

**File:** [`src/views/log_table_view.py`](../../src/views/log_table_view.py:66)

```python
@dataclass
class LogEntryDisplay:
    category: str
    time: str            # CURRENT: Time string extracted from timestamp
    level: LogLevel
    message: str
    file_offset: int
    
    @classmethod
    def from_log_entry(cls, entry) -> "LogEntryDisplay":
        # Extracts time part from timestamp string
        time_str = entry.timestamp
        if " " in time_str:
            time_str = time_str.split(" ")[-1]
        ...
```

### §2.3 Log Format

**File:** [`src/core/parser.py`](../../src/core/parser.py:36)

Log format: `DD-MM-YYYYTHH:MM:SS.MS Category [LEVEL] Message`

Example: `10-03-2026T15:30:45.123 HordeMode LOG_ERROR Connection failed`

---

## §3 Proposed Implementation

### §3.1 LogEntry Model Changes

**File:** [`src/models/log_entry.py`](../../src/models/log_entry.py:20)

```python
@dataclass(frozen=True)
class LogEntry:
    """Immutable log entry data.
    
    Ref: docs/specs/features/log-entry-optimization.md §4.3
    Memory: raw_line removed (Phase 3) - lazy loaded via LogDocument.get_raw_line()
    
    Timestamp stored as Unix Epoch (float) for memory efficiency.
    """
    row_index: int
    timestamp: float      # NEW: Unix Epoch with milliseconds
    category: str
    display_message: str
    level: LogLevel
    file_offset: int
```

**Memory Savings:**
- String timestamp: ~20-30 bytes
- Float timestamp: 8 bytes
- **Savings: ~12-22 bytes per entry**

### §3.2 Parser Changes

**File:** [`src/core/parser.py`](../../src/core/parser.py:36)

Add timestamp parsing function:

```python
from datetime import datetime

def _parse_timestamp(ts_str: str) -> float:
    """Parse timestamp string to Unix Epoch.
    
    Supported formats:
    - DD-MM-YYYYTHH:MM:SS.MS (e.g., "10-03-2026T15:30:45.123")
    - YYYY-MM-DD HH:MM:SS (e.g., "2024-01-01 12:00:00")
    - HH:MM:SS (e.g., "00:00:00") - uses current date
    
    Args:
        ts_str: Timestamp string from log
        
    Returns:
        Unix timestamp (seconds since epoch with milliseconds)
        
    Raises:
        ValueError: If timestamp format is unrecognized
    """
    # Try DD-MM-YYYYTHH:MM:SS.MS format
    if 'T' in ts_str:
        try:
            # Format: DD-MM-YYYYTHH:MM:SS.MS
            dt = datetime.strptime(ts_str, "%d-%m-%YT%H:%M:%S.%f")
            return dt.timestamp()
        except ValueError:
            pass
    
    # Try YYYY-MM-DD HH:MM:SS format
    if ' ' in ts_str:
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            return dt.timestamp()
        except ValueError:
            pass
    
    # Try HH:MM:SS format (use current date)
    try:
        # Parse time only, combine with today's date
        time_part = datetime.strptime(ts_str, "%H:%M:%S")
        today = datetime.now().replace(
            hour=time_part.hour,
            minute=time_part.minute,
            second=time_part.second
        )
        return today.timestamp()
    except ValueError:
        pass
    
    raise ValueError(f"Unrecognized timestamp format: {ts_str}")


def parse_line(self, line: str, row_index: int, file_offset: int) -> Optional[LogEntry]:
    """Parse a single log line."""
    ...
    
    timestamp_str = parts[0]
    timestamp = self._parse_timestamp(timestamp_str)  # Convert to Unix Epoch
    
    ...
    
    return LogEntry(
        row_index=row_index,
        timestamp=timestamp,  # Now a float
        category=category,
        display_message=display_message,
        level=level,
        file_offset=file_offset
    )
```

### §3.3 LogEntryDisplay Changes

**File:** [`src/views/log_table_view.py`](../../src/views/log_table_view.py:66)

```python
from datetime import datetime

@dataclass
class LogEntryDisplay:
    """Display model for log entry in the new UI.
    
    Ref: docs/specs/features/selection-preservation.md §3.3
    Ref: docs/specs/features/log-entry-optimization.md §4.3
    Master: docs/SPEC.md §1
    """
    category: str
    time: str            # H:M:S.MS format for table display
    time_full: str       # Full date-time for tooltip
    level: LogLevel
    message: str
    file_offset: int
    
    @property
    def level_icon(self) -> str:
        """Get the icon character for the level."""
        config = LOG_LEVEL_CONFIGS.get(self.level)
        return config.icon if config else "?"
    
    @classmethod
    def from_log_entry(cls, entry) -> "LogEntryDisplay":
        """Create a display entry from a real LogEntry.
        
        Args:
            entry: LogEntry from src.models.log_entry (timestamp is Unix Epoch float)
            
        Returns:
            LogEntryDisplay instance.
        """
        from src.models.log_entry import LogLevel as RealLogLevel
        
        # Map real log level to display log level
        level_map = {
            RealLogLevel.CRITICAL: LogLevel.CRITICAL,
            RealLogLevel.ERROR: LogLevel.ERROR,
            RealLogLevel.WARNING: LogLevel.WARNING,
            RealLogLevel.MSG: LogLevel.MSG,
            RealLogLevel.DEBUG: LogLevel.DEBUG,
            RealLogLevel.TRACE: LogLevel.TRACE,
        }
        
        # Convert Unix Epoch to datetime
        dt = datetime.fromtimestamp(entry.timestamp)
        
        # Format for table: H:M:S.MS
        time_str = dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        
        # Format for tooltip: YYYY-MM-DD H:M:S.MS
        time_full = dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        
        display_level = level_map.get(entry.level, LogLevel.MSG)
        
        return cls(
            category=entry.category if entry.category else "",
            time=time_str,
            time_full=time_full,
            level=display_level,
            message=entry.display_message,
            file_offset=entry.file_offset
        )
```

### §3.4 Table Model Changes

**File:** [`src/views/log_table_view.py`](../../src/views/log_table_view.py:138)

Update `data()` method for tooltip:

```python
def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object:
    """Return data for display and decoration."""
    if not index.isValid() or index.row() >= len(self._entries):
        return None

    entry = self._entries[index.row()]
    col = index.column()

    if role == Qt.DisplayRole:
        if col == self.COL_TIME:
            return entry.time  # H:M:S.MS
        elif col == self.COL_CATEGORY:
            return entry.category
        elif col == self.COL_TYPE:
            return entry.level_icon
        elif col == self.COL_MESSAGE:
            return entry.message

    elif role == Qt.ToolTipRole:
        if col == self.COL_TIME:
            # Show full date-time in tooltip
            return entry.time_full  # YYYY-MM-DD H:M:S.MS
        elif col == self.COL_MESSAGE:
            return entry.message
        elif col == self.COL_CATEGORY:
            return entry.category
        return None

    # ... rest unchanged ...
```

---

## §4 Memory Impact

### §4.1 Per-Entry Savings

| Field | Original | Optimized | Savings |
|-------|----------|-----------|---------|
| `timestamp` | ~20-30 bytes (str) | 8 bytes (float) | **~12-22 bytes** |

### §4.2 Total Memory (10M Entries)

| Metric | Original | Optimized | Savings |
|--------|----------|-----------|---------|
| Timestamp storage | ~200-300 MB | ~80 MB | **~120-220 MB** |

---

## §5 Performance Impact

### §5.1 Parsing (One-time Cost)

| Operation | Original | Optimized | Impact |
|-----------|----------|-----------|--------|
| Parse line | String split | String split + datetime parse | **+5-10µs per line** |

**Acceptable:** Parsing happens once at file load.

### §5.2 Display (Hot Path)

| Operation | Original | Optimized | Impact |
|-----------|----------|-----------|--------|
| Table cell | String substring | datetime format | **+2-5µs per cell** |

**Acceptable:** Only for visible rows (~50 rows), not all entries.

### §5.3 Tooltip (On-demand)

| Operation | Original | Optimized | Impact |
|-----------|----------|-----------|--------|
| Tooltip | String display | Pre-computed string | **No overhead** |

**Optimized:** `time_full` is computed once at entry creation.

---

## §6 API Compatibility

### §6.1 Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| `LogEntry.timestamp` type | `str` → `float` | Use `datetime.fromtimestamp()` for display |
| `LogEntryDisplay.time_full` | New field | N/A (addition) |

### §6.2 Non-Breaking Changes

- `LogEntryDisplay.time` still returns string (format changed to `H:M:S.MS`)
- `LogEntryDisplay.from_log_entry()` signature unchanged
- Table display API unchanged

---

## §7 Test Updates Required

### §7.1 Parser Tests

**File:** [`tests/test_parser.py`](../../tests/test_parser.py)

```python
def test_parse_timestamp_as_epoch():
    """Test that timestamp is parsed to Unix Epoch."""
    line = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR Test"
    entry = parser.parse_line(line, row_index=0, file_offset=0)
    
    # Verify timestamp is a float
    assert isinstance(entry.timestamp, float)
    
    # Verify correct conversion
    from datetime import datetime
    expected = datetime(2026, 3, 10, 15, 30, 45, 123000).timestamp()
    assert abs(entry.timestamp - expected) < 0.001
```

### §7.2 Display Tests

**File:** [`tests/test_log_table_view.py`](../../tests/test_log_table_view.py)

```python
def test_time_display_format():
    """Test that time column shows H:M:S.MS format."""
    from datetime import datetime
    
    # Create entry with known timestamp
    dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
    entry = LogEntry(
        row_index=0,
        timestamp=dt.timestamp(),
        category="Test",
        display_message="Message",
        level=LogLevel.MSG,
        file_offset=0
    )
    
    display = LogEntryDisplay.from_log_entry(entry)
    
    # Table display: H:M:S.MS
    assert display.time == "15:30:45.123"
    
    # Tooltip: full date-time
    assert display.time_full == "2026-03-10 15:30:45.123"
```

---

## §8 Implementation Checklist

- [ ] Update `LogEntry.timestamp` from `str` to `float`
- [ ] Add `_parse_timestamp()` function to parser
- [ ] Update parser to convert timestamp string to Unix Epoch
- [ ] Add `time_full` field to `LogEntryDisplay`
- [ ] Update `LogEntryDisplay.from_log_entry()` to format time
- [ ] Update table model tooltip for time column
- [ ] Update parser tests for Unix Epoch
- [ ] Update display tests for time format
- [ ] Run full test suite
- [ ] Benchmark memory usage before/after

---

## §9 Cross-References

- **LogEntry Model:** [log_entry.py](../../src/models/log_entry.py)
- **Parser:** [parser.py](../../src/core/parser.py)
- **Table View:** [log_table_view.py](../../src/views/log_table_view.py)
- **Memory Model:** [memory-model.md](../global/memory-model.md)
- **Log Entry Optimization:** [log-entry-optimization.md](log-entry-optimization.md)

---

## §10 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial specification for Unix Epoch timestamp storage |