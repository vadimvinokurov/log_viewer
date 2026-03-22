# Table Column Auto-Size Specification

**Version:** 1.0
**Last Updated:** 2026-03-21
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** READY

---

## §1 Overview

This specification defines the automatic column sizing behavior for the log table view. Columns should be sized to fit their content on initial load, providing optimal readability without requiring manual column adjustment.

### §1.1 Problem Statement

Currently, table columns use fixed default widths:
- **Time column**: 80px (may be too wide for "HH:MM:SS.mmm" format)
- **Category column**: 100px (may be too narrow for long category paths)
- **Type column**: 60px (too wide for single-character log level icons)
- **Message column**: 400px (stretches to fill remaining space)

Users must manually adjust column widths to see full content, especially for:
- Time values that are always the same length
- Type column showing only a single icon character
- Category paths that vary in length

### §1.2 Goals

1. **Time column**: Size to fit the timestamp format "HH:MM:SS.mmm" (12 characters)
2. **Type column**: Size to fit the log level icon (single character)
3. **Category column**: Size to fit the widest visible category path (with reasonable maximum)
4. **Message column**: Continue to stretch to fill remaining space

### §1.3 Scope

- Initial column sizing when file is loaded
- Column sizing when filter changes (new categories may appear)
- Minimum and maximum width constraints
- User manual resize override (auto-size only on initial load)

### §1.4 Cross-References

- **Table Unified Styles:** [table-unified-styles.md](table-unified-styles.md) §3.3 (Column Widths)
- **Table Column Alignment:** [table-column-alignment.md](table-column-alignment.md)
- **UI Components:** [ui-components.md](ui-components.md) §4 (LogTableView)
- **Typography System:** [typography-system.md](typography-system.md) (Font metrics)
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)

---

## §2 Column Width Requirements

### §2.1 Time Column

| Property | Value | Rationale |
|----------|-------|-----------|
| Content Format | "HH:MM:SS.mmm" | Fixed format, 12 characters |
| Font | Monospace | `Typography.LOG_FONT` |
| Auto-Size | Yes | Fixed format allows precise sizing |
| Minimum Width | 60px | Prevents column from becoming too narrow |
| Maximum Width | None | Fixed content length |
| User Resize | Allowed | User can override auto-size |

**Calculation:**
```python
# Time format: "HH:MM:SS.mmm" (12 characters)
# Use QFontMetrics to calculate exact width
font_metrics = QFontMetrics(Typography.LOG_FONT)
time_text = "00:00:00.000"  # Representative sample
time_width = font_metrics.horizontalAdvance(time_text)
# Add padding for cell margins
time_width += 8  # 4px left + 4px right
```

### §2.2 Type Column

| Property | Value | Rationale |
|----------|-------|-----------|
| Content | Single icon character | Log level icon (e.g., "C", "E", "W", "M", "D", "T") |
| Font | System UI Font | `Typography.PRIMARY` |
| Auto-Size | Yes | Single character allows precise sizing |
| Minimum Width | 30px | Prevents column from becoming too narrow |
| Maximum Width | None | Fixed content length |
| User Resize | Allowed | User can override auto-size |

**Calculation:**
```python
# Type column shows single icon character
font_metrics = QFontMetrics(Typography.UI_FONT)
type_text = "W"  # Representative sample (widest icon)
type_width = font_metrics.horizontalAdvance(type_text)
# Add padding for cell margins
type_width += 16  # 8px left + 8px right (centered icon needs more padding)
```

### §2.3 Category Column

| Property | Value | Rationale |
|----------|-------|-----------|
| Content | Variable length category path | e.g., "Category.SubCategory" |
| Font | System UI Font | `Typography.PRIMARY` |
| Auto-Size | Yes (with maximum) | Variable content requires sampling |
| Minimum Width | 50px | Prevents column from becoming too narrow |
| Maximum Width | 300px | Prevents column from taking too much space |
| User Resize | Allowed | User can override auto-size |

**Calculation:**
```python
# Category column shows variable-length paths
# Sample first N visible entries to find widest category
font_metrics = QFontMetrics(Typography.UI_FONT)
max_category_width = 0

# Sample first 100 visible entries (or all if fewer)
sample_size = min(100, len(visible_entries))
for entry in visible_entries[:sample_size]:
    category_width = font_metrics.horizontalAdvance(entry.category)
    max_category_width = max(max_category_width, category_width)

# Add padding for cell margins
max_category_width += 8  # 4px left + 4px right

# Clamp to min/max
category_width = max(50, min(max_category_width, 300))
```

### §2.4 Message Column

| Property | Value | Rationale |
|----------|-------|-----------|
| Content | Variable length log message | Can be very long |
| Font | Monospace | `Typography.LOG_FONT` |
| Auto-Size | No | Stretches to fill remaining space |
| Minimum Width | 100px | Ensures minimum readability |
| User Resize | Allowed | User can adjust width |

