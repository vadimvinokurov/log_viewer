# LogEntry Memory Optimization Specification

**Version:** 2.0
**Last Updated:** 2026-03-18
**Project Context:** Python Tooling (Desktop Application)
**Status:** [DRAFT]

---

## §1 Overview

This specification defines memory optimization strategies for [`LogEntry`](../../src/models/log_entry.py:20) based on usage audit and memory model analysis.

### §1.1 Problem Statement

Current [`LogEntry`](../../src/models/log_entry.py:20) stores redundant string data:

```python
@dataclass(frozen=True)
class LogEntry:
    row_index: int
    timestamp: str
    category: str
    raw_message: str      # REDUNDANT: never used
    display_message: str  # Used for filtering, search, display
    level: LogLevel
    file_offset: int
    raw_line: str         # REDUNDANT: only for clipboard, can load on demand
```

**Memory Impact:**
- Entry size: ~200-500 bytes
- String duplication: 3-4x overhead
- For 10M entries: ~5GB memory

### §1.2 Requirements

Per user requirements:
1. **All filters work on `display_message`** (not `raw_line`)
2. **`raw_line` only needed for clipboard copy**
3. **`raw_line` can be loaded from file on demand** using `file_offset`

### §1.3 Goals

1. Reduce memory footprint by **70-85%**
2. Improve filter/search performance (smaller strings)
3. Maintain clipboard functionality via lazy loading
4. Minimize breaking changes to API

---

## §2 Usage Audit Results

### §2.1 Field Usage Analysis

| Field | Usage Locations | Hot Path | Action |
|-------|-----------------|----------|--------|
| `row_index` | UI display (line number) | No | **KEEP** |
| `timestamp` | Display, sorting | Yes | **KEEP** |
| `category` | Filtering, display | Yes | **INTERN** |
| `raw_message` | **None** | No | **REMOVE** |
| `display_message` | Filter, search, display | **Yes** | **KEEP** |
| `level` | Filtering | Yes | **KEEP** |
| `file_offset` | Selection restore, clipboard | No | **KEEP** |
| `raw_line` | Clipboard only | No | **REMOVE** (lazy load) |

### §2.2 Current Incorrect Usage

**ISSUE:** Current implementation uses `raw_line` for filtering (incorrect per requirements):

| File | Line | Current (Wrong) | Should Be |
|------|------|-----------------|-----------|
| [`filter_engine.py`](../../src/core/filter_engine.py:261) | 261 | `entry.raw_line.lower()` | `entry.display_message.lower()` |
| [`filter_engine.py`](../../src/core/filter_engine.py:288) | 288 | `entry.raw_line` | `entry.display_message` |
| [`simple_query_parser.py`](../../src/core/simple_query_parser.py:209) | 209 | `entry.raw_line.lower()` | `entry.display_message.lower()` |

**Clipboard Usage (Correct, but needs lazy loading):**
- [`log_table_view.py:459`](../../src/views/log_table_view.py:459) - Copy to clipboard

### §2.3 Memory Analysis

**Current Memory per Entry:**
```
raw_line:        ~100-500 bytes  (LARGEST - remove)
raw_message:     ~50-400 bytes   (remove)
display_message: ~40-380 bytes   (keep)
timestamp:       ~20 bytes       (keep)
category:        ~10-50 bytes    (intern)
row_index:       8 bytes         (keep)
file_offset:     8 bytes         (keep)
level:           8 bytes         (keep)
--------------------------------
Total:           ~200-500 bytes
```

**Optimized Memory per Entry:**
```
display_message: ~40-380 bytes   (keep)
timestamp:       ~20 bytes       (keep)
category:        ~10-50 bytes    (interned, shared)
row_index:       8 bytes         (keep)
file_offset:     8 bytes         (keep)
level:           8 bytes         (keep)
--------------------------------
Total:           ~50-150 bytes
```

**Savings: ~150-350 bytes per entry (70-85% reduction)**

---

## §3 Optimization Strategy

### §3.1 Optimized LogEntry Structure

```python
import sys
from dataclasses import dataclass
from enum import Enum

class LogLevel(Enum):
    """Log level enumeration."""
    CRITICAL = "LOG_CRITICAL"
    ERROR = "LOG_ERROR"
    WARNING = "LOG_WARNING"
    MSG = "LOG_MSG"
    DEBUG = "LOG_DEBUG"
    TRACE = "LOG_TRACE"

@dataclass(frozen=True)
class LogEntry:
    """Immutable log entry data (optimized).
    
    Memory footprint: ~50-150 bytes (vs ~200-500 bytes original)
    Savings: 70-85% reduction
    
    Fields:
        row_index: Sequential row number (0-based) - for UI display of line number
        timestamp: Log timestamp string
        category: Interned category string (sys.intern)
        display_message: Message with level prefix removed (used for filtering, search, display)
        level: Parsed log level enum
        file_offset: Byte offset in file for seeking (used for clipboard, selection restore)
    """
    row_index: int           # Sequential index (0 = first line, 1 = second, etc.)
    timestamp: str
    category: str            # sys.intern() applied in parser
    display_message: str     # Used for filtering, search, display
    level: LogLevel
    file_offset: int         # Used to load raw_line on demand for clipboard
```

