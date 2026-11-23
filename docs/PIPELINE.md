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

- Visual acceptance uses the app's own page rendered by a headless browser
  (Playwright against the dev server with Tauri IPC stubbed). OS screen capture is
  not acceptance evidence (it carries foreign windows and is non-deterministic); a
  live-window check stays for what a page cannot show (titlebar, min-clamps,
  real window size).
- After any visible UI change: whole-window before/after shots plus a verbal diff.
- Decision states (empty / loading / loaded / error) are designed before polish;
  look for existing parts before writing new ones; design notes in `design.md`.

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
