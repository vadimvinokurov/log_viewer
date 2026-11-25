# Agent brief — logviewer2

Point every agent prompt here + the one bead id. Keep this file short and current;
the coordinator must not restate spec semantics in prompts (CLAUDE.md rule 7).

## Where truth lives
- Behavior: `docs/FUNCTIONAL_SPEC.html` (§-sections; owner reads it, do not paraphrase).
- Visuals: `docs/UI_DESIGN.html` is the oracle — classes/tokens are copied verbatim from it.
  (Status per the `ui-development` skill: hand-made doc, pre-migration — and that is a
  deliberate owner decision (2026-11-25): the generated-doc migration is PARKED,
  not planned work; see docs/PIPELINE.md §5, CLAUDE.md rule 3.)
- Process: `docs/PIPELINE.md` (TDD, goldens, file partition, IPC conventions).
- Stack/versions: `docs/STACK.md`.

## Hard constraints
- `test_logs/` is never committed and never quoted (CLAUDE.md rule 1).
- All files/comments/commits in English; docs/FUNCTIONAL_SPEC.html stays Russian.
- Strict types everywhere: no `any`, no `as` casts, no suppressed warnings.
- TDD: failing test first, every time (unit red-green; goldens for UI states).

## Project conventions
- Rust: pure logic in `crates/logviewer-core` (headless-tested); `src-tauri` is a thin
  shell; DTO count fields are `u32` (specta forbids u64); workspace layout per `STACK.md`.
- UI: logic in pure `*.ts` modules with vitest tests; components only wire IPC + store;
  state moves through the single reducer (`state.ts`) with two front doors
  (`uiConsole` + `window.__headless`); stubs mirror RAW IPC shapes
  (snake_case), normalization lives only in `ipcClient.ts`.
- Verification gates: `npx vitest run` (from `ui/`) for logic, then
  `npm run build` (tsc -b) — Visual acceptance and live checks are retired
  (owner, 2026-11-25; see docs/PIPELINE.md §5): no goldens, no design oracle,
  do not recreate `ui/e2e/` or `scripts/*.mjs` checkers without an owner request.
- File partition for parallel agents: pre-created stubs + pre-added deps; agents never
  touch `lib.rs`, `Cargo.toml`, or other agents' files; integration is the coordinator's job.

## Sub-agent usage (CLAUDE.md rule 7)

- **Inline by default**: small edits (2–3 tool calls), judgment calls, integration into
  shared files. Spawn overhead + the agent's fresh re-reads beat a small inline task.
- **Delegate bulky process noise**: module builds with test cycles, multi-file analysis,
  gate/debug loops, benchmark runs — the coordinator never pays for those outputs again.
- **Two small agents over one fat one**; checkpoint via `bd update <id> --notes` at every
  milestone, mid-task included (a dead agent without notes is a total loss).
- **Contract before spawn**: bead [Actions]/[Pseudocode]/[Acceptance] + this brief + the
  spec section; the prompt is pointers only (`bd id: <id> — read docs/notes/agent-brief.md
  + <spec section>; touch only <files>; gates: <commands>; bd update <id> --notes at the end.`).
- **Return format**: files changed, gates run and results, risks/follow-ups — no file
  dumps back to the coordinator.

## Known traps
- macOS case-insensitive FS: `import "./LevelBar"` resolves to `levelBar.ts` — always
  import components with the explicit `.tsx` extension.
- Concurrent test writers to the same temp file SIGBUS under the mmap scanner — use
  unique per-module temp prefixes, write-once.
- Run JS gates from `ui/`, Rust gates from the workspace root; a run from the repo root
  breaks jsdom config and produces bogus failures.
- Editing: prefer Write/Edit tools over sed/heredoc; a second failed shell edit means
  rewrite the file (CLAUDE.md rule 7).
