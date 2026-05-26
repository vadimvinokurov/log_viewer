# Pin Rules Design

**Date:** 2026-05-26
**Status:** Approved

## Problem

Pinned tab shows individual pinned lines. Should show pin rules (pattern + mode) like the Filter tab shows filter rules.

## Decision

Replace `pinned_line_numbers: set[int]` with `pinned_rules: list[Filter]` + `pinned_enabled: list[bool]`. Each pin command creates one rule. Pinned tab shows rules with toggle/delete.

## Changes

**`log_store.py`**
- Remove `pinned_line_numbers: set[int]`
- Add `pinned_rules: list[Filter]` + `pinned_enabled: list[bool]`
- `add_pin(Filter)` — append rule, recompute
- `remove_pin(index)` — remove by index, recompute
- `unpin_all()` — clear all rules
- `_apply_filters()` — compute pinned indices from active rules via `filter_engine.match()` for PLAIN/REGEX/SIMPLE, and direct index for LINE_NUMBER

**`gui/pinned_list.py`** (PinnedListWidget)
- Refactor to FilterListWidget pattern: checkbox + label (mode prefix + pattern) + delete button
- `set_pins(rules, enabled)`, `toggle_pin()`, `remove_pin()`, `pin_changed` signal

**`app.py`**
- `:p`/`:pr`/`:ps` → `log_store.add_pin(Filter(pattern=text, mode=mode))`
- `:pn` → `log_store.add_pin(Filter(pattern=str(num), mode=SearchMode.LINE_NUMBER))`
- Connect pin_changed signal to refresh

**`models.py`** — no changes (reuse Filter dataclass)

**`command_parser.py`** — no changes
