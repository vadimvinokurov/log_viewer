# Selection Preservation Specification

**Version:** 1.4
**Status:** APPROVED
**Last Updated:** 2026-03-18
**Master:** docs/SPEC.md §1

---

## §1 Overview

### §1.1 Purpose

Define the mechanism for preserving row selection in the log table when filters or categories change. When the visible rows change due to filtering, the selection state must be preserved for all rows that remain visible. Rows that become hidden must have their selection cleared.

**Critical:** The current keyboard navigation index (current index) must also be preserved. This ensures that arrow key navigation (↑↓) continues from the currently focused row after filter changes, not from the first row.

**Viewport Preservation:** When the selected row remains visible after filter changes, its visual position relative to the viewport must be preserved. This prevents the selected row from jumping to a different position on screen, maintaining user context.

### §1.2 Scope

- Selection preservation during filter text changes
- Selection preservation during category checkbox toggles
- Selection preservation during log level toggles
- Selection preservation during saved filter enable/disable
- Selection clearing for hidden rows
- **Current index preservation for keyboard navigation**
- **Viewport position preservation for selected row**

### §1.3 Out of Scope

- Selection persistence across application restarts (handled by SettingsManager)
- Selection persistence across file switches
- Multi-file selection synchronization

---

## §2 Problem Statement

### §2.1 Current Behavior

When [`MainController._apply_filters()`](src/controllers/main_controller.py:519) is called:

1. Filtered entries are computed from `_all_entries`
2. [`LogTableView.set_entries()`](src/views/log_table_view.py:442) is called with new entries
3. [`LogTableModel.set_entries()`](src/views/log_table_view.py:142) calls `beginResetModel()` / `endResetModel()`
4. All selection state is lost because the model is reset

### §2.2 Desired Behavior

When filters change:

1. Compute new filtered entries
2. Identify currently selected rows by their stable identifiers
3. Determine which selected rows remain visible in the new filter result
4. Restore selection for visible rows
5. Clear selection for rows that are no longer visible

---

## §3 Stable Row Identification

### §3.1 Identifier Strategy

Rows must be identified by stable identifiers, not by row indices which change during filtering.

**Why `file_offset` instead of `raw_line`:**

We use `file_offset` as the stable identifier because:

- Is stored in every `LogEntry` (see [`log_entry.py`](../../src/models/log_entry.py:28))
- Is unique per line (byte position in file)
- Is immutable for a given file
- Is compact (8 bytes vs potentially long strings)

**Identifier Definition:**

```python
@dataclass(frozen=True)
class RowIdentifier:
    """Stable identifier for a log row.
    
    Uses file_offset as the unique identifier because:
    - It's immutable for a given log entry
    - It's unique within a log file (byte position)
    - It's always available (stored in LogEntry)
    - It's compact (8 bytes vs potentially long strings)
    """
    file_offset: int
```

### §3.2 Identifier Extraction

```python
# From LogEntry (src/models/log_entry.py)
def get_identifier(entry: LogEntry) -> RowIdentifier:
    return RowIdentifier(file_offset=entry.file_offset)

# From LogEntryDisplay (src/views/log_table_view.py)
# Note: LogEntryDisplay must include file_offset field
def get_identifier(display: LogEntryDisplay) -> RowIdentifier:
    return RowIdentifier(file_offset=display.file_offset)
```

### §3.3 LogEntryDisplay Extension

`LogEntryDisplay` must be extended to include `file_offset`:

```python
@dataclass
class LogEntryDisplay:
    """Display model for log entry in the new UI."""
    category: str
    time: str
    level: LogLevel
    message: str
    raw_line: str = ""
    file_offset: int = 0  # NEW: Required for selection preservation
    
    @classmethod
    def from_log_entry(cls, entry) -> "LogEntryDisplay":
        # ... existing code ...
        return cls(
            category=category,
            time=time_str,
            level=display_level,
            message=entry.display_message,
            raw_line=entry.raw_line,
            file_offset=entry.file_offset  # NEW: Copy file_offset
        )
```

### §3.4 Edge Cases

| Edge Case | Resolution |
|-----------|------------|
| Zero `file_offset` | Valid (first line of file) |
| Duplicate offsets | Impossible (each line has unique byte position) |
| File changes | Selection cleared on file reload (expected behavior) |

---

## §4 Selection Preservation Algorithm

### §4.1 Algorithm Overview

```
BEFORE filter change:
  1. Get current selected rows from LogTableView
  2. Extract RowIdentifiers from selected entries
  3. Store identifiers in SelectionState

APPLY filter:
  4. Compute new filtered_entries
  5. Build mapping: RowIdentifier -> new_row_index

AFTER filter change:
  6. For each stored identifier:
     - If identifier exists in new filtered_entries:
       - Add new_row_index to restored_selection
     - Else:
       - Discard (row is now hidden)
  7. Apply restored_selection to LogTableView
  8. Emit selection_changed signal if selection changed
```

### §4.2 SelectionState Class

```python
@dataclass(frozen=True)
class SelectionState:
    """Immutable snapshot of selection state.
    
    Stored before filter operation, used after to restore selection.
    Uses file_offset for identification.
    
    Attributes:
        offsets: Set of file_offset values for all selected rows.
        current_offset: file_offset of the currently focused row for keyboard navigation.
            This is the row that will be used as the starting point for arrow key
            navigation (↑↓). Must be preserved across filter changes to maintain
            correct keyboard navigation behavior.
        timestamp: For debugging/logging.
    """
    offsets: frozenset[int]  # Set of file_offset values
    current_offset: int | None = None  # Current row for keyboard navigation
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_entries(
        cls,
        entries: list[LogEntry | LogEntryDisplay],
        current_entry: LogEntry | LogEntryDisplay | None = None
    ) -> SelectionState:
        """Create selection state from selected entries.
        
        Args:
            entries: List of selected entries.
            current_entry: Currently focused entry (for keyboard navigation).
                This is the entry under the keyboard cursor, used for arrow key
                navigation. If None, current_offset will be None.
        
        Returns:
            SelectionState with file_offset values.
        """
        offsets = frozenset(e.file_offset for e in entries)
        current_offset = current_entry.file_offset if current_entry else None
        return cls(offsets=offsets, current_offset=current_offset)
    
    def restore_indices(
        self,
        new_entries: list[LogEntryDisplay]
    ) -> list[int]:
        """Get row indices for entries that remain visible.
        
        Returns:
            List of row indices (in new_entries) that should be selected.
        
        Performance: O(m) where m = number of new visible entries.
        """
        indices = []
        for idx, entry in enumerate(new_entries):
            if entry.file_offset in self.offsets:
                indices.append(idx)
        return indices
```

### §4.3 Current Index for Keyboard Navigation

Qt's `QItemSelectionModel` maintains two distinct concepts:

1. **Selection** - Which rows are highlighted (can be multiple)
2. **Current Index** - The focused row for keyboard navigation (single)

When filters change, both must be preserved:

```
BEFORE filter change:
  1. Get selected entries → extract offsets
  2. Get current index entry → extract current_offset
  3. Store both in SelectionState

AFTER filter change:
  1. Restore selection using offsets
  2. Find current_offset in new entries
  3. Set current index using setCurrentIndex()
  4. Use QItemSelectionModel.NoUpdate flag to avoid changing selection
```

**Why this matters:** Without restoring current index, arrow key navigation (↑↓) 
starts from row 0 instead of the previously focused row, confusing users.

---

## §5 API Changes

### §5.1 LogTableView Additions

