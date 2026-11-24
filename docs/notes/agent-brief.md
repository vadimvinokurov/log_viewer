# Agent brief — logviewer2

Point every agent prompt here + the one bead id. Keep this file short and current;
the coordinator must not restate spec semantics in prompts (CLAUDE.md rule 7).

## Where truth lives
- Behavior: `docs/FUNCTIONAL_SPEC.html` (§-sections; owner reads it, do not paraphrase).
- Visuals: `docs/UI_DESIGN.html` is the oracle — classes/tokens are copied verbatim from it.
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
- Visual acceptance: `npx vitest run` (from `ui/`), then `npm run build && npm run e2e`
  with committed goldens; design oracle `node scripts/design_check.mjs` for design pairs.
- File partition for parallel agents: pre-created stubs + pre-added deps; agents never
  touch `lib.rs`, `Cargo.toml`, or other agents' files; integration is the coordinator's job.

## Known traps
- macOS case-insensitive FS: `import "./LevelBar"` resolves to `levelBar.ts` — always
  import components with the explicit `.tsx` extension.
- Concurrent test writers to the same temp file SIGBUS under the mmap scanner — use
  unique per-module temp prefixes, write-once.
- Run JS gates from `ui/`, Rust gates from the workspace root; a run from the repo root
  breaks jsdom config and produces bogus failures.
- Editing: prefer Write/Edit tools over sed/heredoc; a second failed shell edit means
  rewrite the file (CLAUDE.md rule 7).
