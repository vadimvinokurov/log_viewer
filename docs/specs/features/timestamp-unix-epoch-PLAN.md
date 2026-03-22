# Implementation Plan: Timestamp Unix Epoch Storage

**Feature:** timestamp-unix-epoch
**Spec:** docs/specs/features/timestamp-unix-epoch.md
**Status:** READY FOR DELEGATION
**Created:** 2026-03-21

---

## Overview

Convert timestamp storage from string to Unix Epoch (float) for memory efficiency, with formatted display in table and full date in tooltip.

### Memory Impact
- Per entry: ~12-22 bytes saved
- 10M entries: ~120-220 MB saved

---

## Task Breakdown

### Task T-001: Update LogEntry Model
**Priority:** HIGH (blocking other tasks)
**Estimated Time:** 15 minutes
**Dependencies:** None

📦 TASK DELEGATION
├─ Task ID: T-001
├─ Spec Reference: §3.1 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Engine Core / Models
├─ Scope: src/models/log_entry.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: LogEntry with timestamp: str
│  • Output: LogEntry with timestamp: float
│  • Memory: Stack allocation for float (8 bytes)
├─ Constraints:
│  • Thread context: Main thread (model is immutable)
│  • Memory: Float is 8 bytes vs ~20-30 bytes for string
│  • Performance: No runtime impact (creation only)
├─ Tests Required: Unit tests for LogEntry creation with float timestamp
└─ Dependencies: None

**Changes:**
```python
# src/models/log_entry.py
@dataclass(frozen=True)
class LogEntry:
    row_index: int
    timestamp: float      # Changed from str to float (Unix Epoch)
    category: str
    display_message: str
    level: LogLevel
    file_offset: int
```

---

### Task T-002: Add Timestamp Parser Function
**Priority:** HIGH (blocking T-003)
**Estimated Time:** 30 minutes
**Dependencies:** T-001

📦 TASK DELEGATION
├─ Task ID: T-002
├─ Spec Reference: §3.2 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Engine Core / Parser
├─ Scope: src/core/parser.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: Timestamp string from log line
│  • Output: Unix Epoch float
│  • Memory: No heap allocation for parsing
├─ Constraints:
│  • Thread context: Main thread (during file load)
│  • Performance: +5-10µs per line (acceptable, one-time cost)
│  • Supported formats:
│    - DD-MM-YYYYTHH:MM:SS.MS (primary)
│    - YYYY-MM-DD HH:MM:SS (fallback)
│    - HH:MM:SS (time-only, use current date)
├─ Tests Required: Unit tests for all timestamp formats
└─ Dependencies: T-001 (model change)

**Changes:**
```python
# src/core/parser.py
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
```

---

### Task T-003: Update Parser to Use Unix Epoch
**Priority:** HIGH
**Estimated Time:** 15 minutes
**Dependencies:** T-002

📦 TASK DELEGATION
├─ Task ID: T-003
├─ Spec Reference: §3.2 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Engine Core / Parser
├─ Scope: src/core/parser.py (parse_line method)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: Log line string
│  • Output: LogEntry with float timestamp
├─ Constraints:
│  • Thread context: Main thread (during file load)
│  • Performance: One-time parsing cost
├─ Tests Required: Integration tests with parse_line
└─ Dependencies: T-002 (parser function)

**Changes:**
```python
# src/core/parser.py - parse_line method
def parse_line(self, line: str, row_index: int, file_offset: int) -> Optional[LogEntry]:
    # ... existing code ...
    
    timestamp_str = parts[0]
    timestamp = _parse_timestamp(timestamp_str)  # Convert to Unix Epoch
    
    # ... rest unchanged ...
    
    return LogEntry(
        row_index=row_index,
        timestamp=timestamp,  # Now a float
        category=category,
        display_message=display_message,
        level=level,
        file_offset=file_offset
    )
```

---

### Task T-004: Update LogEntryDisplay Model
**Priority:** HIGH
**Estimated Time:** 20 minutes
**Dependencies:** T-001

📦 TASK DELEGATION
├─ Task ID: T-004
├─ Spec Reference: §3.3 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (LogEntryDisplay class)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: LogEntry with float timestamp
│  • Output: LogEntryDisplay with time and time_full strings
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Performance: Pre-compute both formats at creation time
│  • Memory: Two strings per entry (~40-50 bytes total)
├─ Tests Required: Unit tests for time formatting
└─ Dependencies: T-001 (model change)

**Changes:**
```python
# src/views/log_table_view.py
from datetime import datetime

@dataclass
class LogEntryDisplay:
    category: str
    time: str            # H:M:S.MS format for table display
    time_full: str       # NEW: Full date-time for tooltip
    level: LogLevel
    message: str
    file_offset: int
    
    @classmethod
    def from_log_entry(cls, entry) -> "LogEntryDisplay":
        # ... existing level mapping ...
        
        # Convert Unix Epoch to datetime
        dt = datetime.fromtimestamp(entry.timestamp)
        
        # Format for table: H:M:S.MS
        time_str = dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        
        # Format for tooltip: YYYY-MM-DD H:M:S.MS
        time_full = dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        
        return cls(
            category=entry.category if entry.category else "",
            time=time_str,
            time_full=time_full,  # NEW
            level=display_level,
            message=entry.display_message,
            file_offset=entry.file_offset
        )
```

---