```python
class LogTableView(QTableView):
    # Existing signals
    selection_changed = Signal()
    find_requested = Signal()
    
    # New methods
    
    @beartype
    def get_selection_state(self) -> SelectionState:
        """Capture current selection state including current index.
        
        Returns:
            SelectionState containing identifiers for all selected rows
            and the current index for keyboard navigation.
        
        Performance: O(n) where n = number of selected rows.
        Thread: Main thread only (per docs/specs/global/threading.md §8.1).
        """
        entries = self.get_selected_entries()
        
        # Get current index for keyboard navigation
        current_index = self.selectionModel().currentIndex()
        current_entry = None
        if current_index.isValid():
            current_entry = self._model.get_entry(current_index.row())
        
        return SelectionState.from_entries(entries, current_entry)
    
    @beartype
    def restore_selection(self, state: SelectionState) -> bool:
        """Restore selection from a previous state.
        
        Args:
            state: Selection state captured before filter change.
            
        Returns:
            True if any selection was restored, False if all selected rows
            are now hidden.
        
        Side Effects:
            - Clears previous selection
            - Selects rows that remain visible
            - Restores current index for keyboard navigation
            - Scrolls to first selected row (if any)
            - Emits selection_changed signal
        
        Performance: O(m) where m = number of new visible entries.
        Thread: Main thread only.
        """
        ...
    
    @beartype
    def set_entries_preserve_selection(
        self, 
        entries: list[LogEntryDisplay]
    ) -> None:
        """Set entries while preserving selection for visible rows.
        
        Convenience method that combines get_selection_state(),
        set_entries(), and restore_selection().
        
        Args:
            entries: New filtered entries to display.
        
        Performance: O(n + m) where n = old entry count, m = new entry count.
        Thread: Main thread only.
        """
        state = self.get_selection_state()
        self.set_entries(entries)
        self.restore_selection(state)
```

### §5.2 MainController Changes

```python
class MainController(QObject):
    # Modified method
    
    def _apply_filters(self) -> None:
        """Apply current filters to entries with selection preservation.
        
        // Ref: docs/specs/features/selection-preservation.md §4
        // Master: docs/SPEC.md §1
        """
        if not self._all_entries:
            return
        
        # Step 1: Capture selection state BEFORE filter
        selection_state = self._window.get_log_table().get_selection_state()
        
        # Step 2: Compute filtered entries (existing logic)
        category_filter = self._filter_controller.get_filter()
        saved_text_filter = self._saved_filter_controller.get_combined_filter()
        
        # ... filter application logic ...
        
        # Step 3: Convert to display format
        display_entries = [
            LogEntryDisplay.from_log_entry(entry)
            for entry in self._filtered_entries
        ]
        
        # Step 4: Set entries and restore selection
        self._window.get_log_table().set_entries(display_entries)
        restored = self._window.get_log_table().restore_selection(selection_state)
        
        # Step 5: Update statistics
        self._update_statistics()
        
        # Optional: Log selection preservation result
        if selection_state.offsets:
            logger.debug(
                f"Selection preserved: {len(restored)}/{len(selection_state.offsets)} rows"
            )
```

---

## §6 Selection Model Integration

### §6.1 QItemSelectionModel Usage

The implementation uses Qt's `QItemSelectionModel` for selection management:

```python
def restore_selection(self, state: SelectionState) -> bool:
    """Implementation using QItemSelectionModel."""
    indices = state.restore_indices(self._model.get_entries())
    
    if not indices:
        self.clearSelection()
        return False
    
    # Build selection
    selection = QItemSelection()
    for row in indices:
        index = self._model.index(row, 0)
        selection.select(index, index)
    
    # Apply selection
    self.selectionModel().select(
        selection,
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
    )
    
    # Restore current index for keyboard navigation
    # This ensures arrow keys (↑↓) work from the correct position
    if state.current_offset is not None:
        for row in indices:
            entry = self._model.get_entry(row)
            if entry and entry.file_offset == state.current_offset:
                current_index = self._model.index(row, 0)
                self.selectionModel().setCurrentIndex(
                    current_index,
                    QItemSelectionModel.NoUpdate  # Don't change selection
                )
                break
    
    # Scroll to first selected row
    self.scrollTo(self._model.index(indices[0], 0))
    
    return True
```

**Key Points:**
- `setCurrentIndex()` sets the keyboard navigation position
- `QItemSelectionModel.NoUpdate` flag prevents changing the selection
- Current index is restored from `state.current_offset`

### §6.2 Signal Emission

```python
def restore_selection(self, state: SelectionState) -> bool:
    # ... selection restoration ...
    
    # Emit signal for dependent components
    self.selection_changed.emit()
    
    return len(indices) > 0
```

---

## §7 Viewport Position Preservation

### §7.1 Requirement

When filters or categories change, if the selected row remains in the filtered dataset, its position relative to the viewport must be preserved unchanged. The system must automatically adjust the scroll position to keep the selected entry at the same visual point on the screen, allowing the user to maintain visual context during display mode transitions.

