# Performance Profiling & Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Profile the log viewer on a 6M-line file, identify bottlenecks, apply targeted optimizations, and demonstrate measurable speedup.

**Architecture:** Create a headless profiling script that exercises all core operations (parse, load, filter, category toggle, search, batch match) without Qt. Run it before and after optimizations to produce a comparison table. Optimizations are internal-only — no public API changes.

**Tech Stack:** Python 3.9+, cProfile/pstats (stdlib), time.perf_counter, no new dependencies.

---

### Task 1: Create the profiling script

**Files:**
- Create: `scripts/profile_perf.py`

- [ ] **Step 1: Write `scripts/profile_perf.py`**

The script must:
1. Accept `--file <path>` (default `d:/log.txt`) and `--lines <N>` for synthetic generation.
2. Generate a synthetic 6M-line file in KSIVA format if the target file doesn't exist.
3. Define benchmark functions for each operation, each returning a callable and a label.
4. Run each benchmark 3 times, take the median using `statistics.median`.
5. Use `time.perf_counter()` for wall-clock timing.
6. Print a formatted table: `| Operation | Median (s) |`

```python
"""Headless performance profiling script for LogStore core operations."""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

# Ensure project src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, SearchMode


def generate_synthetic(path: str, n: int = 6_000_000) -> None:
    """Generate a synthetic KSIVA-format log file with n lines."""
    import random
    categories = ["app/main", "net/http", "db/query", "ui/render", "sys/init"]
    levels = ["LOG_INFO", "LOG_DEBUG", "LOG_WARNING", "LOG_ERROR", "LOG_TRACE"]
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n):
            cat = categories[i % len(categories)]
            lvl = levels[i % len(levels)]
            f.write(f"2024-01-15T10:{(i // 60) % 60:02d}:{i % 60:02d}.000 {cat} [{lvl}] Message line {i} with some padding text\n")


def bench_parse(store: LogStore, raw: list[str]) -> float:
    """Benchmark parse_line on all raw lines."""
    from log_viewer.core.parser import parse_line
    start = time.perf_counter()
    for i, line in enumerate(raw):
        parse_line(line, i + 1)
    return time.perf_counter() - start


def bench_load(raw: list[str], path: str) -> float:
    """Benchmark full LogStore.load_lines."""
    store = LogStore()
    start = time.perf_counter()
    store.load_lines(raw, file_path=path)
    elapsed = time.perf_counter() - start
    return elapsed


def bench_apply_filters(store: LogStore) -> float:
    """Benchmark _apply_filters with no active filters."""
    start = time.perf_counter()
    store._apply_filters()
    return time.perf_counter() - start


def bench_apply_filters_with(store: LogStore, n_filters: int) -> float:
    """Benchmark _apply_filters with n plain filters active."""
    saved = (list(store.filters), list(store.filter_enabled))
    store.filters = [Filter(pattern=f"message{i}", mode=SearchMode.PLAIN) for i in range(n_filters)]
    store.filter_enabled = [True] * n_filters
    start = time.perf_counter()
    store._apply_filters()
    elapsed = time.perf_counter() - start
    store.filters, store.filter_enabled = saved
    return elapsed


def bench_category_toggle(store: LogStore) -> float:
    """Benchmark category disable + re-enable."""
    cats = list(store.category_counts.keys())
    if not cats:
        return 0.0
    start = time.perf_counter()
    store.disable_category(cats[0])
    store._apply_filters()
    store.enable_category(cats[0])
    store._apply_filters()
    return time.perf_counter() - start


def bench_search(store: LogStore) -> float:
    """Benchmark search with plain text."""
    start = time.perf_counter()
    store.search("Message", SearchMode.PLAIN)
    return time.perf_counter() - start


def bench_search_regex(store: LogStore) -> float:
    """Benchmark search with regex."""
    start = time.perf_counter()
    store.search(r"Message\s+line\s+\d+", SearchMode.REGEX)
    return time.perf_counter() - start


def bench_search_simple_query(store: LogStore) -> float:
    """Benchmark search with simple query."""
    start = time.perf_counter()
    store.search('"Message" AND "1000"', SearchMode.SIMPLE)
    return time.perf_counter() - start


def bench_batch_match(store: LogStore) -> float:
    """Benchmark filter_engine.batch_match on filtered indices."""
    from log_viewer.core.filter_engine import batch_match
    filters = [Filter(pattern="message", mode=SearchMode.PLAIN)]
    indices = store.filtered_indices[:100_000] if len(store.filtered_indices) > 100_000 else store.filtered_indices
    messages = [store.lines[i].message for i in indices]
    lowered = [store.lines[i].message_lower for i in indices]
    start = time.perf_counter()
    batch_match(messages, filters, pre_lowered=lowered)
    return time.perf_counter() - start


def run_benchmarks(file_path: str, line_count: int) -> list[tuple[str, float]]:
    """Run all benchmarks and return (name, median_seconds) pairs."""
    # Ensure file exists
    if not Path(file_path).exists():
        print(f"Generating synthetic {line_count:,}-line file at {file_path}...")
        generate_synthetic(file_path, line_count)

    print(f"Loading {file_path} into memory...")
    raw = Path(file_path).read_text(encoding="utf-8", errors="replace").split("\n")
    raw = [l for l in raw if l.strip()]  # drop empty trailing line
    print(f"Loaded {len(raw):,} lines")

    results: list[tuple[str, float]] = []

    # Benchmark: parse
    print("Benchmarking parse_line...")
    times = [bench_parse(None, raw) for _ in range(3)]
    results.append(("parse_line (6M lines)", statistics.median(times)))

    # Benchmark: load (includes parse + category tree + filters)
    print("Benchmarking load_lines...")
    times = [bench_load(raw, file_path) for _ in range(3)]
    results.append(("load_lines (full)", statistics.median(times)))

    # Load a single store for remaining benchmarks
    store = LogStore()
    store.load_lines(raw, file_path=file_path)
    print(f"Store ready: {len(store.lines):,} lines, {len(store.category_counts)} categories")

    # Benchmark: _apply_filters (no filters)
    print("Benchmarking _apply_filters (0 filters)...")
    times = [bench_apply_filters(store) for _ in range(3)]
    results.append(("_apply_filters (0 filters)", statistics.median(times)))

    # Benchmark: _apply_filters (1 filter)
    print("Benchmarking _apply_filters (1 filter)...")
    times = [bench_apply_filters_with(store, 1) for _ in range(3)]
    results.append(("_apply_filters (1 filter)", statistics.median(times)))

    # Benchmark: _apply_filters (3 filters)
    print("Benchmarking _apply_filters (3 filters)...")
    times = [bench_apply_filters_with(store, 3) for _ in range(3)]
    results.append(("_apply_filters (3 filters)", statistics.median(times)))

    # Benchmark: _apply_filters (5 filters)
    print("Benchmarking _apply_filters (5 filters)...")
    times = [bench_apply_filters_with(store, 5) for _ in range(3)]
    results.append(("_apply_filters (5 filters)", statistics.median(times)))

    # Benchmark: category toggle
    print("Benchmarking category toggle...")
    times = [bench_category_toggle(store) for _ in range(3)]
    results.append(("category toggle (disable+enable)", statistics.median(times)))

    # Benchmark: search plain
    print("Benchmarking search (plain)...")
    times = [bench_search(store) for _ in range(3)]
    results.append(("search (plain)", statistics.median(times)))

    # Benchmark: search regex
    print("Benchmarking search (regex)...")
    times = [bench_search_regex(store) for _ in range(3)]
    results.append(("search (regex)", statistics.median(times)))

    # Benchmark: search simple query
    print("Benchmarking search (simple query)...")
    times = [bench_search_simple_query(store) for _ in range(3)]
    results.append(("search (simple query)", statistics.median(times)))

    # Benchmark: batch_match
    print("Benchmarking batch_match...")
    times = [bench_batch_match(store) for _ in range(3)]
    results.append(("batch_match (100K lines)", statistics.median(times)))

    return results


def print_table(results: list[tuple[str, float]]) -> None:
    """Print results as a formatted table."""
    print("\n" + "=" * 65)
    print(f"{'Operation':<35} {'Median (s)':>12}")
    print("-" * 65)
    for name, secs in results:
        print(f"{name:<35} {secs:>12.4f}")
    print("=" * 65)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Profile log_viewer core operations")
    parser.add_argument("--file", default="d:/log.txt", help="Log file path")
    parser.add_argument("--lines", type=int, default=6_000_000, help="Lines for synthetic file")
    args = parser.parse_args()

    results = run_benchmarks(args.file, args.lines)
    print_table(results)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the profiling script to capture baseline**

Run: `cd d:/ProjectsNoSaber/log_viewer && uv run python scripts/profile_perf.py`

Expected: A table of timings for each operation. Copy the output into `scripts/baseline.txt` for later comparison.

- [ ] **Step 3: Commit baseline**

```bash
git add scripts/profile_perf.py scripts/baseline.txt
git commit -m "Add performance profiling script and baseline results"
```

---

### Task 2: Optimize `_is_category_enabled` — dict cache

Currently `_is_category_enabled` calls `_find_category_node(category)` on every line, which traverses the tree by splitting on `/` and doing dict lookups for each part. We build a flat `dict[str, bool]` cache that is rebuilt only when category tree state changes.

**Files:**
- Modify: `src/log_viewer/core/log_store.py:301-314` (`_is_category_enabled`)
- Modify: `src/log_viewer/core/log_store.py:316-346` (`_apply_filters`)
- Test: `tests/unit/test_log_store.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_log_store.py`:

```python
def test_is_category_enabled_uses_flat_cache():
    """_is_category_enabled should use a flat dict cache, not tree traversal."""
    store = LogStore()
    store.load_lines([
        "2024-01-01T00:00:00 cat/a [LOG_INFO] msg1",
        "2024-01-01T00:00:01 cat/b [LOG_INFO] msg2",
    ])
    # Cache should exist after load
    assert hasattr(store, "_category_enabled_cache")
    assert store._is_category_enabled("cat/a") is True
    assert store._is_category_enabled("cat/b") is True
    # Disable cat/a
    store.disable_category("cat/a")
    assert store._is_category_enabled("cat/a") is False
    assert store._is_category_enabled("cat/b") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_log_store.py::test_is_category_enabled_uses_flat_cache -v`
Expected: FAIL (no `_category_enabled_cache` attribute)

- [ ] **Step 3: Implement the cache**

In `src/log_viewer/core/log_store.py`, make these changes:

1. Add `_category_enabled_cache: dict[str, bool]` to `__init__`:

```python
self._category_enabled_cache: dict[str, bool] = {}
```

2. Add `_rebuild_category_cache` method:

```python
def _rebuild_category_cache(self) -> None:
    """Rebuild flat dict cache from category tree state."""
    cache: dict[str, bool] = {}
    for path in self.category_counts:
        node = self._find_category_node(path)
        cache[path] = node.enabled if node else True
    self._category_enabled_cache = cache
