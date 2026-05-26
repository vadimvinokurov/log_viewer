# Search Start From Selection

## Problem

When entering search mode (`:s`, `:sr`, `:ss`), the first match is always the first matching line in the file, regardless of which row the user has selected. This forces the user to navigate through many matches to reach the area they were already viewing.

## Desired Behavior

1. If the currently selected line matches the query, it becomes the first search match.
2. If the selected line does not match, the first match after the selected line is shown.
3. If no line is selected, behavior is unchanged (first match from the top).
4. If no matches exist after the selected line, wrap to the first match from the top.

## Design

### Changes

**`log_store.search()`** — add parameter `start_line: int = 0`. After computing `matches`, use `bisect_left(matches, start_line)` to find the first match `>= start_line`. If `bisect_left` returns `len(matches)`, set `current_index = 0` (wrap to start). Otherwise, set `current_index` to the `bisect_left` result.

**`app._do_search()`** — before calling `self.log_store.search()`, get the currently selected row from the table. Convert to global line index via `filtered_indices[row]`. If no row is selected, pass `start_line=0`.

### Getting Current Selection

```python
selection = self.log_table.selectionModel().selectedRows()
if selection:
    pos = selection[0].row()
    global_idx = int(self.log_store.filtered_indices[pos])
else:
    global_idx = 0
```

### What Does Not Change

- SearchState model
- Match navigation (Up/Down)
- Search exit (Escape)
- `_jump_to_search_match()`
- Filter and highlight commands

## Scope

~10 lines of code changes across 2 files. No new files, no model changes.