### §7.2 Rationale

**Without viewport preservation:**
- User selects row in the middle of the screen
- User changes filter or toggles category
- Selected row might jump to top or bottom of viewport
- User loses visual context and must search for the selected row

**With viewport preservation:**
- User selects row at visual position Y (e.g., 50% down from top)
- User changes filter or toggles category
- Selected row remains at visual position Y
- User maintains visual context and can continue working immediately

### §7.3 ViewportState Extension

```python
@dataclass(frozen=True)
class ViewportState:
    """Snapshot of viewport position for preservation.
    
    Captures the visual position of the selected row relative to the viewport
    to enable precise restoration after filter changes.
    
    Attributes:
        selected_offset: file_offset of the selected row (or current index row)
        viewport_offset: Y position of selected row relative to viewport top.
            Positive value = pixels from viewport top.
            Used to restore the exact visual position after filter change.
        row_height: Height of the selected row in pixels (for variable-height rows).
            If None, uses default row height from table view.
    
    Performance: O(1) memory, no allocations.
    Thread: Main thread only (per docs/specs/global/threading.md §8.1).
    """
    selected_offset: int
    viewport_offset: int
    row_height: int | None = None
```

### §7.4 Algorithm

```
BEFORE filter change:
  1. Get current selected row (or current index for keyboard navigation)
  2. Get row's Y coordinate relative to viewport top:
     viewport_offset = rowViewportPosition(row) - verticalScrollBar().value()
  3. Store ViewportState with selected_offset and viewport_offset

AFTER filter change:
  1. Restore selection (per §4)
  2. Find selected row in new entries using selected_offset
  3. If found:
     a. Calculate new scroll position:
        new_scroll_value = rowViewportPosition(new_row) - viewport_offset
     b. Apply scroll:
        verticalScrollBar().setValue(new_scroll_value)
  4. If not found:
     a. Fall back to default behavior (scroll to first selected row)
```

### §7.5 API Additions

```python
class LogTableView(QTableView):
    # Additional methods for viewport preservation
    
    @beartype
    def get_viewport_state(self) -> ViewportState | None:
        """Capture current viewport position for preservation.
        
        Returns:
            ViewportState if a row is selected or has current index,
            None if no selection and no current index.
        
        Performance: O(1).
        Thread: Main thread only.
        
        Note:
            Uses current index (keyboard navigation position) if set,
            otherwise uses first selected row.
        """
        # Get current index (keyboard navigation position)
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            row = current_index.row()
            entry = self._model.get_entry(row)
            if entry:
                viewport_offset = self.rowViewportPosition(row) - self.verticalScrollBar().value()
                return ViewportState(
                    selected_offset=entry.file_offset,
                    viewport_offset=viewport_offset,
                    row_height=self.rowHeight(row)
                )
        
        # Fall back to first selected row
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            entry = self._model.get_entry(row)
            if entry:
                viewport_offset = self.rowViewportPosition(row) - self.verticalScrollBar().value()
                return ViewportState(
                    selected_offset=entry.file_offset,
                    viewport_offset=viewport_offset,
                    row_height=self.rowHeight(row)
                )
        
        return None
    
    @beartype
    def restore_viewport_position(self, state: ViewportState) -> bool:
        """Restore viewport position from a previous state.
        
        Args:
            state: Viewport state captured before filter change.
            
        Returns:
            True if viewport position was restored, False if row not found.
        
        Side Effects:
            - Adjusts vertical scroll bar to restore visual position
            - Does NOT change selection (selection is handled separately)
        
        Performance: O(m) where m = number of visible entries.
        Thread: Main thread only.
        """
        # Find row by file_offset
        for row in range(self._model.rowCount()):
            entry = self._model.get_entry(row)
            if entry and entry.file_offset == state.selected_offset:
                # Calculate scroll position to restore viewport offset
                row_y = self.rowViewportPosition(row)
                new_scroll_value = row_y - state.viewport_offset
                
                # Clamp to valid scroll range
                scroll_bar = self.verticalScrollBar()
                new_scroll_value = max(0, min(new_scroll_value, scroll_bar.maximum()))
                
                scroll_bar.setValue(new_scroll_value)
                return True
        
        return False
```

