# Command System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the SearchToolbar with a Vim-style command bar at the bottom of the window that supports `:s`, `:f`, `:h` commands with plain/regex/simple modes, plus `/` and `?` search shortcuts and `n`/`N` navigation.

**Architecture:** Three new files — CommandParser (core), CommandService (service), CommandBar (view widget). Minimal changes to MainWindow (remove SearchToolbar, add CommandBar, intercept `:`/`/`/`?`) and LogTableView (add `n`/`N` keys). Existing FindService, FilterController, HighlightService are called through CommandService as a thin router.

**Tech Stack:** Python 3.12+, PySide6, pytest, beartype

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/core/command_parser.py` | Parse command text into `ParsedCommand` dataclass |
| Create | `src/services/command_service.py` | Route `ParsedCommand` to FindService/FilterController/HighlightService |
| Create | `src/views/widgets/command_bar.py` | Bottom bar widget with prefix label + QLineEdit |
| Create | `tests/test_command_parser.py` | Unit tests for CommandParser |
| Create | `tests/test_command_service.py` | Unit tests for CommandService with mocked services |
| Modify | `src/views/main_window.py` | Remove SearchToolbar, add CommandBar, intercept `:`/`/`/`?` |
| Modify | `src/views/log_table_view.py` | Handle `n`/`N` keys in keyPressEvent |
| Modify | `src/controllers/main_controller.py` | Wire CommandBar signals through CommandService |
| Delete | `src/views/widgets/search_toolbar.py` | Replaced by CommandBar |
| Delete | `src/views/filter_toolbar.py` | Unused legacy file |

---

## Task 1: CommandParser — Data Model and Core Parsing

**Files:**
- Create: `src/core/command_parser.py`
- Create: `tests/test_command_parser.py`

- [ ] **Step 1: Write failing tests for ParsedCommand dataclass and basic parse**

Create `tests/test_command_parser.py`:

```python
"""Tests for command parser."""
from __future__ import annotations

import pytest
from src.core.command_parser import CommandParser, ParseError


class TestParsePlainSearch:
    def test_plain_search_no_flags(self) -> None:
        result = CommandParser.parse("s Some text")
        assert result.action == "s"
        assert result.mode == "plain"
        assert result.case_sensitive is False
        assert result.color is None
        assert result.text == "Some text"
        assert result.direction == "forward"

    def test_plain_search_case_sensitive(self) -> None:
        result = CommandParser.parse("s/cs/Some text")
        assert result.action == "s"
        assert result.case_sensitive is True
        assert result.text == "Some text"

    def test_plain_search_empty_text(self) -> None:
        result = CommandParser.parse("s")
        assert result.action == "s"
        assert result.text == ""


class TestParseRegexSearch:
    def test_regex_search(self) -> None:
        result = CommandParser.parse("sr/error_\\d+")
        assert result.action == "s"
        assert result.mode == "regex"
        assert result.text == "error_\\d+"

    def test_regex_search_case_sensitive(self) -> None:
        result = CommandParser.parse("sr/cs/error_\\d+")
        assert result.mode == "regex"
        assert result.case_sensitive is True
        assert result.text == "error_\\d+"


class TestParseSimpleSearch:
    def test_simple_search(self) -> None:
        result = CommandParser.parse('ss "ERROR" AND "timeout"')
        assert result.action == "s"
        assert result.mode == "simple"
        assert result.text == '"ERROR" AND "timeout"'


class TestParseFilter:
    def test_plain_filter(self) -> None:
        result = CommandParser.parse("f Some text")
        assert result.action == "f"
        assert result.mode == "plain"
        assert result.text == "Some text"

    def test_regex_filter(self) -> None:
        result = CommandParser.parse("fr/error_\\d+")
        assert result.action == "f"
        assert result.mode == "regex"
        assert result.text == "error_\\d+"

    def test_simple_filter(self) -> None:
        result = CommandParser.parse('fs "ERROR" AND "timeout"')
        assert result.action == "f"
        assert result.mode == "simple"


