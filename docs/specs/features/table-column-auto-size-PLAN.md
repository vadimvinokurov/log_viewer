# Table Column Auto-Size Implementation Plan

**Version:** 1.0
**Last Updated:** 2026-03-21
**Status:** READY FOR IMPLEMENTATION

---

## Overview

This plan breaks down the implementation of automatic column sizing for the log table view into discrete tasks for delegation to spec-coder agents.

**Spec Reference:** [table-column-auto-size.md](table-column-auto-size.md)

**Implementation Strategy:**
1. Add new constants for column width constraints
2. Remove old fixed width constants
3. Implement auto-size logic in LogTableView
4. Update header setup to use Interactive mode
5. Write comprehensive tests

---

## Task Breakdown

### Task T-001: Add Column Width Constraint Constants

**Priority:** HIGH
**Estimated Time:** 15 minutes
**Dependencies:** None

📦 TASK DELEGATION
├─ Task ID: T-001
├─ Spec Reference: §5.1 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Engine Core / Constants
├─ Scope: src/constants/dimensions.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: None
│  • Output: New constants for column width constraints
├─ Constraints:
│  • Thread context: N/A (constants only)
│  • Memory: Stack allocation for constants
│  • Performance: O(1) lookup
├─ Tests Required: Unit tests for constant values
└─ Dependencies: None

**Changes:**

Add the following constants to [`src/constants/dimensions.py`](../../src/constants/dimensions.py):

```python
# Column width constraints for auto-sizing
# Ref: docs/specs/features/table-column-auto-size.md §5.1

TIME_COLUMN_MIN_WIDTH: int = 60
"""Minimum width for time column in pixels."""

TIME_COLUMN_PADDING: int = 8
"""Padding for time column (4px left + 4px right)."""

TYPE_COLUMN_MIN_WIDTH: int = 30
"""Minimum width for type column in pixels."""

TYPE_COLUMN_PADDING: int = 16
"""Padding for type column (8px left + 8px right for centered icon)."""

CATEGORY_COLUMN_MIN_WIDTH: int = 50
"""Minimum width for category column in pixels."""

CATEGORY_COLUMN_MAX_WIDTH: int = 300
"""Maximum width for category column in pixels."""

CATEGORY_COLUMN_PADDING: int = 8
"""Padding for category column (4px left + 4px right)."""

CATEGORY_COLUMN_SAMPLE_SIZE: int = 100
"""Number of entries to sample for category column auto-sizing."""

MESSAGE_COLUMN_MIN_WIDTH: int = 100
"""Minimum width for message column in pixels."""
```

**Verification:**
- All constants are defined with correct values
- All constants have docstrings
- Constants follow naming convention (UPPER_CASE with underscores)

---

### Task T-002: Remove Fixed Width Constants

**Priority:** HIGH
**Estimated Time:** 10 minutes
**Dependencies:** T-001

📦 TASK DELEGATION
├─ Task ID: T-002
├─ Spec Reference: §5.2 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Engine Core / Constants
├─ Scope: src/constants/dimensions.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: None
│  • Output: Removal of fixed width constants
├─ Constraints:
│  • Thread context: N/A (constants only)
│  • Ensure no imports break
├─ Tests Required: Verify no import errors
└─ Dependencies: T-001 (add new constants first)

**Changes:**

Remove the following constants from [`src/constants/dimensions.py`](../../src/constants/dimensions.py):

```python
# REMOVED - No longer used (auto-size replaces fixed widths)
# TIME_COLUMN_WIDTH: int = 80
# CATEGORY_COLUMN_WIDTH: int = 100
# TYPE_COLUMN_WIDTH: int = 60
# MESSAGE_COLUMN_WIDTH: int = 400
```

**Verification:**
- Fixed width constants are removed
- No import errors in files that use these constants
- Update imports in `src/views/log_table_view.py`

---

### Task T-003: Update LogTableView Imports

**Priority:** HIGH
**Estimated Time:** 5 minutes
**Dependencies:** T-002

📦 TASK DELEGATION
├─ Task ID: T-003
├─ Spec Reference: §3.2 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: None
│  • Output: Updated imports
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Remove old constant imports
│  • Add new constant imports
├─ Tests Required: Verify no import errors
└─ Dependencies: T-002 (constants removed)

