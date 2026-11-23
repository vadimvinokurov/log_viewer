# CLAUDE.md

## Rules

1. **The `test_logs/` folder contains real logs used for testing.**
   - Never publish it to git.
   - Never copy any information from these logs into README, docs, commit messages, or any other files.
   - Its only purpose is being opened by the app during manual testing.
   - Exception (user-confirmed): `docs/FUNCTIONAL_SPEC.html` stays in Russian, and the fact that `test_logs/` holds sample files of both log formats is documented there.

2. **All information about the project lives in `docs/`** — look there first before asking or exploring elsewhere. Current contents: `docs/FUNCTIONAL_SPEC.html` (the functional specification, in Russian by decision of the owner), `docs/UI_DESIGN.html`, `docs/STACK.md`, `docs/PIPELINE.md`.

3. **Use the installed skills, always.** Before any coding session, check the skill list and invoke what applies: `/vvv-claude-kit:building-testable-apps` for any new code, `/superpowers:test-driven-development` for any code, `/vvv-claude-kit:ui-development` for any UI work. Do not skip them because a task looks small — do not rely on memory of their contents; invoke them.

4. **Language.** Always talk to me in Russian. Keep all project files — docs, README, code
   comments, commits, issues, etc. — in English. Exception: `docs/FUNCTIONAL_SPEC.html`
   stays Russian (see rule 2).

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

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
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
