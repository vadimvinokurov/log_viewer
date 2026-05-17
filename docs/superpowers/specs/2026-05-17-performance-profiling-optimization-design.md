# Performance Profiling & Optimization — "Quick Wins"

**Date:** 2026-05-17
**Approach:** A (Quick Wins) — profile first, then targeted optimizations without architecture changes.
**Phase 2 (separate commit):** B (Architectural refactor with virtual scrolling) to follow later.

## Problem

The application is unusably slow on log files with ~6M lines. Loading, category switching, filtering, and highlighting all exhibit significant latency.

## Baseline Measurement

### Profiling Script

Create `scripts/profile_perf.py` — a standalone headless script that:

1. Loads `d:/log.txt` (6M lines) via `LogStore` + `parser`
2. Measures each operation:
   - **Parse:** `parser.parse_lines()` on raw file content
   - **Load:** `LogStore.load_file()` end-to-end
   - **Filter apply:** `LogStore._apply_filters()` with 1, 3, 5 active filters
   - **Category toggle:** `LogStore._apply_filters()` after enabling/disabling categories
   - **Search:** `LogStore.search()` with plain text, regex, and simple query
   - **Batch match:** `filter_engine.batch_match()` for highlight spans
3. Runs each operation 3 times, takes the median
4. Outputs a table: operation | time_before | time_after | speedup
5. Can be run as: `uv run python scripts/profile_perf.py`

### Test File

Uses `d:/log.txt` as the benchmark file. If not present, script generates a synthetic 6M-line file.

## Targeted Optimizations

### 1. Parser

- **Pre-compile regex:** `_SPLIT_RE` compiled once at module level, not per-call
- **Reduce allocations:** Avoid creating intermediate strings; use `match.groups()` directly
- **Batch parsing:** Parse lines in chunks if profiling shows per-line overhead

### 2. LogStore._apply_filters()

- **Set for filtered_indices:** Convert from `list[int]` to sorted structure or set for O(1) lookups
- **Cache category membership:** Build a `dict[int, bool]` mapping line index → category_enabled, rebuild only when categories change
- **Incremental filter application:** When adding one filter, intersect with existing result instead of full rebuild
- **Separate filter and category paths:** Apply category filter once (changes rarely), apply text filters incrementally

### 3. Category Lookup

- **Replace tree traversal with dict lookup:** `_is_category_enabled()` should be O(1) via a `dict[str, bool]` cache, rebuilt only when category checkboxes change
- **Batch category state:** Instead of checking per-line, group lines by category and filter by group

### 4. Qt Model

- **Avoid full model reset:** Use `beginInsertRows/endInsertRows` or `layoutAboutToBeChanged/layoutChanged` instead of `beginResetModel/endResetModel` where the row count changes
- **Cache data() results:** For `DisplayRole`, cache the formatted string per row to avoid repeated formatting
- **Debounce rapid updates:** If multiple filter changes happen in quick succession, batch them

### 5. Filter Engine

- **Cache compiled regexes:** `batch_match()` should cache compiled patterns between calls
- **Optimize search()**: Use pre-built index for plain text search instead of linear scan

## Verification

1. Run `uv run python scripts/profile_perf.py` → save baseline
2. Apply optimizations
3. Run `uv run python scripts/profile_perf.py` → save results
4. Print summary table with speedup factors
5. Run `uv run pytest` — all existing tests must pass
6. No changes to public API of `core/` modules

## Out of Scope

- GUI widget/layout changes
- Virtual scrolling (Phase 2)
- New dependencies
- Public API changes
- Refactoring for code cleanliness unrelated to performance

## Success Criteria

- 3-10x speedup on measured operations
- All existing tests pass
- No regressions in functionality
- Reproducible benchmark numbers