**Changes:**

Update imports in [`src/views/log_table_view.py`](../../src/views/log_table_view.py):

```python
# OLD imports (remove):
from src.constants.dimensions import (
    get_table_cell_height,
    TIME_COLUMN_WIDTH,
    CATEGORY_COLUMN_WIDTH,
    TYPE_COLUMN_WIDTH,
    MESSAGE_COLUMN_WIDTH,
    MIN_COLUMN_WIDTH,
)

# NEW imports (add):
from src.constants.dimensions import (
    get_table_cell_height,
    TIME_COLUMN_MIN_WIDTH,
    TIME_COLUMN_PADDING,
    TYPE_COLUMN_MIN_WIDTH,
    TYPE_COLUMN_PADDING,
    CATEGORY_COLUMN_MIN_WIDTH,
    CATEGORY_COLUMN_MAX_WIDTH,
    CATEGORY_COLUMN_PADDING,
    CATEGORY_COLUMN_SAMPLE_SIZE,
    MESSAGE_COLUMN_MIN_WIDTH,
    MIN_COLUMN_WIDTH,
)
```

**Verification:**
- No import errors
- All new constants are imported
- Old constants are removed

---

### Task T-004: Add Auto-Size Flag to LogTableView

**Priority:** HIGH
**Estimated Time:** 5 minutes
**Dependencies:** T-003

📦 TASK DELEGATION
├─ Task ID: T-004
├─ Spec Reference: §3.1 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (LogTableView.__init__)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: None
│  • Output: New instance variable _auto_sized
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Memory: Single boolean flag per instance
├─ Tests Required: Unit test for flag initialization
└─ Dependencies: T-003 (imports updated)

**Changes:**

Add `_auto_sized` flag to [`src/views/log_table_view.py`](../../src/views/log_table_view.py):

```python
class LogTableView(QTableView):
    """Table view for log entries with new column structure."""

    # Signal emitted when selection changes
    selection_changed = Signal()
    # Signal emitted when find is requested (Ctrl+F)
    find_requested = Signal()

    def __init__(self, parent=None) -> None:
        """Initialize the table view."""
        super().__init__(parent)
        self._model = LogTableModel(self)
        self._highlight_service = HighlightService()
        self._find_service = FindService()
        self._highlight_delegate = HighlightDelegate(parent=self)
        self._context_menu: Optional[TableContextMenu] = None
        self._document: Optional["LogDocument"] = None  # For lazy loading raw lines
        self._auto_sized = False  # Track if auto-size has been applied
        
        self.setModel(self._model)
        self._setup_ui()
        self._setup_shortcuts()
```

**Verification:**
- Flag is initialized to False
- Flag is an instance variable (self._auto_sized)

---

### Task T-005: Implement Auto-Size Columns Method

**Priority:** HIGH
**Estimated Time:** 30 minutes
**Dependencies:** T-004

📦 TASK DELEGATION
├─ Task ID: T-005
├─ Spec Reference: §3.2 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (new method _auto_size_columns)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: None (uses model entries)
│  • Output: Column widths set via setColumnWidth()
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Performance: O(min(100, n)) for category column
│  • Memory: QFontMetrics cached by Qt
├─ Tests Required: Unit tests for each column auto-size
└─ Dependencies: T-004 (flag added)

**Changes:**

Add `_auto_size_columns()` method to [`src/views/log_table_view.py`](../../src/views/log_table_view.py):

