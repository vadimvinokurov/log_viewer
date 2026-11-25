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
- OS screen capture is not acceptance evidence.
- **Visual acceptance and live checks are retired (owner, 2026-11-25):** the
  golden-PNG harness (`ui/e2e/`, 43 goldens, `npm run e2e`), the design oracle
  (`scripts/design_check.mjs`) and the live-window driver
  (`scripts/live_check.mjs`) were removed — the whole machinery is in git
  history. The UI is stable and not under test; `docs/UI_DESIGN.html` stays as
  a passive reference. Headless logic testing through `window.__headless` +
  vitest continues to govern any future UI change.
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
   - `ui`: `npx vitest run` (full suite, not per file).
2. The script's marker `.release-gates/last-run.json` (commit SHA, `ok: true`)
   is the evidence the tagged commit passed; a gate run on a different commit
   has no value.
3. Only when the marker is green on the tagged commit: commit, push `main`,
   create and push the `v*` tag. (Live-window verification is retired —
   owner, 2026-11-25.)
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
