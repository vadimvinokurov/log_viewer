# Saved Filters Implementation Plan

**Version:** 1.0
**Created:** 2026-03-14
**Status:** READY FOR DELEGATION
**Spec Reference:** [docs/specs/features/saved-filters.md](../docs/specs/features/saved-filters.md)

---

## Overview

This plan breaks down the implementation of the Saved Filters feature into discrete tasks for delegation to spec-coder agents.

### Feature Summary

- Save frequently-used filter configurations
- Display saved filters in Filters tab of CategoryPanel
- Enable/disable filters via checkboxes
- Combine multiple enabled filters with OR logic
- Persist filters via QSettings

### Dependencies

- **filter-controller.md**: FilterState, FilterMode, FilterEngine
- **settings-manager.md**: QSettings persistence
- **ui-components.md**: CategoryPanel structure
- **threading.md**: Main thread only operations
- **memory-model.md**: Qt parent-child ownership

---

## Task Breakdown

### T-001: Create SavedFilter Model and SavedFilterStore

**Type:** NEW FILE
**Priority:** HIGH (foundation for other tasks)
**Estimated Time:** 1-2 hours

#### Files to Create

- `src/models/saved_filter.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §2.1, §2.2

#### Implementation Details

```python
# src/models/saved_filter.py

from __future__ import annotations
from beartype import beartype
from dataclasses import dataclass
from typing import TYPE_CHECKING
import uuid
import time

if TYPE_CHECKING:
    from src.models.filter_state import FilterMode

@dataclass
class SavedFilter:
    """Saved filter configuration.
    
    // Ref: docs/specs/features/saved-filters.md §2.1
    """
    id: str                    # Unique identifier (UUID)
    name: str                   # User-visible name
    filter_text: str            # Filter text content
    filter_mode: FilterMode     # Plain, Regex, or Simple
    created_at: float           # Unix timestamp
    enabled: bool = True       # Whether filter is currently active


class SavedFilterStore:
    """Manages saved filters collection.
    
    // Ref: docs/specs/features/saved-filters.md §2.2
    // Persists to QSettings via SettingsManager
    """
    
    @beartype
    def __init__(self) -> None:
        """Initialize the store."""
        self._filters: dict[str, SavedFilter] = {}
    
    @beartype
    def add_filter(self, filter: SavedFilter) -> str:
        """Add new filter, return ID."""
        
    @beartype
    def remove_filter(self, id: str) -> bool:
        """Remove filter by ID, return success."""
        
    @beartype
    def rename_filter(self, id: str, new_name: str) -> bool:
        """Rename filter, return success."""
        
    @beartype
    def set_enabled(self, id: str, enabled: bool) -> bool:
        """Toggle filter enabled state."""
        
    @beartype
    def get_enabled_filters(self) -> list[SavedFilter]:
        """Get all enabled filters."""
        
    @beartype
    def get_all_filters(self) -> list[SavedFilter]:
        """Get all filters (enabled and disabled)."""
```

#### Constraints

- **Thread Context:** Main thread only (per [threading.md](../docs/specs/global/threading.md) §8.1)
- **Memory:** Stack-allocated dataclass, dict for O(1) lookup
- **Performance:** O(1) add/remove/lookup, O(n) for get_all_filters
- **Type Safety:** All public methods decorated with `@beartype`

#### Tests Required

- Unit test: `tests/test_saved_filter.py`
  - Test SavedFilter creation
  - Test SavedFilterStore CRUD operations
  - Test filter combination (OR logic)

---

### T-002: Create SavedFilterController

**Type:** NEW FILE
**Priority:** HIGH (coordinates all operations)
**Estimated Time:** 2-3 hours
**Depends On:** T-001

#### Files to Create

- `src/controllers/saved_filter_controller.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §5.1

#### Implementation Details