```python
def _auto_size_columns(self) -> None:
    """Auto-size Time, Type, and Category columns based on content.
    
    This method calculates optimal column widths based on content:
    - Time column: Fixed format "HH:MM:SS.mmm" (monospace font)
    - Type column: Single icon character (UI font)
    - Category column: Sample first 100 entries (UI font)
    
    Auto-size only runs once on initial file load. Subsequent loads
    preserve user's manual adjustments.
    
    Ref: docs/specs/features/table-column-auto-size.md §3.2
    Master: docs/SPEC.md §1
    """
    from PySide6.QtGui import QFontMetrics
    from src.constants.typography import Typography
    
    # Time column: Fixed format "HH:MM:SS.mmm"
    # Use monospace font for accurate width calculation
    time_font_metrics = QFontMetrics(Typography.LOG_FONT)
    time_text = "00:00:00.000"  # Representative sample (12 characters)
    time_width = time_font_metrics.horizontalAdvance(time_text)
    time_width += TIME_COLUMN_PADDING  # 4px left + 4px right
    time_width = max(time_width, TIME_COLUMN_MIN_WIDTH)  # Minimum width
    self.setColumnWidth(LogTableModel.COL_TIME, time_width)
    
    # Type column: Single icon character
    # Use UI font (icon characters are not monospace)
    type_font_metrics = QFontMetrics(Typography.UI_FONT)
    type_text = "W"  # Representative sample (widest icon character)
    type_width = type_font_metrics.horizontalAdvance(type_text)
    type_width += TYPE_COLUMN_PADDING  # 8px left + 8px right (centered icon)
    type_width = max(type_width, TYPE_COLUMN_MIN_WIDTH)  # Minimum width
    self.setColumnWidth(LogTableModel.COL_TYPE, type_width)
    
    # Category column: Sample visible entries
    # Use UI font for category text
    category_font_metrics = QFontMetrics(Typography.UI_FONT)
    max_category_width = 0
    
    # Sample first 100 visible entries (or all if fewer)
    entries = self._model.get_entries()
    sample_size = min(CATEGORY_COLUMN_SAMPLE_SIZE, len(entries))
    for i in range(sample_size):
        entry = entries[i]
        category_width = category_font_metrics.horizontalAdvance(entry.category)
        max_category_width = max(max_category_width, category_width)
    
    # Add padding
    max_category_width += CATEGORY_COLUMN_PADDING  # 4px left + 4px right
    
    # Clamp to min/max
    category_width = max(
        CATEGORY_COLUMN_MIN_WIDTH,
        min(max_category_width, CATEGORY_COLUMN_MAX_WIDTH)
    )
    self.setColumnWidth(LogTableModel.COL_CATEGORY, category_width)
    
    # Message column: No auto-size, uses Stretch mode
    # (already set in _setup_header)
```

**Verification:**
- Time column width is calculated correctly
- Type column width is calculated correctly
- Category column width is clamped to min/max
- Message column is not modified

---

### Task T-006: Update set_entries to Call Auto-Size

**Priority:** HIGH
**Estimated Time:** 10 minutes
**Dependencies:** T-005

📦 TASK DELEGATION
├─ Task ID: T-006
├─ Spec Reference: §3.1 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (set_entries method)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: List of LogEntry
│  • Output: Auto-size called on first load
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Auto-size only runs once
│  • Flag prevents re-running
├─ Tests Required: Unit test for auto-size-once behavior
└─ Dependencies: T-005 (auto-size method implemented)

**Changes:**

Update `set_entries()` method in [`src/views/log_table_view.py`](../../src/views/log_table_view.py):

```python
def set_entries(self, entries: List[LogEntry]) -> None:
    """Set log entries.
    
    Auto-sizes columns on first load only. Subsequent loads preserve
    user's manual column adjustments.
    
    Args:
        entries: List of log entries to display.
    
    Ref: docs/specs/features/table-column-auto-size.md §3.1
    Master: docs/SPEC.md §1
    """
    self._model.set_entries(entries)
    self._force_row_height()
    
    # Auto-size columns only on first load
    if not self._auto_sized:
        self._auto_size_columns()
        self._auto_sized = True
```

**Verification:**
- Auto-size is called on first load
- Auto-size is NOT called on subsequent loads
- Flag is set after first auto-size

---

### Task T-007: Update Header Setup

**Priority:** MEDIUM
**Estimated Time:** 10 minutes
**Dependencies:** T-006

📦 TASK DELEGATION
├─ Task ID: T-007
├─ Spec Reference: §3.2 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (_setup_header method)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: None
│  • Output: Header configured with Interactive mode
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • All columns use Interactive mode
│  • Message column uses Stretch for last section
├─ Tests Required: Visual test for column resize behavior
└─ Dependencies: T-006 (set_entries updated)