### §7.6 Integration with Selection Preservation

```python
def set_entries_preserve_selection_and_viewport(
    self, 
    entries: list[LogEntryDisplay]
) -> None:
    """Set entries while preserving both selection and viewport position.
    
    Complete preservation flow:
    1. Capture selection state (selected rows + current index)
    2. Capture viewport state (visual position)
    3. Set new entries
    4. Restore selection
    5. Restore viewport position
    
    Args:
        entries: New filtered entries to display.
    
    Performance: O(n + m) where n = old entry count, m = new entry count.
    Thread: Main thread only.
    """
    # Capture states BEFORE
    selection_state = self.get_selection_state()
    viewport_state = self.get_viewport_state()
    
    # Apply new entries
    self.set_entries(entries)
    
    # Restore states AFTER
    self.restore_selection(selection_state)
    
    if viewport_state:
        self.restore_viewport_position(viewport_state)
```

### §7.7 Edge Cases

| Edge Case | Resolution |
|-----------|------------|
| No selection and no current index | `get_viewport_state()` returns `None`, skip viewport restoration |
| Selected row not in new filter | `restore_viewport_position()` returns `False`, fall back to default scroll |
| Viewport offset exceeds scroll range | Clamp to valid scroll range (0 to maximum) |
| Variable row heights | Use stored `row_height` for adjustment (if needed) |
| Partial row visibility | Preserve exact pixel offset, even if row is partially visible |

### §7.8 Performance Budget

| Operation | Budget | Target |
|-----------|--------|--------|
| `get_viewport_state()` | < 1ms | O(1) operation |
| `restore_viewport_position()` | < 5ms | O(m) where m = visible entries |
| Combined with selection | < 20ms | Total filter change cycle |

### §7.9 Scroll Mode Considerations

#### §7.9.1 Qt Scroll Modes

Qt's `QTableView` supports two scroll modes that affect how scroll values are interpreted:

| Mode | Scroll Value Unit | Activation |
|------|-------------------|-------------|
| `ScrollPerItem` | **Rows** (integer) | Default for QTableView |
| `ScrollPerPixel` | **Pixels** (integer) | Requires explicit activation |

**Critical:** The implementation MUST account for the scroll mode when calculating viewport restoration. Using the wrong unit leads to incorrect scroll positions.

#### §7.9.2 Scroll Mode Detection

```python
def get_scroll_mode(self) -> ScrollMode:
    """Detect current scroll mode.
    
    Returns:
        ScrollPerItem if scroll value is in rows.
        ScrollPerPixel if scroll value is in pixels.
    """
    return self.verticalScrollMode()
```

#### §7.9.3 Viewport Offset Capture (ScrollPerItem Mode)

When using `ScrollPerItem` mode (default), the viewport offset is captured in **pixels** but the scroll value is in **rows**:

```python
def get_viewport_state(self) -> ViewportState | None:
    # rowViewportPosition() returns pixels from viewport top
    # This is ALWAYS in pixels, regardless of scroll mode
    viewport_y = self.rowViewportPosition(row)  # PIXELS
    
    # rowHeight() returns the row height in PIXELS
    row_height = self.rowHeight(row)  # PIXELS
    
    # Store viewport offset in PIXELS
    return ViewportState(
        selected_offset=entry.file_offset,
        viewport_offset=viewport_y,  # PIXELS
        row_height=row_height         # PIXELS
    )
```

**Key Insight:** `rowViewportPosition()` always returns pixels, regardless of scroll mode. This is the viewport-relative Y coordinate of the row.

#### §7.9.4 Viewport Position Restoration (ScrollPerItem Mode)

When using `ScrollPerItem` mode, the scroll value must be calculated in **rows**:

```python
def restore_viewport_position(self, state: ViewportState) -> bool:
    # Find row by file_offset
    for row in range(self._model.rowCount()):
        entry = self._model.get_entry(row)
        if entry and entry.file_offset == state.selected_offset:
            # Convert viewport offset from PIXELS to ROWS
            # viewport_offset is in pixels, row_height is in pixels
            # viewport_offset_rows is how many rows to scroll up
            row_height = state.row_height if state.row_height else self.rowHeight(row)
            viewport_offset_rows = state.viewport_offset / row_height
            
            # Calculate new scroll value in ROWS
            # We want the row to appear at viewport_offset from top
            # So we scroll to (row - viewport_offset_rows)
            new_scroll_value = row - viewport_offset_rows
            
            # Clamp to valid scroll range
            scroll_bar = self.verticalScrollBar()
            clamped_scroll = max(0, min(new_scroll_value, scroll_bar.maximum()))
            
            # Set scroll value (in ROWS for ScrollPerItem mode)
            scroll_bar.setValue(int(clamped_scroll))
            return True
    
    return False
```

#### §7.9.5 Conversion Formulas

**ScrollPerItem Mode (Default):**

| Operation | Formula | Units |
|-----------|---------|-------|
| Capture viewport offset | `viewport_offset = rowViewportPosition(row)` | Pixels |
| Convert to rows | `viewport_offset_rows = viewport_offset / row_height` | Rows |
| Calculate scroll | `new_scroll = row - viewport_offset_rows` | Rows |
| Set scroll | `scroll_bar.setValue(int(new_scroll))` | Rows |

**ScrollPerPixel Mode (Alternative):**

| Operation | Formula | Units |
|-----------|---------|-------|
| Capture viewport offset | `viewport_offset = rowViewportPosition(row)` | Pixels |
| Get content Y | `row_content_y = rowViewportPosition(row) + scroll_value` | Pixels |
| Calculate scroll | `new_scroll = row_content_y - viewport_offset` | Pixels |
| Set scroll | `scroll_bar.setValue(int(new_scroll))` | Pixels |

#### §7.9.6 Why Scroll Mode Matters

**Bug Example (ScrollPerItem mode with pixel-based calculation):**

```python
# WRONG: Treating scroll as pixels in ScrollPerItem mode
row_content_y = rowViewportPosition(row) + scroll_value  # scroll_value is in ROWS!
new_scroll = row_content_y - viewport_offset  # WRONG: mixing rows and pixels
# Result: Row disappears from viewport (scroll value way too large)
```

**Correct Implementation (ScrollPerItem mode):**

```python
# CORRECT: Convert viewport offset to rows first
viewport_offset_rows = viewport_offset / row_height  # Convert pixels to rows
new_scroll = row - viewport_offset_rows  # All values in ROWS
# Result: Row appears at correct viewport position
```

#### §7.9.7 Implementation Notes

1. **Always use `ScrollPerItem` mode** (default) for log table view - it provides better performance with large datasets.

2. **Never mix units** - viewport offset is always in pixels, scroll value unit depends on scroll mode.

3. **Test scroll mode changes** - if switching to `ScrollPerPixel`, update the restoration formula accordingly.

4. **Row height must be consistent** - variable row heights require additional handling (store per-row height in ViewportState).

---

## §8 Performance Considerations

### §8.1 Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `get_selection_state()` | O(s) | s = number of selected rows |
| `restore_selection()` | O(m) | m = number of new visible entries |
| `set_entries_preserve_selection()` | O(n + m) | n = old entries, m = new entries |
| `get_viewport_state()` | O(1) | Single row lookup |
| `restore_viewport_position()` | O(m) | m = number of visible entries |

### §8.2 Memory Overhead

| Data | Size | Notes |
|------|------|-------|
| `SelectionState` | O(s) | s = selected rows, stores int offsets (8 bytes each) |
| `ViewportState` | O(1) | Fixed size: 2 ints + optional int |
| `file_offset` | 8 bytes | Compact integer, no string storage needed |

### §8.3 Performance Budget

Per [docs/SPEC.md §7](docs/SPEC.md):

| Operation | Budget | Target |
|-----------|--------|--------|
| Selection capture | < 5ms | For 1000 selected rows |
| Selection restore | < 10ms | For 100K visible entries |
| Viewport capture | < 1ms | O(1) operation |
| Viewport restore | < 5ms | For 100K visible entries |
| Full cycle | < 20ms | Combined with filter application |

---

## §9 Edge Cases