```python
# src/controllers/saved_filter_controller.py

from __future__ import annotations
from beartype import beartype
from typing import TYPE_CHECKING, Callable
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from src.models.saved_filter import SavedFilter
    from src.utils.settings_manager import SettingsManager
    from src.models.filter_state import FilterMode
    from src.models.log_entry import LogEntry

class SavedFilterController(QObject):
    """Controller for saved filter operations.
    
    // Ref: docs/specs/features/saved-filters.md §5.1
    """
    
    # Signals
    filters_changed = Signal()              # Filter list changed
    filter_applied = Signal()                # Combined filter applied
    
    @beartype
    def __init__(
        self, 
        settings_manager: SettingsManager, 
        parent: QObject | None = None
    ) -> None:
        """Initialize controller with settings manager."""
        
    @beartype
    def save_filter(
        self, 
        text: str, 
        mode: FilterMode, 
        name: str | None = None
    ) -> str:
        """Save a new filter, return ID."""
        
    @beartype
    def delete_filter(self, filter_id: str) -> bool:
        """Delete a saved filter."""
        
    @beartype
    def rename_filter(self, filter_id: str, new_name: str) -> bool:
        """Rename a saved filter."""
        
    @beartype
    def set_filter_enabled(self, filter_id: str, enabled: bool) -> None:
        """Enable/disable a saved filter."""
        
    def get_combined_filter(self) -> Callable[[LogEntry], bool] | None:
        """Get combined filter for all enabled saved filters.
        
        Returns:
            Callable that returns True if entry matches ANY enabled filter,
            or None if no filters are enabled.
        """
        
    @beartype
    def get_all_filters(self) -> list[SavedFilter]:
        """Get all saved filters."""
```

#### Constraints

- **Thread Context:** Main thread only (per [threading.md](../docs/specs/global/threading.md) §8.1)
- **Memory:** Owned by MainController (Qt parent-child)
- **Performance:** Filter compilation on-demand, cached until filter list changes
- **Type Safety:** All public methods decorated with `@beartype`

#### Tests Required

- Unit test: `tests/test_saved_filter.py`
  - Test save/delete/rename operations
  - Test filter combination (OR logic)
  - Test settings persistence

---

### T-003: Create FiltersTabContent UI Component

**Type:** NEW FILE
**Priority:** MEDIUM (UI component)
**Estimated Time:** 2-3 hours
**Depends On:** T-001

#### Files to Create

- `src/views/components/filters_tab.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §4.2

#### Implementation Details

```python
# src/views/components/filters_tab.py

from __future__ import annotations
from beartype import beartype
from typing import TYPE_CHECKING
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QListWidgetItem, QPushButton, QLabel
)

if TYPE_CHECKING:
    from src.models.saved_filter import SavedFilter

