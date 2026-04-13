# File Path Autocomplete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Tab-completion of file/directory paths when typing `:open <partial_path>` in the command input.

**Architecture:** Custom `FilePathSuggester` extends Textual's `Suggester` ABC. It parses the input for `:open ` prefix, resolves the partial path against the filesystem, and returns the first match. `CommandInput` passes this suggester to `Input.__init__` and adds `key_tab` to accept suggestions.

**Tech Stack:** Python stdlib (`os`, `os.path`), Textual `Suggester` API.

---

### Task 1: Create `FilePathSuggester` core logic (RED)

**Files:**
- Create: `tests/unit/test_suggester.py`
- Create: `src/log_viewer/core/suggester.py` (initially just a stub)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_suggester.py`:

```python
"""Tests for FilePathSuggester."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from log_viewer.core.suggester import FilePathSuggester


@pytest.fixture
def suggester() -> FilePathSuggester:
    return FilePathSuggester()


@pytest.fixture
def tmp_tree(tmp_path: Path) -> Path:
    """Create a temp directory with files and subdirs for testing."""
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "alpha.log").write_text("b")
    (tmp_path / "beta.txt").write_text("c")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.log").write_text("d")
    return tmp_path


@pytest.mark.asyncio
async def test_returns_none_for_non_open_command(
    suggester: FilePathSuggester,
) -> None:
    result = await suggester.get_suggestion(":q")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_empty_path(
    suggester: FilePathSuggester,
) -> None:
    result = await suggester.get_suggestion(":open ")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_no_match(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/zzz")
    assert result is None


@pytest.mark.asyncio
async def test_completes_single_file_match(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/bet")
    assert result == f":open {tmp_tree}/beta.txt"


@pytest.mark.asyncio
async def test_completes_first_match_when_multiple(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/alpha")
    assert result == f":open {tmp_tree}/alpha.log"


@pytest.mark.asyncio
async def test_completes_directory_with_trailing_slash(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/subd")
    assert result == f":open {tmp_tree}/subdir/"


@pytest.mark.asyncio
async def test_completes_inside_existing_directory(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/subdir/nest")
    assert result == f":open {tmp_tree}/subdir/nested.log"


@pytest.mark.asyncio
async def test_expands_tilde(
    suggester: FilePathSuggester,
) -> None:
    home = os.path.expanduser("~")
    entries = os.listdir(home)
    if not entries:
        pytest.skip("Home directory is empty")
    first = sorted(entries)[0]
    result = await suggester.get_suggestion(f":open ~/{first[0]}")
    expected_full = os.path.join(home, first)
    if os.path.isdir(expected_full):
        expected_full += "/"
    assert result == f":open {expected_full}"


@pytest.mark.asyncio
async def test_completes_absolute_root_dir(
    suggester: FilePathSuggester,
) -> None:
    entries = os.listdir("/")
    if not entries:
        pytest.skip("Root directory is empty")
    first = sorted(entries)[0]
    result = await suggester.get_suggestion(f":open /{first[0]}")
    expected_full = os.path.join("/", first)
    if os.path.isdir(expected_full):
        expected_full += "/"
    assert result == f":open {expected_full}"


@pytest.mark.asyncio
async def test_returns_none_for_non_path_text(
    suggester: FilePathSuggester,
) -> None:
    result = await suggester.get_suggestion(":f pattern")
    assert result is None
```

- [ ] **Step 2: Create the stub module**

Create `src/log_viewer/core/suggester.py`:

```python
"""File path suggester for the :open command."""

from __future__ import annotations
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_suggester.py -v`
Expected: FAIL — `ImportError: cannot import name 'FilePathSuggester'`

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_suggester.py src/log_viewer/core/suggester.py
git commit -m "test: add FilePathSuggester tests (RED)"
```

---

### Task 2: Implement `FilePathSuggester` (GREEN)

**Files:**
- Modify: `src/log_viewer/core/suggester.py`

- [ ] **Step 1: Implement the suggester**

Replace `src/log_viewer/core/suggester.py` with:

```python
"""File path suggester for the :open command."""

from __future__ import annotations

import os

from textual.suggester import Suggester


class FilePathSuggester(Suggester):
    """Suggest file/directory completions for the `:open` command."""

    def __init__(self) -> None:
        super().__init__(use_cache=False, case_sensitive=True)

    async def get_suggestion(self, value: str) -> str | None:
        prefix = ":open "
        if not value.startswith(prefix):
            return None

        partial = value[len(prefix):]
        if not partial:
            return None

        expanded = os.path.expanduser(partial)
        parent = os.path.dirname(expanded)
        base = os.path.basename(expanded)

        try:
            entries = sorted(os.listdir(parent))
        except (OSError, PermissionError):
            return None

        for entry in entries:
            if entry.startswith(base):
                full = os.path.join(parent, entry)
                if os.path.isdir(full):
                    full += "/"
                return f":open {full}"

        return None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_suggester.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/suggester.py
git commit -m "feat: implement FilePathSuggester for :open autocomplete (GREEN)"
```

---

### Task 3: Wire suggester into `CommandInput` and add Tab key (RED)

**Files:**
- Modify: `src/log_viewer/tui/widgets/command_input.py`
- Create: `tests/integration/test_autocomplete.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/integration/test_autocomplete.py`:

```python
"""Tests for Tab-autocomplete in CommandInput."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from log_viewer.tui.app import LogViewerApp
from log_viewer.tui.widgets.command_input import CommandInput