### §9.1 Empty Selection

```python
# When no rows are selected before filter change:
state = SelectionState(offsets=frozenset(), timestamp=datetime.now())
# restore_selection() returns False, no rows selected
```

### §9.2 All Selected Rows Hidden

```python
# When all previously selected rows are filtered out:
state.offsets = {offset1, offset2, offset3}
new_entries = [...]  # None of offset1, offset2, offset3 present
indices = state.restore_indices(new_entries)  # Returns []
# Selection is cleared, restore_selection() returns False
```

### §9.3 Partial Selection Preservation

```python
# When some selected rows remain visible:
state.offsets = {offset1, offset2, offset3}
new_entries = [entry_with_offset1, entry_with_offset2, other_entry]
indices = state.restore_indices(new_entries)  # Returns [0, 1]
# Rows 0 and 1 are selected, offset3 is discarded
```

### §9.4 Model Reset During Selection

```python
# set_entries() calls beginResetModel() / endResetModel()
# Selection must be restored AFTER endResetModel()
# Implementation uses QTimer.singleShot(0, ...) if needed
```

---

## §10 Thread Safety

### §10.1 Thread Affinity

Per [docs/specs/global/threading.md §8.1](docs/specs/global/threading.md):

- All selection operations must run on the **main thread**
- `SelectionState` is not thread-safe; do not pass between threads
- Signal emission is thread-safe via Qt's queued connection

### §10.2 Concurrent Modifications

| Scenario | Resolution |
|----------|------------|
| Filter changes during selection | Qt event loop serializes; no race condition |
| Multiple rapid filter changes | Each filter change captures current state before applying |
| Selection change during filter | Last operation wins; acceptable behavior |

---

## §11 Error Handling

### §11.1 Error Scenarios

| Error | Handling | User Impact |
|-------|----------|-------------|
| `file_offset` is invalid | Log warning, skip entry | Partial selection restored |
| Model reset fails | Log error, clear selection | Selection lost, app continues |
| Index out of bounds | Skip invalid indices | Partial selection restored |

### §11.2 Recovery Strategy

```python
def restore_selection(self, state: SelectionState) -> bool:
    try:
        indices = state.restore_indices(self._model.get_entries())
        # ... apply selection ...
    except Exception as e:
        logger.warning(f"Selection restoration failed: {e}")
        self.clearSelection()
        return False
```

---

## §12 Testing Requirements

### §12.1 Unit Tests

| Test | File | Coverage |
|------|------|----------|
| `SelectionState.from_entries()` | `test_selection_state.py` | State creation with file_offset |
| `SelectionState.from_entries() with current_entry` | `test_selection_state.py` | Current index capture |
| `SelectionState.restore_indices()` | `test_selection_state.py` | Index mapping |
| `LogEntryDisplay.file_offset` | `test_log_table_view.py` | Field propagation |
| `LogTableView.get_selection_state()` | `test_log_table_view.py` | State capture with current index |
| `LogTableView.restore_selection()` | `test_log_table_view.py` | State restoration with current index |
| `ViewportState` creation | `test_selection_state.py` | Viewport state dataclass |
| `LogTableView.get_viewport_state()` | `test_log_table_view.py` | Viewport state capture |
| `LogTableView.restore_viewport_position()` | `test_log_table_view.py` | Viewport position restoration |

### §12.2 Integration Tests

| Test | File | Coverage |
|------|------|----------|
| Filter change preserves visible selection | `test_integration.py` | End-to-end flow |
| Category toggle preserves visible selection | `test_integration.py` | End-to-end flow |
| Level toggle preserves visible selection | `test_integration.py` | End-to-end flow |
| Hidden rows lose selection | `test_integration.py` | Edge case |
| Empty selection handling | `test_integration.py` | Edge case |
| Viewport position preserved on filter change | `test_integration.py` | End-to-end viewport preservation |
| Viewport position preserved on category toggle | `test_integration.py` | End-to-end viewport preservation |
| Viewport fallback when row hidden | `test_integration.py` | Edge case |

### §12.3 Test Scenarios