class FiltersTabContent(QWidget):
    """Content for the Filters tab in CategoryPanel.
    
    // Ref: docs/specs/features/saved-filters.md §4.2
    """
    
    # Signals
    filter_enabled_changed = Signal(str, bool)  # filter_id, enabled
    filter_deleted = Signal(str)                 # filter_id
    filter_renamed = Signal(str, str)            # filter_id, new_name
    
    @beartype
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the filters tab content."""
        
    @beartype
    def set_filters(self, filters: list[SavedFilter]) -> None:
        """Populate filter list."""
        
    @beartype
    def add_filter(self, filter: SavedFilter) -> None:
        """Add single filter to list."""
        
    @beartype
    def remove_filter(self, filter_id: str) -> None:
        """Remove filter from list."""
```

#### UI Layout

```
┌─────────────────────────────────────┐
│ QListWidget                         │
│ ┌─────────────────────────────────┐ │
│ │ ☑ Filter Name                   │ │
│ │   "error|warning" [Plain]        │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ ☐ Network Issues                │ │
│ │   "network.*timeout" [Regex]     │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ [Delete] [Rename]                   │
└─────────────────────────────────────┘
```

#### Constraints

- **Thread Context:** Main thread only (Qt UI component)
- **Memory:** Qt parent-child ownership (parent: CategoryPanel)
- **Performance:** O(n) to populate list, O(1) for single add/remove
- **Type Safety:** All public methods decorated with `@beartype`

#### Tests Required

- Unit test: `tests/test_saved_filter.py`
  - Test UI signal emissions
  - Test checkbox toggle
  - Test inline rename

---

### T-004: Modify SearchToolbar to Add Save Button

**Type:** MODIFY EXISTING FILE
**Priority:** MEDIUM (UI integration)
**Estimated Time:** 1 hour
**Depends On:** T-002

#### Files to Modify

- `src/views/widgets/search_toolbar.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §4.1

#### Changes Required

1. Add save button next to filter mode dropdown
2. Add `save_filter_requested` signal
3. Connect button to signal emission
4. Disable button when filter text is empty

#### Implementation Details

```python
# In SearchToolbar class

# New signal
save_filter_requested = Signal(str, str)  # filter_text, mode

def _setup_ui(self) -> None:
    # ... existing code ...
    
    # Add save button after mode dropdown
    self._save_button = QPushButton("💾")
    self._save_button.setToolTip("Save current filter")
    self._save_button.setFixedSize(24, 24)
    self._save_button.clicked.connect(self._on_save_clicked)
    
    # Initially disabled
    self._save_button.setEnabled(False)
    
def _on_save_clicked(self) -> None:
    """Handle save button click."""
    text = self._search_input.text().strip()
    mode = self._mode_combo.currentData()
    if text:
        self.save_filter_requested.emit(text, mode)

def _on_text_changed(self, text: str) -> None:
    """Enable/disable save button based on text."""
    self._save_button.setEnabled(bool(text.strip()))
```

#### Constraints

- **Thread Context:** Main thread only (Qt UI component)
- **Memory:** Button owned by SearchToolbar (Qt parent-child)
- **Performance:** O(1) for button state update
- **Type Safety:** Signal parameters typed

---

### T-005: Modify CategoryPanel to Integrate Filters Tab

**Type:** MODIFY EXISTING FILE
**Priority:** MEDIUM (UI integration)
**Estimated Time:** 1-2 hours
**Depends On:** T-003

#### Files to Modify

- `src/views/category_panel.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §4.3

#### Changes Required

1. Import FiltersTabContent
2. Replace placeholder Filters tab with FiltersTabContent
3. Add signals for saved filter operations
4. Connect FiltersTabContent signals to CategoryPanel signals

#### Implementation Details

```python
# In CategoryPanel class

# New signals
saved_filter_enabled_changed = Signal(str, bool)  # filter_id, enabled
saved_filter_deleted = Signal(str)                 # filter_id
saved_filter_renamed = Signal(str, str)            # filter_id, new_name

def _setup_ui(self) -> None:
    # ... existing code ...
    
    # Replace placeholder with actual Filters tab content
    self._filters_content = FiltersTabContent()
    filters_layout = QVBoxLayout(self._filters_tab)
    filters_layout.setContentsMargins(4, 4, 4, 4)
    filters_layout.addWidget(self._filters_content)
    
    # Connect signals
    self._filters_content.filter_enabled_changed.connect(
        self.saved_filter_enabled_changed
    )
    self._filters_content.filter_deleted.connect(
        self.saved_filter_deleted
    )
    self._filters_content.filter_renamed.connect(
        self.saved_filter_renamed
    )
```

#### Constraints

- **Thread Context:** Main thread only (Qt UI component)
- **Memory:** FiltersTabContent owned by CategoryPanel (Qt parent-child)
- **Performance:** O(1) for signal forwarding
- **Type Safety:** Signal parameters typed

---

### T-006: Modify MainController to Integrate SavedFilterController

**Type:** MODIFY EXISTING FILE
**Priority:** HIGH (core integration)
**Estimated Time:** 2-3 hours
**Depends On:** T-002, T-004, T-005

#### Files to Modify

- `src/controllers/main_controller.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §5.2

#### Changes Required

1. Import SavedFilterController
2. Create SavedFilterController instance
3. Connect SearchToolbar save signal
4. Connect CategoryPanel filter signals
5. Modify `_apply_filters()` to combine saved filters with category filters
6. Implement `_on_save_filter_requested()`
7. Implement `_on_saved_filters_applied()`

#### Implementation Details

```python
# In MainController class

def __init__(self, window: MainWindow, settings_manager: SettingsManager):
    # ... existing code ...
    
    # Add saved filter controller
    self._saved_filter_controller = SavedFilterController(
        settings_manager, 
        self
    )
    
    # Connect signals
    self._saved_filter_controller.filter_applied.connect(
        self._on_saved_filters_applied
    )

def _connect_signals(self) -> None:
    # ... existing code ...
    
    # Connect SearchToolbar save signal
    self._window.get_search_toolbar().save_filter_requested.connect(
        self._on_save_filter_requested
    )
    
    # Connect CategoryPanel filter signals
    self._window.get_category_panel().saved_filter_enabled_changed.connect(
        self._on_saved_filter_enabled_changed
    )
    self._window.get_category_panel().saved_filter_deleted.connect(
        self._on_saved_filter_deleted
    )
    self._window.get_category_panel().saved_filter_renamed.connect(
        self._on_saved_filter_renamed
    )

def _on_save_filter_requested(self, text: str, mode: str) -> None:
    """Handle save filter request from SearchToolbar."""
    from src.models.filter_state import FilterMode
    mode_map = {
        "plain": FilterMode.PLAIN,
        "regex": FilterMode.REGEX,
        "simple": FilterMode.SIMPLE,
    }
    filter_mode = mode_map.get(mode, FilterMode.PLAIN)
    self._saved_filter_controller.save_filter(text, filter_mode)

def _on_saved_filters_applied(self) -> None:
    """Re-apply filters when saved filters change."""
    self._apply_filters()

def _apply_filters(self) -> None:
    """Apply current filters to entries."""
    if not self._all_entries:
        return
    
    # Get category filter
    category_filter = self._filter_controller.get_filter()
    
    # Get saved text filter (combined OR)
    saved_text_filter = self._saved_filter_controller.get_combined_filter()
    
    # Combine filters with AND logic
    if category_filter is None and saved_text_filter is None:
        self._filtered_entries = self._all_entries.copy()
    elif category_filter is None:
        self._filtered_entries = [
            e for e in self._all_entries if saved_text_filter(e)
        ]
    elif saved_text_filter is None:
        self._filtered_entries = [
            e for e in self._all_entries if category_filter(e)
        ]
    else:
        self._filtered_entries = [
            e for e in self._all_entries 
            if category_filter(e) and saved_text_filter(e)
        ]
    
    # Update display
    self._window.get_log_table().set_entries(
        [LogEntryDisplay.from_log_entry(e) for e in self._filtered_entries]
    )
    self._update_statistics()
```

#### Constraints

- **Thread Context:** Main thread only (per [threading.md](../docs/specs/global/threading.md) §8.1)
- **Memory:** SavedFilterController owned by MainController (Qt parent-child)
- **Performance:** Filter application < 50ms for 100K entries (per [SPEC.md](../docs/SPEC.md) §7)
- **Type Safety:** All public methods decorated with `@beartype`

---

### T-007: Add saved_filters Key to SettingsManager

**Type:** MODIFY EXISTING FILE
**Priority:** MEDIUM (persistence)
**Estimated Time:** 30 minutes
**Depends On:** T-001

#### Files to Modify

- `src/utils/settings_manager.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §6.1

#### Changes Required

1. Add `KEY_SAVED_FILTERS = "saved_filters"` constant
2. Add `save_saved_filters()` method
3. Add `load_saved_filters()` method

#### Implementation Details

```python
# In SettingsManager class

KEY_SAVED_FILTERS = "savedFilters"

@beartype
def save_saved_filters(self, filters: list[dict[str, Any]]) -> None:
    """Save saved filters.
    
    Args:
        filters: List of filter dictionaries with keys:
            - id: str
            - name: str
            - filter_text: str
            - filter_mode: str
            - created_at: float
            - enabled: bool
    """
    self._settings.setValue(self.KEY_SAVED_FILTERS, json.dumps(filters))

def load_saved_filters(self) -> list[dict[str, Any]]:
    """Load saved filters.
    
    Returns:
        List of filter dictionaries, or empty list if not set.
    """
    data = self._settings.value(self.KEY_SAVED_FILTERS, "[]")
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        logger.warning(f"Failed to load saved filters: {e}")
        return []
```

#### Constraints

- **Thread Context:** Main thread only (per [settings-manager.md](../docs/specs/features/settings-manager.md) §3.2)
- **Memory:** JSON serialization, O(n) where n = number of filters
- **Performance:** < 5ms for typical filter list (per [settings-manager.md](../docs/specs/features/settings-manager.md) §8.1)
- **Type Safety:** All public methods decorated with `@beartype`

---

### T-008: Create Unit Tests for SavedFilter Components

**Type:** NEW FILE
**Priority:** MEDIUM (quality assurance)
**Estimated Time:** 2-3 hours
**Depends On:** T-001, T-002, T-003

#### Files to Create

- `tests/test_saved_filter.py`

#### Spec Reference

- [saved-filters.md](../docs/specs/features/saved-filters.md) §10

#### Test Coverage

1. **SavedFilter Model Tests**
   - Test SavedFilter creation with all fields
   - Test default enabled=True
   - Test UUID generation

2. **SavedFilterStore Tests**
   - Test add_filter()
   - Test remove_filter()
   - Test rename_filter()
   - Test set_enabled()
   - Test get_enabled_filters()
   - Test get_all_filters()

3. **SavedFilterController Tests**
   - Test save_filter()
   - Test delete_filter()
   - Test rename_filter()
   - Test set_filter_enabled()
   - Test get_combined_filter() with no filters
   - Test get_combined_filter() with one filter
   - Test get_combined_filter() with multiple filters (OR logic)
   - Test settings persistence

4. **FiltersTabContent Tests**
   - Test set_filters()
   - Test add_filter()
   - Test remove_filter()
   - Test checkbox toggle signal
   - Test delete button signal
   - Test rename button signal

5. **Integration Tests**
   - Test save from toolbar
   - Test enable/disable in panel
   - Test combined filtering (saved + category + level)

#### Test Template

```python
# tests/test_saved_filter.py

from __future__ import annotations
from beartype import beartype
import pytest
from unittest.mock import Mock, patch
from PySide6.QtCore import Qt

from src.models.saved_filter import SavedFilter, SavedFilterStore
from src.controllers.saved_filter_controller import SavedFilterController
from src.views.components.filters_tab import FiltersTabContent


class TestSavedFilter:
    """Tests for SavedFilter model."""
    
    def test_create_saved_filter(self):
        """Test SavedFilter creation."""
        filter = SavedFilter(
            id="test-id",
            name="Test Filter",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=1700000000.0,
            enabled=True
        )
        
        assert filter.id == "test-id"
        assert filter.name == "Test Filter"
        assert filter.filter_text == "error"
        assert filter.filter_mode == FilterMode.PLAIN
        assert filter.enabled is True


class TestSavedFilterStore:
    """Tests for SavedFilterStore."""
    
    def test_add_filter(self):
        """Test adding a filter."""
        store = SavedFilterStore()
        filter = SavedFilter(
            id="test-id",
            name="Test",
            filter_text="error",
            filter_mode=FilterMode.PLAIN,
            created_at=1700000000.0
        )
        
        result = store.add_filter(filter)
        
        assert result == "test-id"
        assert len(store.get_all_filters()) == 1
    
    # ... more tests ...
```

---

## Dependency Graph

```
T-001 (SavedFilter model)
  ├── T-002 (SavedFilterController) ──┐
  ├── T-003 (FiltersTabContent)      │
  ├── T-007 (SettingsManager)         │
  └── T-008 (Tests)                   │
                                      │
T-004 (SearchToolbar) ────────────────┤
                                      │
T-005 (CategoryPanel) ────────────────┤
                                      │
T-006 (MainController) ◄──────────────┘
  (depends on T-002, T-004, T-005)
```

---

## Execution Order

1. **T-001** (SavedFilter model) - Foundation, no dependencies
2. **T-002** (SavedFilterController) - Depends on T-001
3. **T-003** (FiltersTabContent) - Depends on T-001
4. **T-004** (SearchToolbar) - Independent, can run parallel
5. **T-005** (CategoryPanel) - Depends on T-003
6. **T-006** (MainController) - Depends on T-002, T-004, T-005
7. **T-007** (SettingsManager) - Depends on T-001, can run parallel
8. **T-008** (Tests) - Depends on T-001, T-002, T-003

---

## Cross-Spec Validation Checklist

After implementation, verify compliance with:

- [ ] **saved-filters.md** §2.1 - SavedFilter model matches spec
- [ ] **saved-filters.md** §2.2 - SavedFilterStore API matches spec
- [ ] **saved-filters.md** §3.1 - Multiple filters combine with OR
- [ ] **saved-filters.md** §3.2 - Saved filters AND with category/level filters
- [ ] **saved-filters.md** §4.1 - Save button in SearchToolbar
- [ ] **saved-filters.md** §4.2 - FiltersTabContent UI matches spec
- [ ] **saved-filters.md** §4.3 - CategoryPanel integration matches spec
- [ ] **saved-filters.md** §5.1 - SavedFilterController API matches spec
- [ ] **saved-filters.md** §5.2 - MainController integration matches spec
- [ ] **saved-filters.md** §6.1 - Settings key "saved_filters"
- [ ] **saved-filters.md** §7.1 - Error handling matches spec
- [ ] **saved-filters.md** §8.1 - Main thread only operations
- [ ] **memory-model.md** §2.1 - Qt parent-child ownership for widgets
- [ ] **threading.md** §3.1 - All UI operations on main thread
- [ ] **error-handling.md** §7.1 - Never crash on invalid input
- [ ] **filter-controller.md** §5.2 - Filter combination logic

---

## Notes for Spec-Coder

1. **Type Annotations**: Use `from __future__ import annotations` and modern type hints (`list[str]` not `List[str]`, `X | None` not `Optional[X]`)

2. **Beartype Decorator**: All public functions must have `@beartype` decorator

3. **Qt Parent-Child**: All widgets must have parent parameter in `__init__`

4. **Signal/Slot**: Use `Signal` from `PySide6.QtCore`, connect with `.connect()`

5. **Logging**: Use `logging.getLogger(__name__)` for module-level logger

6. **Error Handling**: Log warnings for recoverable errors, show error dialog for critical errors

7. **Thread Safety**: All operations must run on main thread (no background threads)

8. **Performance**: Filter compilation should be cached, re-compile only when filter list changes

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-14 | Initial implementation plan |