# Search Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit search mode where Up/Down arrows navigate between matched lines, Esc exits, and the window title shows the active search pattern.

**Architecture:** Add `in_search: bool` to `SearchState` and a `_current_filename` field to `MainWindow`. Refactor window title management into `_update_title()` helper. Rewrite `eventFilter` to handle Up/Down/Esc instead of n/N.

**Tech Stack:** Python 3.9+, PySide6 (Qt6), pytest + pytest-qt

---

### Task 1: Add `in_search` field to SearchState

**Files:**
- Modify: `src/log_viewer/core/models.py:123-131`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_models.py`:

```python
def test_search_state_in_search_defaults_false():
    from log_viewer.core.models import SearchState, SearchMode, SearchDirection
    state = SearchState(
        pattern="test",
        mode=SearchMode.PLAIN,
        case_sensitive=False,
        direction=SearchDirection.FORWARD,
    )
    assert state.in_search is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_models.py::test_search_state_in_search_defaults_false -v`
Expected: FAIL — `SearchState.__init__()` got an unexpected keyword argument `in_search` (field doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

In `src/log_viewer/core/models.py`, add `in_search: bool = False` to `SearchState`:

```python
@dataclass
class SearchState:
    pattern: str
    mode: SearchMode
    case_sensitive: bool
    direction: SearchDirection
    matches: list[int] = field(default_factory=list)
    current_index: int = 0
    in_search: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_models.py::test_search_state_in_search_defaults_false -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/core/models.py tests/unit/test_models.py
git commit -m "feat: add in_search field to SearchState"
```

---

### Task 2: Add `_update_title()` helper to MainWindow

**Files:**
- Modify: `src/log_viewer/gui/app.py:72-189`

This task adds `_current_filename` field, `_update_title()` method, and wires them into existing `_on_file_loaded`.

- [ ] **Step 1: Write the failing test**

Add to `tests/gui/test_app.py`:

```python
def test_update_title_shows_filename_after_load(main_window):
    main_window._on_file_loaded(
        ["2025-01-01T10:00:00 LOG_INFO app/main hello"],
        "test.log",
    )
    assert main_window.windowTitle() == "Log Viewer \u2014 test.log"


def test_update_title_shows_search_mode(main_window):
    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert "Search: error" in main_window.windowTitle()
    assert "test.log" in main_window.windowTitle()


def test_update_title_reverts_on_search_exit(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QLineEdit

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert "Search: error" in main_window.windowTitle()
    # Simulate Esc key
    esc_event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, esc_event)
    assert main_window.windowTitle() == "Log Viewer \u2014 test.log"
```

Note: `test_update_title_shows_filename_after_load` should pass already (existing behavior). The new tests are the search-mode title ones.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/gui/test_app.py::test_update_title_shows_search_mode tests/gui/test_app.py::test_update_title_reverts_on_search_exit -v`
Expected: FAIL — `"Search: error"` not in window title.

- [ ] **Step 3: Implement `_current_filename` and `_update_title()`**

In `src/log_viewer/gui/app.py`, modify `__init__` to add:

```python
# after self.log_store = LogStore()
self._current_filename: str = ""
```

In `_on_file_loaded`, replace the direct `setWindowTitle` call:

```python
def _on_file_loaded(self, lines: list[str], path: str) -> None:
    self.log_store.load_lines(lines, file_path=path)
    del lines  # Free raw string list immediately
    self._current_filename = (
        Path(path).name if not path.startswith(("http://", "https://")) else path
    )
    self._hide_empty_state()
    self._refresh_display()
    self._save_last_open_dir(path)
    self._update_title()
```

Add the `_update_title` method (after `_update_status`):

