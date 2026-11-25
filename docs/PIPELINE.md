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
- **Dual-path oracle (skill `vvv-claude-kit:dual-path-oracle`)**: every non-obvious/optimized
  algorithm ships with its naive reference twin in the same changeset; an equality test
  (identical inputs to both, Δ ≤ ε) is permanent — deleting it is a violation; the speedup
  is measured and recorded in `docs/BENCHMARKS.md` (the project's performance table).
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
  (Skill `vvv-claude-kit:headless-text-rpc` carries the obligations: one shared
  handler for button and command, typed coercion at one boundary, fakes shaped
  like the real IPC, snapshot as the acceptance ground.)
- **Visual acceptance is a committed, repeatable harness (testable-apps-development
  rules 6–7; skill `vvv-claude-kit:ui-development`)**:
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
  - Rebaseline 2026-11-25 (bead log_viewer2-7u9, owner decision: no per-category
    row counters): the right-aligned `.ct` counter is removed from every tree
    row (All included) — both in the design mock (UI_DESIGN.html) and the app;
    the load pipeline no longer counts rows per category (Rust: the FileModel
    holds a BTreeSet of distinct paths; IPC `categories` = `{path}[]`).
    All loaded-state goldens re-baselined — the only content change is the
    removed counter text at the panel's right edge; `panel-categories`,
    `panel-uncheck`, `panel-tree-search` and `light-panel-categories` re-captured
    (0.000% on the following full run). All diffs pre-baseline stayed inside the
    0.5% threshold, so the re-baseline was done explicitly per the visual-change
    rule, not because the suite failed.
  - All golden work follows the `vvv-claude-kit:golden-rebaseline` triage protocol:
    read the diff output before any artifact, classify intended vs regression in the
    task text, record a before/after diff per overwritten golden, fresh render review
    before any overwrite.
  - Golden layout status: the harness serves whole-screen **state goldens**
    (one PNG per UI state). The kit's `ui-development` skill moves to **component ×
    variant goldens plus 3–5 composite screens**, with the design doc GENERATED from
    the component sources (`ui_design/ui_components/`); a hand-made mock compared
    against the app (today's `design_check.mjs` PAIRS) is a listed trap. The project
    is in the skill's "hand-made design doc present (pre-migration)" state, and the
    owner decided (2026-11-25) to STAY there: the migration is parked (bead
    log_viewer2-5d3), not planned work — do not start it without an explicit owner
    request (CLAUDE.md rule 3 exception).
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

The rules live in the kit skill `vvv-claude-kit:release-gates`; this section
fixes the project instantiation. A release tag (`v*`, the tag-driven `release`
workflow) is pushed only after the project script **`bash release_gates.sh`**
(repo root) ran green on the exact commit the tag will point to — same-gated
run, no tag from memory:

1. `release_gates.sh` holds the gate list in release order (obligation 2: the
   script is the list, never memory):
   - `cargo test --workspace` (repo root; regenerates `ui/src/bindings.ts` - a
     dirty tree after it is a finding, not commit noise);
   - `ui`: stale tsbuildinfo wiped, then `npm run build` (`tsc -b && vite
     build`) - `tsc -b` is the only gate that catches TypeScript errors; vitest
     does not (esbuild strips types), so a suite green without this step proves
     nothing about types;
   - `ui`: `npx vitest run` (full suite, not per file);
   - `ui`: `npm run e2e` (all states against the committed goldens).
2. The script's marker `.release-gates/last-run.json` (commit SHA, `ok: true`)
   is the evidence the tagged commit passed; a gate run on a different commit
   has no value.
3. Only when the marker is green on the tagged commit: commit, push `main`,
   create and push the `v*` tag. A live check in the real window
   (`scripts/live_check.mjs`) stays a milestone obligation (CLAUDE.md rule 5)
   for whatever the release adds - the release-gates skill covers the gates
   list, the milestone rule covers the window.
4. A failed tag push names the run: fix the cause, re-run
   `bash release_gates.sh`, then publish. If CI still fails after the local
   gates passed on the same commit, the diff between local and CI environments
   is the task - not another blind tag push.

The release history (v0.2.0, 2026-11-25): the gates were run from memory, with
a stale incremental tsc cache and without a fresh `tsc -b`; the tag had to be
moved after the CI typecheck failure. The script exists so this cannot recur
silently.

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