**Changes:**

Update `_setup_header()` method in [`src/views/log_table_view.py`](../../src/views/log_table_view.py):

```python
def _setup_header(self) -> None:
    """Setup table header.
    
    Ref: docs/specs/features/table-unified-styles.md §3.2
    Ref: docs/specs/features/table-column-auto-size.md §3.2
    Master: docs/SPEC.md §1
    """
    header = self.horizontalHeader()
    # Ref: Unified cell height for header and rows
    header.setFixedHeight(get_table_cell_height())
    header.setSectionsClickable(False)
    
    # Use Interactive mode for all columns (allows user resize)
    # Ref: docs/specs/features/table-column-auto-size.md §3.2
    header.setSectionResizeMode(LogTableModel.COL_TIME, QHeaderView.Interactive)
    header.setSectionResizeMode(LogTableModel.COL_CATEGORY, QHeaderView.Interactive)
    header.setSectionResizeMode(LogTableModel.COL_TYPE, QHeaderView.Interactive)
    header.setSectionResizeMode(LogTableModel.COL_MESSAGE, QHeaderView.Interactive)
    
    # Set minimum section size (allows user to resize down to minimum)
    header.setMinimumSectionSize(MIN_COLUMN_WIDTH)
    
    # Stretch last section (Message column) to fill remaining space
    header.setStretchLastSection(True)

    self.setSortingEnabled(False)
    self.setShowGrid(False)
    self.setStyleSheet(get_table_stylesheet())
    self.setWordWrap(False)
    self.setTextElideMode(Qt.ElideRight)
```

**Note:** The key change is that we NO LONGER set default column widths in `_setup_header()`. Instead, auto-size will set them on first load.

**Verification:**
- All columns use Interactive mode
- Minimum section size is set
- Last section stretches
- No fixed widths are set in this method

---

### Task T-008: Update sizeHintForColumn Method

**Priority:** LOW
**Estimated Time:** 10 minutes
**Dependencies:** T-007

📦 TASK DELEGATION
├─ Task ID: T-008
├─ Spec Reference: §3.2 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: UI Layer / Views
├─ Scope: src/views/log_table_view.py (sizeHintForColumn method)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: Column index
│  • Output: Size hint for column
├─ Constraints:
│  • Thread context: Main thread (UI)
│  • Performance: O(1) lookup
├─ Tests Required: Unit test for size hints
└─ Dependencies: T-007 (header setup updated)

**Changes:**

Update `sizeHintForColumn()` method in [`src/views/log_table_view.py`](../../src/views/log_table_view.py):

```python
def sizeHintForColumn(self, column: int) -> int:
    """Return size hint for column.
    
    This method provides size hints for Qt's internal layout calculations.
    The actual column widths are set by _auto_size_columns() on first load.
    
    Args:
        column: Column index.
    
    Returns:
        Size hint for the column (minimum width).
    
    Ref: docs/specs/features/table-column-auto-size.md §3.2
    Master: docs/SPEC.md §1
    """
    # Return minimum widths as size hints
    # These are used by Qt for initial layout before auto-size
    if column == LogTableModel.COL_TIME:
        return TIME_COLUMN_MIN_WIDTH
    elif column == LogTableModel.COL_CATEGORY:
        return CATEGORY_COLUMN_MIN_WIDTH
    elif column == LogTableModel.COL_TYPE:
        return TYPE_COLUMN_MIN_WIDTH
    elif column == LogTableModel.COL_MESSAGE:
        return MESSAGE_COLUMN_MIN_WIDTH
    return MIN_COLUMN_WIDTH
```

**Verification:**
- Size hints return minimum widths
- Size hints are used before auto-size

---

### Task T-009: Write Unit Tests

**Priority:** HIGH
**Estimated Time:** 45 minutes
**Dependencies:** T-006

