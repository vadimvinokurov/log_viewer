# Command System Design

Date: 2026-04-23

## Overview

Implement a Vim-style command bar for the Log Viewer. The command bar replaces the existing SearchToolbar and provides modal command input (`:`), search (`/`, `?`), and navigation (`n`/`N`).

**Scope:** command bar widget, command parser, command routing to existing services. Presets and category management are out of scope.

**Reference:** `docs/spec_on_comman.md`

---

## Architecture

```
User presses :, /, ?
        |
   MainWindow (key handler)
        |
   CommandBar (widget, bottom of window)
        |  command_submitted(text)
   CommandParser
        |  ParsedCommand
   CommandService (router)
        |
   +----+----+-----------+
   |    |    |           |
FindService  FilterController  HighlightService
```

Three new files, minimal changes to existing code. Existing services receive the same calls they already handle.

---

## Components

### New files

1. **`src/views/widgets/command_bar.py`** — CommandBar widget
2. **`src/core/command_parser.py`** — Parses command text into `ParsedCommand`
3. **`src/services/command_service.py`** — Routes `ParsedCommand` to the right service

### Modified files

- **`src/views/main_window.py`** — Remove SearchToolbar, add CommandBar, intercept `:`/`/`/`?` keys
- **`src/views/log_table_view.py`** — Handle `n`/`N` keys for match navigation (only when CommandBar is inactive)

### Deleted files

- **`src/views/widgets/search_toolbar.py`**
- **`src/views/filter_toolbar.py`** (if it exists and is used)

---

## CommandBar Widget

**Behavior:**
- Hidden by default (Normal mode)
- Shown on `:`, `/`, `?` key press with the corresponding prefix pre-filled
- `Enter` — parse and execute command, hide bar
- `Esc` — hide bar, return focus to log table
- `Up`/`Down` — navigate command history

**Implementation:**
- QWidget with QHBoxLayout
- QLabel for the prefix character (`:`, `/`, `?`)
- QLineEdit for command input
- Styled to match the app theme (dark background, monospace font)

**Prefix handling:**
- `:` → Command mode. Text after `:` is the command.
- `/` → Search forward. Equivalent to `:s <text>`. Direction stored as `forward`.
- `?` → Search backward. Equivalent to `:s <text>`. Direction stored as `backward`.

**Signals:**
- `command_submitted(text: str, prefix: str)` — emitted on Enter. `prefix` is `:`, `/`, or `?`.
- `cancelled()` — emitted on Esc.

---

## CommandParser

### Grammar

```
input = action [mode] ["/" flags "/"] [text]
     | action [mode] " " [text]              # space separator when no flags
     | action [mode]                         # no-arg commands (:rmf, :lsf, :n, etc.)

action = "s" | "f" | "h" | "rmf" | "rmh" | "lsf" | "lsh" | "n" | "N"
mode = "r" | "s"                           # regex, simple. plain = no suffix
flags = flag ("/" flag)+
flag = "cs" | "color=" value
text = .*                                  # remainder of input (may be empty)
```

`text` is optional — commands like `:rmf`, `:lsf`, `:n` have no text argument.

### Result

```python
@dataclass(frozen=True)
class ParsedCommand:
    action: str           # "s", "f", "h", "rmf", "rmh", "lsf", "lsh", "n", "N"
    mode: str             # "plain", "regex", "simple"
    case_sensitive: bool  # False by default, True if /cs flag present
    color: str | None     # Highlight color, None if not specified
    text: str             # Query text (empty string for no-arg commands)
    direction: str        # "forward" (default) or "backward" (for ? prefix)
```

### Parsing rules (from spec)

1. First space after command+mode is a separator, not part of the text.
2. If the first character after command+mode is `/`, parse flags until the next `/`, then the rest is text.
3. Empty flags (`//text`) are an error.
4. Default: case insensitive, plain mode, no color.
5. If text starts with a space, use double space: `:f  text` searches for `" text"`.

### Supported commands

