# Line Number Commands (`:fn`, `:sn`, `:hn`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three commands that navigate/filter/highlight by line number instead of text pattern.

**Architecture:** Add `SearchMode.LINE_NUMBER` to models, handle it in filter_engine and log_store, wire commands in command_parser and app.py.

**Tech Stack:** Python 3.9+, PySide6, NumPy

---

### Task 1: Add `SearchMode.LINE_NUMBER` and extend command parser

**Files:**
- Modify: `src/log_viewer/core/models.py:72-76`
- Modify: `src/log_viewer/core/command_parser.py:17-26`
- Test: `tests/unit/test_command_parser.py`

- [ ] **Step 1: Add LINE_NUMBER to SearchMode enum**

In `src/log_viewer/core/models.py`, add the new enum member after `SIMPLE`:

```python
class SearchMode(Enum):
    PLAIN = "plain"
    REGEX = "regex"
    SIMPLE = "simple"
    LINE_NUMBER = "line_number"
```

- [ ] **Step 2: Add fn, sn, hn to valid commands**

In `src/log_viewer/core/command_parser.py`, update `_VALID_COMMANDS`:

```python
_VALID_COMMANDS: set[str] = {
    "s", "sr", "ss",
    "f", "fr", "fs",
    "fn", "sn", "hn",
    "h", "hr", "hs",
    "rmf", "rmh",
    "cate", "catd",
    "open", "reload",
    "pin", "rmpin",
    "q",
}
```

- [ ] **Step 3: Write parser tests**

In `tests/unit/test_command_parser.py`, add a new class at the end (before `TestEdgeCases`):

```python
class TestLineNumberCommands:
    """Test fn, sn, hn commands."""

    def test_fn_with_line_number(self) -> None:
        result = parse_command("fn 100")
        assert result == ParsedCommand(
            name="fn",
            text="100",
            raw="fn 100",
        )

    def test_sn_with_line_number(self) -> None:
        result = parse_command("sn 42")
        assert result == ParsedCommand(
            name="sn",
            text="42",
            raw="sn 42",
        )

    def test_hn_with_line_number(self) -> None:
        result = parse_command("hn 5")
        assert result == ParsedCommand(
            name="hn",
            text="5",
            raw="hn 5",
        )

    def test_fn_without_number_errors(self) -> None:
        with pytest.raises(ParseError, match="[Tt]ext"):
            parse_command("fn")

    def test_sn_without_number_errors(self) -> None:
        with pytest.raises(ParseError, match="[Tt]ext"):
            parse_command("sn")

    def test_hn_without_number_errors(self) -> None:
        with pytest.raises(ParseError, match="[Tt]ext"):
            parse_command("hn")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_command_parser.py -v`
Expected: All tests PASS (including new ones)

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/core/models.py src/log_viewer/core/command_parser.py tests/unit/test_command_parser.py
git commit -m "feat: add SearchMode.LINE_NUMBER and fn/sn/hn command parsing"
```

---

### Task 2: Handle LINE_NUMBER in filter_engine

**Files:**
- Modify: `src/log_viewer/core/filter_engine.py:21-29` (match function)
- Modify: `src/log_viewer/core/filter_engine.py:57-67` (find_spans function)
- Test: `tests/unit/test_filter_engine.py`

- [ ] **Step 1: Add LINE_NUMBER handling to match()**

In `src/log_viewer/core/filter_engine.py`, add a branch to `match()` after the SIMPLE check (line 28):

```python
def match(text: str, filt: Filter) -> bool:
    """Check if text matches the filter pattern."""
    if filt.mode == SearchMode.PLAIN:
        return _match_plain(text, filt.pattern, filt.case_sensitive)
    elif filt.mode == SearchMode.REGEX:
        return _match_regex(text, filt.pattern, filt.case_sensitive)
    elif filt.mode == SearchMode.SIMPLE:
        return _match_simple(text, filt.pattern, filt.case_sensitive)
    elif filt.mode == SearchMode.LINE_NUMBER:
        return True
    return False