📦 TASK DELEGATION
├─ Task ID: T-009
├─ Spec Reference: §6.1 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Tests
├─ Scope: tests/test_log_table_view.py (new tests)
├─ Language: Python 3.10
├─ Input/Output:
│  • Input: LogEntry test fixtures
│  • Output: Test results
├─ Constraints:
│  • Thread context: N/A (tests)
│  • Test all column auto-size scenarios
│  • Test auto-size-once behavior
│  • Test manual resize override
├─ Tests Required: All tests in §6.1
└─ Dependencies: T-006 (auto-size implemented)

**Test Cases:**

Add the following tests to [`tests/test_log_table_view.py`](../../tests/test_log_table_view.py):

```python
def test_time_column_auto_size(log_table_view):
    """Test that time column is sized to fit 'HH:MM:SS.mmm' format.
    
    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.models.log_entry import LogEntry, LogLevel
    from datetime import datetime
    
    # Create entry with known timestamp
    entry = LogEntry(
        row_index=0,
        timestamp=datetime(2026, 3, 21, 12, 34, 56, 789000).timestamp(),
        category="TestCategory",
        display_message="Test message",
        level=LogLevel.MSG,
        file_offset=0
    )
    
    log_table_view.set_entries([entry])
    
    time_width = log_table_view.columnWidth(LogTableModel.COL_TIME)
    assert time_width >= 60  # Minimum width
    assert time_width <= 120  # Reasonable maximum for monospace font


def test_type_column_auto_size(log_table_view):
    """Test that type column is sized to fit single icon character.
    
    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.models.log_entry import LogEntry, LogLevel
    from datetime import datetime
    
    entry = LogEntry(
        row_index=0,
        timestamp=datetime.now().timestamp(),
        category="TestCategory",
        display_message="Test message",
        level=LogLevel.WARNING,  # Widest icon character
        file_offset=0
    )
    
    log_table_view.set_entries([entry])
    
    type_width = log_table_view.columnWidth(LogTableModel.COL_TYPE)
    assert type_width >= 30  # Minimum width
    assert type_width <= 60  # Reasonable maximum for single character


def test_category_column_auto_size(log_table_view):
    """Test that category column is sized based on sampled entries.
    
    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.models.log_entry import LogEntry, LogLevel
    from datetime import datetime
    
    # Create entries with varying category lengths
    entries = [
        LogEntry(
            row_index=i,
            timestamp=datetime.now().timestamp(),
            category=f"Category{i}.SubCategory{i}",
            display_message="Test message",
            level=LogLevel.MSG,
            file_offset=i
        )
        for i in range(100)
    ]
    
    log_table_view.set_entries(entries)
    
    category_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)
    assert category_width >= 50  # Minimum width
    assert category_width <= 300  # Maximum width


def test_category_column_max_width(log_table_view):
    """Test that category column respects maximum width.
    
    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.models.log_entry import LogEntry, LogLevel
    from datetime import datetime
    
    # Create entries with very long category paths
    entries = [
        LogEntry(
            row_index=i,
            timestamp=datetime.now().timestamp(),
            category="A" * 500,  # Very long category
            display_message="Test message",
            level=LogLevel.MSG,
            file_offset=i
        )
        for i in range(100)
    ]
    
    log_table_view.set_entries(entries)
    
    category_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)
    assert category_width == 300  # Should clamp to maximum


def test_auto_size_only_once(log_table_view):
    """Test that auto-size only runs on first load.
    
    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.models.log_entry import LogEntry, LogLevel
    from datetime import datetime
    
    # First load: auto-size
    entries1 = [
        LogEntry(
            row_index=0,
            timestamp=datetime.now().timestamp(),
            category="Short",
            display_message="Test message",
            level=LogLevel.MSG,
            file_offset=0
        )
    ]
    log_table_view.set_entries(entries1)
    initial_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)
    
    # Manually resize
    log_table_view.setColumnWidth(LogTableModel.COL_CATEGORY, 200)
    
    # Second load: should preserve manual resize
    entries2 = [
        LogEntry(
            row_index=0,
            timestamp=datetime.now().timestamp(),
            category="VeryLongCategoryName",
            display_message="Test message",
            level=LogLevel.MSG,
            file_offset=0
        )
    ]
    log_table_view.set_entries(entries2)
    final_width = log_table_view.columnWidth(LogTableModel.COL_CATEGORY)
    
    assert final_width == 200  # Manual resize preserved


def test_manual_resize_override(log_table_view):
    """Test that manual resize overrides auto-size.
    
    Ref: docs/specs/features/table-column-auto-size.md §6.1
    """
    from src.models.log_entry import LogEntry, LogLevel
    from datetime import datetime
    
    entry = LogEntry(
        row_index=0,
        timestamp=datetime.now().timestamp(),
        category="TestCategory",
        display_message="Test message",
        level=LogLevel.MSG,
        file_offset=0
    )
    
    log_table_view.set_entries([entry])
    
    # Manually resize
    log_table_view.setColumnWidth(LogTableModel.COL_TIME, 150)
    
    # Width should be preserved
    assert log_table_view.columnWidth(LogTableModel.COL_TIME) == 150
```