| Command | Action | Mode | Example text |
|---------|--------|------|-------------|
| `:s Some text` | search | plain | `Some text` |
| `:s/cs/Some text` | search | plain | `Some text` |
| `:sr/error_\d+` | search | regex | `error_\d+` |
| `:ss "ERROR" AND "timeout"` | search | simple | `"ERROR" AND "timeout"` |
| `:f Some text` | filter | plain | `Some text` |
| `:f/cs/Some text` | filter | plain | `Some text` |
| `:fr/error_\d+` | filter | regex | `error_\d+` |
| `:fs "ERROR" AND "timeout"` | filter | simple | `"ERROR" AND "timeout"` |
| `:h/color=red/ERROR` | highlight | plain | `ERROR` |
| `:h/cs/color=red/ERROR` | highlight | plain | `ERROR` |
| `:hr/error_\d+` | highlight | regex | `error_\d+` |
| `:hs "ERROR" OR "WARN"` | highlight | simple | `"ERROR" OR "WARN"` |
| `:rmf Some text` | remove_filter | plain | `Some text` |
| `:rmf` | clear_filters | — | — |
| `:rmh/color=red/ERROR` | remove_highlight | plain | `ERROR` |
| `:rmh` | clear_highlights | — | — |
| `:lsf` | list_filters | — | — |
| `:lsh` | list_highlights | — | — |
| `:n` | next_match | — | — |
| `:N` | prev_match | — | — |

### Error handling

Parse errors return a descriptive string (e.g., "Unknown command: xyz", "Empty flags not allowed"). The CommandBar displays errors in red text without closing the bar, so the user can correct the command.

---

## CommandService

Routes `ParsedCommand` to the correct existing service.

| ParsedCommand.action | Target | Call |
|---------------------|--------|------|
| `s` | `FindService` | Set search pattern, jump to first match |
| `f` | `FilterController` | Add filter (multiple filters combine via OR) |
| `h` | `HighlightService` | Add highlight with specified or default color |
| `rmf` (with text) | `FilterController` | Remove specific filter by exact match |
| `rmf` (no text) | `FilterController` | Clear all filters |
| `rmh` (with text) | `HighlightService` | Remove specific highlight by exact match |
| `rmh` (no text) | `HighlightService` | Clear all highlights |
| `lsf` | CommandBar overlay | Display active filters list as multi-line overlay in the command bar area |
| `lsh` | CommandBar overlay | Display active highlights list as multi-line overlay in the command bar area |
| `n` | `FindService` | Jump to next match |
| `N` | `FindService` | Jump to previous match |

**Error display:** Service errors shown in CommandBar (red text) or status bar temporary message.

**`:lsf`/`:lsh` display:** shown as a temporary multi-line overlay in the CommandBar area (not the status bar — the output can span multiple lines). Disappears on next key press or after a timeout.

Output format (from spec):
```
Active filters (2):
  1. :f Some text
  2. :f/cs/Some text
```

---

## MainWindow Integration

1. **Remove SearchToolbar** from the layout.
2. **Add CommandBar** at the bottom, between the splitter and status bar.
3. **Key event handler** on MainWindow:
   - `:` → show CommandBar with prefix `:`
   - `/` → show CommandBar with prefix `/`
   - `?` → show CommandBar with prefix `?`
   - Only when focus is not in CommandBar or other text input widgets.
4. **Connections:**
   - `CommandBar.command_submitted` → `CommandService.execute`
   - `CommandBar.cancelled` → hide CommandBar, restore focus to table

## LogTableView Integration

- `n` key → call FindService next match (only when CommandBar is hidden)
- `N` key → call FindService previous match (only when CommandBar is hidden)

---

## Command History

- Stored in memory as a list of strings (full command including prefix).
- `Up`/`Down` arrows in CommandBar navigate history.
- Non-consecutive duplicates are preserved (per spec).
- Persisted to `~/.logviewer/history.json` (per spec section 4.4).
- Max size configurable via `historySize` in settings (default 100).

---

## Direction handling for `/` and `?`

- `/` sets direction to `forward`. `n` = next match forward, `N` = previous match (backward).
- `?` sets direction to `backward`. `n` = next match backward, `N` = previous match (forward).
- `:s` defaults to `forward` direction.
- Direction is stored in the last executed search command and applies to subsequent `n`/`N`.

---

## Default highlight color

The first color from the named color list: `red`.

**Named colors (from spec):** red, green, blue, yellow, cyan, magenta, white, black, orange, purple, pink, brown, grey.

**Custom colors:** HEX format `/color=#FF5733`.

---

## Testing strategy

1. **Unit tests for CommandParser** — all command formats, edge cases (empty flags, leading spaces, missing text).
2. **Unit tests for CommandService** — mock services, verify correct routing.
3. **Integration tests** — CommandBar + CommandParser + CommandService with real services.
4. **Manual verification** — run the app, test command input visually.