```

`LINE_NUMBER` always returns `True` because actual matching is done by index in `_compute_filter_mask`. The `match()` function is only called for text-based matching, so for line-number filters it's a no-op pass-through.

- [ ] **Step 2: Add LINE_NUMBER handling to find_spans()**

In the same file, add a branch to `find_spans()` after the SIMPLE check (line 66):

```python
def find_spans(
    text: str, pattern: str, mode: SearchMode, case_sensitive: bool = False
) -> list[tuple[int, int]]:
    """Find all match spans (start, end) for a pattern in text."""
    if mode == SearchMode.PLAIN:
        return _find_plain_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.REGEX:
        return _find_regex_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.SIMPLE:
        return _find_simple_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.LINE_NUMBER:
        return [(0, len(text))] if text else []
    return []
```

- [ ] **Step 3: Write filter engine tests**

In `tests/unit/test_filter_engine.py`, add two new classes at the end:

```python
class TestLineNumberMatch:
    """Test LINE_NUMBER mode in match()."""

    def test_line_number_always_matches(self) -> None:
        f = Filter(pattern="100", mode=SearchMode.LINE_NUMBER)
        assert match("any text at all", f) is True

    def test_line_number_empty_text(self) -> None:
        f = Filter(pattern="100", mode=SearchMode.LINE_NUMBER)
        assert match("", f) is True

    def test_line_number_pattern_ignored(self) -> None:
        f = Filter(pattern="999", mode=SearchMode.LINE_NUMBER)
        assert match("unrelated text", f) is True


class TestFindSpansLineNumber:
    """Test find_spans with LINE_NUMBER mode."""

    def test_line_number_full_span(self) -> None:
        spans = find_spans("hello world", "5", SearchMode.LINE_NUMBER)
        assert spans == [(0, 11)]

    def test_line_number_empty_text(self) -> None:
        spans = find_spans("", "5", SearchMode.LINE_NUMBER)
        assert spans == []

    def test_line_number_pattern_ignored(self) -> None:
        spans = find_spans("some text", "999", SearchMode.LINE_NUMBER)
        assert spans == [(0, 9)]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_filter_engine.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/core/filter_engine.py tests/unit/test_filter_engine.py
git commit -m "feat: handle LINE_NUMBER mode in filter engine match and find_spans"
```

---

### Task 3: Handle LINE_NUMBER in log_store._compute_filter_mask

**Files:**
- Modify: `src/log_viewer/core/log_store.py:503-537`
- Test: `tests/unit/test_log_store.py`

- [ ] **Step 1: Add LINE_NUMBER branch to _compute_filter_mask**

In `src/log_viewer/core/log_store.py`, add a new early-return branch in `_compute_filter_mask` before the PLAIN branch (after line 509, `mask = np.zeros(n, dtype=bool)`):

```python
def _compute_filter_mask(self, filt: Filter) -> np.ndarray:
    """Compute boolean mask for ALL lines matching a single filter."""
    n = self.n
    if n == 0:
        return np.empty(0, dtype=bool)

    mask = np.zeros(n, dtype=bool)

    if filt.mode == SearchMode.LINE_NUMBER:
        idx = int(filt.pattern) - 1
        if 0 <= idx < n:
            mask[idx] = True
        return mask

    if filt.mode == SearchMode.PLAIN and not filt.case_sensitive:
        # ... rest unchanged
