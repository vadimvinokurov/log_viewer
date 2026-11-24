# Development pipeline

How work flows through this repo. The plan lives in beads; stable truths live in
`docs/FUNCTIONAL_SPEC.html` (referenced as §N); this file fixes the *process*.

## 1. Work selection

```
bd ready                    → unblocked tasks only
bd update <id> --claim      → claim (one task per agent / per session)
```

Depends-on graph is seeded per epic, so `bd ready` reflects the real next work.
Pick by priority (P1 before P2) and by unblocking the dependency chain.

## 2. Spec first

Tasks reference spec sections (`[Spec ref]` in the bead description); they never
paraphrase the spec. Ambiguities are resolved with the simplest faithful reading and
marked `// spec interpretation:` in code; report each such decision.

## 3. Implementation (every task)

- **TDD**: tests are written first with hand-computed expectations; only then the code.
- **Golden fixtures**: committed small synthetic files (core: `tests/fixtures/`), at
  least one case computed fully by hand. `test_logs/` is never a test corpus (rule 1
  of CLAUDE.md) and is never copied from.
- **Dual-path oracle**: every non-obvious/optimized algorithm gets a naive reference
  implementation compared against the fast one on the same inputs.
- **Quality gates**: `cargo test --workspace` all green; `cargo clippy --workspace
  --all-targets` zero warnings; TypeScript strict with no `any`/`as` suppression on
  the UI side.
- **Bead closure**: `bd close <id>` only after the bead's `[Acceptance]` actually
  passes.

## 4. Parallelization

Independent ready tasks fan out to parallel subagents:

1. The main session pre-creates the module skeleton: `pub mod <name>;` stubs and all
   needed crate deps, so agents never touch shared files (lib.rs, Cargo.toml).
2. Each agent gets exactly one task and a hard file list; tests inside its own files.
3. The main session integrates, reads the full diff, re-runs gates, closes beads.
Claim tasks in the main session before spawning agents.

## 5. UI work

- **Text RPC first (rule 6)**: every interactive capability is reachable
  without a window through the app's own text interface - `window.__headless`
  (state snapshots + actions, see `ui/src/headless.ts`). The visual harness
  and component verification use it, never DOM poking in ad-hoc scripts.
- **Visual acceptance is a committed, repeatable harness (rules 6/7)**:
  `npm run e2e` (ui/e2e/render.mjs) builds the app, serves `dist` itself,
  renders each declared state (empty / loaded / loaded-scrolled / error)
  through system Chrome with the IPC stubbed, screenshots to PNG and compares
  against committed goldens (ui/e2e/goldens, pixelmatch threshold 0.5%).
  New UI states must be added to the harness and get a golden before their
  task closes; visual changes re-baseline goldens explicitly (`--update-goldens`)
  with a verbal before/after diff.
  - Rebaseline 2026-11-24 (bead dsq.3, §7 visibility bridge): loaded /
    loaded-scrolled / 13-selection / 14-selection-menu gained the §11 LevelBar
    in the footer; new states `loaded-level-off` (dimmed disabled level) and
    `filters-live-empty`/`filters-live-mixed` (FiltersTab on live console
    state) with fresh goldens.
  - Rebaseline 2026-11-24 (bead qt7.3, §4 viewport anchor): new state
    `anchor-scrolled-refilter` — scrolled deep, trace toggled off, anchored;
    assertions run on `window.__headless.viewport()` numbers, golden
    ui/e2e/goldens/anchor-scrolled-refilter.png.
  - Rebaseline 2026-11-24 (bead rhl.2, §10 categories panel): loaded /
    loaded-scrolled / 13-selection / 14-selection-menu / loaded-level-off /
    anchor-scrolled-refilter shrank by the 220-px side panel (§10.1 opens
    with a file); filters-live-mixed re-captured after the workspace wrapper.
    New states `panel-categories`, `panel-uncheck` (toggleCategory propagation
    hides the subtree rows) and `panel-tree-search` (matching branches only,
    fully expanded) with fresh goldens.
- OS screen capture is not acceptance evidence; a live-window check stays
  for what the harness cannot show (titlebar, min-clamps, real window size).
- Live-window check runs the committed driver: start the debug app
  (`cargo tauri dev` from the root — the build config starts the ui dev
  server itself — or manually `npm run dev` in `ui/` + `cargo run` in
  `src-tauri/`) and `node scripts/live_check.mjs <test_logs file>` — it
  drives `window.__headless` (load, levels, filters, categories, selection,
  copy, viewport anchor, search) through the real IPC and asserts on counts
  only, never log contents (rule 1).
- Decision states (empty / loading / loaded / error) are designed before
  polish; look for existing parts before writing new ones; design notes in
  `design.md`.
- The UI is a thin layer: all logic lives in pure modules (state.ts, table.ts,
  uiConsole.ts) tested with vitest; components only wire IPC + store to markup.

## 6. IPC layer (schema-driven commands)

Every Tauri command is a contract: typed params, typed result, TS bindings generated
from schemas (tauri-specta) - no hand-written bindings files. UI state stays thin;
data transformations live in logviewer-core.

## 7. Knowledge lifecycle

- Future-session facts → `bd remember "<insight>"`.
- Option comparison / diagrams → `docs/notes/*.md` draft; the conclusion goes to the
  task (`--design`); a superseded note gets a `resolution: <id>` header line.
- Stack/doc-level decisions → `docs/STACK.md` / `docs/PIPELINE.md`.

## 8. Session close

1. File follow-up beads for anything spotted but unstarted.
2. Run all quality gates.
3. `bd close` completed work; `bd ready` again.
4. Report changed files, validation status, and (conservative profile) proposed git
   commands - commit/push only on explicit user approval.
