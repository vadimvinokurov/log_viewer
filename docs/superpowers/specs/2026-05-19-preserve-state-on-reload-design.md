# Preserve State on Reload

## Problem

When the user presses reload, all UI state is lost: disabled categories re-enable, pins persist (unwanted), search state carries over. Filters and highlights happen to survive because their lists are not cleared in `load_lines`, but this is incidental rather than intentional.

## Requirements

- **Preserve**: filters, highlights, disabled categories
- **Clear**: pinned lines, search state
- **Edge case**: category removed after reload → skip it; new category → enabled by default

## Design

### `log_store.py` — `load_lines`

1. Before rebuilding categories, snapshot disabled category names:
   ```python
   disabled_cat_names = {
       self._category_names[cid]
       for cid in self.disabled_categories
       if cid < len(self._category_names)
   }
   ```

2. After `_build_category_tree()` and `_count_levels()`, restore by name:
   ```python
   self.disabled_categories = {
       self._category_name_to_id[name]
       for name in disabled_cat_names
       if name in self._category_name_to_id
   }
   ```

3. Clear pins:
   ```python
   self.pinned_line_numbers = set()
   ```

4. Do not touch `filters`, `filter_enabled`, `highlights`, `highlight_enabled` — they already persist.

### `app.py` — reload handler

Reset search state before calling `_open_file`. Call the existing search-clear method on `log_store` (or set `search_state` to a fresh `SearchState`).

### Restore disabled categories on CategoryNode tree

After restoring `disabled_categories`, propagate to the category tree nodes so the UI checkboxes reflect the correct state. Call `_set_enabled_recursive` or equivalent for each disabled category.

## Testing

Unit test in `tests/unit/`:

1. Create a LogStore with lines containing categories "app" and "db"
2. Add a filter, a highlight, disable "db", pin a line
3. Call `load_lines` with new content (same categories + new "cache")
4. Assert: filter and highlight lists unchanged, "db" still disabled, "cache" enabled, no pins

## Files touched

- `src/log_viewer/core/log_store.py` — `load_lines` method
- `src/log_viewer/gui/app.py` — reload command handler
- `tests/unit/` — new or extended test for reload behavior
