# Cache Text Filter Mask for Instant Category Toggle

## Problem

When text filters are active, toggling categories is slow in one direction:
- **Disable** category: instant (fewer lines to process)
- **Enable** category: slow (more lines to process)

Root cause: `_apply_filters()` calls `_bulk_match()` on every toggle, re-running
expensive text matching (buffer scan or per-line decode+match) against all
category-enabled lines.

## Solution

Cache the text filter match result as a boolean numpy mask computed once per
filter change. Category/level toggles become pure numpy mask intersections.

## Design

### New attribute

`LogStore._text_filter_mask: np.ndarray` — boolean array of length n.
`True` = line matches at least one active text filter (OR logic).

### New method: `_recompute_text_filter_mask()`

Runs the full text matching pipeline for ALL lines (not just category-enabled),
using the same logic as current `_bulk_match`:
- Plain-CI: buffer scan via `combined.finditer(self._buf)`, map positions to
  line indices via `searchsorted`.
- Regex/CS/Simple: per-line loop over all n lines, decode message, match.

Result stored in `_text_filter_mask`. Called only when active filters change.

### Modified `_apply_filters()`

Replace `_bulk_match` call with numpy intersection:

```python
if has_text_filters:
    combined = cat_level_mask & self._text_filter_mask
    would_be_visible = np.where(combined)[0].astype(np.uint32)
```

### Invalidation points

`_recompute_text_filter_mask()` called before `_apply_filters()` in:
- `add_filter()`, `remove_filter()`, `clear_filters()`
- Filter enable/disable toggle
- `_finalize_load()` (after file parse)

### Memory

One boolean array of length n (~1MB per 1M lines). Negligible.

### What stays the same

- `_bulk_match()` can be kept for search (`store.search()`) or removed if unused
  elsewhere.
- Filter OR logic (lines matching any filter) unchanged.
- Category/level toggle API unchanged.

## Verification

- Existing test suite passes (no behavior change).
- Manual: add filter on large file, toggle category — both directions instant.