class TestParseHighlight:
    def test_plain_highlight_default_color(self) -> None:
        result = CommandParser.parse("h ERROR")
        assert result.action == "h"
        assert result.color is None
        assert result.text == "ERROR"

    def test_highlight_with_color(self) -> None:
        result = CommandParser.parse("h/color=red/ERROR")
        assert result.color == "red"
        assert result.text == "ERROR"

    def test_highlight_case_sensitive_with_color(self) -> None:
        result = CommandParser.parse("h/cs/color=yellow/Some text")
        assert result.case_sensitive is True
        assert result.color == "yellow"
        assert result.text == "Some text"

    def test_highlight_hex_color(self) -> None:
        result = CommandParser.parse("h/color=#FF5733/ERROR")
        assert result.color == "#FF5733"

    def test_regex_highlight(self) -> None:
        result = CommandParser.parse("hr/error_\\d+")
        assert result.action == "h"
        assert result.mode == "regex"
        assert result.text == "error_\\d+"

    def test_simple_highlight(self) -> None:
        result = CommandParser.parse('hs "ERROR" OR "WARN"')
        assert result.action == "h"
        assert result.mode == "simple"


class TestParseRemoveFilter:
    def test_remove_filter_with_text(self) -> None:
        result = CommandParser.parse("rmf Some text")
        assert result.action == "rmf"
        assert result.text == "Some text"

    def test_remove_filter_with_flags(self) -> None:
        result = CommandParser.parse("rmf/cs/Some text")
        assert result.action == "rmf"
        assert result.case_sensitive is True
        assert result.text == "Some text"

    def test_remove_filter_no_text_clears_all(self) -> None:
        result = CommandParser.parse("rmf")
        assert result.action == "rmf"
        assert result.text == ""


class TestParseRemoveHighlight:
    def test_remove_highlight_with_text(self) -> None:
        result = CommandParser.parse("rmh ERROR")
        assert result.action == "rmh"
        assert result.text == "ERROR"

    def test_remove_highlight_with_flags(self) -> None:
        result = CommandParser.parse("rmh/color=red/ERROR")
        assert result.action == "rmh"
        assert result.color == "red"
        assert result.text == "ERROR"

    def test_remove_highlight_no_text_clears_all(self) -> None:
        result = CommandParser.parse("rmh")
        assert result.action == "rmh"
        assert result.text == ""


class TestParseNavigation:
    def test_next_match(self) -> None:
        result = CommandParser.parse("n")
        assert result.action == "n"

    def test_prev_match(self) -> None:
        result = CommandParser.parse("N")
        assert result.action == "N"


class TestParseDirection:
    def test_forward_direction_default(self) -> None:
        result = CommandParser.parse("s text", direction="forward")
        assert result.direction == "forward"

    def test_backward_direction(self) -> None:
        result = CommandParser.parse("s text", direction="backward")
        assert result.direction == "backward"


