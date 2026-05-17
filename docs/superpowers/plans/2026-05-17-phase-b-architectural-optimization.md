# Phase B: Architectural Performance Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the remaining performance bottlenecks — virtual scrolling to avoid 6M-element list copies, cache `parse_query()` AST, and parallelize parsing — to achieve 3-30x speedups on the slowest operations.

**Architecture:** The model switches from holding a flat list of visible `LogLine` objects to holding `filtered_indices: list[int]` + a reference to `store.lines`. `data()` resolves `store.lines[filtered_indices[row]]` on demand. `parse_query()` results are cached by pattern string. Parsing is parallelized across CPU cores via `concurrent.futures.ProcessPoolExecutor`.

**Tech Stack:** Python 3.9+, PySide6 (Qt6), `concurrent.futures` (stdlib), `functools.lru_cache` (stdlib). No new dependencies.

**Baseline from Phase A (6.3M lines):**

| Operation | Time (s) | Target |
|---|---|---|
| parse_line (all) | 26.8 | ~5-8s (parallel) |
| LogStore.load_lines | 36.7 | ~10-15s (parallel parse) |
| _apply_filters (1 filter) | 6.0 | ~0.5-1s (virtual model) |
| category toggle | 5.4 | ~1-2s (virtual model) |
| search plain | 0.48 | ~0.5s (already fast) |
| search regex | 8.1 | ~8s (no change) |
| search simple query | 34.1 | ~1-2s (cache AST) |

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/log_viewer/gui/log_table.py` | Modify | Model holds indices + store ref, resolves on demand |
| `src/log_viewer/gui/app.py` | Modify | Remove `[store.lines[i] for i in ...]` list creation |
| `src/log_viewer/core/simple_query.py` | Modify | Add `lru_cache` to `parse_query` |
| `src/log_viewer/core/filter_engine.py` | Modify | Use cached parse_query in `_match_simple` and `_find_simple_spans` |
| `src/log_viewer/core/log_store.py` | Modify | Add `load_lines_parallel` for parallel parsing |
| `src/log_viewer/core/parser.py` | Modify | Add `parse_lines_batch` for chunk-based parallel parsing |
| `scripts/profile_perf.py` | Modify | Add new benchmarks, update comparison |
| `tests/unit/test_log_store.py` | Modify | Tests for virtual model integration |
| `tests/unit/test_simple_query.py` | Modify | Tests for parse_query caching |
| `tests/unit/test_parser.py` | Modify | Tests for batch parsing |
| `tests/gui/test_log_table.py` | Modify | Tests for index-based model |

---

### Task 1: Cache `parse_query()` results

The `parse_query()` function in `simple_query.py` is called for every line during simple query search (34s total). The same pattern string is parsed into an AST 6M times. Cache it.

**Files:**
- Modify: `src/log_viewer/core/simple_query.py:201-204`
- Modify: `src/log_viewer/core/filter_engine.py:48-54, 100-108`
- Test: `tests/unit/test_simple_query.py`

- [ ] **Step 1: Add `lru_cache` to `parse_query`**

In `src/log_viewer/core/simple_query.py`, add import and wrap `parse_query`:

```python
from functools import lru_cache

# ... existing code ...

@lru_cache(maxsize=256)
def parse_query(source: str) -> QueryNode:
    """Parse a simple query expression into an AST. Results are cached."""
    parser = _Parser(source)
    return parser.parse()
```

- [ ] **Step 2: Write test for caching**

Add to `tests/unit/test_simple_query.py`:

```python
def test_parse_query_is_cached():
    """parse_query should return the same object for identical inputs."""
    from log_viewer.core.simple_query import parse_query
    parse_query.cache_clear()
    ast1 = parse_query('"hello" AND "world"')
    ast2 = parse_query('"hello" AND "world"')
    assert ast1 is ast2
    assert parse_query.cache_info().hits == 1