@pytest.fixture
def tmp_tree(tmp_path: Path) -> Path:
    (tmp_path / "hello.log").write_text("line1")
    (tmp_path / "hello.txt").write_text("line2")
    return tmp_path


@pytest.mark.asyncio
async def test_tab_accepts_suggestion(tmp_tree: Path) -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = f":open {tmp_tree}/hel"
        cmd_input.cursor_position = len(cmd_input.value)
        await pilot.pause()

        # The suggester should have set a suggestion — press Tab to accept
        await pilot.press("tab")
        await pilot.pause()

        assert cmd_input.value == f":open {tmp_tree}/hello.log"


@pytest.mark.asyncio
async def test_tab_does_nothing_without_suggestion() -> None:
    app = LogViewerApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one(CommandInput)
        cmd_input.value = ":open /nonexistent_zzz_path"
        cmd_input.cursor_position = len(cmd_input.value)
        await pilot.pause()

        await pilot.press("tab")
        await pilot.pause()

        assert cmd_input.value == ":open /nonexistent_zzz_path"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_autocomplete.py -v`
Expected: FAIL — `test_tab_accepts_suggestion` fails because Tab doesn't accept the suggestion yet.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_autocomplete.py
git commit -m "test: add autocomplete integration tests (RED)"
```

---

### Task 4: Wire suggester + Tab key (GREEN)

**Files:**
- Modify: `src/log_viewer/tui/widgets/command_input.py`

- [ ] **Step 1: Update CommandInput to use suggester and handle Tab**

Replace `src/log_viewer/tui/widgets/command_input.py` with:

```python
"""CommandInput widget — command bar with file path autocomplete for :open."""

from __future__ import annotations

from textual.widgets import Input

from log_viewer.core.suggester import FilePathSuggester


class CommandInput(Input):
    """Input field for entering commands like :open and :q."""

    DEFAULT_CSS = """
    CommandInput, CommandInput:focus, CommandInput:hover {
        border: none;
        height: 1;
        width: 1fr;
        padding: 0;
        background: $surface;
    }
    """

    def __init__(self) -> None:
        super().__init__(
            select_on_focus=False,
            suggester=FilePathSuggester(),
        )

    def key_escape(self) -> None:
        """Cancel input and return focus to LogPanel."""
        self.value = ""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            app._return_to_log_panel()

    def key_tab(self) -> None:
        """Accept the current suggestion, if any."""
        if self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)

    def key_up(self) -> None:
        """Navigate command history up."""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            cmd = app._command_history.navigate_up()
            if cmd:
                self.value = cmd
                self.cursor_position = len(cmd)

    def key_down(self) -> None:
        """Navigate command history down."""
        from log_viewer.tui.app import LogViewerApp

        app = self.app
        if isinstance(app, LogViewerApp):
            cmd = app._command_history.navigate_down()
            self.value = cmd
            self.cursor_position = len(cmd)
```

- [ ] **Step 2: Run all tests**

Run: `uv run pytest tests/unit/test_suggester.py tests/integration/test_autocomplete.py -v`
Expected: ALL PASS

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/log_viewer/tui/widgets/command_input.py
git commit -m "feat: wire FilePathSuggester into CommandInput with Tab acceptance (GREEN)"
```

---

### Task 5: Quality gates + final verification

- [ ] **Step 1: Run linter**

Run: `uv run ruff check src/log_viewer/core/suggester.py src/log_viewer/tui/widgets/command_input.py tests/unit/test_suggester.py tests/integration/test_autocomplete.py`
Expected: No errors

- [ ] **Step 2: Run formatter check**

Run: `uv run black --check src/log_viewer/core/suggester.py src/log_viewer/tui/widgets/command_input.py tests/unit/test_suggester.py tests/integration/test_autocomplete.py`
Expected: No changes needed

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS
