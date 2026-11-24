# 2wu.1 — search panel: design (final)

Spec: §8 (Ctrl+F; Chrome-style top panel: input, mutually exclusive Regex |
Simple tumblers (both off = substring), match counter «k of N» / «0 of 0»,
prev/next, close; cyclic navigation; over VISIBLE rows only; starts from the
current selection downward; scroll-to-match centers; Esc closes; arrows
navigate matches while open, act as row navigation when closed).

## Raw IPC (new, one command — Rust agent)

```
search_visible(mode: string, pattern: string) -> SearchMatchDto
SearchMatchDto { total: u32, positions: Vec<u32> }   // 0-based VISIBLE indexes, ascending
```

- mode ∈ plain | regex | simple (same strings as add_filter). Unknown mode →
  Err (dsq.3 precedent). Invalid pattern → matches nothing (core never()).
- Empty pattern → `{ total: 0, positions: [] }` («0 of 0»).
- Case-insensitivity comes from the core matchers.
- Scope: the shell's cached visible sequence (§7) — hidden rows never match.
- No cap on `positions`; the UI debounces recompute (250 ms). If that becomes
  slow on the big corpus, 7no.1 measures and decides.

## UI (reducer slice + console + components)

- `search { open, mode, query, positions, current }`; counter = (k, N):
  k = 1-based rank of the current match, N = total; «0 of 0» when N == 0.
- Actions: `openSearch` (Ctrl+F; focuses the input), `closeSearch` (Esc),
  `setSearchMode(m|null)` (exclusive tumblers), `setSearchQuery(q)` (debounced
  recompute → console action), `nextMatch(dir)` (cyclic; selects the match row
  + scrollToRow centering via the qt7.3 helper). Each recompute keeps the
  starting rule: first match at-or-below the selection's visible index.
- Global keydown: Ctrl/Cmd+F opens (file loaded only); while the panel is
  open Up/Down = match navigation; while closed Up/Down = select previous /
  next visible row (clamp at the edges — spec interpretation: «обычная
  навигация»), preserving shift/ctrl modifiers? No: plain arrows only move
  the selection, modifiers keep the §4 semantics through onRowClick paths.
- Selecting a match dispatches the ordinary selection events (the match row
  becomes the selection; multi-select untouched — §4 rule for the click kind).
- Panel markup per docs/UI_DESIGN.html (top-edge floating bar, compact
  tumblers, counter, ↑/↓/✕). Classes/tokens verbatim from the reference.

## e2e + gates

- States: open panel with a query (counter + highlighted row), regex mode,
  simple mode, cyclic wrap (0→last), search with a category hidden (N counts
  visible only). Committed goldens + numbers via __headless
  (search slice in ConsoleSnapshot; actions mirrored).
- Full gates from ui/, oracle from root; live-check section (g) by the
  coordinator at the milestone.

## Interpretations documented in code

- Both tumblers off = substring; tumblers are radio-like (turning one on
  turns the other off), clicking an active tumbler turns it back off? No —
  at least plain must remain: clicking an active tumbler switches to plain
  (both-off state). UI never sends an unknown mode.
- Arrows while the panel is open AND the focus is in a text field still
  navigate matches (the panel owns arrows while open).
