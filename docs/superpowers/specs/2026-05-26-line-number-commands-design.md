# Line Number Commands: `:fn`, `:sn`, `:hn`

## Summary

Three new commands that take a line number (1-based, matching the first column in the table) instead of a text pattern. Semantics mirror existing `:f`/`:s`/`:h` families.

- `:sn 100` — navigate to line 100 (scroll + select, no search mode)
- `:fn 100` — add a filter showing only line 100; multiple `:fn` calls accumulate (OR logic)
- `:hn 100` — highlight line 100; auto-assigned color from palette, same as `:h`

## Architecture

Add `SearchMode.LINE_NUMBER` to `models.py`. Filters and highlights with this mode match by line number instead of text content. The pattern field stores the line number as a string (e.g., `"100"`).

### `:sn` — Navigate by line number

Pure navigation, no filter/search state created. Flow:
1. Parse `sn N` from command parser
2. Convert N to 0-based index (`N - 1`)
3. Validate: `0 <= idx < store.n`
4. Find position of idx in `filtered_indices` via `np.searchsorted`
5. If found: `selectRow(pos)` + `scrollTo` with `PositionAtCenter`
6. If not found (line filtered out): show status "Line N is filtered out"

### `:fn` — Filter by line number

Creates a `Filter(pattern="N", mode=SearchMode.LINE_NUMBER)`. Treated identically to text filters:
- Appears in side_panel filter list
- Can be toggled on/off
- Can be removed via `rmf`
- Multiple `:fn` filters combine with OR logic (same as text filters)

In `_compute_filter_mask()`: `mask[N - 1] = True`, all other indices `False`. O(1) per filter.

### `:hn` — Highlight by line number

Creates a `Highlight(pattern="N", mode=SearchMode.LINE_NUMBER)`. Color auto-assigned inside `add_highlight()` from `HIGHLIGHT_PALETTE` — identical to `:h` commands.

For highlight rendering, the entire row is highlighted (no text span matching needed). In `filter_engine.find_spans()` with `LINE_NUMBER` mode: return a single span covering the full text, so the whole row lights up.

## Files changed

### `src/log_viewer/core/models.py`
- Add `LINE_NUMBER = "line_number"` to `SearchMode` enum

### `src/log_viewer/core/command_parser.py`
- Add `"fn"`, `"sn"`, `"hn"` to `_VALID_COMMANDS`

### `src/log_viewer/gui/app.py`
- Handle `fn` in `_handle_command()`: parse int, create `Filter` with `LINE_NUMBER` mode
- Handle `sn` in `_handle_command()`: parse int, navigate to row
- Handle `hn` in `_handle_command()`: parse int, create `Highlight` with `LINE_NUMBER` mode
- Validate that argument is a positive integer; show error if not

### `src/log_viewer/core/filter_engine.py`
- `match()`: if `filt.mode == SearchMode.LINE_NUMBER`, always return `True` (matching is by index, not text — the mask handles it)
- `find_spans()`: if `LINE_NUMBER`, return `[(0, len(text))]` to highlight entire text

### `src/log_viewer/core/log_store.py`
- `_compute_filter_mask()`: if `filt.mode == SearchMode.LINE_NUMBER`, parse `int(filt.pattern)` and set `mask[idx] = True`

## Error handling

- Non-integer argument: "Error: fn/sn/hn requires a line number"
- Out of range (N < 1 or N > total lines): "Error: line N out of range (1..M)"
- `:sn` when target line is filtered out: "Line N is filtered out"

## Tests

- Unit: command parser accepts `fn`, `sn`, `hn` with numeric text
- Unit: `SearchMode.LINE_NUMBER` in filter_engine returns correct match
- Unit: `_compute_filter_mask` with `LINE_NUMBER` produces correct single-element mask
- Unit: `find_spans` with `LINE_NUMBER` returns full-text span
- GUI: `:sn 5` scrolls to correct row; `:fn 10` adds filter; `:hn 3` adds highlight
