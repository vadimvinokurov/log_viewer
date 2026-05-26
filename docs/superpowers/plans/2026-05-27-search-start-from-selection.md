# Search Start From Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make search start from the currently selected line instead of always from the top.

**Architecture:** Add `start_line` parameter to `log_store.search()`, use `bisect_left` to find the first match at or after that position. MainWindow passes the selected row's global index as `start_line`.

**Tech Stack:** Python 3.9+, PySide6, numpy

---

### Task 1: Add `start_line` parameter to `log_store.search()`

**Files:**
- Modify: `src/log_viewer/core/log_store.py:1` (add import), `src/log_viewer/core/log_store.py:326-352` (search method)
- Test: `tests/unit/test_log_store.py`

- [ ] **Step 1: Write the failing unit tests**

Add these tests to `tests/unit/test_log_store.py` inside the `TestLogStoreSearch` class (after `test_search_backward_starts_from_last`):

```python
def test_search_start_line_matches_selected(self) -> None:
    """If selected line is a match, it becomes current_index."""
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    # matches for "Failed" are indices [1, 2]
    state = store.search("Failed", SearchMode.PLAIN, start_line=1)
    assert state.matches == [1, 2]
    assert state.current_index == 0  # bisect_left([1,2], 1) == 0

def test_search_start_line_between_matches(self) -> None:
    """If selected line is between matches, start from next match."""
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    # No line at index 5 matches "Failed", but line 1 does
    # After filtering, all 6 lines visible. matches=[1,2]
    # start_line=5 → bisect_left([1,2], 5) == 2 → wrap to 0
    state = store.search("Failed", SearchMode.PLAIN, start_line=5)
    assert state.matches == [1, 2]
    assert state.current_index == 0  # wraps to first

def test_search_start_line_before_first_match(self) -> None:
    """start_line=0 behaves like default (first match)."""
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    state = store.search("Failed", SearchMode.PLAIN, start_line=0)
    assert state.current_index == 0

def test_search_start_line_with_backward_direction(self) -> None:
    """start_line is ignored for BACKWARD direction (stays at last)."""
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    state = store.search("Failed", SearchMode.PLAIN, direction=SearchDirection.BACKWARD, start_line=1)
    assert state.current_index == 1  # last match, backward ignores start_line
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_log_store.py::TestLogStoreSearch::test_search_start_line_matches_selected -v`
Expected: FAIL — `search()` does not accept `start_line` keyword argument.

- [ ] **Step 3: Implement `start_line` in `log_store.search()`**

Add import at top of `src/log_viewer/core/log_store.py` (after `import re`):

```python
from bisect import bisect_left
```

Modify `search()` method. Replace lines 326-352 with:

```python
def search(
    self,
    pattern: str,
    mode: SearchMode,
    direction: SearchDirection = SearchDirection.FORWARD,
    start_line: int = 0,
) -> SearchState:
    filt = Filter(pattern=pattern, mode=mode)
    mask = self._compute_filter_mask(filt)

    # Intersect with currently visible lines
    visible_mask = mask[self.filtered_indices]
    local_indices = np.where(visible_mask)[0]
    matches = self.filtered_indices[local_indices].tolist()

    start = 0
    if matches and direction == SearchDirection.BACKWARD:
        start = len(matches) - 1
    elif matches:
        idx = bisect_left(matches, start_line)
        start = 0 if idx == len(matches) else idx

    state = SearchState(
        pattern=pattern,
        mode=mode,
        direction=direction,
        matches=matches,
        current_index=start,
    )
    self.search_state = state
    return state
```

- [ ] **Step 4: Run all unit tests to verify they pass**

Run: `uv run pytest tests/unit/test_log_store.py -v`
Expected: ALL PASS (both new and existing tests).

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/core/log_store.py tests/unit/test_log_store.py
git commit -m "feat(search): add start_line param to search for selection-based start"
```

---

### Task 2: Pass selected row from MainWindow to search

**Files:**
- Modify: `src/log_viewer/gui/app.py:301-312` (`_do_search` method)
- Test: `tests/gui/test_app.py`

- [ ] **Step 1: Write the failing GUI test**

Add these tests to `tests/gui/test_app.py` (after existing search tests):

```python
def test_search_starts_from_selected_row(main_window):
    lines = [
        "2025-01-01T10:00:00 LOG_INFO app/main hello",
        "2025-01-01T10:00:01 LOG_INFO app/main error one",
        "2025-01-01T10:00:02 LOG_INFO app/main ok",
        "2025-01-01T10:00:03 LOG_INFO app/main error two",
    ]
    main_window._on_file_loaded(_buf(*lines), "test.log")
    # Select row 2 (global index 2, "ok") — not a match
    main_window.log_table.selectRow(2)
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    ss = main_window.log_store.search_state
    assert ss is not None
    # matches are [1, 3], start_line=2 → bisect_left([1,3], 2) == 1 → match at index 3
    assert ss.matches[ss.current_index] == 3


def test_search_starts_from_selected_row_when_match(main_window):
    lines = [
        "2025-01-01T10:00:00 LOG_INFO app/main hello",
        "2025-01-01T10:00:01 LOG_INFO app/main error one",
        "2025-01-01T10:00:02 LOG_INFO app/main error two",
    ]
    main_window._on_file_loaded(_buf(*lines), "test.log")
    # Select row 1 (global index 1, "error one") — a match
    main_window.log_table.selectRow(1)
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    ss = main_window.log_store.search_state
    assert ss is not None
    # matches are [1, 2], start_line=1 → bisect_left([1,2], 1) == 0 → match at index 1
    assert ss.matches[ss.current_index] == 1


def test_search_starts_from_top_when_no_selection(main_window):
    lines = [
        "2025-01-01T10:00:00 LOG_INFO app/main hello",
        "2025-01-01T10:00:01 LOG_INFO app/main error one",
        "2025-01-01T10:00:02 LOG_INFO app/main error two",
    ]
    main_window._on_file_loaded(_buf(*lines), "test.log")
    # Clear selection
    main_window.log_table.clearSelection()
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    ss = main_window.log_store.search_state
    assert ss is not None
    assert ss.matches[ss.current_index] == 1  # first match from top
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/gui/test_app.py::test_search_starts_from_selected_row -v`
Expected: FAIL — `_do_search` does not pass `start_line`, so search always starts at match 0.

- [ ] **Step 3: Implement — modify `_do_search` in `app.py`**

Replace `_do_search` method (lines 301-312 in `src/log_viewer/gui/app.py`) with:

```python
def _do_search(
    self, pattern: str, mode: SearchMode, direction: SearchDirection
) -> None:
    if not pattern:
        return
    start_line = 0
    sel = self.log_table.selectionModel().selectedRows()
    if sel:
        pos = sel[0].row()
        indices = self.log_store.filtered_indices
        if pos < len(indices):
            start_line = int(indices[pos])
    self.log_store.search(pattern, mode, direction=direction, start_line=start_line)
    ss = self.log_store.search_state
    if ss and ss.matches:
        ss.in_search = True
    self._update_status()
    self._update_title()
    self._jump_to_search_match()
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/gui/app.py tests/gui/test_app.py
git commit -m "feat(search): start search from selected row instead of file top"
```
