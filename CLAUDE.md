# CLAUDE.md

## Rules

1. **The `test_logs/` folder contains real logs used for testing.**
   - Never publish it to git.
   - Never copy any information from these logs into README, docs, commit messages, or any other files.
   - Its only purpose is being opened by the app during manual testing.
   - Exception (user-confirmed): `docs/FUNCTIONAL_SPEC.html` stays in Russian, and the fact that `test_logs/` holds sample files of both log formats is documented there.

2. **All information about the project lives in `docs/`** — look there first before asking or exploring elsewhere. Current contents: `docs/FUNCTIONAL_SPEC.html` (the functional specification, in Russian by decision of the owner), `docs/UI_DESIGN.html`, `docs/STACK.md`, `docs/PIPELINE.md`.

3. **Use the installed skills, always.** Before any coding session, check the skill list and invoke what applies: `/vvv-claude-kit:testable-apps-development` for any new code, `/superpowers:test-driven-development` for any code, `/vvv-claude-kit:headless-text-rpc` when adding an interactive capability or wiring automated UI checks, `/vvv-claude-kit:ui-development` for any UI work, `/vvv-claude-kit:dual-path-oracle` when writing or optimizing a non-obvious algorithm, `/vvv-claude-kit:release-gates` before any release-tag work. Do not skip them because a task looks small — do not rely on memory of their contents; invoke them.
   **Exception (owner, 2026-11-25): design stays on the hand-made doc.** The `ui-development` generated-doc / component-variant migration is deliberately NOT applied — the hand-made `docs/UI_DESIGN.html` stays in the repo as a passive visual reference. The UI is stable and not under test (owner, 2026-11-25: golden PNG tests, design oracle and live checks retired); no UI work is planned. Invoke `ui-development` for its image-budget discipline only.

