# Stack

Defines the technology stack for rewriting Log Viewer from scratch. Functional truth
lives in `docs/FUNCTIONAL_SPEC.html` (referenced below as §N); this file only fixes
*how* the rewrite is built. Decision date: 2026-11-23.

## Decision

**Tauri 2 — application core in Rust + UI in web technologies (TypeScript + React).**

Approaches considered:

| Approach | Verdict |
|---|---|
| Tauri 2 (Rust core + web UI) | Chosen. Native-grade speed for hundreds-of-MB files; HTML/CSS renders the complex row markup (span highlights, overlays, menus) cheaply. |
| Electron + TypeScript | Rejected: Chromium baseline memory plus slow JS parsing of 842 MB; a native offload would be needed anyway, removing Electron's only advantage. |
| Native GUI (Qt / egui / Flutter) | Rejected: a table with per-span highlight overlays, tooltips, context menus and side panels means weeks of manual widget work that a web renderer gives for free. |

Non-goals that bound the choice (§1): single window, read-only, no networking,
macOS + Windows only.

## Layers

### 1. Core — Rust crate, no UI dependencies

Everything that can be tested headless lives here:

- **File reading & scanning** — memory-mapped reading, SIMD-accelerated line splitting
  (`memmap2`, `memchr`); parallel warm paths with `rayon`. Loading never blocks the UI
  (§2): it runs in background threads and the result is applied on completion.
- **Parsing** — formats A (KSIVA) and B (PLAIN), the shared parse rules and edge cases
  (§3): whitespace separators, optional level, level-tag vs message disambiguation,
  uncategorized fallback, time-of-day display, hierarchical categories split by `/`.
- **Match engine** (§5–§6) — four match modes:
  - plain substring, case-insensitive;
  - regex, case-insensitive — `regex` crate as the fast path, `fancy-regex` for
    patterns using lookarounds/backreferences (spec says Python-compatible syntax);
    an invalid pattern matches nothing and never panics;
  - simple query — small boolean grammar (`OR < AND < NOT`, quoted terms, parentheses);
    hand-rolled recursive-descent parser, no grammar framework needed;
  - exact line number.
- **Visibility semantics** (§7) — the combined rule (text filters OR none) AND level
  AND category OR pin, plus the level-button counters that ignore level toggles.
- **Viewport/index bookkeeping** — stable line numbering (1-based, survives filtering,
  §4), anchor-based viewport preservation, scroll-to-row computations.
- **Settings & history store** (§15) — JSON read/write in `~/.logviewer/`,
  unknown keys preserved, missing keys defaulted, lazy directory creation, disk errors
  never abort the app.

The crate exposes a synchronous, pure API (explicit state in, results out) so the whole
engine is unit-tested by `cargo test` with no UI, no threads, no IPC.

### 2. UI — TypeScript + React (Vite)

- **Virtualized table** — `@tanstack/react-virtual`: pixel-based virtualization for
  6.4M rows; the anchor/scroll-to-row logic from §4 rides on its offset APIs. Row cells
  are HTML with inline-style spans for highlight overlays (§9) — no canvas needed at
  ~50 visible rows.
- **Panels** — tabbed side panel (Categories tree with tri-state checkboxes, Filters,
  Highlights, Pinned; §10–§10.1), bottom bar (Open / Reload / command line / level
  buttons with counts; §11), Chrome-style search panel (§8).
- **Command line & hotkeys** (§13–§14) — plain input element with history navigation;
  global key handling in React.
- State kept as a single explicit application state object; no heavy state framework
  unless scale proves otherwise.

### 3. Shell — Tauri 2

- `tauri-plugin-dialog` for Open, `tauri-plugin-clipboard-manager` for Copy/Copy
  Message (§4); drag-and-drop via Tauri's file-drop events (§2).
- Core crate is compiled into the Tauri app; UI talks to it over Tauri IPC via thin,
  generated bindings — the UI holds view state only, all data transformations stay in
  the core.

## Versions & tooling

- Rust stable (edition 2024); crates: `regex`, `fancy-regex`, `memmap2`, `memchr`,
  `rayon`, `serde`/`serde_json` (also for IPC payload types).
- TypeScript 5, React 18, Vite, `@tanstack/react-virtual`.
- Tauri 2.x with the dialog and clipboard-manager plugins.
- Tests: `cargo test` for the core (formats, matching, visibility, settings — using
  fixtures shaped like `test_logs/`, never its contents), Vitest for UI logic
  (command parsing, tree building, state transitions).
- Build: `npm` for the web side (pnpm is not installed on this machine), `cargo`/`cargo-tauri` for the shell.

## What is deliberately out of scope here

Concrete UI layout, colors and interaction details are owned by `docs/UI_DESIGN.html`
and the spec; per-feature work plans live in beads. This file changes only when the
stack itself changes.