**Behavior:**
- Message column uses `QHeaderView.Stretch` to fill remaining space
- No auto-sizing needed
- User can manually resize if desired

---

## §3 Auto-Size Algorithm

### §3.1 When to Auto-Size

| Event | Auto-Size? | Rationale |
|-------|-----------|-----------|
| File Load (Initial) | Yes | First time content is displayed |
| File Load (Subsequent) | No | Preserve user's manual adjustments |
| Filter Change | No | Preserve user's manual adjustments |
| Category Toggle | No | Preserve user's manual adjustments |
| Window Resize | No | Preserve user's manual adjustments |

**Implementation:**
```python
class LogTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_sized = False  # Track if auto-size has been applied
    
    def set_entries(self, entries: List[LogEntry]) -> None:
        """Set log entries."""
        self._model.set_entries(entries)
        self._force_row_height()
        
        # Auto-size columns only on first load
        if not self._auto_sized:
            self._auto_size_columns()
            self._auto_sized = True
```

### §3.2 Auto-Size Implementation

```python
def _auto_size_columns(self) -> None:
    """Auto-size Time, Type, and Category columns based on content.
    
    Ref: docs/specs/features/table-column-auto-size.md §3.2
    Master: docs/SPEC.md §1
    """
    from PySide6.QtGui import QFontMetrics
    from src.constants.typography import Typography
    from src.constants.dimensions import MIN_COLUMN_WIDTH
    
    # Time column: Fixed format "HH:MM:SS.mmm"
    time_font_metrics = QFontMetrics(Typography.LOG_FONT)
    time_text = "00:00:00.000"  # Representative sample
    time_width = time_font_metrics.horizontalAdvance(time_text)
    time_width += 8  # Padding: 4px left + 4px right
    time_width = max(time_width, 60)  # Minimum width
    self.setColumnWidth(LogTableModel.COL_TIME, time_width)
    
    # Type column: Single icon character
    type_font_metrics = QFontMetrics(Typography.UI_FONT)
    type_text = "W"  # Representative sample (widest icon)
    type_width = type_font_metrics.horizontalAdvance(type_text)
    type_width += 16  # Padding: 8px left + 8px right (centered icon)
    type_width = max(type_width, 30)  # Minimum width
    self.setColumnWidth(LogTableModel.COL_TYPE, type_width)
    
    # Category column: Sample visible entries
    category_font_metrics = QFontMetrics(Typography.UI_FONT)
    max_category_width = 0
    
    # Sample first 100 visible entries (or all if fewer)
    entries = self._model.get_entries()
    sample_size = min(100, len(entries))
    for i in range(sample_size):
        entry = entries[i]
        category_width = category_font_metrics.horizontalAdvance(entry.category)
        max_category_width = max(max_category_width, category_width)
    
    # Add padding
    max_category_width += 8  # 4px left + 4px right
    
    # Clamp to min/max
    category_width = max(50, min(max_category_width, 300))
    self.setColumnWidth(LogTableModel.COL_CATEGORY, category_width)
    
    # Message column: No auto-size, uses Stretch mode
    # (already set in _setup_header)
```

### §3.3 Performance Considerations

| Operation | Time Complexity | Impact |
|-----------|------------------|--------|
| Time column auto-size | O(1) | Negligible (fixed format) |
| Type column auto-size | O(1) | Negligible (single character) |
| Category column auto-size | O(min(100, n)) | Acceptable (sample first 100 entries) |

**Optimization:**
- Category column only samples first 100 entries, not all entries
- Auto-size only runs once on initial file load
- Font metrics are cached by Qt

---

## §4 User Interaction

### §4.1 Manual Resize Override

Users can manually resize columns after auto-size:

| Column | User Can Resize? | Behavior |
|--------|-------------------|----------|
| Time | Yes | Manual resize overrides auto-size |
| Type | Yes | Manual resize overrides auto-size |
| Category | Yes | Manual resize overrides auto-size |
| Message | Yes | Manual resize adjusts stretch ratio |

**Implementation:**
- Auto-size only runs once on initial file load
- Subsequent file loads preserve user's manual adjustments
- User's column widths are saved/restored via SettingsManager

### §4.2 Settings Persistence

Column widths are saved and restored via [`SettingsManager`](settings-manager.md):

```python
# Save column widths on application exit
widths = log_table.get_column_widths()
settings_manager.save_column_widths(widths)

# Restore column widths on application start
widths = settings_manager.load_column_widths()
if widths:
    log_table.set_column_widths(widths)
else:
    # First run: auto-size columns
    log_table._auto_size_columns()
```

**Note:** If saved widths exist, they take precedence over auto-size. Auto-size only applies when no saved widths exist (first run or after settings reset).

---

## §5 Constants

### §5.1 Column Width Constants

**File:** [`src/constants/dimensions.py`](../../src/constants/dimensions.py)