```

3. Replace `_is_category_enabled`:

```python
def _is_category_enabled(self, category: str) -> bool:
    """Check if a category is visible via flat cache. O(1)."""
    if not category:
        return True
    return self._category_enabled_cache.get(category, True)
```

4. Call `_rebuild_category_cache()` at the end of `_build_category_tree` and at the end of every method that changes category state (`enable_category`, `disable_category`, `enable_all_categories`, `disable_all_categories`, `set_disabled_categories`). Each of these already calls `_apply_filters()`, so add the rebuild just before `_apply_filters()` in each.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_log_store.py::test_is_category_enabled_uses_flat_cache -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: All tests pass. The cache is internal — no public API change.

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/core/log_store.py tests/unit/test_log_store.py
git commit -m "perf: cache category enabled state in flat dict for O(1) lookup"
```

---

### Task 3: Optimize `_apply_filters` — pre-compute category set once

Currently `_apply_filters` iterates over `_category_index` items and calls `_is_category_enabled` for each category on every invocation. With the cache from Task 2 this is already faster, but we can go further: compute `category_enabled` as a set union only when category state changes, not on every filter change.

**Files:**
- Modify: `src/log_viewer/core/log_store.py:316-346` (`_apply_filters`)
- Modify: `src/log_viewer/core/log_store.py` — add `_category_visible_set: set[int]`