def test_parse_query_different_inputs_not_cached():
    """Different inputs should produce different AST objects."""
    from log_viewer.core.simple_query import parse_query
    parse_query.cache_clear()
    ast1 = parse_query('"hello"')
    ast2 = parse_query('"world"')
    assert ast1 is not ast2
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_simple_query.py -v`
Expected: All pass.

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest`
Expected: All 422 pass.

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/core/simple_query.py tests/unit/test_simple_query.py
git commit -m "perf: cache parse_query results with lru_cache to avoid re-parsing"
```

---

### Task 2: Use cached AST in filter_engine `_match_simple` and `_find_simple_spans`

The `_match_simple` and `_find_simple_spans` functions call `parse_query(pattern)` on every invocation. With caching from Task 1, this is now a dict lookup, but the functions also create `QuerySyntaxError` wrappers. Simplify the call path.

**Files:**
- Modify: `src/log_viewer/core/filter_engine.py:48-54` (`_match_simple`)
- Modify: `src/log_viewer/core/filter_engine.py:100-108` (`_find_simple_spans`)

- [ ] **Step 1: Simplify `_match_simple`**

In `src/log_viewer/core/filter_engine.py`, replace `_match_simple`:

```python
def _match_simple(text: str, pattern: str, case_sensitive: bool) -> bool:
    """Simple query language match (AND/OR/NOT). Uses cached AST."""
    try:
        ast = parse_query(pattern)
        return ast.evaluate(text, case_sensitive)
    except QuerySyntaxError:
        return False
```

- [ ] **Step 2: Simplify `_find_simple_spans`**

Replace `_find_simple_spans`:

```python
def _find_simple_spans(
    text: str, pattern: str, case_sensitive: bool
) -> list[tuple[int, int]]:
    """Find all simple query match spans. Uses cached AST."""
    try:
        ast = parse_query(pattern)
        return ast.find_spans(text, case_sensitive)
    except QuerySyntaxError:
        return []
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest`
Expected: All 422 pass.

- [ ] **Step 4: Commit**

```bash
git add src/log_viewer/core/filter_engine.py
git commit -m "perf: simplify simple_query call sites to use cached AST"
```

---

### Task 3: Add `parse_lines_batch` for parallel parsing

Currently `load_lines` parses 6M lines sequentially. Add a batch parsing function that uses `ProcessPoolExecutor` to parse chunks in parallel.

**Files:**
- Modify: `src/log_viewer/core/parser.py` — add `parse_lines_batch` and `parse_plain_lines_batch`
- Modify: `src/log_viewer/core/log_store.py:72-95` — use parallel parsing in `load_lines`
- Test: `tests/unit/test_parser.py`

- [ ] **Step 1: Add batch parsing functions to parser.py**

Add at the end of `src/log_viewer/core/parser.py`:

```python
def _parse_chunk(args: tuple[list[str], int, list[tuple[int, int]]]) -> list[LogLine]:
    """Parse a chunk of lines. Worker function for parallel parsing."""
    raw_lines, start_idx, offsets = args
    return [
        parse_line(raw, start_idx + i + 1, offsets[i][0], offsets[i][1])
        for i, raw in enumerate(raw_lines)
    ]


def _parse_plain_chunk(args: tuple[list[str], int, list[tuple[int, int]]]) -> list[LogLine]:
    """Parse a chunk of plain-format lines. Worker function for parallel parsing."""
    raw_lines, start_idx, offsets = args
    return [
        parse_plain_line(raw, start_idx + i + 1, offsets[i][0], offsets[i][1])
        for i, raw in enumerate(raw_lines)
    ]