```python
def _update_title(self) -> None:
    ss = self.log_store.search_state
    base = f"Log Viewer \u2014 {self._current_filename}" if self._current_filename else "Log Viewer"
    if ss and ss.in_search:
        self.setWindowTitle(f"{base} \u2014 Search: {ss.pattern}")
    else:
        self.setWindowTitle(base)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/gui/test_app.py::test_update_title_shows_search_mode tests/gui/test_app.py::test_update_title_reverts_on_search_exit tests/gui/test_app.py::test_update_title_shows_filename_after_load -v`
Expected: ALL PASS

- [ ] **Step 5: Run full GUI test suite to verify no regressions**

Run: `uv run pytest tests/gui/test_app.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/gui/app.py tests/gui/test_app.py
git commit -m "feat: add _update_title helper with search mode support"
```

---

### Task 3: Activate search mode in `_do_search()`

**Files:**
- Modify: `src/log_viewer/gui/app.py:322-329`

- [ ] **Step 1: Write the failing test**

Add to `tests/gui/test_app.py`:

```python
def test_do_search_activates_in_search_when_matches_found(main_window):
    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state is not None
    assert main_window.log_store.search_state.in_search is True


def test_do_search_does_not_activate_when_no_matches(main_window):
    main_window._on_file_loaded(
        ["2025-01-01T10:00:00 LOG_INFO app/main hello"],
        "test.log",
    )
    main_window._do_search("nonexistent", SearchMode.PLAIN, SearchDirection.FORWARD)
    ss = main_window.log_store.search_state
    assert ss is None or ss.in_search is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/gui/test_app.py::test_do_search_activates_in_search_when_matches_found -v`
Expected: FAIL — `search_state.in_search` is `False` (default, never set to `True`).

- [ ] **Step 3: Implement search mode activation**

In `src/log_viewer/gui/app.py`, modify `_do_search`:

```python
def _do_search(
    self, pattern: str, mode: SearchMode, direction: SearchDirection
) -> None:
    if not pattern:
        return
    self.log_store.search(pattern, mode, direction=direction)
    ss = self.log_store.search_state
    if ss and ss.matches:
        ss.in_search = True
    self._update_status()
    self._update_title()
    self._jump_to_search_match()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/gui/test_app.py::test_do_search_activates_in_search_when_matches_found tests/gui/test_app.py::test_do_search_does_not_activate_when_no_matches -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/gui/app.py tests/gui/test_app.py
git commit -m "feat: activate search mode when matches are found"
```

---

### Task 4: Rewrite eventFilter — Up/Down for match navigation, Esc to exit, remove n/N

**Files:**
- Modify: `src/log_viewer/gui/app.py:437-459`

- [ ] **Step 1: Write the failing tests**

Add to `tests/gui/test_app.py`:

```python
def test_arrow_down_navigates_next_match_in_search_mode(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main error one",
            "2025-01-01T10:00:01 LOG_INFO app/main error two",
            "2025-01-01T10:00:02 LOG_INFO app/main other",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state.current_index == 0

    down = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, down)
    assert main_window.log_store.search_state.current_index == 1


def test_arrow_up_navigates_prev_match_in_search_mode(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main error one",
            "2025-01-01T10:00:01 LOG_INFO app/main error two",
            "2025-01-01T10:00:02 LOG_INFO app/main other",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    # current_index == 0, prev wraps to last
    up = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, up)
    assert main_window.log_store.search_state.current_index == 1


def test_esc_exits_search_mode(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state.in_search is True

    esc = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, esc)
    assert main_window.log_store.search_state.in_search is False
    assert "Search" not in main_window.windowTitle()


def test_arrow_keys_normal_when_not_in_search(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main world",
        ],
        "test.log",
    )
    # No search active — arrows should pass through (return False)
    down = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
    )
    result = main_window.eventFilter(main_window.log_table, down)
    assert result is False


def test_n_key_no_longer_navigates_search(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main error one",
            "2025-01-01T10:00:01 LOG_INFO app/main error two",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    initial_index = main_window.log_store.search_state.current_index

    # Simulate 'n' keypress
    n_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_N,
        Qt.KeyboardModifier.NoModifier,
        "n",
    )
    main_window.eventFilter(main_window.log_table, n_event)
    # n should NOT advance match index
    assert main_window.log_store.search_state.current_index == initial_index
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/gui/test_app.py::test_arrow_down_navigates_next_match_in_search_mode tests/gui/test_app.py::test_arrow_up_navigates_prev_match_in_search_mode tests/gui/test_app.py::test_esc_exits_search_mode tests/gui/test_app.py::test_n_key_no_longer_navigates_search -v`
Expected: FAIL — current eventFilter handles n/N, not Up/Down/Esc.