- [ ] **Step 1: Write the failing test**

```python
def test_apply_filters_uses_cached_category_set():
    """Filter changes should not recompute category-visible indices."""
    store = LogStore()
    store.load_lines([
        "2024-01-01T00:00:00 cat/a [LOG_INFO] msg1",
        "2024-01-01T00:00:01 cat/b [LOG_INFO] msg2",
        "2024-01-01T00:00:02 cat/a [LOG_ERROR] msg3",
    ])
    # _category_visible_set should exist
    assert hasattr(store, "_category_visible_set")
    initial_set = store._category_visible_set.copy()
    # Adding a filter should NOT change _category_visible_set
    store.add_filter(Filter(pattern="msg", mode=SearchMode.PLAIN))
    assert store._category_visible_set == initial_set
    # Disabling a category SHOULD change it
    store.disable_category("cat/a")
    assert store._category_visible_set != initial_set
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_log_store.py::test_apply_filters_uses_cached_category_set -v`
Expected: FAIL (no `_category_visible_set`)

- [ ] **Step 3: Implement cached category-visible set**

In `src/log_viewer/core/log_store.py`:

1. Add to `__init__`:

```python
self._category_visible_set: set[int] = set()
```

2. Add method `_rebuild_category_visible_set`:

```python
def _rebuild_category_visible_set(self) -> None:
    """Compute set of line indices whose category is enabled."""
    self._category_visible_set = set()
    for cat, indices in self._category_index.items():
        if self._is_category_enabled(cat):
            self._category_visible_set |= indices
```