### Task T-005: Update Table Model Tooltip
**Priority:** MEDIUM
**Estimated Time:** 10 minutes
**Dependencies:** T-004

📦 TASK DELEGATION
├─ Task ID: T-005
├─ Spec Reference: §3.4 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (LogTableModel.data method)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: LogEntryDisplay with time_full
│  • Output: Tooltip text for time column
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Performance: O(1) lookup (pre-computed string)
├─ Tests Required: Unit tests for tooltip display
└─ Dependencies: T-004 (LogEntryDisplay change)

**Changes:**
```python
# src/views/log_table_view.py - LogTableModel.data method
def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object:
    # ... existing DisplayRole code ...
    
    elif role == Qt.ToolTipRole:
        if col == self.COL_TIME:
            # Show full date-time in tooltip
            return entry.time_full  # YYYY-MM-DD H:M:S.MS
        elif col == self.COL_MESSAGE:
            return entry.message
        elif col == self.COL_CATEGORY:
            return entry.category
        return None
```

---

### Task T-006: Update Parser Tests
**Priority:** MEDIUM
**Estimated Time:** 20 minutes
**Dependencies:** T-003

📦 TASK DELEGATION
├─ Task ID: T-006
├─ Spec Reference: §7.1 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Tests
├─ Scope: tests/test_parser.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: Log lines with various timestamp formats
│  • Output: Test assertions for Unix Epoch conversion
├─ Constraints:
│  • Thread context: N/A (tests)
│  • Test all supported formats
├─ Tests Required: N/A (this IS the test task)
└─ Dependencies: T-003 (parser implementation)

**Test Cases:**
1. Test DD-MM-YYYYTHH:MM:SS.MS format
2. Test YYYY-MM-DD HH:MM:SS format
3. Test HH:MM:SS format
4. Test timestamp is float type
5. Test timestamp conversion accuracy

---

### Task T-007: Update Display Tests
**Priority:** MEDIUM
**Estimated Time:** 20 minutes
**Dependencies:** T-004, T-005

📦 TASK DELEGATION
├─ Task ID: T-007
├─ Spec Reference: §7.2 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Tests
├─ Scope: tests/test_log_table_view.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: LogEntry with float timestamp
│  • Output: Test assertions for time formatting
├─ Constraints:
│  • Thread context: N/A (tests)
│  • Test both table display and tooltip
├─ Tests Required: N/A (this IS the test task)
└─ Dependencies: T-004, T-005 (display implementation)

**Test Cases:**
1. Test time display format (H:M:S.MS)
2. Test time_full format (YYYY-MM-DD H:M:S.MS)
3. Test tooltip returns time_full
4. Test milliseconds formatting

---

### Task T-008: Update Test Fixtures
**Priority:** MEDIUM
**Estimated Time:** 15 minutes
**Dependencies:** T-001

📦 TASK DELEGATION
├─ Task ID: T-008
├─ Spec Reference: §3.1 in docs/specs/features/timestamp-unix-epoch.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Tests
├─ Scope: tests/conftest.py, tests/test_*.py (all test files using LogEntry)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: Test fixtures creating LogEntry
│  • Output: Updated fixtures with float timestamp
├─ Constraints:
│  • Thread context: N/A (tests)
│  • Update all fixtures that create LogEntry
├─ Tests Required: N/A (this IS the test task)
└─ Dependencies: T-001 (model change)

**Files to Update:**
- tests/conftest.py (sample_entries fixture)
- tests/test_filter_engine.py
- tests/test_integration.py
- tests/test_statistics.py
- tests/test_saved_filter.py
- tests/test_log_document.py

---

## Dependency Graph

```
T-001 (LogEntry model)
    ├── T-002 (Parser function)
    │       └── T-003 (Parser integration)
    │               └── T-006 (Parser tests)
    ├── T-004 (LogEntryDisplay)
    │       └── T-005 (Table tooltip)
    │               └── T-007 (Display tests)
    └── T-008 (Test fixtures)
```

---

## Execution Order

1. **T-001** - LogEntry model (blocking all others)
2. **T-002** - Parser function (can run parallel with T-004, T-008)
3. **T-008** - Test fixtures (can run parallel with T-002, T-004)
4. **T-003** - Parser integration (requires T-002)
5. **T-004** - LogEntryDisplay (can run parallel with T-002, T-008)
6. **T-005** - Table tooltip (requires T-004)
7. **T-006** - Parser tests (requires T-003)
8. **T-007** - Display tests (requires T-004, T-005)

---

## Parallel Execution

**Batch 1 (sequential):** T-001
**Batch 2 (parallel):** T-002, T-004, T-008
**Batch 3 (sequential):** T-003, T-005
**Batch 4 (parallel):** T-006, T-007

---

## Verification Checklist

After all tasks complete:
- [ ] All tests pass
- [ ] Memory benchmark shows reduction
- [ ] Table displays H:M:S.MS format
- [ ] Tooltip shows full date-time
- [ ] Parser handles all timestamp formats
- [ ] No regression in existing functionality

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Timestamp format not recognized | Low | High | Fallback to time-only format |
| Test fixtures break | Medium | Medium | Update all fixtures in T-008 |
| Performance regression | Low | Low | Benchmark before/after |
| Timezone issues | Low | Medium | Use local time (datetime.fromtimestamp) |

---

## Ready for Delegation

All tasks are ready for delegation to spec-coder mode. Start with T-001 (LogEntry model) as it blocks all other tasks.