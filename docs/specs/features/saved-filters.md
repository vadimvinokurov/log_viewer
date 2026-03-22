# Saved Filters Feature Specification

**Version:** 1.0 (DRAFT)
**Last Updated:** 2026-03-14
**Status:** READY FOR IMPLEMENTATION
**Depends On:** [filter-controller.md](filter-controller.md), [ui-components.md](ui-components.md), [settings-manager.md](settings-manager.md)

---

## §1 Overview

### §1.1 Purpose

The Saved Filters feature allows users to save frequently-used filter configurations for quick access and reuse. Saved filters are displayed in the Filters tab of the CategoryPanel and can be enabled/disabled via checkboxes.

### §1.2 Scope

- Save button in SearchToolbar (next to filter mode dropdown)
- Saved filters list in Filters tab (CategoryPanel)
- Enable/disable filters via checkboxes
- Rename and delete operations
- Filter combination logic (OR for text filters)
- Persistence via QSettings

### §1.3 Out of Scope

- Editing saved filter text/mode (delete and re-create instead)
- Category or level filter saving (text + mode only)
- Quick-access dropdown in main toolbar
- Import/export of filter presets

---

## §2 Data Model

### §2.1 SavedFilter Model

```python
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
```

### §2.2 SavedFilterStore

```python
class SavedFilterStore:
    """Manages saved filters collection.
    
    // Ref: docs/specs/features/saved-filters.md §2.2
    // Persists to QSettings via SettingsManager
    """
    _filters: dict[str, SavedFilter]  # id -> SavedFilter
    _settings_key: str = "saved_filters"
    
    def add_filter(self, filter: SavedFilter) -> str:
        """Add new filter, return ID."""
        
    def remove_filter(self, id: str) -> bool:
        """Remove filter by ID, return success."""
        
    def rename_filter(self, id: str, new_name: str) -> bool:
        """Rename filter, return success."""
        
    def set_enabled(self, id: str, enabled: bool) -> bool:
        """Toggle filter enabled state."""
        
    def get_enabled_filters(self) -> list[SavedFilter]:
        """Get all enabled filters."""
        
    def get_all_filters(self) -> list[SavedFilter]:
        """Get all filters (enabled and disabled)."""
        
    def save_to_settings(self) -> None:
        """Persist to QSettings."""
        
    def load_from_settings(self) -> None:
        """Load from QSettings."""
```

---

## §3 Filter Combination Logic

### §3.1 Multiple Enabled Filters

When multiple saved filters are enabled simultaneously, they combine using **logical OR**:

```
enabled_filters = [filter_a, filter_b, filter_c]
entry_matches = filter_a.matches(entry) OR filter_b.matches(entry) OR filter_c.matches(entry)
```

### §3.2 Interaction with Category/Level Filters

Saved text filters combine with category and level filters using **logical AND**:

```
final_match = (saved_text_filter_matches) AND (category_filter_matches) AND (level_filter_matches)
```

**Example:**
- Saved Filter A: text="error", mode=Plain (enabled)
- Saved Filter B: text="warning", mode=Plain (enabled)
- Categories: "System" enabled, "Network" disabled
- Levels: ERROR, WARNING enabled

Entry matches if:
```
(text contains "error" OR text contains "warning") 
AND category in ["System", ...] 
AND level in [ERROR, WARNING]
```

### §3.3 No Enabled Filters

When no saved filters are enabled, the text filter is empty (matches all entries). This is equivalent to the current behavior.

---

## §4 UI Components

### §4.1 Save Filter Button

**Location:** SearchToolbar, next to filter mode dropdown

**Behavior:**
1. Button shows "💾" icon with tooltip "Save current filter"
2. Clicking opens inline input for filter name (or auto-generates from text)
3. Saves current filter text + mode to SavedFilterStore
4. Shows brief confirmation (status bar message)
5. Clears the filter text input and removes the applied filter (mode remains unchanged)

**States:**
- Enabled: When filter text is not empty
- Disabled: When filter text is empty

