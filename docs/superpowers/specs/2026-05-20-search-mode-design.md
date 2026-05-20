# Search Mode Design

## Goal

Add an explicit "search mode" to the log viewer. When active, Up/Down arrow keys navigate between matched lines instead of adjacent rows. The mode is shown in the window title.

## Entry

Commands `:s text`, `:sr regex`, `:ss query` perform search as today. If matches are found (count > 0), search mode activates. If zero matches, the mode does not activate and the status bar shows "no matches" as before.

On entry, the window title changes to:
```
Log Viewer — {filename} — Search: {pattern}
```

A new search replaces the previous one (same behavior as today, plus the mode flag resets/re-enters).

## Navigation in Search Mode

- **Up arrow**: move to previous match (wrap around)
- **Down arrow**: move to next match (wrap around)
- Normal row-by-row Up/Down navigation is suppressed while in search mode
- Other keys (j, k, g, G, etc.) remain unaffected

## Exit

- **Esc** key exits search mode
- Window title reverts to `Log Viewer — {filename}`
- Matches list and current selection are preserved (user stays on the same row)
- A subsequent `:s`/`:sr`/`:ss` can re-enter the mode

## n/N Commands

The `:n` and `:N` commands are removed. Arrow keys are the sole navigation method in search mode.

## Changes

### `models.py` — SearchState

Add one field:

```python
@dataclass
class SearchState:
    # ... existing fields ...
    in_search: bool = False
```

### `app.py` — MainWindow

1. **`_do_search()`**: after populating matches, if `len(matches) > 0`, set `search_state.in_search = True` and call `_update_title()`.
2. **`_update_title()`** (new helper): sets `self.setWindowTitle()` to either the search-mode format or the plain filename format, based on `search_state.in_search`.
3. **`eventFilter()`**:
   - Up/Down: if `search_state` exists and `in_search`, call `prev_match()`/`next_match()` and jump to match. Return `True` to suppress default navigation. Otherwise, return `False` to let QTableView handle normally.
   - Esc: if `in_search`, set `in_search = False` and call `_update_title()`. Return `True`.
   - Remove n/N key handlers.
4. **`_load_file()` / file open**: after loading, if `search_state` exists, reset `in_search = False` and update title.

No changes to `log_store.py`, `log_table.py`, `bottom_bar.py`, or `command_input.py`.