3. Call `_rebuild_category_visible_set()` inside `_rebuild_category_cache` (after building the cache, before returning).

4. In `_apply_filters`, replace the category scan block:

```python
# BEFORE (remove this block):
category_enabled: set[int] = set()
for cat, indices in self._category_index.items():
    if self._is_category_enabled(cat):
        category_enabled |= indices

# AFTER:
category_enabled = self._category_visible_set
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_log_store.py::test_apply_filters_uses_cached_category_set -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/core/log_store.py tests/unit/test_log_store.py
git commit -m "perf: cache category-visible index set, skip rebuild on filter-only changes"
```

---

### Task 4: Optimize `_apply_filters` — avoid rebuilding visible_lines list in GUI

Currently `_refresh_log_only` and `_refresh_display` in `app.py` create a new list via `[store.lines[i] for i in store.filtered_indices]` on every refresh. For 6M lines this allocates a list of 6M references. The model's `update_lines` already checks identity, so we can pass index-range-based access instead.

**Files:**
- Modify: `src/log_viewer/gui/log_table.py` — add index-based `update_from_store` method to model
- Modify: `src/log_viewer/gui/app.py:435-444, 446-454` (`_refresh_log_only`, `_refresh_display`)

- [ ] **Step 1: Add `update_from_store` to `LogTableModel`**

The model currently holds `self._lines` as a flat list of visible `LogLine` objects. Add an alternative update path that stores the full `lines` list and `filtered_indices` list, resolving on demand in `data()`:

In `src/log_viewer/gui/log_table.py`, add to `LogTableModel`:

```python
def update_from_store(self, all_lines: list[LogLine], filtered_indices: list[int]) -> None:
    """Update using index mapping — avoids creating a visible-lines list."""
    self.beginResetModel()
    self._all_lines = all_lines
    self._filtered_indices = filtered_indices
    self._lines = [all_lines[i] for i in filtered_indices]
    self.endResetModel()
```

This is a minimal change — it still creates the list but we'll optimize further if needed. The key gain is that we can skip the list creation in `_refresh_log_only` when only the view needs updating.

Actually, let me reconsider — the main cost is `beginResetModel/endResetModel` which forces Qt to discard all layout info. For now, the simplest win is to skip the list comprehension when the filtered indices haven't changed.

Revised approach: skip `update_lines` call when indices are identical.

- [ ] **Step 2: Track filtered_indices hash in model**

In `src/log_viewer/gui/log_table.py`, modify `LogTableModel`:

```python
def __init__(self, lines: list[LogLine] | None = None, store: LogStore | None = None) -> None:
    super().__init__()
    self._lines: list[LogLine] = lines or []
    self._highlights: list[Highlight] = []
    self._pinned_line_numbers: set[int] = set()
    self._store = store
    self._last_indices_len: int = 0
    self._last_indices_first: int = -1
    self._last_indices_last: int = -1

def update_lines(self, lines: list[LogLine]) -> None:
    if self._lines is lines:
        return
    if (len(self._lines) == len(lines)
        and self._lines
        and lines
        and self._lines[0] is lines[0]
        and self._lines[-1] is lines[-1]):
        return
    self.beginResetModel()
    self._lines = lines
    self.endResetModel()
```

This is a light identity check — same first/last element, same length → skip reset. It avoids the expensive `all(a is b for a, b in zip(...))` scan of 6M items.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/log_viewer/gui/log_table.py
git commit -m "perf: skip Qt model reset when visible lines are unchanged"
```

---

### Task 5: Optimize `_apply_filters` — avoid sorted() on full result set

Currently `_apply_filters` ends with `self.filtered_indices = sorted(visible)`. For 6M lines, `sorted()` on a set of millions of integers is expensive. Since the indices come from iterating `_category_index` (which groups by category, not by position), the union is unsorted. However, since line indices are already naturally ordered (0..N), and we're building a set, we can use `list(visible)` and sort only if needed, or use a numpy-style approach.

Simpler optimization: build as sorted list from the start using the natural ordering of line indices.

**Files:**
- Modify: `src/log_viewer/core/log_store.py:316-346` (`_apply_filters`)

- [ ] **Step 1: Replace set union + sorted with incremental sorted build**

Replace the end of `_apply_filters`:

```python
# BEFORE:
level_enabled = {i for i in would_be_visible if self.lines[i].level not in self.disabled_levels}
pinned_in_range = {n - 1 for n in self.pinned_line_numbers if 0 <= n - 1 < len(self.lines)}
visible = level_enabled | pinned_in_range
self.filtered_indices = sorted(visible)

# AFTER:
# Build sorted list directly from would_be_visible (already a set of ints)
disabled = self.disabled_levels
result = sorted(i for i in would_be_visible if self.lines[i].level not in disabled)
if self.pinned_line_numbers:
    pinned_in_range = sorted(n - 1 for n in self.pinned_line_numbers if 0 <= n - 1 < len(self.lines))
    # Merge two sorted lists
    result = _merge_sorted(result, pinned_in_range)
self.filtered_indices = result
```

2. Add helper function at module level in `log_store.py`:

```python
def _merge_sorted(a: list[int], b: list[int]) -> list[int]:
    """Merge two sorted lists, removing duplicates."""
    result: list[int] = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] < b[j]:
            result.append(a[i])
            i += 1
        elif a[i] > b[j]:
            result.append(b[j])
            j += 1
        else:
            result.append(a[i])
            i += 1
            j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/log_store.py
