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
  - Addition 2026-11-24 (bead 2wu.1, §8 search panel): new states
    `search-open`, `search-regex`, `search-hidden-scope` (N counts visible
    rows only), `search-cyclic-wrap` (0 -> last -> 0) with fresh goldens;
    no existing golden shifted (all diffs 0.000%).
  - Addition 2026-11-24 (bead q1f.1, §12 pins UI): new states `20-pins-panel`
    (Pinned tab: entries + a dimmed disabled one) and `21-pins-survive-filter`
    (§7 pin override under a narrowing filter, then the §4 context-menu Unpin
    removes the exact-row pin) with fresh goldens; `14-selection-menu`
    re-baselined - the Pin command un-dims (live §4 presence evaluation,
    Unpin stays dim on an unpinned selection).
  - Addition 2026-11-24 (bead exx.2, §9 highlights UI): new states `22-highlights-overlap`
    (two stacked tints, Message column only), `23-highlights-disabled` (dimmed tab item,
    no spans), `24-highlights-color-picked` (user override hex + byte-offset match) and
    `25-highlights-lineno` (:hn whole-message row) with fresh goldens; no existing golden
    shifted (all diffs 0.000%).
  - Addition 2026-11-24 (bead 7rf.1, §13 command line): the flat `:type command...`
    input joined the footer of every state, so ALL 26 existing goldens were re-baselined
    (footer band only; table/panel content unchanged); new states `26-cmdline-visible`
    (':'-activated focused field), `27-cmdline-filter-executed`, `28-cmdline-error`
    (Unknown command in the status area) and `29-cmdline-history` (↑-recalled entry)
    with fresh goldens.
  - Addition 2026-11-24 (bead 7rf.2, §13.2 persistent history): new state
    `30-cmdline-history-persistent` (↑ recalls the STORE's newest entry; the
    history file is seeded through an `addInitScript` stub before the app boots) with a
    fresh golden — the recalled field text renders as in state 29 (the table band
    differs: nothing was executed in this state).
  - Addition 2026-11-24 (bead vk9.2, §15 settings): new state `31-last-open-dir`
    (the boot-time settings_get seed lands on the Open-dialog start dir; a successful
    open persists the file's dirname — asserted as numbers through
    `window.__headless.state().settings.lastOpenDir`) with a fresh golden; no
    existing golden shifted (all diffs 0.000%).
  - Addition 2026-11-25 (bead fe6, v1-parity restyle, mock commits b9931bb..e5bf7e3):
    system fonts (IBM Plex Mono webfont dropped), `--table-bg` token (#f5f7fa light),
    21px rows, 32px bottom bar with flat buttons, 280px panel, native tree
    checkboxes, 16px twisties. ALL existing goldens re-baselined (every state
    shifted: palette, metrics, fonts); `column-dragged` geometry recomputed for
    the 280px panel (message 750/790 instead of 810/850). New states
    `light-empty`, `light-loaded`, `light-panel-categories` — the harness now
    supports a per-state `colorScheme` override and the light palette gets its
    own rendered acceptance (the runner default stays dark).
  - Addition 2026-11-25 (owner call on top of fe6, mock 97b7ed7): log rows
    tightened 21px -> 18px; the single source is `ROW_HEIGHT_PX` (pinned by a
    test, viewportAnchoring.test.ts) and the CSS `.row`/`.table-header` height
    agree with it. All goldens re-baselined again.
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

## 6a. Release (owner rule, 2026-11-25 - learned from the v0.2.0 failure)

Pushing a release tag (`v*`, the tag-driven `release` workflow) is allowed only
after the SAME runs the CI performs have been made locally, on the exact commit
the tag will point to, and came back green:

1. `cargo test --workspace` (repo root; regenerates `ui/src/bindings.ts` - a
   dirty tree after it is a finding, not commit noise).
2. From `ui/`: `npm run build` - this is `tsc -b && vite build`. `tsc -b` is the
   only gate that catches TypeScript errors; vitest does not (esbuild strips
   types), so a suite green without this step proves nothing about types.
   The incremental cache (tsbuildinfo) can hide breakage: wipe stale caches
   (or `rm -f tsconfig*.tsbuildinfo node_modules/.tmp/*.tsbuildinfo`) before
   the decisive check.
3. From `ui/`: `npx vitest run` (full suite, not per file).
4. From `ui/`: `npm run e2e` (all states against the committed goldens).
5. A live check in the real window (`scripts/live_check.mjs`) for whatever the
   release adds - the milestone rule 5 lives here too.

Only when all of the above passed: commit, push `main`, create and push the
`v*` tag. Watching the run (`gh run view`) completes the release; a red run is
a stop-and-fix, not a re-tag later. The release history (v0.2.0, 2026-11-25):
the gates were run, but with a stale incremental tsc cache and without a fresh
`tsc -b`; the tag had to be moved after the CI typecheck failure.

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