```python
def test_selection_preserved_on_filter_change():
    """Selection should be preserved for visible rows."""
    # Setup: Load file with entries A, B, C, D
    # Select rows A, B, C
    # Apply filter that hides C
    # Verify: A, B still selected, C not in selection
    
def test_selection_cleared_for_hidden_rows():
    """Selection should be cleared for hidden rows."""
    # Setup: Load file with entries A, B, C
    # Select rows A, B, C
    # Apply filter that hides all
    # Verify: No rows selected
    
def test_selection_preserved_on_category_toggle():
    """Selection should survive category toggle."""
    # Setup: Load file with categories Cat1, Cat2
    # Select rows from both categories
    # Uncheck Cat2
    # Verify: Only Cat1 rows selected
    
def test_empty_selection_before_filter():
    """Empty selection should remain empty."""
    # Setup: Load file, no selection
    # Apply filter
    # Verify: Still no selection

def test_viewport_position_preserved_on_filter_change():
    """Viewport position should be preserved for selected row."""
    # Setup: Load file with entries A, B, C, D, E
    # Select row C (in middle of viewport)
    # Record viewport position: C is at Y pixels from top
    # Apply filter that hides B
    # Verify: C is still at Y pixels from top
    
def test_viewport_position_preserved_on_category_toggle():
    """Viewport position should survive category toggle."""
    # Setup: Load file with categories Cat1, Cat2
    # Select row from Cat1 (at Y pixels from top)
    # Toggle Cat2 off
    # Verify: Selected row still at Y pixels from top
    
def test_viewport_fallback_when_row_hidden():
    """Viewport should use default scroll when selected row is hidden."""
    # Setup: Load file with entries A, B, C
    # Select row B
    # Apply filter that hides B
    # Verify: Default scroll behavior (to first selected or top)
```

---

## §13 Implementation Checklist

### §13.1 New Files

| File | Purpose |
|------|---------|
| `src/models/selection_state.py` | `SelectionState` class (uses `file_offset` for identification), `ViewportState` class |

### §13.2 Modified Files

| File | Changes |
|------|---------|
| `src/views/log_table_view.py` | Add `file_offset` to `LogEntryDisplay`, add `get_selection_state()`, `restore_selection()`, `get_viewport_state()`, `restore_viewport_position()`, `set_entries_preserve_selection_and_viewport()` |
| `src/controllers/main_controller.py` | Modify `_apply_filters()` to use selection and viewport preservation |
| `tests/test_selection_preservation.py` | New test file for selection preservation |
| `tests/test_integration.py` | Add integration tests for selection and viewport preservation |

---

## §14 Dependencies

### §14.1 Internal Dependencies

- [docs/specs/features/ui-components.md](ui-components.md) - LogTableView
- [docs/specs/features/main-controller.md](main-controller.md) - MainController
- [docs/specs/features/filter-controller.md](filter-controller.md) - FilterController
- [docs/specs/global/threading.md](../global/threading.md) - Thread safety

### §14.2 Qt Dependencies

- `QItemSelectionModel` - Selection management
- `QItemSelection` - Selection ranges
- `QModelIndex` - Model indices

---

## §15 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.4 | 2026-03-18 | Removed lazy loading references (memory model now uses full load). Updated §3.1 and §3.2 to remove lazy loading justification. |
| 1.3 | 2026-03-15 | Added §7.9 Scroll Mode Considerations. Documented the critical difference between `ScrollPerItem` mode (scroll in rows) and `ScrollPerPixel` mode (scroll in pixels). Added conversion formulas for viewport offset between pixels and rows. Added bug example showing incorrect pixel-based calculation in ScrollPerItem mode. |
| 1.2 | 2026-03-15 | Added viewport position preservation (§7). When filters or categories change, the selected row's visual position relative to the viewport is preserved. Added `ViewportState` class, `get_viewport_state()`, `restore_viewport_position()`, and `set_entries_preserve_selection_and_viewport()` methods. |
| 1.1 | 2026-03-15 | Added current index preservation for keyboard navigation (↑↓). Added `current_offset` field to `SelectionState`. Updated `get_selection_state()` to capture current index. Updated `restore_selection()` to restore current index using `setCurrentIndex()` with `NoUpdate` flag. |
| 1.0 | 2026-03-15 | Initial specification |