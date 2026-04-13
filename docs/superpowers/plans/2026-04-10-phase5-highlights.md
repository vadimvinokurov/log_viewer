# Phase 5: Highlights — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Color-highlight matching text in log lines with `:h`, `:hr`, `:hs`, `:rmh`, `:lsh` commands.

**Architecture:** Extends filter_engine with span-finding capabilities (`find_spans`). Adds `find_spans` to QueryNode AST for SIMPLE mode. Modifies `refresh_log_panel()` to render highlight spans via Rich Text styling. Follows existing FilterListScreen and command handler patterns.

**Tech Stack:** Python 3.9+, Textual, Rich, pytest

**Prerequisite:** P5.1 (Highlight model + LogStore operations) is already implemented — `Highlight` dataclass in `models.py`, `add_highlight/remove_highlight/clear_highlights` in `log_store.py`, tests in `test_log_store.py` lines 236-267.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `src/log_viewer/core/simple_query.py` | Add `find_spans()` to QueryNode AST |
| Modify | `src/log_viewer/core/filter_engine.py` | Add `find_spans()` function for all modes |
| Modify | `src/log_viewer/tui/app.py` | Highlight rendering + command handlers |
| Create | `src/log_viewer/tui/screens/highlight_list.py` | `:lsh` modal screen |
| Modify | `tests/unit/test_simple_query.py` | Tests for AST `find_spans` |
| Modify | `tests/unit/test_filter_engine.py` | Tests for `find_spans` function |

---

### Task 1: Add `find_spans` to QueryNode AST classes

**Files:**
- Modify: `src/log_viewer/core/simple_query.py`
- Test: `tests/unit/test_simple_query.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_simple_query.py`:

```python
class TestFindSpans:
    """Test find_spans on QueryNode AST nodes."""

    def test_term_find_spans_single(self) -> None:
        node = parse_query('"error"')
        assert node.find_spans("An error occurred", case_sensitive=False) == [(3, 8)]

    def test_term_find_spans_multiple(self) -> None:
        node = parse_query('"error"')
        spans = node.find_spans("error and error again", case_sensitive=False)
        assert spans == [(0, 5), (10, 15)]

    def test_term_find_spans_case_sensitive(self) -> None:
        node = parse_query('"ERROR"')
        assert node.find_spans("An ERROR occurred", case_sensitive=True) == [(3, 8)]
        assert node.find_spans("An error occurred", case_sensitive=True) == []

    def test_term_find_spans_no_match(self) -> None:
        node = parse_query('"timeout"')
        assert node.find_spans("An error occurred", case_sensitive=False) == []

    def test_and_find_spans_combines_children(self) -> None:
        node = parse_query('"Failed" AND "config"')
        spans = node.find_spans("Failed to load config", case_sensitive=False)
        assert (0, 6) in spans  # "Failed"
        assert (15, 21) in spans  # "config"

    def test_or_find_spans_combines_children(self) -> None:
        node = parse_query('"Failed" OR "ok"')
        spans = node.find_spans("Failed but ok", case_sensitive=False)
        assert (0, 6) in spans  # "Failed"
        assert (11, 13) in spans  # "ok"

    def test_not_find_spans_returns_empty(self) -> None:
        node = parse_query('NOT "warning"')
        assert node.find_spans("warning issued", case_sensitive=False) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_simple_query.py::TestFindSpans -v`
Expected: FAIL — `AttributeError: 'TermNode' object has no attribute 'find_spans'`

- [ ] **Step 3: Implement `find_spans` on QueryNode classes**

Add `find_spans` method to each class in `src/log_viewer/core/simple_query.py`.

Add to `QueryNode` (abstract base):
```python
@abstractmethod
def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]: ...
```

Add to `TermNode`:
```python
def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    search_text = text if case_sensitive else text.lower()
    search_term = self.text if case_sensitive else self.text.lower()
    start = 0
    while True:
        idx = search_text.find(search_term, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(self.text)))
        start = idx + 1
    return spans
```

Add to `AndNode`:
```python
def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
    return self.left.find_spans(text, case_sensitive) + self.right.find_spans(text, case_sensitive)
```

Add to `OrNode`:
```python
def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
    return self.left.find_spans(text, case_sensitive) + self.right.find_spans(text, case_sensitive)
```