**API:**
```python
class SearchToolbar(QWidget):
    # New signal
    save_filter_requested = Signal(str, str)  # filter_text, mode
    
    def _setup_ui(self) -> None:
        # Add after mode dropdown
        self._save_button = QPushButton("💾")
        self._save_button.setToolTip("Save current filter")
        self._save_button.setFixedSize(24, 24)
        self._save_button.clicked.connect(self._on_save_clicked)
        
    def _on_save_clicked(self) -> None:
        text = self._search_input.text().strip()
        mode = self._mode_combo.currentData()
        if text:
            self.save_filter_requested.emit(text, mode)
```

### §4.2 Filters Tab Content

**Location:** CategoryPanel, second tab (Filters)

**Components:**
1. **Filter List Widget** - QListWidget with custom items
2. **Button Bar** - Delete, Rename buttons

**Filter List Item:**
```
┌─────────────────────────────────────┐
│ ☑ Filter Name                       │
│   "error|warning" [Plain]            │
└─────────────────────────────────────┘
```

- Checkbox: Enable/disable filter
- First line: Filter name (editable inline)
- Second line: Filter text + mode (read-only, gray italic)

**Button Bar:**
- Delete button: Remove selected filter (with confirmation)
- Rename button: Start inline edit of filter name

**API:**
```python
class FiltersTabContent(QWidget):
    """Content for the Filters tab in CategoryPanel.
    
    // Ref: docs/specs/features/saved-filters.md §4.2
    """
    # Signals
    filter_enabled_changed = Signal(str, bool)  # filter_id, enabled
    filter_deleted = Signal(str)                 # filter_id
    filter_renamed = Signal(str, str)            # filter_id, new_name
    
    def set_filters(self, filters: list[SavedFilter]) -> None:
        """Populate filter list."""
        
    def add_filter(self, filter: SavedFilter) -> None:
        """Add single filter to list."""
        
    def remove_filter(self, filter_id: str) -> None:
        """Remove filter from list."""
```

### §4.3 CategoryPanel Integration

**Modified CategoryPanel:**

```python
class CategoryPanel(QWidget):
    # Existing signals...
    
    # New signals for saved filters
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

---

## §5 Controller Integration

### §5.1 SavedFilterController

**New controller to manage saved filters:**

```python
class SavedFilterController(QObject):
    """Controller for saved filter operations.
    
    // Ref: docs/specs/features/saved-filters.md §5.1
    """
    # Signals
    filters_changed = Signal()              # Filter list changed
    filter_applied = Signal()               # Combined filter applied
    
    def __init__(self, settings_manager: SettingsManager, parent: QObject | None = None):
        super().__init__(parent)
        self._store = SavedFilterStore()
        self._settings_manager = settings_manager
        self._load_from_settings()
    
    def save_filter(self, text: str, mode: FilterMode, name: str | None = None) -> str:
        """Save a new filter.
        
        Args:
            text: Filter text
            mode: Filter mode
            name: Optional name (auto-generated if None)
            
        Returns:
            Filter ID
        """
        filter_id = str(uuid.uuid4())
        if name is None:
            name = self._generate_name(text)
        
        filter = SavedFilter(
            id=filter_id,
            name=name,
            filter_text=text,
            filter_mode=mode,
            created_at=time.time(),
            enabled=True
        )
        
        self._store.add_filter(filter)
        self._save_to_settings()
        self.filters_changed.emit()
        return filter_id
    
    def delete_filter(self, filter_id: str) -> bool:
        """Delete a saved filter."""
        success = self._store.remove_filter(filter_id)
        if success:
            self._save_to_settings()
            self.filters_changed.emit()
        return success
    
    def rename_filter(self, filter_id: str, new_name: str) -> bool:
        """Rename a saved filter."""
        success = self._store.rename_filter(filter_id, new_name)
        if success:
            self._save_to_settings()
            self.filters_changed.emit()
        return success
    
    def set_filter_enabled(self, filter_id: str, enabled: bool) -> None:
        """Enable/disable a saved filter."""
        self._store.set_enabled(filter_id, enabled)
        self._save_to_settings()
        self.filter_applied.emit()
    
    def get_combined_filter(self) -> Callable[[LogEntry], bool] | None:
        """Get combined filter for all enabled saved filters.
        
        Returns:
            Callable that returns True if entry matches ANY enabled filter,
            or None if no filters are enabled.
        """
        enabled_filters = self._store.get_enabled_filters()
        if not enabled_filters:
            return None
        
        # Compile each filter
        filter_engine = FilterEngine()
        compiled_filters: list[Callable[[LogEntry], bool]] = []
        
        for f in enabled_filters:
            state = FilterState(
                filter_text=f.filter_text,
                filter_mode=f.filter_mode
            )
            compiled = filter_engine.compile_filter(state)
            compiled_filters.append(compiled)
        
        # Combine with OR
        def combined_filter(entry: LogEntry) -> bool:
            return any(f(entry) for f in compiled_filters)
        
        return combined_filter
    
    def get_all_filters(self) -> list[SavedFilter]:
        """Get all saved filters."""
        return self._store.get_all_filters()
    
    def _generate_name(self, text: str) -> str:
        """Generate filter name from text."""
        # Use first 30 chars of text as name
        return text[:30] + ("..." if len(text) > 30 else "")
    
    def _save_to_settings(self) -> None:
        """Persist filters to settings."""
        filters_data = [
            {
                "id": f.id,
                "name": f.name,
                "filter_text": f.filter_text,
                "filter_mode": f.filter_mode.value,
                "created_at": f.created_at,
                "enabled": f.enabled
            }
            for f in self._store.get_all_filters()
        ]
        self._settings_manager.set("saved_filters", filters_data)
    
    def _load_from_settings(self) -> None:
        """Load filters from settings."""
        filters_data = self._settings_manager.get("saved_filters", [])
        for data in filters_data:
            filter = SavedFilter(
                id=data["id"],
                name=data["name"],
                filter_text=data["filter_text"],
                filter_mode=FilterMode(data["filter_mode"]),
                created_at=data["created_at"],
                enabled=data["enabled"]
            )
            self._store.add_filter(filter)