### §3.2 Removed Fields

| Field | Reason | Replacement |
|-------|--------|-------------|
| `raw_message` | Never used outside parser | N/A |
| `raw_line` | Only for clipboard | Load from file using `file_offset` |

### §3.3 Lazy Raw Line Loading

**New Method in LogDocument:**

```python
class LogDocument:
    def get_raw_line(self, file_offset: int) -> str:
        """Load raw line from file at given byte offset.
        
        Args:
            file_offset: Byte offset in file
            
        Returns:
            Raw line string (original log line)
            
        Raises:
            FileNotFoundError: If file no longer exists
            IOError: If seek fails
        """
        with open(self.filepath, 'rb') as f:
            f.seek(file_offset)
            line_bytes = f.readline()
            return line_bytes.decode('utf-8').rstrip('\r\n')
```

**Usage in Clipboard:**

```python
# In log_table_view.py
def copy_selected(self):
    """Copy selected entries to clipboard."""
    lines = []
    for entry in self.get_selected_entries():
        # Load raw_line on demand
        raw_line = self._document.get_raw_line(entry.file_offset)
        lines.append(raw_line)
    # ... copy to clipboard ...
```

---

## §4 Implementation Plan

### §4.1 Phase 1: String Interning for Categories

**Files to Modify:**
- [`src/core/parser.py`](../../src/core/parser.py:36) - Add `sys.intern()` for category

**Changes:**
```python
# src/core/parser.py
import sys

def parse_line(self, line: str, row_index: int, file_offset: int) -> LogEntry | None:
    # ... existing code ...
    
    # Intern category for memory efficiency
    category = sys.intern(parts[1])
    
    # ... rest unchanged ...
```

**Memory Savings:**
- Per entry: ~10-50 bytes
- For 10M entries: ~100-500 MB

### §4.2 Phase 2: Remove raw_message

**Files to Modify:**
- [`src/models/log_entry.py`](../../src/models/log_entry.py:20) - Remove field
- [`src/core/parser.py`](../../src/core/parser.py:48) - Remove assignment

**Changes:**
```python
# src/models/log_entry.py
@dataclass(frozen=True)
class LogEntry:
    row_index: int
    timestamp: str
    category: str
    # raw_message removed - never used
    display_message: str
    level: LogLevel
    file_offset: int
    # raw_line removed - lazy loaded for clipboard
```

**Memory Savings:**
- Per entry: ~50-400 bytes
- For 10M entries: ~500 MB - 4 GB

### §4.3 Phase 3: Remove raw_line + Fix Filters

**Files to Modify:**
- [`src/models/log_entry.py`](../../src/models/log_entry.py:20) - Remove `raw_line` field
- [`src/core/filter_engine.py`](../../src/core/filter_engine.py:261) - Use `display_message`
- [`src/core/simple_query_parser.py`](../../src/core/simple_query_parser.py:209) - Use `display_message`
- [`src/models/log_document.py`](../../src/models/log_document.py:1) - Add `get_raw_line()` method
- [`src/views/log_table_view.py`](../../src/views/log_table_view.py:459) - Lazy load for clipboard

**Changes:**

```python
# src/core/filter_engine.py
def plain_filter(entry: LogEntry) -> bool:
    return search_text in entry.display_message.lower()  # Changed from raw_line

def regex_filter(entry: LogEntry) -> bool:
    return compiled.search(entry.display_message) is not None  # Changed from raw_line
```

```python
# src/core/simple_query_parser.py
def plain_filter(entry: LogEntry) -> bool:
    return node.text.lower() in entry.display_message.lower()  # Changed from raw_line
```

```python
# src/models/log_document.py
def get_raw_line(self, file_offset: int) -> str:
    """Load raw line from file at given byte offset."""
    with open(self.filepath, 'rb') as f:
        f.seek(file_offset)
        line_bytes = f.readline()
        return line_bytes.decode('utf-8').rstrip('\r\n')
```

```python
# src/views/log_table_view.py
def copy_selected(self):
    """Copy selected entries to clipboard."""
    lines = []
    for entry in self.get_selected_entries():
        # Lazy load raw_line for clipboard
        raw_line = self._document.get_raw_line(entry.file_offset)
        lines.append(raw_line)
    # ... copy to clipboard ...
```