git commit -m "perf: build sorted filtered_indices directly, avoid set-then-sort"
```

---

### Task 6: Optimize `batch_match` — avoid redundant `text.lower()` calls

Currently in `batch_match`, even when `pre_lowered` is provided, the loop does `combined.search(lowered[i] if pre_lowered is not None else text)` which has a branch per iteration. We can split into two paths.

**Files:**
- Modify: `src/log_viewer/core/filter_engine.py:111-151` (`batch_match`)

- [ ] **Step 1: Split batch_match loop into two paths**

Replace the plain CI block in `batch_match`:

```python
# BEFORE:
if plain_ci:
    combined = re.compile("|".join(plain_ci), re.IGNORECASE)
    lowered = pre_lowered if pre_lowered is not None else [t.lower() for t in texts]
    for i, text in enumerate(texts):
        if combined.search(lowered[i] if pre_lowered is not None else text):
            matching.add(i)

# AFTER:
if plain_ci:
    combined = re.compile("|".join(plain_ci), re.IGNORECASE)
    if pre_lowered is not None:
        for i, low in enumerate(pre_lowered):
            if combined.search(low):
                matching.add(i)
    else:
        for i, text in enumerate(texts):
            if combined.search(text):
                matching.add(i)
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/filter_engine.py
git commit -m "perf: split batch_match loop to avoid per-iteration branch"
```

---

### Task 7: Optimize `_match_plain` — use pre-lowered text

Currently `_match_plain` does `pattern.lower() in text.lower()` on every call. For case-insensitive matches (the common path), we can compare against pre-lowered text.

**Files:**
- Modify: `src/log_viewer/core/filter_engine.py:32-36` (`_match_plain`)
- Modify: `src/log_viewer/core/log_store.py:172-199` (`search`)

- [ ] **Step 1: Add `match_lower` variant to filter_engine**

In `src/log_viewer/core/filter_engine.py`, add:

```python
def match_pre_lowered(text_lower: str, filt: Filter) -> bool:
    """Match against pre-lowered text. Only handles PLAIN and case-insensitive."""
    if filt.mode == SearchMode.PLAIN and not filt.case_sensitive:
        return filt.pattern.lower() in text_lower
    # Fallback for other modes
    if filt.mode == SearchMode.PLAIN:
        return filt.pattern in text_lower.upper() if not filt.case_sensitive else filt.pattern in text_lower
    return match(text_lower, filt)
```

Actually, simpler approach — just optimize `_match_plain` to cache `pattern.lower()`:

```python
def _match_plain(text: str, pattern: str, case_sensitive: bool) -> bool:
    if case_sensitive:
        return pattern in text
    return pattern.lower() in text.lower()
```

This is already optimal for the API. The real win is in `search()` — pass `message_lower` directly:

In `log_store.py` `search()`, change:

```python
# BEFORE:
for idx in self.filtered_indices:
    if filter_match(self.lines[idx].message, filt):
        matches.append(idx)

# AFTER:
if not filt.case_sensitive:
    pat_lower = filt.pattern.lower()
    for idx in self.filtered_indices:
        if pat_lower in self.lines[idx].message_lower:
            matches.append(idx)
