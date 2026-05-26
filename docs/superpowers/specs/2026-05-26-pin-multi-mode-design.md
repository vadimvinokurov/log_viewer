# Pin Command Multi-Mode Design

**Date:** 2026-05-26
**Status:** Approved

## Problem

The `:pin` command only accepts a single line number. Other commands (`:f`, `:h`, `:s`) support multiple match modes (plain, regex, simple query, line number). Pin should follow the same pattern.

## Decision

Replace `:pin` with four mode variants:

| Command | Mode | Behavior |
|---------|------|----------|
| `:p <text>` | Plain | Pin all lines containing text |
| `:pr <regex>` | Regex | Pin all lines matching regex |
| `:ps <query>` | Simple | Pin all lines matching simple query (AND/OR/NOT) |
| `:pn <number>` | Line number | Pin a specific line (current `:pin` behavior) |

Remove `:pin` entirely — no backward-compatible alias.

## Architecture

Reuse existing `SearchMode` enum and `filter_engine.match()`. No new models or data structures.

### Changes

**`command_parser.py`**
- Add `"p"`, `"pr"`, `"ps"`, `"pn"` to `_VALID_COMMANDS`
- Remove `"pin"` from `_VALID_COMMANDS`

**`app.py`**
- Remove `elif name == "pin"` block
- Add dispatch for `"p"`, `"pr"`, `"ps"`:
  - Map command name to `SearchMode` (same dict pattern as `f`/`fr`/`fs`)
  - Iterate over `self.log_store.lines`
  - Call `filter_engine.match(line.raw_text, Filter(pattern=text, mode=mode))` for each
  - Collect matching line numbers
  - Call `log_store.pin_lines(line_numbers)` (new batch method)
- Add dispatch for `"pn"`:
  - Parse integer from `parsed.text`
  - Call `log_store.pin_line(line_num)` (existing method)
- Remove any references to `"pin"` command name

**`log_store.py`**
- Add `pin_lines(line_numbers: Iterable[int])` — adds all numbers to `pinned_line_numbers`, calls `_apply_filters()` once
- Existing `pin_line()` unchanged (still used by `:pn` and `rmpin`)

### Files not changed

- `models.py` — no new enums or data classes needed
- `filter_engine.py` — no changes
- `side_panel.py` — pin list widget unchanged
- `bottom_bar.py` — unchanged

## Verification

- `uv run pytest tests/unit/` passes
- Manual test: `:p error` pins all lines containing "error"
- Manual test: `:pr ^\\[LOG_ERROR\\]` pins all error lines
- Manual test: `:ps "error" AND "timeout"` pins lines matching both words
- Manual test: `:pn 42` pins line 42
- Manual test: `:pin 42` returns unknown command error
