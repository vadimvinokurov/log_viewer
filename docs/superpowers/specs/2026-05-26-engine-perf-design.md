# Search/Filter Engine Performance Optimization

**Date:** 2026-05-26
**Status:** Approved
**Baseline file:** d:/log.txt (6,375,495 lines, 842 MB)

## Problem

All search and filter operations are slow on large logs (6.4M+ lines). Python per-line decode loops dominate runtime. Search uses a separate code path from filters/pins instead of reusing the mask infrastructure.

## Baseline Benchmarks

| Operation | Time (ms) |
|---|---|
| File load | 1,866 |
| Plain-CI filter | 5,327 |
| Regex filter | 16,585 |
| Simple query filter | 11,971 |
| Filter toggle | 20 |
| Level toggle | 86–135 |
| Category toggle | 40–134 |
| Plain-CI search | 8,800 |
| Plain-CS search | 8,613 |
| Regex search | 16,386 |
| Simple query search | 12,439 |
| Pin add | 5,398 |
| Pin toggle | 41 |
| Reload (with filter) | 7,146 |

## Design Decisions

1. **Unified mask pipeline.** Search, filter, and pin all go through `_compute_filter_mask()`. Difference is only in how the mask is consumed: AND (filter), OR (pin), intersect with `filtered_indices` (search).

2. **Always case-insensitive.** Remove `case_sensitive` parameter from `Filter`, `Highlight`, `SearchState`. All matching is case-insensitive. Simplifies code, removes branching in hot paths.

3. **Buffer-wide regex for plain and regex modes.** Single `re.finditer` over entire `_buf` + `np.searchsorted` to map positions back to lines. Eliminates per-line decode.

4. **Cython for simple query fallback.** Per-line matching that can't use buffer-wide scan goes through `_filter_cy.pyx` with typed memoryviews. Direct C pointer access to `_buf`, no Python slice objects.

## Architecture

### Data Flow (Unified)

```
Command (:s, :f, :p, :h)
  |
  v
_compute_filter_mask(pattern, mode)  ->  bool mask[n]
  |
  +-- Plain:  re.finditer(re.escape(pattern), _buf, IGNORECASE) + np.searchsorted
  +-- Regex:  re.finditer(pattern, _buf, IGNORECASE) + np.searchsorted
  +-- Simple: _filter_cy.compute_mask_simple(_buf, spans, ast)  [Cython]
  +-- Line#:  single index set
  |
  v
  +-- Filter:   combined &= mask
  +-- Pin:      combined |= mask
  +-- Search:   matches = np.where(mask)[0] intersect filtered_indices
  +-- Highlight: spans from mask for coloring
```

### Changed Files

| File | Change |
|---|---|
| `core/models.py` | Remove `case_sensitive` from `Filter`, `Highlight`, `SearchState` |
| `core/_filter_cy.pyx` | New — Cython per-line matching for simple query on bytes |
| `core/log_store.py` | `search()` through `_compute_filter_mask` + intersect; `_compute_filter_mask` buffer regex for regex mode; Cython fallback for simple query; remove `case_sensitive` branches |
| `core/filter_engine.py` | Remove `case_sensitive` from signatures, always `re.IGNORECASE` |
| `core/simple_query.py` | Remove `case_sensitive` parameter, always lower |
| `pyproject.toml` | Add `_filter_cy` to Cython extensions |

### Unchanged

- `_apply_filters()` — mask combination logic stays the same
- GUI layer — not touched
- Parser (`_parser_cy.pyx`) — not touched

## Expected Results

| Operation | Before | Target |
|---|---|---|
| Plain filter/search | 5,300 / 8,800 ms | 200–500 ms |
| Regex filter/search | 16,600 / 16,400 ms | 500–1,000 ms |
| Simple query filter/search | 12,000 / 12,400 ms | 2,000–4,000 ms |
| Pin add | 5,400 ms | 200–500 ms |

## Verification

- `bench_engine.py` after each step, compare against baseline
- `uv run pytest tests/unit/` for regression
- `uv run pytest tests/gui/` for GUI integration