**Verification:**
- All tests pass
- Tests cover all scenarios in spec §6.1

---

### Task T-010: Update Documentation

**Priority:** LOW
**Estimated Time:** 10 minutes
**Dependencies:** T-009

📦 TASK DELEGATION
├─ Task ID: T-010
├─ Spec Reference: §7 in docs/specs/features/table-column-auto-size.md
├─ Master Constraints: docs/SPEC.md §1
├─ Project Context: Documentation
├─ Scope: docs/specs/features/table-unified-styles.md
├─ Language: Markdown
├─ Input/Output:
│  • Input: None
│  • Output: Updated cross-references
├─ Constraints:
│  • Update cross-references
│  • Update column width section
├─ Tests Required: N/A
└─ Dependencies: T-009 (tests complete)

**Changes:**

Update [`docs/specs/features/table-unified-styles.md`](../../docs/specs/features/table-unified-styles.md) §3.3:

```markdown
### §3.3 Column Widths

Column widths are automatically sized based on content on initial file load.
See [table-column-auto-size.md](table-column-auto-size.md) for complete specification.

| Column | Auto-Size | Minimum | Maximum | Behavior |
|--------|-----------|---------|---------|----------|
| Time | Yes | 60px | None | Fixed format "HH:MM:SS.mmm" |
| Category | Yes | 50px | 300px | Sample first 100 entries |
| Type | Yes | 30px | None | Single icon character |
| Message | No | 100px | None | Stretches to fill space |

**Note:** Users can manually resize columns after auto-size. Manual adjustments are
preserved across file loads via SettingsManager.
```

**Verification:**
- Cross-references are correct
- Column width table is updated

---

## Implementation Order

Tasks should be completed in the following order:

1. **T-001**: Add column width constraint constants (15 min)
2. **T-002**: Remove fixed width constants (10 min)
3. **T-003**: Update LogTableView imports (5 min)
4. **T-004**: Add auto-size flag (5 min)
5. **T-005**: Implement auto-size method (30 min)
6. **T-006**: Update set_entries (10 min)
7. **T-007**: Update header setup (10 min)
8. **T-008**: Update sizeHintForColumn (10 min)
9. **T-009**: Write unit tests (45 min)
10. **T-010**: Update documentation (10 min)

**Total Estimated Time:** 2.5 hours

---

## Verification Checklist

After all tasks are complete, verify:

- [ ] All constants are defined in `src/constants/dimensions.py`
- [ ] Old constants are removed
- [ ] Imports are updated in `src/views/log_table_view.py`
- [ ] `_auto_sized` flag is added to `LogTableView.__init__`
- [ ] `_auto_size_columns()` method is implemented
- [ ] `set_entries()` calls auto-size on first load
- [ ] `_setup_header()` uses Interactive mode for all columns
- [ ] `sizeHintForColumn()` returns minimum widths
- [ ] All unit tests pass
- [ ] Documentation is updated

---

## Cross-References

- **Specification:** [table-column-auto-size.md](table-column-auto-size.md)
- **Table Unified Styles:** [table-unified-styles.md](table-unified-styles.md)
- **Typography System:** [typography-system.md](typography-system.md)
- **Settings Manager:** [settings-manager.md](settings-manager.md)
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)
- **LogTableView:** [src/views/log_table_view.py](../../src/views/log_table_view.py)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial implementation plan |