def parse_lines_batch(
    raw_lines: list[str],
    offsets: list[tuple[int, int]],
    plain: bool = False,
    chunk_size: int = 500_000,
) -> list[LogLine]:
    """Parse all lines using multiple processes.

    Args:
        raw_lines: Raw text lines to parse.
        offsets: Pre-computed (file_offset, line_length) tuples.
        plain: Use plain format parser if True, KSIVA format if False.
        chunk_size: Lines per chunk. Tune for CPU count and memory.

    Returns:
        Flat list of LogLine objects in original order.
    """
    import concurrent.futures
    import os

    worker = _parse_plain_chunk if plain else _parse_chunk
    n = len(raw_lines)
    num_workers = min(os.cpu_count() or 4, max(1, n // chunk_size))

    if num_workers <= 1 or n < chunk_size:
        # Not enough lines or CPUs to justify overhead
        if plain:
            return [
                parse_plain_line(raw, i + 1, offsets[i][0], offsets[i][1])
                for i, raw in enumerate(raw_lines)
            ]
        return [
            parse_line(raw, i + 1, offsets[i][0], offsets[i][1])
            for i, raw in enumerate(raw_lines)
        ]

    chunks: list[tuple[list[str], int, list[tuple[int, int]]]] = []
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        chunks.append((raw_lines[start:end], start, offsets[start:end]))

    results: list[LogLine] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        for chunk_result in executor.map(worker, chunks):
            results.extend(chunk_result)

    return results
```

- [ ] **Step 2: Write test for batch parsing**

Add to `tests/unit/test_parser.py`:

```python
def test_parse_lines_batch_matches_sequential():
    """Batch parsing should produce identical results to sequential parsing."""
    from log_viewer.core.parser import parse_lines_batch, parse_line
    raw = [
        "2024-01-01T00:00:00 app/main [LOG_INFO] hello",
        "2024-01-01T00:00:01 net/http [LOG_ERROR] world",
        "",
        "2024-01-01T00:00:02 db/query [LOG_DEBUG] test message here",
    ]
    offsets = [(0, len(l.encode("utf-8"))) for l in raw]

    batch_result = parse_lines_batch(raw, offsets, chunk_size=2)
    sequential = [
        parse_line(raw[i], i + 1, offsets[i][0], offsets[i][1])
        for i in range(len(raw))
    ]

    assert len(batch_result) == len(sequential)
    for b, s in zip(batch_result, sequential):
        assert b.line_number == s.line_number
        assert b.message == s.message
        assert b.category == s.category
        assert b.level == s.level
```

- [ ] **Step 3: Run test**

Run: `uv run pytest tests/unit/test_parser.py::test_parse_lines_batch_matches_sequential -v`
Expected: PASS

- [ ] **Step 4: Integrate into `LogStore.load_lines`**

In `src/log_viewer/core/log_store.py`, replace the sequential parsing in `load_lines`:

```python
# Replace this block:
#     if fmt == LogFormat.PLAIN:
#         self.lines = [
#             parse_plain_line(raw, i + 1, offsets[i][0], offsets[i][1])
#             for i, raw in enumerate(raw_lines)
#         ]
#     else:
#         self.lines = [
#             parse_line(raw, i + 1, offsets[i][0], offsets[i][1])
#             for i, raw in enumerate(raw_lines)
#         ]

# With:
    from log_viewer.core.parser import parse_lines_batch
    self.lines = parse_lines_batch(raw_lines, offsets, plain=(fmt == LogFormat.PLAIN))
```

Also remove the now-unused imports at the top of `log_store.py` if `parse_line` and `parse_plain_line` are no longer called directly:

```python
# Change:
#   from log_viewer.core.parser import detect_format, parse_line, parse_plain_line
# To:
    from log_viewer.core.parser import detect_format
```

Wait — `parse_line` and `parse_plain_line` are still used inside `parse_lines_batch` internally, so the import in `log_store.py` can be simplified but doesn't have to be. Only remove them from `log_store.py`'s imports if they're not used elsewhere in the file. Since `load_lines` was the only caller, remove them:

```python
from log_viewer.core.parser import detect_format
```

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest`
Expected: All 422 pass.

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/core/parser.py src/log_viewer/core/log_store.py tests/unit/test_parser.py
git commit -m "perf: parallelize log line parsing across CPU cores"
```

---

### Task 4: Virtual model — LogTableModel holds indices + store ref

The biggest architectural change. Currently `_refresh_log_only` creates `[store.lines[i] for i in store.filtered_indices]` — a 6M-element list of `LogLine` references. The model stores this list and `data()` indexes into it.

Change: the model stores `filtered_indices: list[int]` and a reference to `store.lines`. `data()` resolves `store.lines[filtered_indices[row]]` on demand. No list of 6M objects is ever created.

**Files:**
- Modify: `src/log_viewer/gui/log_table.py:33-156` (`LogTableModel`)
- Modify: `src/log_viewer/gui/app.py:435-454` (`_refresh_log_only`, `_refresh_display`)

- [ ] **Step 1: Rewrite `LogTableModel` to be index-based**

Replace `LogTableModel` in `src/log_viewer/gui/log_table.py`:

```python
class LogTableModel(QAbstractTableModel):
    """Table model that resolves rows via index mapping into store.lines.

    Instead of holding a flat list of visible LogLine objects (expensive at 6M),
    holds filtered_indices and resolves store.lines[idx] on demand in data().
    """

    def __init__(self, store: LogStore | None = None) -> None:
        super().__init__()
        self._store = store
        self._filtered_indices: list[int] = []
        self._highlights: list[Highlight] = []
        self._pinned_line_numbers: set[int] = set()

    @property
    def lines(self) -> list[LogLine]:
        """Compatibility property — builds list on demand. Avoid in hot paths."""
        if self._store is None:
            return []
        return [self._store.lines[i] for i in self._filtered_indices]

    def _line_at(self, row: int) -> LogLine | None:
        """Resolve a LogLine for a visible row. O(1)."""
        if self._store is None or row < 0 or row >= len(self._filtered_indices):
            return None
        return self._store.lines[self._filtered_indices[row]]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._filtered_indices)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(_COLUMNS)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or index.row() >= len(self._filtered_indices):
            return None

        line = self._line_at(index.row())
        if line is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return str(line.line_number)
            if col == 1:
                return line.time_only
            if col == 2:
                return line.category
            if col == 3:
                return line.message
            return None

        if role == Qt.ItemDataRole.ForegroundRole:
            color_name = _LEVEL_COLORS.get(line.level.name)
            return QColor(color_name) if color_name else None

        if role == Qt.ItemDataRole.BackgroundRole:
            if line.line_number in self._pinned_line_numbers:
                return QColor(_t("pinned_bg"))
            return None

        if role == Qt.ItemDataRole.UserRole:
            return line

        if role == Qt.ItemDataRole.FontRole:
            return None

        return None

    def update_indices(
        self,
        filtered_indices: list[int],
        selection_model: object = None,
        table_view: object = None,
    ) -> None:
        """Update visible rows via index list. No LogLine list creation needed."""
        if self._filtered_indices is filtered_indices:
            return
        if (len(self._filtered_indices) == len(filtered_indices)
            and self._filtered_indices
            and filtered_indices
            and self._filtered_indices[0] == filtered_indices[0]
            and self._filtered_indices[-1] == filtered_indices[-1]):
            return
        # Save selected line numbers and viewport offset before reset
        selected_line_numbers: set[int] = set()
        anchor_line_number: int | None = None
        anchor_viewport_y: int | None = None
        if selection_model is not None:
            from PySide6.QtCore import QItemSelectionModel
            if isinstance(selection_model, QItemSelectionModel):
                selected_rows = sorted({idx.row() for idx in selection_model.selectedIndexes()})
                for row in selected_rows:
                    line = self._line_at(row)
                    if line is not None:
                        selected_line_numbers.add(line.line_number)
                if selected_rows and table_view is not None:
                    anchor_line = self._line_at(selected_rows[0])
                    if anchor_line is not None:
                        anchor_line_number = anchor_line.line_number
                        anchor_viewport_y = table_view.rowViewportPosition(selected_rows[0])
        self.beginResetModel()
        self._filtered_indices = filtered_indices
        self.endResetModel()
        # Restore selection for lines that remain visible
        if selected_line_numbers and selection_model is not None:
            from PySide6.QtCore import QItemSelectionModel
            if isinstance(selection_model, QItemSelectionModel):
                for row in range(len(self._filtered_indices)):
                    line = self._line_at(row)
                    if line is not None and line.line_number in selected_line_numbers:
                        selection_model.select(
                            self.index(row, 0),
                            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                        )
        # Restore viewport position so anchor row stays at same visual position
        if anchor_line_number is not None and anchor_viewport_y is not None and table_view is not None:
            for row in range(len(self._filtered_indices)):
                line = self._line_at(row)
                if line is not None and line.line_number == anchor_line_number:
                    table_view.scrollTo(self.index(row, 0))
                    current_y = table_view.rowViewportPosition(row)
                    diff = current_y - anchor_viewport_y
                    if diff != 0:
                        sb = table_view.verticalScrollBar()
                        sb.setValue(max(sb.minimum(), min(sb.value() + diff, sb.maximum())))
                    break

    def update_lines(self, lines: list[LogLine], selection_model: object = None, table_view: object = None) -> None:
        """Compatibility: accept a list of LogLine objects."""
        # Build indices from line_number field
        if self._store is None:
            self.beginResetModel()
            self._filtered_indices = []
            self.endResetModel()
            return
        # Build a set of line_numbers for fast lookup
        line_nums = {l.line_number for l in lines}
        indices = [i for i, l in enumerate(self._store.lines) if l.line_number in line_nums]
        self.update_indices(indices, selection_model, table_view)

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self._highlights = highlights

    def set_pinned_line_numbers(self, line_numbers: set[int]) -> None:
        self._pinned_line_numbers = line_numbers

    def highlights(self) -> list[Highlight]:
        return self._highlights
```

- [ ] **Step 2: Update `_refresh_log_only` and `_refresh_display` in app.py**

In `src/log_viewer/gui/app.py`, replace both methods to use `update_indices`:

```python
def _refresh_log_only(self) -> None:
    """Refresh log table and status without rebuilding side panel."""
    store = self.log_store
    store._apply_filters()
    self._table_model.update_indices(
        store.filtered_indices,
        selection_model=self.log_table.selectionModel(),
        table_view=self.log_table,
    )
    self._table_model.set_pinned_line_numbers(store.pinned_line_numbers)
    active_highlights = [h for h, e in zip(store.highlights, store.highlight_enabled) if e]
    self._table_model.set_highlights(active_highlights)
    self._update_status()

def _refresh_display(self) -> None:
    store = self.log_store
    self._table_model.update_indices(
        store.filtered_indices,
        selection_model=self.log_table.selectionModel(),
        table_view=self.log_table,
    )
    self._table_model.set_pinned_line_numbers(store.pinned_line_numbers)
    active_highlights = [h for h, e in zip(store.highlights, store.highlight_enabled) if e]
    self._table_model.set_highlights(active_highlights)
    self._refresh_side_panel()
    self._update_status()
```

- [ ] **Step 3: Update `_jump_to_search_match` to use bisect**

Currently uses `self.log_store.filtered_indices.index(matched_idx)` which is O(n). Replace with binary search:

In `src/log_viewer/gui/app.py`, replace `_jump_to_search_match`:

```python
def _jump_to_search_match(self) -> None:
    import bisect
    ss = self.log_store.search_state
    if not ss or not ss.matches:
        return
    matched_idx = ss.matches[ss.current_index]
    indices = self.log_store.filtered_indices
    pos = bisect.bisect_left(indices, matched_idx)
    if pos < len(indices) and indices[pos] == matched_idx:
        self.log_table.selectRow(pos)
        self.log_table.scrollTo(self._table_model.index(pos, 0))
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest`
Expected: All pass. If any GUI test fails due to model API change, update the test to use `update_indices` or `update_lines` (compatibility method).

- [ ] **Step 5: Fix any test failures**

Common failure points:
- Tests that call `LogTableModel(lines=[...])` — update to use `update_lines` after construction
- Tests that check `model.lines` — still works via compatibility property
- Tests that check `model._lines` — update to check `model._filtered_indices` or use `model.lines`

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/gui/log_table.py src/log_viewer/gui/app.py tests/
git commit -m "perf: virtual model — hold filtered indices, resolve on demand in data()"
```

---

### Task 5: Run post-Phase-B benchmarks and produce final comparison

**Files:**
- Modify: `scripts/profile_perf.py` — add parallel parsing benchmark
- Create: `scripts/phase_b_results.txt`

- [ ] **Step 1: Add parallel parsing benchmark to profile_perf.py**

Add a new benchmark function:

```python
def bench_parse_parallel(raw: list[str]) -> float:
    """Benchmark parallel parsing via parse_lines_batch."""
    from log_viewer.core.parser import parse_lines_batch
    offsets = []
    offset = 0
    for raw_line in raw:
        line_bytes = raw_line.encode("utf-8")
        offsets.append((offset, len(line_bytes)))
        offset += len(line_bytes) + 1
    start = time.perf_counter()
    parse_lines_batch(raw, offsets)
    return time.perf_counter() - start
```

Add to `run_benchmarks` after the `parse_line` benchmark:

```python
# Benchmark: parallel parse
print("Benchmarking parse_lines_batch (parallel)...")
times = [bench_parse_parallel(raw) for _ in range(3)]
results.append(("parse_lines_batch (parallel)", statistics.median(times)))
```

- [ ] **Step 2: Run benchmarks with comparison**

Run: `uv run python scripts/profile_perf.py --compare scripts/baseline.txt`

Save output to `scripts/phase_b_results.txt`.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/profile_perf.py scripts/phase_b_results.txt
git commit -m "Add Phase B benchmark results and final comparison table"
```

---

## Self-Review

**1. Spec coverage:**
- Virtual scrolling: Task 4 ✓
- Incremental filter updates: Already addressed in Phase A (fast path + cached sets). Task 4 completes it by removing the 6M-element list copy. ✓
- Cache `parse_query()`: Tasks 1, 2 ✓
- Parallel parsing: Task 3 ✓
- Final benchmarks: Task 5 ✓

**2. Placeholder scan:** No TBD/TODO. All steps have concrete code.

**3. Type consistency:**
- `_filtered_indices: list[int]` — used consistently across model
- `_store: LogStore | None` — same type as before
- `update_indices(filtered_indices: list[int], ...)` — new method, `update_lines` kept for compatibility
- `parse_query` returns `QueryNode` — same as before, now cached
- `_parse_chunk` / `_parse_plain_chunk` return `list[LogLine]` — consistent with `parse_lines_batch` return type