4. **`testable-apps-development` (with its text-RPC companion `headless-text-rpc`) rules apply in full, not selectively.** (Owner's feedback, 2026-11-24 — invoke the skill(s) and re-check this list before closing any code or UI task.)
   - The UI is a thin layer: every decision is logic in a pure module with vitest tests; components only wire IPC + store to markup.
   - Text RPC: the app exposes `window.__headless` (state snapshots + actions); harnesses drive it — no ad-hoc DOM poking, no one-off `evaluate` scripts.
   - Visual acceptance is retired (owner, 2026-11-25): the golden-PNG harness, design oracle and live-window checks were removed; the UI is stable and not under test. `docs/UI_DESIGN.html` stays as a passive reference for any future visual question.
   - Stub contracts mirror the raw IPC shapes exactly; normalization lives in exactly one place (the IPC adapter).
   - Headless testing covers state snapshots (via `window.__headless` + vitest) before its task closes.

5. **Headless-first UI development.** (Owner's feedback, 2026-11-24; verification retired 2026-11-25.) Any future UI change still runs headless: unit logic in vitest, states and interactions through `window.__headless`. Live-window checks and golden-PNG verification are retired — the UI is stable and not under test (owner, 2026-11-25).

6. **Language.** Always talk to me in Russian. Keep all project files — docs, README, code
   comments, commits, issues, etc. — in English. Exception: `docs/FUNCTIONAL_SPEC.html`
   stays Russian (see rule 2).

7. **Token economy.** (Owner's feedback, 2026-11-24 — based on `docs/report-01-token-usage.html`; the coordinator pays the whole visible conversation every turn, so size of turns and of agent prompts is the main lever.)
   - **Short turns, milestones as checkpoints.** End a turn at a committed milestone instead of continuing through several milestones in one turn; long turns grow a replay tail that is paid again on every turn. Commit per milestone (with the owner's approval) also makes usage-limit interruptions harmless.
   - **Agent prompts point at a shared brief.** Write `docs/notes/agent-brief.md` once (per-layer rules, file-partition conventions, style, gates, known traps — e.g. the case-insensitive import trap) and keep it current; agent prompts reference it + the one bead id instead of restating spec semantics inline (they were paid 9+ times across agents).
   - **Never debug by shell-escaping into files.** A second failed `sed`/heredoc edit → stop and rewrite the whole file (or the affected block) with the Write/Edit tools; each extra quoting round-trip costs a full read+edit cycle (the `driver.rs` fight cost tens of thousands of tokens).
   - **Numbers instead of screenshots.** Non-visual checks (element present, counts, sizes, returned copy text) go through text results from evaluate/tests. OS screenshots are not part of the loop at all — visual acceptance is retired (rule 4), so there is nothing left that needs a PNG.
   - **Scoped gates between steps, full gates once.** Run the single module's test file (`npx vitest run <name>` / `cargo test -p <crate> <module>`) while iterating; run the full workspace suite + clippy once before a commit, not after every micro-edit. Run everything from the directory the config lives in (`ui/` for JS) — a run from the repo root silently tests the wrong environment and forces a paid rerun.
   - **Cap and checkpoint agents.** Keep one task's engine + its QA surfaces from ballooning; if an agent nears its budget it checkpoints (notes + beads update) instead of pushing through and dying mid-run at a usage limit.
   - **Sub-agents absorb process noise; the coordinator keeps decisions.** The split is by tool cost, not task type. Delegate what would cost me more than a handful of tool calls or one gate cycle — module builds with test loops, multi-file analysis, gate/debug cycles, benchmark runs — to a fresh narrow agent: its reads and test output never enter the coordinator conversation that gets replayed every turn, and only the conclusion comes back. Keep inline what is small or session-shaped: 2–3-call edits, judgment calls, integration into shared files (`lib.rs`, `Cargo.toml`, `App.tsx`, generated bindings). Spawn only on a durable contract: bead `[Actions]/[Pseudocode]/[Acceptance]` + `docs/notes/agent-brief.md` + the spec section, prompt = pointers only (if the prompt must explain *why*, that context is not written down yet — write it into the bead/note first). Prefer two small independent agents over one fat one (agents checkpoint via `bd update --notes` at each milestone, never die silently); a context-inheriting fork only when reusing this conversation visibly beats a fresh prompt, never for routine lookups.
   - **No banked visual automation.** The design oracle (`scripts/design_check.mjs`) and the live driver (`scripts/live_check.mjs`) were removed (owner, 2026-11-25); do not look for them or recreate them without an explicit owner request. Manual window screenshots are not part of the loop (rule 7, "numbers instead of screenshots").

8. **Standing commit authority.** (Owner's feedback, 2026-11-24: «комить сам, когда считаешь нужным».) The agent commits locally on its own judgment — after every milestone with green gates (per rule 7's checkpoint commits), no owner approval needed. Push / Dolt remote sync stays out of scope: local commits only; pushing requires an explicit owner request.

9. **Release push = gated by the project script, never memory.** (Owner's rule,
   2026-11-25, after the v0.2.0 CI typecheck failure; operating form: the kit's
   `release-gates` skill.) A release tag push must come only after
   `bash release_gates.sh` (repo root) ran green on the exact commit the tag
   will point to: `cargo test --workspace` + `npm run build` in `ui/` (tsc -b!
   — the only gate that catches TS errors; the script wipes stale tsbuildinfo
   caches first) + full `npx vitest run`. The run leaves the
   marker `.release-gates/last-run.json` (commit SHA, ok) — the evidence a tag
   push is legitimate. Details and the lesson learned: `docs/PIPELINE.md` §6a.
   **Full procedure, including the tauri.conf.json version bump (the CI gate
   that dropped the v0.3.1 windows build) and the tag/push shape: the
   project skill `.claude/skills/release-flow/SKILL.md` — always invoke it
   before release-tag work.**

10. **Building the app binary: never bare `cargo build` in `src-tauri/`.**
    (Owner's rule, 2026-11-25, after a plain `cargo build` produced a blank
    white window: without the `tauri/custom-protocol` feature the tauri crate
    reports dev mode, and the webview loads `build.devUrl`
    (`http://localhost:5173`) where nothing listens.) Build with
    `cargo build --features tauri/custom-protocol` in `src-tauri/` — the flag
    `cargo tauri build` passes. The tauri build script recompiles the app
    package automatically when `ui/dist` changes, so the usual flow is
    `npm --prefix ui run build` → that cargo command → run
    `target/debug/logviewer`. Symptom checklist if a launched window is blank:
    driver POST with `{"js": "return ..."}` returning `null` vs hanging, and
    beads memory `tauri-debug-build-needs-custom-protocol`.

    **Owner's rule, 2026-11-25: a request to "run the app" means a CI-shaped
    build, not a test run.** CI (`.github/workflows/release.yml`, tauri-action)
    produces `tauri build` = `npm --prefix ui run build` + cargo **release**
    with `tauri/custom-protocol`. So the local equivalent for launching is:
    `npm --prefix ui run build` → `cargo build --release --features
    tauri/custom-protocol` (in `src-tauri/`) → run
    `target/release/logviewer`. Bundling (dmg/NSIS/updater signing) is CI-only
    and is skipped locally. No test runs are required for a launch request —
    release gates are for release-tag pushes only (rule 9).

## Workflow

Three storage roles:

| Storage | Holds |
|---|---|
| `docs/FUNCTIONAL_SPEC.html` | Stable truth about app behavior (owner reads it; never paraphrase it into tasks — reference sections, e.g. "§3") |
| `docs/notes/*.md` | Temporary reasoning: option comparisons, diagrams, discarded ideas |
| beads (`bd`) | The work plan: epics → tasks, with concrete actions and pseudocode inside the task |

Beads structure:

- **Epic = one subsystem** (parsing, matching, table, filtering, search, highlights,
  categories, levels, pins, cmdline, appshell, settings, perf).
- **Task = one work session.** Self-contained: a session picking it up needs no prior
  conversation. Required blocks in the description: `[Spec ref]` (sections, no duplication),
  `[Actions]` (numbered concrete steps), `[Pseudocode]` (solution skeleton), `[Acceptance]`
  (verifiable criteria — commands/runs, not vibes). Bigger than one session → decompose
  with `--parent=<task>`, don't grow the description.
- Set dependencies with `bd dep add` so `bd ready` shows real next work.

Session loop:

```
bd ready                 → what is unblocked
bd update <id> --claim   → claim it
<code + tests>           → read the spec, don't rewrite it for the task
bd close <id>            → only after [Acceptance] actually passes
bd remember "<insight>"  → for anything future sessions must not lose
```

Acceptance criteria reference `test_logs/` real files wherever possible (numbers and
shapes, never contents — rule 1). Enable `bd config set validation.on-create warn` so
empty tasks can't slip in. Notes lifecycle: `notes/*.md` is a draft → conclusion goes to
the task → final decision recorded in `--design`; put a "resolution: <id>" line at the top
of a superseded note.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:1105d646 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Commits are authorized by rule 8 (local, per milestone); git pushes and Dolt remote sync only on explicit request. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