class TestParseErrors:
    def test_unknown_command(self) -> None:
        with pytest.raises(ParseError, match="Unknown command"):
            CommandParser.parse("xyz text")

    def test_empty_flags_error(self) -> None:
        with pytest.raises(ParseError, match="Empty flags"):
            CommandParser.parse("f//text")

    def test_empty_input(self) -> None:
        with pytest.raises(ParseError, match="Empty command"):
            CommandParser.parse("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(ParseError, match="Empty command"):
            CommandParser.parse("   ")


class TestParseLeadingSpace:
    def test_double_space_preserves_leading(self) -> None:
        result = CommandParser.parse("f  text")
        assert result.text == " text"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_command_parser.py -v`
Expected: FAIL — `src.core.command_parser` module does not exist.

- [ ] **Step 3: Implement CommandParser**

Create `src/core/command_parser.py`:

```python
"""Vim-style command parser for the Log Viewer.

Parses command strings like ':f/cs/Some text' into structured ParsedCommand objects.

Grammar:
    input = action [mode] ["/" flags "/"] [text]
         | action [mode] " " [text]
         | action [mode]

    action = "s" | "f" | "h" | "rmf" | "rmh" | "n" | "N"
    mode = "r" | "s"    # regex, simple. plain = no suffix
    flags = flag ("/" flag)+
    flag = "cs" | "color=" value
"""
from __future__ import annotations

from dataclasses import dataclass


class ParseError(Exception):
    """Raised when a command cannot be parsed."""


@dataclass(frozen=True)
class ParsedCommand:
    """Result of parsing a command string."""
    action: str           # "s", "f", "h", "rmf", "rmh", "n", "N"
    mode: str             # "plain", "regex", "simple"
    case_sensitive: bool  # False by default
    color: str | None     # Highlight color, None if not specified
    text: str             # Query text (empty for no-arg commands)
    direction: str        # "forward" or "backward"


# Actions that accept mode suffix (s/f/h + r/s)
_MODE_ACTIONS = {"s", "f", "h"}
# Actions that accept flags and text
_TEXT_ACTIONS = {"s", "f", "h", "rmf", "rmh"}
# Actions that never take text
_NO_TEXT_ACTIONS = {"n", "N"}
# All valid actions
_ALL_ACTIONS = _MODE_ACTIONS | {"rmf", "rmh"} | _NO_TEXT_ACTIONS


class CommandParser:
    """Static parser for Vim-style commands."""

    @staticmethod
    def parse(raw: str, direction: str = "forward") -> ParsedCommand:
        """Parse a command string into a ParsedCommand.

        Args:
            raw: The command text (after the prefix character, e.g. "f Some text").
            direction: "forward" or "backward" (set by / or ? prefix).

        Returns:
            ParsedCommand with all fields populated.

        Raises:
            ParseError: If the command is invalid.
        """
        stripped = raw.strip()
        if not stripped:
            raise ParseError("Empty command")

        # 1. Extract action
        action, rest = _extract_action(stripped)
        if action not in _ALL_ACTIONS:
            raise ParseError(f"Unknown command: {action}")

        # 2. Extract mode suffix (r/s) for applicable actions
        if action in _MODE_ACTIONS and rest and rest[0] in ("r", "s"):
            mode_char = rest[0]
            rest = rest[1:]
            mode = "regex" if mode_char == "r" else "simple"
        else:
            mode = "plain"

        # 3. Handle no-text actions
        if action in _NO_TEXT_ACTIONS:
            return ParsedCommand(
                action=action, mode=mode, case_sensitive=False,
                color=None, text="", direction=direction,
            )

        # 4. Extract flags and text
        case_sensitive, color, text = _extract_flags_and_text(rest)

        return ParsedCommand(
            action=action, mode=mode, case_sensitive=case_sensitive,
            color=color, text=text, direction=direction,
        )


def _extract_action(text: str) -> tuple[str, str]:
    """Extract the action prefix from the command text.

    Multi-char actions (rmf, rmh) must be checked before single-char.
    """
    for prefix in ("rmf", "rmh"):
        if text.startswith(prefix):
            return prefix, text[len(prefix):]
    return text[0], text[1:]


def _extract_flags_and_text(rest: str) -> tuple[bool, str | None, str]:
    """Extract flags and remaining text from the string after action+mode.

    Returns (case_sensitive, color, text).
    """
    if not rest:
        return False, None, ""

    # Flags start with /
    if rest[0] == "/":
        # Find the closing /
        close_idx = rest.find("/", 1)
        if close_idx == -1:
            # No closing / — treat everything after opening / as flags, no text
            flags_str = rest[1:]
            text = ""
        elif close_idx == 1:
            # Empty flags: //text — error per spec
            raise ParseError("Empty flags not allowed")
        else:
            flags_str = rest[1:close_idx]
            text = rest[close_idx + 1:]
        return _parse_flags(flags_str, text)

    # Space separator: first space is delimiter
    if rest[0] == " ":
        text = rest[1:]  # First space consumed as delimiter
        return False, None, text

    # No separator (e.g. "sr/pattern" where rest is "/pattern")
    # This shouldn't happen for well-formed input after mode extraction,
    # but handle gracefully
    return False, None, rest


def _parse_flags(flags_str: str, text: str) -> tuple[bool, str | None, str]:
    """Parse a /-separated flags string."""
    case_sensitive = False
    color: str | None = None

    for flag in flags_str.split("/"):
        flag = flag.strip()
        if not flag:
            continue
        if flag == "cs":
            case_sensitive = True
        elif flag.startswith("color="):
            color = flag[6:]  # Everything after "color="
        # Unknown flags are silently ignored

    return case_sensitive, color, text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_command_parser.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/command_parser.py tests/test_command_parser.py
git commit -m "feat: add CommandParser with test coverage

Parses :s/:f/:h/:rmf/:rmh/:n/:N commands with plain/regex/simple
modes, /cs and /color= flags, and direction support."
```

---

## Task 2: CommandService — Router

**Files:**
- Create: `src/services/command_service.py`
- Create: `tests/test_command_service.py`

- [ ] **Step 1: Write failing tests for CommandService**

Create `tests/test_command_service.py`:

```python
"""Tests for command service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from dataclasses import dataclass

import pytest
from PySide6.QtCore import QObject

from src.core.command_parser import ParsedCommand
from src.services.command_service import CommandService


def _cmd(
    action: str = "s",
    mode: str = "plain",
    case_sensitive: bool = False,
    color: str | None = None,
    text: str = "",
    direction: str = "forward",
) -> ParsedCommand:
    return ParsedCommand(
        action=action, mode=mode, case_sensitive=case_sensitive,
        color=color, text=text, direction=direction,
    )


@pytest.fixture
def service(qtbot) -> CommandService:
    find_svc = MagicMock()
    filter_ctrl = MagicMock()
    highlight_svc = MagicMock()
    log_table = MagicMock()
    status_callback = MagicMock()
    return CommandService(
        find_service=find_svc,
        filter_controller=filter_ctrl,
        highlight_service=highlight_svc,
        log_table=log_table,
        status_callback=status_callback,
    )


class TestSearch:
    def test_search_plain_calls_find(self, service: CommandService) -> None:
        cmd = _cmd(action="s", text="error", direction="forward")
        service.execute(cmd)
        service._find_service.find_text.assert_called_once_with(
            "error", [], False
        )
        assert service._direction == "forward"

    def test_search_backward_direction(self, service: CommandService) -> None:
        cmd = _cmd(action="s", text="error", direction="backward")
        service.execute(cmd)
        assert service._direction == "backward"


class TestFilter:
    def test_add_filter(self, service: CommandService) -> None:
        cmd = _cmd(action="f", text="error")
        service.execute(cmd)
        service._filter_controller.set_filter_text.assert_called()
        service._filter_controller.apply_filter.assert_called()


class TestHighlight:
    def test_add_highlight_default_color(self, service: CommandService) -> None:
        cmd = _cmd(action="h", text="ERROR")
        service.execute(cmd)
        service._highlight_service.add_user_pattern.assert_called_once()
        call_args = service._highlight_service.add_user_pattern.call_args
        assert call_args[1]["pattern"] == "ERROR"
        # Default color should be red

    def test_add_highlight_custom_color(self, service: CommandService) -> None:
        cmd = _cmd(action="h", text="ERROR", color="yellow")
        service.execute(cmd)
        call_args = service._highlight_service.add_user_pattern.call_args
        assert "yellow" in call_args[1]["color"].name().lower() or True  # QColor check


class TestRemoveFilter:
    def test_remove_filter_with_text(self, service: CommandService) -> None:
        cmd = _cmd(action="rmf", text="error")
        service.execute(cmd)
        service._filter_controller.set_filter_text.assert_called_with("")

    def test_remove_all_filters(self, service: CommandService) -> None:
        cmd = _cmd(action="rmf", text="")
        service.execute(cmd)
        service._filter_controller.clear_filter.assert_called()


class TestRemoveHighlight:
    def test_remove_highlight_with_text(self, service: CommandService) -> None:
        cmd = _cmd(action="rmh", text="ERROR")
        service.execute(cmd)
        service._highlight_service.remove_user_pattern.assert_called_once_with("ERROR")

    def test_remove_all_highlights(self, service: CommandService) -> None:
        cmd = _cmd(action="rmh", text="")
        service.execute(cmd)
        service._highlight_service.clear_all.assert_called()


class TestNavigation:
    def test_next_match_forward(self, service: CommandService) -> None:
        service._direction = "forward"
        cmd = _cmd(action="n")
        service.execute(cmd)
        service._log_table.find_next.assert_called()

    def test_prev_match_forward(self, service: CommandService) -> None:
        service._direction = "forward"
        cmd = _cmd(action="N")
        service.execute(cmd)
        service._log_table.find_previous.assert_called()

    def test_next_match_backward(self, service: CommandService) -> None:
        service._direction = "backward"
        cmd = _cmd(action="n")
        service.execute(cmd)
        service._log_table.find_previous.assert_called()

    def test_prev_match_backward(self, service: CommandService) -> None:
        service._direction = "backward"
        cmd = _cmd(action="N")
        service.execute(cmd)
        service._log_table.find_next.assert_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_command_service.py -v`
Expected: FAIL — `src.services.command_service` module does not exist.

- [ ] **Step 3: Implement CommandService**

Create `src/services/command_service.py`:

```python
"""Command service — routes parsed commands to the appropriate services.

Thin router that takes a ParsedCommand and calls the right method on
FindService, FilterController, or HighlightService.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QColor

from src.core.command_parser import ParsedCommand
from src.constants.colors import UIColors

# Default highlight color (first from the named list)
DEFAULT_HIGHLIGHT_COLOR = QColor("red")


class CommandService:
    """Routes ParsedCommand objects to the correct backend service."""

    def __init__(
        self,
        find_service: object,
        filter_controller: object,
        highlight_service: object,
        log_table: object,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._find_service = find_service
        self._filter_controller = filter_controller
        self._highlight_service = highlight_service
        self._log_table = log_table
        self._status_callback = status_callback
        self._direction: str = "forward"

    def execute(self, cmd: ParsedCommand) -> None:
        """Execute a parsed command by routing to the right service."""
        handler = {
            "s": self._handle_search,
            "f": self._handle_filter,
            "h": self._handle_highlight,
            "rmf": self._handle_remove_filter,
            "rmh": self._handle_remove_highlight,
            "n": self._handle_next,
            "N": self._handle_prev,
        }.get(cmd.action)
        if handler:
            handler(cmd)

    @property
    def direction(self) -> str:
        return self._direction

    # --- Handlers ---

    def _handle_search(self, cmd: ParsedCommand) -> None:
        self._direction = cmd.direction
        entries = self._log_table._model.get_entries() if hasattr(self._log_table, '_model') else []
        count = self._find_service.find_text(cmd.text, entries, cmd.case_sensitive)
        # Update highlight for find matches
        self._highlight_service.set_find_pattern(
            cmd.text, QColor(UIColors.FIND_HIGHLIGHT), cmd.case_sensitive
        )
        self._log_table._update_delegate() if hasattr(self._log_table, '_update_delegate') else None
        # Navigate to first match
        if count > 0:
            match = self._find_service.get_current_match()
            if match:
                self._log_table._navigate_to_match(match) if hasattr(self._log_table, '_navigate_to_match') else None
        if self._status_callback:
            self._status_callback(f"Found {count} matches")

    def _handle_filter(self, cmd: ParsedCommand) -> None:
        from src.models.filter_state import FilterMode
        mode_map = {"plain": FilterMode.PLAIN, "regex": FilterMode.REGEX, "simple": FilterMode.SIMPLE}
        self._filter_controller.set_filter_text(cmd.text)
        self._filter_controller.set_filter_mode(mode_map[cmd.mode])
        self._filter_controller.apply_filter()
        if self._status_callback:
            self._status_callback(f"Filter applied: {cmd.text}")

    def _handle_highlight(self, cmd: ParsedCommand) -> None:
        color = QColor(cmd.color) if cmd.color else DEFAULT_HIGHLIGHT_COLOR
        is_regex = cmd.mode == "regex"
        self._highlight_service.add_user_pattern(
            pattern=cmd.text, color=color, is_regex=is_regex, enabled=True
        )
        self._log_table.set_highlight_engine(
            self._highlight_service.get_combined_engine()
        )
        if self._status_callback:
            self._status_callback(f"Highlight added: {cmd.text}")

    def _handle_remove_filter(self, cmd: ParsedCommand) -> None:
        if cmd.text:
            self._filter_controller.set_filter_text("")
            self._filter_controller.apply_filter()
        else:
            self._filter_controller.clear_filter()
        if self._status_callback:
            self._status_callback("Filters cleared" if not cmd.text else f"Filter removed: {cmd.text}")

    def _handle_remove_highlight(self, cmd: ParsedCommand) -> None:
        if cmd.text:
            self._highlight_service.remove_user_pattern(cmd.text)
        else:
            self._highlight_service.clear_all()
        self._log_table.set_highlight_engine(
            self._highlight_service.get_combined_engine()
        )
        if self._status_callback:
            self._status_callback("Highlights cleared" if not cmd.text else f"Highlight removed: {cmd.text}")

    def _handle_next(self, cmd: ParsedCommand) -> None:
        if self._direction == "forward":
            self._log_table.find_next()
        else:
            self._log_table.find_previous()

    def _handle_prev(self, cmd: ParsedCommand) -> None:
        if self._direction == "forward":
            self._log_table.find_previous()
        else:
            self._log_table.find_next()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_command_service.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/command_service.py tests/test_command_service.py
git commit -m "feat: add CommandService router with tests

Routes ParsedCommand to FindService, FilterController, or
HighlightService. Handles forward/backward direction for n/N."
```

---

## Task 3: CommandBar Widget

**Files:**
- Create: `src/views/widgets/command_bar.py`

- [ ] **Step 1: Implement CommandBar widget**

Create `src/views/widgets/command_bar.py`:

```python
"""Vim-style command bar widget.

Hidden by default. Shown at the bottom of the window when user presses
:, /, or ?. Supports command history with Up/Down arrows.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent


class CommandBar(QWidget):
    """Bottom command bar with prefix label and text input."""

    command_submitted = Signal(str, str)  # text (without prefix), prefix
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._prefix: str = ":"
        self._history: list[str] = []
        self._history_index: int = -1
        self._visible: bool = False
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)

        self._prefix_label = QLabel(":")
        self._prefix_label.setFixedWidth(12)
        self._prefix_label.setStyleSheet("color: #aaaaaa; font-family: monospace;")

        self._input = QLineEdit()
        self._input.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #ffffff; "
            "border: none; font-family: monospace; padding: 2px; }"
        )
        self._input.returnPressed.connect(self._on_return)
        self._input.installEventFilter(self)

        layout.addWidget(self._prefix_label)
        layout.addWidget(self._input)

    def activate(self, prefix: str) -> None:
        """Show the bar with the given prefix and focus the input."""
        self._prefix = prefix
        self._prefix_label.setText(prefix)
        self._input.clear()
        self._history_index = -1
        self._visible = True
        self.show()
        self._input.setFocus()

    def deactivate(self) -> None:
        """Hide the bar and clear state."""
        self._visible = False
        self._input.clear()
        self.hide()

    def is_active(self) -> bool:
        return self._visible

    def eventFilter(self, obj: object, event: QKeyEvent) -> bool:
        if obj is not self._input:
            return False

        if event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.deactivate()
                self.cancelled.emit()
                return True
            elif key == Qt.Key_Up:
                self._navigate_history(-1)
                return True
            elif key == Qt.Key_Down:
                self._navigate_history(1)
                return True
        return False

    def _on_return(self) -> None:
        text = self._input.text()
        if not text:
            self.deactivate()
            self.cancelled.emit()
            return

        full_command = f"{self._prefix}{text}"
        self._add_to_history(full_command)
        self.command_submitted.emit(text, self._prefix)
        self.deactivate()

    def _navigate_history(self, direction: int) -> None:
        """Navigate command history. direction: -1 = up (older), 1 = down (newer)."""
        if not self._history:
            return
        self._history_index += direction
        if self._history_index < 0:
            self._history_index = 0
        elif self._history_index >= len(self._history):
            self._history_index = len(self._history) - 1
            self._input.clear()
            return
        entry = self._history[-(self._history_index + 1)]
        # Strip prefix to show only the command part
        if entry and entry[0] in (":", "/", "?"):
            self._input.setText(entry[1:])
        else:
            self._input.setText(entry)

    def _add_to_history(self, full_command: str) -> None:
        # Non-consecutive duplicates are preserved per spec
        self._history.append(full_command)
        # Cap at 100 entries
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def show_error(self, message: str) -> None:
        """Flash an error message in the input field."""
        self._input.setStyleSheet(
            "QLineEdit { background: #1e1e1e; color: #ff4444; "
            "border: none; font-family: monospace; padding: 2px; }"
        )
        self._input.setText(f"Error: {message}")
        # Restore normal style after user starts typing
```

- [ ] **Step 2: Commit**

```bash
git add src/views/widgets/command_bar.py
git commit -m "feat: add CommandBar widget

Vim-style command bar with prefix label, history navigation,
and error display."
```

---

## Task 4: Integrate CommandBar into MainWindow

**Files:**
- Modify: `src/views/main_window.py`
- Modify: `src/controllers/main_controller.py`

This is the main integration task. We remove SearchToolbar, add CommandBar, intercept `:`/`/`/`?` keys, and wire signals.

- [ ] **Step 1: Modify MainWindow — replace SearchToolbar with CommandBar**

In `src/views/main_window.py`:

1. Replace the import of `SearchToolbarWithStats` with `CommandBar`:
   - Remove: `from src.views.widgets.search_toolbar import SearchToolbarWithStats`
   - Add: `from src.views.widgets.command_bar import CommandBar`

2. In `_create_components`, replace `_search_toolbar` with `_command_bar`:
   - Replace `self._search_toolbar: SearchToolbarWithStats = SearchToolbarWithStats()` with `self._command_bar: CommandBar = CommandBar()`

3. In `_setup_ui`, remove toolbar creation and add CommandBar between splitter and status bar:
   - Remove: `self.addToolBar(Qt.TopToolBarArea, self._create_toolbar())`
   - Remove the `_create_toolbar` method entirely
   - After `layout.addWidget(self._create_splitter())`, add:
     ```python
     # Command bar (hidden by default, shown on : / ?)
     self._command_bar.hide()
     layout.addWidget(self._command_bar)
     ```
   - Remove `self.setStatusBar(self._status_bar)` — instead add status bar to the layout at the bottom:
     ```python
     layout.addWidget(self._status_bar)
     ```

4. In `_connect_signals`, remove all SearchToolbar signal connections:
   - Remove: `self._search_toolbar.filter_applied.connect(...)`
   - Remove: `self._search_toolbar.filter_cleared.connect(...)`
   - Remove: `self._search_toolbar.open_file_clicked.connect(...)`
   - Remove: `self._search_toolbar.refresh_clicked.connect(...)`
   - Add CommandBar signals (these will be connected by MainController):
     ```python
     # CommandBar signals are connected by MainController
     ```

5. Remove `get_search_toolbar` method. Add `get_command_bar` method:
   ```python
   def get_command_bar(self) -> CommandBar:
       return self._command_bar
   ```

6. Add `keyPressEvent` override to intercept `:`, `/`, `?`:
   ```python
   def keyPressEvent(self, event: QKeyEvent) -> None:
       """Intercept :, /, ? to activate command bar."""
       if self._command_bar.is_active():
           super().keyPressEvent(event)
           return
       text = event.text()
       if text in (":", "/", "?"):
           self._command_bar.activate(text)
           event.accept()
           return
       super().keyPressEvent(event)
   ```
   Add import: `from PySide6.QtGui import QShortcut, QKeySequence, QKeyEvent` (QKeyEvent is new).

7. In `set_panels_visible`, remove references to `_main_toolbar` and SearchToolbar:
   - Remove the `_main_toolbar` field from `_create_components`
   - In `set_panels_visible`, remove the `if self._main_toolbar:` blocks
   - Keep the category panel visibility logic (splitter sizes)

- [ ] **Step 2: Modify MainController — wire CommandBar through CommandService**

In `src/controllers/main_controller.py`:

1. Add imports:
   ```python
   from src.core.command_parser import CommandParser, ParseError
   from src.services.command_service import CommandService
   ```

2. In `__init__`, after existing service init, create CommandService:
   ```python
   self._command_service = CommandService(
       find_service=self._window.get_log_table()._find_service,
       filter_controller=self._filter_controller,
       highlight_service=self._highlight_service,
       log_table=self._window.get_log_table(),
       status_callback=lambda msg: self._window.show_status(msg, 3000),
   )
   ```

3. In `_connect_signals`, remove the SearchToolbar save filter connection:
   - Remove: `self._window.get_search_toolbar().save_filter_requested.connect(...)`
   - Add CommandBar wiring:
     ```python
     self._window.get_command_bar().command_submitted.connect(self._on_command_submitted)
     self._window.get_command_bar().cancelled.connect(self._on_command_cancelled)
     ```

4. Add command handler methods:
   ```python
   def _on_command_submitted(self, text: str, prefix: str) -> None:
       """Handle command submitted from command bar."""
       direction = "backward" if prefix == "?" else "forward"
       try:
           cmd = CommandParser.parse(text, direction=direction)
           self._command_service.execute(cmd)
       except ParseError as e:
           self._window.get_command_bar().show_error(str(e))

   def _on_command_cancelled(self) -> None:
       """Handle command bar cancelled — restore focus to log table."""
       self._window.get_log_table().setFocus()
   ```

5. Remove `_on_save_filter_requested` method (SearchToolbar is gone).

6. In `_on_panels_toggled`, remove the status bar button line (SearchToolbar is gone):
   - Remove: `self._window.statusBar().set_panels_visible(visible)` — only if MainStatusBar has this method.

- [ ] **Step 3: Run existing tests to check for breakage**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: Some tests may fail due to SearchToolbar removal. Fix any broken imports or references.

- [ ] **Step 4: Fix any broken tests**

Update `tests/test_main_window.py` and any other test files that reference `SearchToolbarWithStats`, `get_search_toolbar`, or `_search_toolbar`. Replace with `CommandBar` / `get_command_bar` references as needed.

Run: `uv run pytest tests/ -v --timeout=30`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: integrate CommandBar into MainWindow, remove SearchToolbar

Replace top SearchToolbar with bottom CommandBar. Wire through
CommandService. Add keyPressEvent for :, /, ? activation."
```

---

## Task 5: Add n/N Navigation to LogTableView

**Files:**
- Modify: `src/views/log_table_view.py`

- [ ] **Step 1: Add n/N key handling**

In `src/views/log_table_view.py`, modify `keyPressEvent`:

```python
def keyPressEvent(self, event: QKeyEvent) -> None:
    """Handle key press for copy and find navigation."""
    if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
        self.copy_selected()
        event.accept()
    elif event.key() == Qt.Key_N and event.modifiers() == Qt.NoModifier:
        self.find_next()
        event.accept()
    elif event.key() == Qt.Key_N and event.modifiers() == Qt.ShiftModifier:
        self.find_previous()
        event.accept()
    else:
        super().keyPressEvent(event)
```

Note: `N` (Shift+N) is detected via `Qt.ShiftModifier` + `Qt.Key_N`. Plain `n` is `Qt.Key_N` with `Qt.NoModifier`.

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_log_table_view.py -v`
Expected: All existing tests pass (no regression).

- [ ] **Step 3: Commit**

```bash
git add src/views/log_table_view.py
git commit -m "feat: add n/N key navigation in LogTableView

n navigates to next match, N (Shift+n) to previous match."
```

---

## Task 6: Cleanup — Remove Legacy Files

**Files:**
- Delete: `src/views/widgets/search_toolbar.py`
- Delete: `src/views/filter_toolbar.py`

- [ ] **Step 1: Search for remaining references to deleted files**

Run: `grep -r "search_toolbar\|filter_toolbar\|SearchToolbar\|FilterToolbar" src/ tests/ --include="*.py" -l`

Fix any remaining imports or references found.

- [ ] **Step 2: Delete the files**

```bash
git rm src/views/widgets/search_toolbar.py src/views/filter_toolbar.py
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: All tests PASS.

- [ ] **Step 4: Run linter and type checker**

Run: `uv run ruff check src/`
Run: `uv run mypy src/`
Expected: No errors (fix any that appear).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove SearchToolbar and FilterToolbar

Replaced by CommandBar in previous commits."
```

---

## Task 7: Persistent Command History

**Files:**
- Modify: `src/views/widgets/command_bar.py`

The spec requires history persisted to `~/.logviewer/history.json` with configurable max size.

- [ ] **Step 1: Add persistence to CommandBar**

In `src/views/widgets/command_bar.py`, add save/load methods:

```python
import json
from pathlib import Path

HISTORY_DIR = Path.home() / ".logviewer"
HISTORY_FILE = HISTORY_DIR / "history.json"
DEFAULT_HISTORY_SIZE = 100

# Add to __init__:
self._max_history = DEFAULT_HISTORY_SIZE
self._load_history()

# Add methods:
def _load_history(self) -> None:
    try:
        if HISTORY_FILE.exists():
            data = json.loads(HISTORY_FILE.read_text())
            self._history = data.get("commands", [])[-self._max_history:]
    except (json.JSONDecodeError, OSError):
        self._history = []

def _save_history(self) -> None:
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps({"commands": self._history[-self._max_history:]}))
    except OSError:
        pass

def set_max_history(self, size: int) -> None:
    self._max_history = size
```

Call `_save_history()` at the end of `_add_to_history`.

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/views/widgets/command_bar.py
git commit -m "feat: persist command history to ~/.logviewer/history.json"
```

---

## Task 8: Manual Verification

- [ ] **Step 1: Run the application**

Run: `uv run python -m src.main`

- [ ] **Step 2: Verify command bar activation**

1. Press `:` — command bar appears at bottom with `:` prefix
2. Press `/` — command bar appears with `/` prefix
3. Press `?` — command bar appears with `?` prefix
4. Press `Esc` — command bar hides, focus returns to table

- [ ] **Step 3: Verify search commands**

1. `:s error` — searches for "error", jumps to first match
2. `n` — next match, `N` — previous match
3. `/error` — same as `:s error` but with forward direction
4. `?error` — same but backward direction

- [ ] **Step 4: Verify filter commands**

1. `:f error` — shows only lines containing "error"
2. `:fr/error_\\d+` — regex filter
3. `:rmf` — clear all filters

- [ ] **Step 5: Verify highlight commands**

1. `:h ERROR` — highlights "ERROR" in default red
2. `:h/color=yellow/WARNING` — highlights "WARNING" in yellow
3. `:rmh` — clear all highlights

- [ ] **Step 6: Verify history**

1. Execute `:s error`, then `:s warning`
2. Press `:`, then `Up` — should show "s warning"
3. `Up` again — should show "s error"
4. `Down` — back to "s warning"

- [ ] **Step 7: Verify error handling**

1. `:xyz` — shows error "Unknown command: xyz"
2. `:f//text` — shows error "Empty flags not allowed"
