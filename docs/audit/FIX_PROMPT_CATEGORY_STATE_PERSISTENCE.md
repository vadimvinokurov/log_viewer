# Fix Task: Per-File Category State Persistence

## Problem Statement

The audit report ([`CATEGORY_PANEL_AUDIT_REPORT.md`](CATEGORY_PANEL_AUDIT_REPORT.md)) identified a **critical deviation** from the specification:

**Current Behavior:** Category checkbox states are stored globally in a single dictionary, shared across all log files.

**Required Behavior:** Category states must be stored per-file, so that:
1. When user switches files, the previous file's state is saved
2. When user reopens a file, its previous state is restored
3. When user opens a new file, all categories default to checked

## Specification Reference

Per [`docs/specs/features/category-checkbox-behavior.md`](../specs/features/category-checkbox-behavior.md) §5.2 and §5.3:

> **Save Triggers:**
> 1. User checks/unchecks any category
> 2. Application closes (save current state)
> 3. **User switches to a different log file (save previous file's state)**
>
> **Restore Triggers:**
> 1. Application starts (load last state)
> 2. **User opens a previously-viewed log file (restore that file's state)**
> 3. New log file opened (default: all categories checked)

## Files to Modify

### 1. `src/utils/settings_manager.py`

**Current:**
```python
@dataclass
class AppSettings:
    category_states: Dict[str, bool] = field(default_factory=dict)
```

**Change to:**
```python
@dataclass
class AppSettings:
    # Per-file category states: {filepath: {category_path: checked}}
    category_states_by_file: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    # Current file path for context
    current_file: Optional[str] = None
```

**Update methods:**
- `set_category_states(filepath: str, states: Dict[str, bool])` - Save states for a specific file
- `get_category_states(filepath: str) -> Dict[str, bool]` - Get states for a specific file
- Remove or deprecate the old `set_category_states()` and `get_category_states()` methods

### 2. `src/controllers/main_controller.py`

**Update `_save_category_states()`:**
```python
def _save_category_states(self) -> None:
    """Save current category checkbox states for current file."""
    if self._document is None:
        return
    
    filepath = self._document.filepath
    category_states = self._window.get_category_panel().get_category_states()
    self._settings_manager.set_category_states(filepath, category_states)
```

**Update `_restore_category_states()`:**
```python
def _restore_category_states(self) -> None:
    """Restore category checkbox states for current file.
    
    If no saved state exists for this file, all categories default to checked.
    """
    if self._document is None:
        return
    
    filepath = self._document.filepath
    saved_states = self._settings_manager.get_category_states(filepath)
    
    if saved_states:
        # Apply saved states
        self._window.get_category_panel().set_category_states(saved_states)
        
        # Update filter controller with restored states
        for category_path, checked in saved_states.items():
            self._filter_controller.set_category_enabled(category_path, checked)
        
        # Recompile filter
        self._filter_controller.apply_filter()
    else:
        # New file - all categories checked (default)
        # CategoryPanel already has all checked from set_categories()
        pass
```

**Add save on file switch in `open_file()`:**
```python
def open_file(self, filepath: str) -> None:
    # Save previous file's category states before switching
    if self._document is not None:
        self._save_category_states()
    
    # ... rest of open_file logic
```

### 3. `docs/specs/features/category-checkbox-behavior.md`

**Update §5.1 Storage Format:**
```json
{
  "category_states_by_file": {
    "/path/to/file1.log": {
      "HordeMode": true,
      "HordeMode/scripts": true,
      "HordeMode/scripts/app": false
    },
    "/path/to/file2.log": {
      "Game": true,
      "Game/network": true
    }
  },
  "current_file": "/path/to/file1.log"
}
```

## Implementation Steps

1. **Update `AppSettings` dataclass** in `settings_manager.py`
   - Add `category_states_by_file: Dict[str, Dict[str, bool]]`
   - Add `current_file: Optional[str]`
   - Keep backward compatibility with old `category_states` field

2. **Add migration logic** in `SettingsManager.load()`
   - If old `category_states` exists, migrate to `category_states_by_file`
   - Use `last_file` as the key for migration

3. **Update `set_category_states()` and `get_category_states()`**
   - Change signatures to accept `filepath` parameter
   - Update `to_dict()` and `from_dict()` for serialization

4. **Update `MainController`**
   - Modify `_save_category_states()` to use current file path
   - Modify `_restore_category_states()` to use current file path
   - Add save before file switch in `open_file()`

5. **Add tests** in `tests/test_settings_manager.py`
   - Test per-file state storage
   - Test migration from old format
   - Test default state for new files

## Backward Compatibility

The implementation must handle existing settings files with the old format:

```python
# Old format (single global state)
{
  "category_states": {"HordeMode": true, "Game": false}
}

# New format (per-file state)
{
  "category_states_by_file": {
    "/path/to/file.log": {"HordeMode": true, "Game": false}
  }
}
```

Migration logic:
```python
def from_dict(cls, data: Dict[str, Any]) -> AppSettings:
    # Handle migration from old format
    old_states = data.get("category_states", {})
    new_states = data.get("category_states_by_file", {})
    
    if old_states and not new_states:
        # Migrate: use last_file as key
        last_file = data.get("last_file")
        if last_file:
            new_states = {last_file: old_states}
    
    return cls(
        category_states_by_file=new_states,
        # ... other fields
    )
```

## Testing

Add tests to verify:

1. **Per-file storage:**
   ```python
   def test_category_states_per_file():
       manager = SettingsManager()
       manager.set_category_states("/file1.log", {"Cat1": True})
       manager.set_category_states("/file2.log", {"Cat2": False})
       
       assert manager.get_category_states("/file1.log") == {"Cat1": True}
       assert manager.get_category_states("/file2.log") == {"Cat2": False}
   ```

2. **Default for new files:**
   ```python
   def test_new_file_default_states():
       manager = SettingsManager()
       states = manager.get_category_states("/new_file.log")
       assert states == {}  # Empty = all checked default
   ```

3. **Migration from old format:**
   ```python
   def test_migration_from_old_format():
       # Create settings with old format
       data = {
           "category_states": {"Cat1": True, "Cat2": False},
           "last_file": "/old_file.log"
       }
       manager = SettingsManager()
       manager._settings = AppSettings.from_dict(data)
       
       # Should migrate to new format
       states = manager.get_category_states("/old_file.log")
       assert states == {"Cat1": True, "Cat2": False}
   ```

## Acceptance Criteria

- [ ] Category states are stored per-file
- [ ] Switching files saves previous file's state
- [ ] Reopening file restores its previous state
- [ ] New file defaults to all categories checked
- [ ] Backward compatible with old settings format
- [ ] Unit tests pass
- [ ] Integration test for file switching scenario

## Estimated Effort

- **Time:** 2-3 hours
- **Complexity:** Medium
- **Risk:** Low (backward compatible)

## Prompt for Spec Coder

```
Implement per-file category state persistence as described in docs/audit/FIX_PROMPT_CATEGORY_STATE_PERSISTENCE.md.

Key changes:
1. Update SettingsManager to store category_states_by_file instead of global category_states
2. Modify MainController to save/restore states per-file
3. Add migration logic for backward compatibility
4. Add unit tests

Reference: docs/specs/features/category-checkbox-behavior.md §5.2, §5.3
Audit Report: docs/audit/CATEGORY_PANEL_AUDIT_REPORT.md