- [ ] **Step 3: Rewrite eventFilter**

Replace the entire `eventFilter` method in `src/log_viewer/gui/app.py`:

```python
def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
    if event.type() == event.Type.KeyPress:
        text = event.text()
        key = event.key()
        ss = self.log_store.search_state

        if text == ":":
            self.bottom_bar.activate_command_mode()
            return True
        if text == "/" and not isinstance(obj, (QLineEdit, QTextEdit)):
            self.bottom_bar.command_input.setText("/")
            self.bottom_bar.command_input.setFocus()
            return True

        # Search mode navigation
        if ss and ss.in_search:
            if key == Qt.Key.Key_Down:
                self.log_table.setFocus()
                self.log_store.next_match()
                self._update_status()
                self._jump_to_search_match()
                return True
            if key == Qt.Key.Key_Up:
                self.log_table.setFocus()
                self.log_store.prev_match()
                self._update_status()
                self._jump_to_search_match()
                return True
            if key == Qt.Key.Key_Escape:
                ss.in_search = False
                self._update_title()
                return True

    return super().eventFilter(obj, event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/gui/test_app.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/gui/app.py tests/gui/test_app.py
git commit -m "feat: search mode navigation with arrow keys, Esc to exit, remove n/N"
```

---

### Task 5: Reset search mode on file reload

**Files:**
- Modify: `src/log_viewer/gui/app.py:180-188`

- [ ] **Step 1: Write the failing test**

Add to `tests/gui/test_app.py`:

```python
def test_file_reload_resets_search_mode(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state.in_search is True
    assert "Search" in main_window.windowTitle()

    # Reload same file
    main_window._on_file_loaded(
        ["2025-01-01T10:00:00 LOG_INFO app/main hello"],
        "other.log",
    )
    assert "Search" not in main_window.windowTitle()
    assert "other.log" in main_window.windowTitle()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/gui/test_app.py::test_file_reload_resets_search_mode -v`
Expected: FAIL — `load_lines` already clears `search_state` (sets to `None`), so `_update_title` would see no search state and show plain title. But `_on_file_loaded` doesn't call `_update_title()` after load — it only calls it if we wired it in Task 2. This test should pass already after Task 2 since `_on_file_loaded` calls `_update_title()`, and `load_lines` clears `search_state`. Verify and adjust if needed.

- [ ] **Step 3: If test passes, skip implementation**

If `_on_file_loaded` already calls `_update_title()` and `load_lines` already sets `search_state = None`, the test should pass. Verify:

Run: `uv run pytest tests/gui/test_app.py::test_file_reload_resets_search_mode -v`

If PASS — no code changes needed, just commit the test.

If FAIL — add to `_on_file_loaded` after `load_lines`:

```python
if self.log_store.search_state:
    self.log_store.search_state.in_search = False
```

- [ ] **Step 4: Commit**

```bash
git add tests/gui/test_app.py
git commit -m "test: verify search mode resets on file reload"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 2: Run linter**

Run: `uv run --with ruff ruff check src/`
Expected: No errors

- [ ] **Step 3: Manual smoke test**

Run: `uv run log-viewer`
Load a log file. Type `:s some_pattern` — verify title changes, Down/Up navigate matches, Esc reverts title and restores normal arrow behavior.