Add to `NotNode`:
```python
def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_simple_query.py::TestFindSpans -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/core/simple_query.py tests/unit/test_simple_query.py
git commit -m "feat: add find_spans to QueryNode AST for highlight span extraction"
```

---

### Task 2: Add `find_spans` to filter_engine.py

**Files:**
- Modify: `src/log_viewer/core/filter_engine.py`
- Test: `tests/unit/test_filter_engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_filter_engine.py`:

```python
from log_viewer.core.filter_engine import find_spans


class TestFindSpansPlain:
    """Test find_spans with plain text mode."""

    def test_plain_single_span(self) -> None:
        spans = find_spans("An error occurred", "error", SearchMode.PLAIN)
        assert spans == [(3, 8)]

    def test_plain_multiple_spans(self) -> None:
        spans = find_spans("error and error again", "error", SearchMode.PLAIN)
        assert spans == [(0, 5), (10, 15)]

    def test_plain_no_match(self) -> None:
        spans = find_spans("no match here", "timeout", SearchMode.PLAIN)
        assert spans == []

    def test_plain_case_insensitive(self) -> None:
        spans = find_spans("An ERROR occurred", "error", SearchMode.PLAIN, case_sensitive=False)
        assert spans == [(3, 8)]

    def test_plain_case_sensitive(self) -> None:
        spans = find_spans("An ERROR occurred", "error", SearchMode.PLAIN, case_sensitive=True)
        assert spans == []

    def test_plain_case_sensitive_match(self) -> None:
        spans = find_spans("An ERROR occurred", "ERROR", SearchMode.PLAIN, case_sensitive=True)
        assert spans == [(3, 8)]

    def test_plain_empty_text(self) -> None:
        spans = find_spans("", "error", SearchMode.PLAIN)
        assert spans == []

    def test_plain_empty_pattern(self) -> None:
        spans = find_spans("hello", "", SearchMode.PLAIN)
        assert spans == []


class TestFindSpansRegex:
    """Test find_spans with regex mode."""

    def test_regex_single_span(self) -> None:
        spans = find_spans("error_42 occurred", r"error_\d+", SearchMode.REGEX)
        assert spans == [(0, 8)]

    def test_regex_multiple_spans(self) -> None:
        spans = find_spans("error_1 and error_2", r"error_\d+", SearchMode.REGEX)
        assert spans == [(0, 7), (12, 19)]

    def test_regex_no_match(self) -> None:
        spans = find_spans("no match", r"error_\d+", SearchMode.REGEX)
        assert spans == []

    def test_regex_case_insensitive(self) -> None:
        spans = find_spans("ERROR_42", r"error_\d+", SearchMode.REGEX, case_sensitive=False)
        assert spans == [(0, 8)]

    def test_regex_case_sensitive(self) -> None:
        spans = find_spans("ERROR_42", r"error_\d+", SearchMode.REGEX, case_sensitive=True)
        assert spans == []

    def test_regex_invalid_pattern_returns_empty(self) -> None:
        spans = find_spans("some text", r"[invalid", SearchMode.REGEX)
        assert spans == []


class TestFindSpansSimple:
    """Test find_spans with simple query mode."""

    def test_simple_single_term(self) -> None:
        spans = find_spans("An error occurred", '"error"', SearchMode.SIMPLE)
        assert spans == [(3, 8)]

    def test_simple_and_combines_spans(self) -> None:
        spans = find_spans("Failed to load config", '"Failed" AND "config"', SearchMode.SIMPLE)
        assert (0, 6) in spans  # "Failed"
        assert (15, 21) in spans  # "config"

    def test_simple_or_combines_spans(self) -> None:
        spans = find_spans("Failed but ok", '"Failed" OR "ok"', SearchMode.SIMPLE)
        assert (0, 6) in spans
        assert (11, 13) in spans

    def test_simple_not_returns_empty(self) -> None:
        spans = find_spans("warning issued", 'NOT "warning"', SearchMode.SIMPLE)
        assert spans == []

    def test_simple_invalid_query_returns_empty(self) -> None:
        spans = find_spans("some text", "unquoted", SearchMode.SIMPLE)
        assert spans == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_filter_engine.py::TestFindSpansPlain -v`
Expected: FAIL — `ImportError: cannot import name 'find_spans'`

- [ ] **Step 3: Implement `find_spans` in filter_engine.py**

Add to `src/log_viewer/core/filter_engine.py`:

```python
def find_spans(text: str, pattern: str, mode: SearchMode, case_sensitive: bool = False) -> list[tuple[int, int]]:
    """Find all match spans (start, end) for a pattern in text."""
    if mode == SearchMode.PLAIN:
        return _find_plain_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.REGEX:
        return _find_regex_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.SIMPLE:
        return _find_simple_spans(text, pattern, case_sensitive)
    return []


def _find_plain_spans(text: str, pattern: str, case_sensitive: bool) -> list[tuple[int, int]]:
    """Find all substring match spans."""
    if not pattern:
        return []
    spans: list[tuple[int, int]] = []
    search_text = text if case_sensitive else text.lower()
    search_pattern = pattern if case_sensitive else pattern.lower()
    start = 0
    while True:
        idx = search_text.find(search_pattern, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(pattern)))
        start = idx + 1
    return spans


def _find_regex_spans(text: str, pattern: str, case_sensitive: bool) -> list[tuple[int, int]]:
    """Find all regex match spans."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        return [(m.start(), m.end()) for m in re.finditer(pattern, text, flags)]
    except re.error:
        return []


def _find_simple_spans(text: str, pattern: str, case_sensitive: bool) -> list[tuple[int, int]]:
    """Find all simple query match spans."""
    try:
        ast = parse_query(pattern)
        return ast.find_spans(text, case_sensitive)
    except QuerySyntaxError:
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_filter_engine.py::TestFindSpansPlain tests/unit/test_filter_engine.py::TestFindSpansRegex tests/unit/test_filter_engine.py::TestFindSpansSimple -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/core/filter_engine.py tests/unit/test_filter_engine.py
git commit -m "feat: add find_spans to filter_engine for all matching modes"
```

---

### Task 3: Rich Text highlight rendering in refresh_log_panel

**Files:**
- Modify: `src/log_viewer/tui/app.py`

- [ ] **Step 1: Add imports and `_apply_highlights` helper function**

Add import to `src/log_viewer/tui/app.py`. Modify the existing models import and add filter_engine import:

```python
from log_viewer.core.filter_engine import find_spans
from log_viewer.core.models import Filter, Highlight, InputMode, SearchDirection, SearchMode
```

Add this module-level function after the imports, before the `LogViewerApp` class:

```python
def _apply_highlights(text: str, base_style: str, highlights: list[Highlight]) -> Text:
    """Create a Rich Text with highlight color spans applied on top of base style."""
    rich = Text(text, style=base_style)
    for h in highlights:
        spans = find_spans(text, h.pattern, h.mode, h.case_sensitive)
        for start, end in spans:
            rich.stylize(h.color, start, end)
    return rich
```

- [ ] **Step 2: Modify `refresh_log_panel()` to use highlights**

Replace the `refresh_log_panel` method body. Change the four `Text(...)` cells to use `_apply_highlights` for category and message:

```python
def refresh_log_panel(self) -> None:
    """Rebuild LogPanel rows and CategoryPanel from LogStore state."""
    panel = self.query_one(LogPanel)
    panel.clear()
    store = self.log_store
    highlights = store.highlights
    for idx in store.filtered_indices:
        line = store.lines[idx]
        style = line.level.row_style
        panel.add_row(
            Text(str(line.line_number), style=style),
            Text(line.time_only, style=style),
            _apply_highlights(line.category, style, highlights),
            _apply_highlights(line.message, style, highlights),
        )
    try:
        cat_panel = self.query_one(CategoryPanel)
        cat_panel.rebuild()
    except Exception:
        pass  # CategoryPanel may not be in DOM during tests
    self._update_status()
    self._update_search_highlight()
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/log_viewer/tui/app.py
git commit -m "feat: apply highlight color spans to DataTable cell rendering"
```

---

### Task 4: HighlightListScreen modal

**Files:**
- Create: `src/log_viewer/tui/screens/highlight_list.py`

- [ ] **Step 1: Create HighlightListScreen**

Create `src/log_viewer/tui/screens/highlight_list.py`:

```python
"""HighlightListScreen — modal showing active highlights.

Triggered by :lsh command.
Format:
    Active highlights (2):
      1. :h ERROR [red]
      2. :h/color=yellow/WARNING
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from log_viewer.core.models import Highlight, SearchMode


def _format_highlight(h: Highlight, index: int) -> str:
    """Format a highlight for display."""
    cmd = "h" if h.mode == SearchMode.PLAIN else ("hr" if h.mode == SearchMode.REGEX else "hs")
    color = h.color
    if h.case_sensitive and color != "red":
        return f"  {index}. :{cmd}/cs,color={color}/{h.pattern}"
    elif h.case_sensitive:
        return f"  {index}. :{cmd}/cs/{h.pattern}"
    elif color != "red":
        return f"  {index}. :{cmd}/color={color}/{h.pattern}"
    else:
        return f"  {index}. :{cmd} {h.pattern}"


class HighlightListScreen(ModalScreen[None]):
    """Modal screen showing active highlights."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def __init__(self, highlights: list[Highlight]) -> None:
        super().__init__()
        self._highlights = highlights

    def compose(self) -> ComposeResult:
        with Vertical(id="highlight-list-dialog"):
            if not self._highlights:
                yield Label("No active highlights")
            else:
                yield Label(f"Active highlights ({len(self._highlights)}):")
                for i, h in enumerate(self._highlights, 1):
                    yield Label(_format_highlight(h, i))
            yield Label("[dim]Press Esc to close[/dim]")

    def action_dismiss(self) -> None:
        self.dismiss(None)
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/tui/screens/highlight_list.py
git commit -m "feat: add HighlightListScreen modal for :lsh command"
```

---

### Task 5: Integrate highlight commands into TUI

**Files:**
- Modify: `src/log_viewer/tui/app.py`

- [ ] **Step 1: Add HighlightListScreen import**

Add to imports in `src/log_viewer/tui/app.py`:

```python
from log_viewer.tui.screens.highlight_list import HighlightListScreen
```

- [ ] **Step 2: Add highlight command handlers**

Add these methods to `LogViewerApp` class in `src/log_viewer/tui/app.py`, after the `_lsf` method:

```python
def _h(self, pattern: str, mode: SearchMode, case_sensitive: bool, color: str) -> None:
    """Add a highlight and refresh."""
    self.log_store.add_highlight(
        Highlight(pattern=pattern, mode=mode, case_sensitive=case_sensitive, color=color)
    )
    self.refresh_log_panel()

def _rmh(self, pattern: str) -> None:
    """Remove highlight(s) by pattern. Empty pattern clears all."""
    if not pattern:
        self.log_store.clear_highlights()
    else:
        # Remove ALL highlights with matching pattern (regardless of color)
        self.log_store.highlights = [
            h for h in self.log_store.highlights if h.pattern != pattern
        ]
    self.refresh_log_panel()

def _lsh(self) -> None:
    """Show highlight list modal."""
    self.push_screen(HighlightListScreen(self.log_store.highlights))
```

- [ ] **Step 3: Add command dispatch cases**

In the `_handle_command` method, add these elif branches after the `lscat` case (before the end of the if/elif chain):

```python
elif name == "h":
    color = parsed.flags.get("color", "red")
    self._h(parsed.text, SearchMode.PLAIN, parsed.flags.get("cs") == "", color)
elif name == "hr":
    color = parsed.flags.get("color", "red")
    self._h(parsed.text, SearchMode.REGEX, parsed.flags.get("cs") == "", color)
elif name == "hs":
    color = parsed.flags.get("color", "red")
    self._h(parsed.text, SearchMode.SIMPLE, parsed.flags.get("cs") == "", color)
elif name == "rmh":
    self._rmh(parsed.text)
elif name == "lsh":
    self._lsh()
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Run quality gates**

Run: `uv run ruff check . && uv run black --check .`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/tui/app.py
git commit -m "feat: integrate highlight commands (:h, :hr, :hs, :rmh, :lsh) into TUI"
```

---

## Manual Testing Checklist

After all tasks are implemented:

- [ ] `:h ERROR` — "ERROR" highlighted red in message cells
- [ ] `:h/color=yellow/WARNING` — "WARNING" highlighted yellow
- [ ] `:h/color=#FF5733/timeout` — "timeout" highlighted with custom hex color
- [ ] `:hr/error_\d+` — regex pattern highlighted red
- [ ] `:hs/"Failed" AND "config"` — both "Failed" and "config" highlighted
- [ ] Multiple highlights with different colors visible simultaneously
- [ ] `:rmh ERROR` — remove specific highlight
- [ ] `:rmh` — clear all highlights
- [ ] `:lsh` — modal showing active highlights
- [ ] Highlights don't affect filtering (all lines still visible)