```

- [ ] **Step 2: Write log_store tests**

In `tests/unit/test_log_store.py`, add a new class at the end of the file:

```python
class TestLineNumberFilter:
    """Test LINE_NUMBER filter mode in LogStore."""

    def test_fn_shows_only_specified_line(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="3", mode=SearchMode.LINE_NUMBER))
        visible = store.filtered_indices.tolist()
        assert visible == [2]  # 0-based index for line 3

    def test_fn_multiple_accumulates(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="1", mode=SearchMode.LINE_NUMBER))
        store.add_filter(Filter(pattern="3", mode=SearchMode.LINE_NUMBER))
        visible = store.filtered_indices.tolist()
        assert visible == [0, 2]  # lines 1 and 3

    def test_fn_out_of_range_shows_nothing(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="999", mode=SearchMode.LINE_NUMBER))
        visible = store.filtered_indices.tolist()
        assert visible == []

    def test_fn_zero_shows_nothing(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="0", mode=SearchMode.LINE_NUMBER))
        visible = store.filtered_indices.tolist()
        assert visible == []

    def test_fn_toggle_disables(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="3", mode=SearchMode.LINE_NUMBER))
        store.filter_enabled[0] = False
        store._apply_filters()
        assert len(store.filtered_indices) == store.n
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_log_store.py::TestLineNumberFilter -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/log_viewer/core/log_store.py tests/unit/test_log_store.py
git commit -m "feat: handle LINE_NUMBER mode in _compute_filter_mask"
```

---

### Task 4: Wire fn/sn/hn commands in app.py

**Files:**
- Modify: `src/log_viewer/gui/app.py:230-300`
- Test: `tests/gui/test_log_table.py` (or manual verification)

- [ ] **Step 1: Add command handlers in _handle_command**

In `src/log_viewer/gui/app.py`, add three new `elif` blocks after the `h/hr/hs` block (after line 266, before `elif name == "rmh"`). Also add a helper method `_navigate_to_line`:

```python
        elif name in ("h", "hr", "hs"):
            mode = {"h": SearchMode.PLAIN, "hr": SearchMode.REGEX, "hs": SearchMode.SIMPLE}[name]
            self.log_store.add_highlight(
                Highlight(pattern=parsed.text, mode=mode)
            )
            self._refresh_display()
        elif name in ("fn", "hn"):
            line_num = self._parse_line_number(parsed.text, name)
            if line_num is None:
                return
            if name == "fn":
                self.log_store.add_filter(Filter(pattern=str(line_num), mode=SearchMode.LINE_NUMBER))
                self._refresh_display()
            else:
                self.log_store.add_highlight(Highlight(pattern=str(line_num), mode=SearchMode.LINE_NUMBER))
                self._refresh_display()
        elif name == "sn":
            line_num = self._parse_line_number(parsed.text, name)
            if line_num is None:
                return
            self._navigate_to_line(line_num)
```

And add these two methods to `MainWindow` (before `_jump_to_search_match`):

```python
    def _parse_line_number(self, text: str, cmd_name: str) -> int | None:
        """Parse and validate a line number from command text."""
        try:
            n = int(text.strip())
        except ValueError:
            self.bottom_bar.set_status(f"Error: {cmd_name} requires a line number")
            return None
        if n < 1 or n > self.log_store.n:
            self.bottom_bar.set_status(f"Error: line {n} out of range (1..{self.log_store.n})")
            return None
        return n

    def _navigate_to_line(self, line_number: int) -> None:
        """Scroll to and select a line by its 1-based line number."""
        idx = line_number - 1
        indices = self.log_store.filtered_indices
        pos = int(np.searchsorted(indices, idx))
        if pos < len(indices) and int(indices[pos]) == idx:
            self.log_table.selectRow(pos)
            self.log_table.scrollTo(
                self._table_model.index(pos, 0),
                LogTableView.ScrollHint.PositionAtCenter,
            )
        else:
            self.bottom_bar.set_status(f"Line {line_number} is filtered out")
```

Note: `_navigate_to_line` uses the same `selectRow`/`scrollTo` pattern as `_jump_to_search_match`, but simpler since we know the exact index.

- [ ] **Step 2: Run all unit tests**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/gui/app.py
git commit -m "feat: wire fn/sn/hn commands in MainWindow"
```

---

### Task 5: Update CLAUDE.md command docs

**Files:**
- Modify: `CLAUDE.md` (Command system section)

- [ ] **Step 1: Add fn/sn/hn to command docs**

In the Command system section, add to the Search/Filter/Highlight lines:

```
- **Search**: `s` (plain), `sr` (regex), `ss` (simple query), `sn` (line number) — enters search mode; `↑`/`↓` navigate matches, `Esc` exits
- **Filter**: `f`, `fr`, `fs`, `fn` (line number) — hide non-matching lines
- **Highlight**: `h`, `hr`, `hs`, `hn` (line number) — color matching text
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add fn/sn/hn to command system docs"
```

---

### Task 6: Smoke test

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `uv run --with ruff ruff check src/`
Expected: No errors
