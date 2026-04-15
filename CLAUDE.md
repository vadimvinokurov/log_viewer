# Development Principles

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Code Standards

- **Comments** — Only for complex logic (code should be self-documenting)
- **Security** — Never commit secrets, use .env
- **Context7** — Use for API docs when working with unfamiliar or rapidly-changing libraries. Not needed for stdlib or well-known patterns.
- **Single Responsibility** — For all modules, classes, and functions

# Workflow

## Tiers

Not every task needs the full process. Pick the right tier:

### Trivial (typo fix, config change, one-liner)
1. Fix it
2. Verify manually or with existing tests
3. Commit

### Normal (bug fix, small feature, refactor)
1. `bd create` — track the task
2. Write a failing test (if applicable)
3. Implement until tests pass
4. Run quality gates
5. `bd close` + commit

### Feature (new capability, multi-file change, architectural decision)
1. Follow the /unified-workflow skill recommendations 

### How to choose
- In doubt? Start with Normal. Upgrade to Feature if scope grows.
- Downgrading mid-work is fine — don't force ceremony on small things.

## Context7

Use `resolve-library-id` → `query-docs` when working with external libraries/frameworks. Skip for stdlib, builtins, or patterns you're confident about.

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

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

# Project Standards

## Python & uv

**Modern Python (3.9+) with uv as the package manager.**

- **ALWAYS use `uv run`** for ALL Python execution — tests, scripts, one-liners, everything. Never call `python`, `python3`, or `.venv/bin/python` directly.
- **Package management**: All dependencies through `uv`
- **Type hints**: Required for all function signatures and class attributes
- **Linting & formatting**: ruff for linting, black for formatting
- **Testing**: pytest for all tests
- **Structure**: Standard layout (src/, tests/, pyproject.toml)
- **Documentation**: Docstrings for public APIs

**How to apply**: `uv init` to start, `uv add` for deps, `uv run pytest` to test, `uv run black .` to format, `uv run ruff check .` to lint, `uv run python -c "..."` for one-liners.

## Quality Gates

**All code must pass before merging:**

1. `uv run pytest` — exits with 0
2. `uv run mypy src/` — no errors
3. `uv run ruff check .` — no errors
4. `uv run black --check .` — no changes needed