```

### §5.2 MainController Integration

**Modified MainController:**

```python
class MainController(QObject):
    def __init__(self, window: MainWindow, settings_manager: SettingsManager):
        # ... existing code ...
        
        # Add saved filter controller
        self._saved_filter_controller = SavedFilterController(settings_manager)
        
        # Connect signals
        self._saved_filter_controller.filter_applied.connect(
            self._on_saved_filters_applied
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
        
        # Combine filters
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

---

## §6 Persistence

### §6.1 SettingsManager Integration

**Settings key:** `saved_filters`

**Data format:**
```json
{
  "saved_filters": [
    {
      "id": "uuid-1",
      "name": "Error Filter",
      "filter_text": "error|critical",
      "filter_mode": "plain",
      "created_at": 1700000000.0,
      "enabled": true
    },
    {
      "id": "uuid-2",
      "name": "Network Issues",
      " "filter_text": "network.*timeout",
      "filter_mode": "regex",
      "created_at": 1700001000.0,
      "enabled": false
    }
  ]
}
```

### §6.2 Migration

No migration needed - new feature. If `saved_filters` key doesn't exist, start with empty list.

---

## §7 Error Handling

### §7.1 Error Cases

| Error | Handling |
|-------|----------|
| Empty filter text | Disable save button, show tooltip "Enter filter text first" |
| Duplicate name | Allow (names don't need to be unique) |
| Settings save failure | Log warning, continue (in-memory state preserved) |
| Settings load failure | Log warning, start with empty filter list |
| Invalid filter mode | Default to Plain |

### §7.2 User Feedback

- **Save success:** Status bar message "Filter saved: {name}"
- **Delete success:** Status bar message "Filter deleted: {name}"
- **Rename success:** Status bar message "Filter renamed to: {name}"
- **Enable/disable:** No message (immediate visual feedback in checkbox)

---

## §8 Thread Safety

### §8.1 Thread Context

| Component | Thread | Notes |
|-----------|--------|-------|
| `SavedFilterStore` | Main thread only | Not thread-safe, no locks |
| `SavedFilterController` | Main thread only | All operations on main thread |
| `FiltersTabContent` | Main thread only | Qt UI component |
| `SettingsManager` access | Main thread | Per [settings-manager.md](settings-manager.md) §3.2 |

### §8.2 Concurrency Rules

1. **No concurrent access**: All saved filter operations must run on the main thread
2. **Signal emission**: All signals emitted from main thread (Qt requirement)
3. **Settings persistence**: `QSettings` operations are synchronous and blocking
4. **No background compilation**: Filter compilation happens on-demand in `get_combined_filter()`

### §8.3 Rationale

- Saved filters are user-driven operations (button clicks, checkbox toggles)
- No performance-critical paths require background processing
- Qt signal/slot mechanism ensures thread-safe UI updates
- Simpler implementation without thread synchronization overhead

---

## §9 Performance

### §9.1 Filter Compilation

- Saved filters are compiled on-demand when `get_combined_filter()` is called
- Compiled filters are cached until filter list changes
- Maximum recommended: 20 saved filters (UI scalability)

### §9.2 Memory

- Each SavedFilter: ~200 bytes
- 100 filters: ~20 KB (negligible)

---

## §10 Testing

### §10.1 Unit Tests

| Test | File | Coverage |
|------|------|----------|
| SavedFilter creation | `test_saved_filter.py` | Model validation |
| SavedFilterStore CRUD | `test_saved_filter.py` | Add, remove, rename, enable/disable |
| Filter combination (OR) | `test_saved_filter.py` | Multiple enabled filters |
| Settings persistence | `test_saved_filter.py` | Save/load roundtrip |

### §10.2 Integration Tests

| Test | File | Coverage |
|------|------|----------|
| Save from toolbar | `test_integration.py` | End-to-end save flow |
| Enable/disable in panel | `test_integration.py` | Checkbox toggle flow |
| Combined filtering | `test_integration.py` | Saved + category + level filters |

---

## §11 API Reference

### §11.1 New Classes

| Class | Module | Description |
|-------|--------|-------------|
| `SavedFilter` | `models.saved_filter` | Filter data model |
| `SavedFilterStore` | `models.saved_filter` | Filter collection manager |
| `SavedFilterController` | `controllers.saved_filter_controller` | Filter operations controller |
| `FiltersTabContent` | `views.components.filters_tab` | Filters tab UI component |

### §11.2 Modified Classes

| Class | Module | Changes |
|-------|--------|---------|
| `SearchToolbar` | `views.widgets.search_toolbar` | Add save button + signal |
| `CategoryPanel` | `views.category_panel` | Replace Filters tab placeholder |
| `MainController` | `controllers.main_controller` | Integrate SavedFilterController |
| `SettingsManager` | `utils.settings_manager` | Add `saved_filters` key |

---

## §12 Implementation Notes

### §12.1 File Structure

```
src/
├── models/
│   └── saved_filter.py          # NEW: SavedFilter, SavedFilterStore
├── controllers/
│   └── saved_filter_controller.py # NEW: SavedFilterController
├── views/
│   ├── category_panel.py         # MODIFY: Replace Filters tab
│   ├── widgets/
│   │   └── search_toolbar.py     # MODIFY: Add save button
│   └── components/
│       └── filters_tab.py        # NEW: FiltersTabContent
└── utils/
    └── settings_manager.py       # MODIFY: Add saved_filters key
```

### §12.2 Dependencies

- `uuid` for filter IDs
- `time` for timestamps
- Existing: `FilterEngine`, `FilterState`, `FilterMode`, `SettingsManager`

---

## §13 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-14 | Initial specification (DRAFT) |