**Memory Savings:**
- Per entry: ~100-500 bytes
- For 10M entries: ~1-5 GB

### §4.4 Phase 4: Update LogEntryDisplay

**Files to Modify:**
- [`src/views/log_table_view.py`](../../src/views/log_table_view.py:78) - Remove `raw_line` from display model

**Changes:**
```python
@dataclass
class LogEntryDisplay:
    """Display model for log entry."""
    category: str
    timestamp: str
    level: LogLevel
    message: str
    file_offset: int  # Used to load raw_line on demand
    # raw_line removed - lazy loaded
```

---

## §5 Memory Budget Comparison

### §5.1 Per-Entry Memory

| Metric | Original | Optimized | Savings |
|--------|----------|-----------|---------|
| Entry size | ~200-500 bytes | ~50-150 bytes | **70-85%** |
| String fields | 5 strings | 3 strings | 40% |
| Largest field | `raw_line` (~100-500 bytes) | `display_message` (~40-380 bytes) | 60-90% |

### §5.2 Total Memory (10M Entries)

| Metric | Original | Optimized | Savings |
|--------|----------|-----------|---------|
| Total memory | ~2-5 GB | ~0.5-1.5 GB | **~1.5-3.5 GB** |
| Peak memory | ~5 GB | ~1.5 GB | **~3.5 GB** |

---

## §6 Performance Impact

### §6.1 Hot Paths (Improved)

| Operation | Original | Optimized | Impact |
|-----------|----------|-----------|--------|
| Text filter | `raw_line` (~100-500 bytes) | `display_message` (~40-380 bytes) | **Faster** (smaller strings) |
| Regex filter | `raw_line` | `display_message` | **Faster** |
| Query search | `raw_line` | `display_message` | **Faster** |
| Category filter | String compare | Interned compare | **Faster** (identity compare) |

### §6.2 Cold Paths (Acceptable)

| Operation | Original | Optimized | Impact |
|-----------|----------|-----------|--------|
| Clipboard copy | In-memory string | File seek + read | **Slower** (but rare) |
| File open | Load all | Load all | Same |

### §6.3 Trade-offs

**Pros:**
- ✅ 70-85% memory reduction
- ✅ Faster filtering and search
- ✅ Faster category comparison (interned strings)
- ✅ Simpler data model

**Cons:**
- ⚠️ Clipboard copy requires file seek (slower, but rare)
- ⚠️ File must exist for clipboard (valid assumption for session)
- ⚠️ Breaking change for `raw_line` field access

---

## §7 API Compatibility

### §7.1 Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| Remove `raw_message` | None (unused) | N/A |
| Remove `raw_line` | Clipboard code | Use `LogDocument.get_raw_line(file_offset)` |
| Filter on `display_message` | None (correct behavior) | N/A |
| Intern `category` | Transparent | N/A |

### §7.2 Non-Breaking Changes

All changes maintain the public API:
- `entry.category` returns string (interned internally)
- `entry.display_message` returns string (unchanged)
- `entry.file_offset` unchanged
- `LogDocument.get_raw_line(file_offset)` - new method

---

## §8 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-------------|
| File not found for clipboard | Low | Medium | Cache raw_line in LogDocument on first load |
| Filter performance regression | Low | High | Benchmark before/after |
| Missing raw_line usage | Low | Medium | Full code audit completed |
| Memory regression | Low | High | Memory profiling |

---

## §9 Implementation Checklist

- [ ] Phase 1: Add `sys.intern(category)` in parser
- [ ] Phase 2: Remove `raw_message` field
- [ ] Phase 3: Remove `raw_line` field
- [ ] Phase 3: Fix filter_engine.py to use `display_message`
- [ ] Phase 3: Fix simple_query_parser.py to use `display_message`
- [ ] Phase 3: Add `LogDocument.get_raw_line(file_offset)` method
- [ ] Phase 3: Update clipboard code to lazy load
- [ ] Phase 4: Update LogEntryDisplay model
- [ ] Testing: Run full test suite
- [ ] Benchmark: Memory usage before/after
- [ ] Benchmark: Filter performance before/after

---

## §10 Cross-References

- **Memory Model:** [memory-model.md](../global/memory-model.md)
- **File Management:** [file-management.md](file-management.md)
- **Filter Engine:** [filter-engine.md](filter-engine.md)
- **LogEntry Implementation:** [log_entry.py](../../src/models/log_entry.py)
- **LogDocument Implementation:** [log_document.py](../../src/models/log_document.py)

---

## §11 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-03-18 | Major revision: remove raw_line, use display_message for filters, lazy load for clipboard |
| 1.0 | 2026-03-18 | Initial optimization specification |