else:
    for idx in self.filtered_indices:
        if filter_match(self.lines[idx].message, filt):
            matches.append(idx)
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/filter_engine.py src/log_viewer/core/log_store.py
git commit -m "perf: use pre-lowered message in search for case-insensitive plain match"
```

---

### Task 8: Optimize `_apply_filters` — fast path when no filters active

When there are no text filters and no disabled levels and no pinned lines, `filtered_indices` is just all indices. Short-circuit this.

**Files:**
- Modify: `src/log_viewer/core/log_store.py:316-346` (`_apply_filters`)

- [ ] **Step 1: Add fast path at top of `_apply_filters`**

```python
def _apply_filters(self) -> None:
    """Recompute filtered_indices."""
    # Fast path: no filters, no disabled levels, no pins, all categories enabled
    has_text_filters = any(self.filter_enabled)
    has_level_filters = bool(self.disabled_levels)
    has_pins = bool(self.pinned_line_numbers)
    all_cats = all(self._category_enabled_cache.get(c, True) for c in self.category_counts)

    if not has_text_filters and not has_level_filters and not has_pins and all_cats:
        self.filtered_indices = list(range(len(self.lines)))
        self._count_visible_levels()
        self.level_button_counts = dict(self.level_counts)
        return

    # ... rest of existing logic ...
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/log_store.py
git commit -m "perf: fast path in _apply_filters when no filters/levels/pins active"
```

---

### Task 9: Run post-optimization benchmarks and produce comparison

**Files:**
- Modify: `scripts/profile_perf.py` — add `--compare <baseline_file>` flag
- Create: `scripts/optimized.txt` (captured output)

- [ ] **Step 1: Add comparison mode to profiling script**

Add to `scripts/profile_perf.py`:

```python
def load_baseline(path: str) -> dict[str, float]:
    """Load baseline timings from a text file."""
    results = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("-") or line.startswith("Operation"):
                continue
            parts = line.rsplit(None, 1)
            if len(parts) == 2:
                try:
                    results[parts[0].strip()] = float(parts[1])
                except ValueError:
                    pass
    return results


def print_comparison(results: list[tuple[str, float]], baseline: dict[str, float]) -> None:
    """Print comparison table."""
    print("\n" + "=" * 85)
    print(f"{'Operation':<35} {'Before (s)':>10} {'After (s)':>10} {'Speedup':>10}")
    print("-" * 85)
    for name, secs in results:
        before = baseline.get(name)
        if before is not None and secs > 0:
            speedup = before / secs
            print(f"{name:<35} {before:>10.4f} {secs:>10.4f} {speedup:>9.2f}x")
        else:
            print(f"{name:<35} {'N/A':>10} {secs:>10.4f} {'N/A':>10}")
    print("=" * 85)
```

Update `main()` to accept `--compare`:

```python
parser.add_argument("--compare", default=None, help="Baseline file to compare against")
# ...
if args.compare:
    baseline = load_baseline(args.compare)
    print_comparison(results, baseline)
else:
    print_table(results)
```

- [ ] **Step 2: Run post-optimization benchmarks**

Run: `uv run python scripts/profile_perf.py --compare scripts/baseline.txt`

Capture output to `scripts/optimized.txt`.

- [ ] **Step 3: Run full test suite one final time**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 4: Commit final results**

```bash
git add scripts/profile_perf.py scripts/optimized.txt
git commit -m "Add comparison mode to profiling script, capture optimized results"
```

---

### Task 10: Show summary to user

- [ ] **Step 1: Print the comparison table for the user**

Display the before/after table from `scripts/optimized.txt`. If any operation shows < 2x speedup, note it as a candidate for Phase B (architectural refactor with virtual scrolling).

---

## Self-Review

**1. Spec coverage:**
- Profiling script: Task 1 ✓
- Parser optimization: `_SPLIT_RE` is already compiled at module level (verified by reading parser.py line 17). No task needed.
- `_apply_filters` set/cache: Tasks 2, 3, 5, 8 ✓
- Category lookup dict cache: Task 2 ✓
- Qt model optimization: Task 4 ✓
- Filter engine optimization: Tasks 6, 7 ✓
- Comparison table: Task 9 ✓

**2. Placeholder scan:** No TBD/TODO found. All steps have concrete code.

**3. Type consistency:** `filtered_indices` remains `list[int]`. `_category_enabled_cache` is `dict[str, bool]`. `_category_visible_set` is `set[int]`. All consistent across tasks.