```python
# Column width constraints
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

### §5.2 Removed Constants

The following fixed width constants are **REMOVED** (no longer needed):

```python
# REMOVED - No longer used (auto-size replaces fixed widths)
# TIME_COLUMN_WIDTH: int = 80
# CATEGORY_COLUMN_WIDTH: int = 100
# TYPE_COLUMN_WIDTH: int = 60
# MESSAGE_COLUMN_WIDTH: int = 400
```

---

## §6 Testing Requirements

### §6.1 Unit Tests

```python
def test_time_column_auto_size():
    """Test that time column is sized to fit 'HH:MM:SS.mmm' format."""
    table = LogTableView()
    table.set_entries([create_entry("00:00:00.000", "Category", "Message")])
    
    time_width = table.columnWidth(LogTableModel.COL_TIME)
    assert time_width >= 60  # Minimum width
    assert time_width <= 120  # Reasonable maximum for monospace font

def test_type_column_auto_size():
    """Test that type column is sized to fit single icon character."""
    table = LogTableView()
    table.set_entries([create_entry("00:00:00.000", "Category", "Message")])
    
    type_width = table.columnWidth(LogTableModel.COL_TYPE)
    assert type_width >= 30  # Minimum width
    assert type_width <= 60  # Reasonable maximum for single character

def test_category_column_auto_size():
    """Test that category column is sized based on sampled entries."""
    table = LogTableView()
    entries = [
        create_entry("00:00:00.000", f"Category{i}.SubCategory{i}", "Message")
        for i in range(100)
    ]
    table.set_entries(entries)
    
    category_width = table.columnWidth(LogTableModel.COL_CATEGORY)
    assert category_width >= 50  # Minimum width
    assert category_width <= 300  # Maximum width

def test_category_column_max_width():
    """Test that category column respects maximum width."""
    table = LogTableView()
    # Create entries with very long category paths
    entries = [
        create_entry("00:00:00.000", "A" * 500, "Message")
        for i in range(100)
    ]
    table.set_entries(entries)
    
    category_width = table.columnWidth(LogTableModel.COL_CATEGORY)
    assert category_width == 300  # Should clamp to maximum

def test_auto_size_only_once():
    """Test that auto-size only runs on first load."""
    table = LogTableView()
    
    # First load: auto-size
    table.set_entries([create_entry("00:00:00.000", "Short", "Message")])
    initial_width = table.columnWidth(LogTableModel.COL_CATEGORY)
    
    # Manually resize
    table.setColumnWidth(LogTableModel.COL_CATEGORY, 200)
    
    # Second load: should preserve manual resize
    table.set_entries([create_entry("00:00:00.000", "VeryLongCategory", "Message")])
    final_width = table.columnWidth(LogTableModel.COL_CATEGORY)
    
    assert final_width == 200  # Manual resize preserved

def test_manual_resize_override():
    """Test that manual resize overrides auto-size."""
    table = LogTableView()
    table.set_entries([create_entry("00:00:00.000", "Category", "Message")])
    
    # Manually resize
    table.setColumnWidth(LogTableModel.COL_TIME, 150)
    
    # Width should be preserved
    assert table.columnWidth(LogTableModel.COL_TIME) == 150
```

### §6.2 Visual Tests

- [ ] Time column shows full timestamp without truncation
- [ ] Type column shows centered icon with adequate padding
- [ ] Category column shows full category path (or truncates with ellipsis if too long)
- [ ] Message column fills remaining space
- [ ] Columns can be manually resized after auto-size
- [ ] Column widths are saved and restored on application restart

---

## §7 Implementation Checklist

- [ ] Add column width constraint constants to `src/constants/dimensions.py`
- [ ] Remove fixed width constants (`TIME_COLUMN_WIDTH`, etc.)
- [ ] Add `_auto_sized` flag to `LogTableView.__init__`
- [ ] Implement `_auto_size_columns()` method in `LogTableView`
- [ ] Call `_auto_size_columns()` in `set_entries()` on first load
- [ ] Update `sizeHintForColumn()` to return auto-sized widths
- [ ] Update `_setup_header()` to use `Interactive` mode for all columns
- [ ] Write unit tests for auto-size behavior
- [ ] Write visual regression tests
- [ ] Update `docs/SPEC-INDEX.md` with new spec entry
- [ ] Update `docs/specs/features/table-unified-styles.md` §3.3 to reference this spec

---

## §8 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial specification for column auto-sizing |

---

## §9 Cross-References

- **Table Unified Styles:** [table-unified-styles.md](table-unified-styles.md) §3.3 (Column Widths)
- **Table Column Alignment:** [table-column-alignment.md](table-column-alignment.md)
- **UI Components:** [ui-components.md](ui-components.md) §4 (LogTableView)
- **Typography System:** [typography-system.md](typography-system.md) (Font metrics)
- **Settings Manager:** [settings-manager.md](settings-manager.md) (Column width persistence)
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)