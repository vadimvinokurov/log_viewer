# Core Principles

## 1. Agent rule

### MUST
- **Interview me** — Use **AskUserQuestion tool** to clarify tasks
- **Clarify first** — If ambiguous, ask at least 1 question before coding
- **Verification** — Before coding, state how we will verify the result
- **Follow existing patterns** — Don't reinvent the wheel
- **Code comments** — Only for complex logic (code should be self-documenting)
- **Error handling** — Always, don't ignore edge cases
- **Security** — Never commit secrets, use .env
- **Honesty** — Say "I don't know" instead of guessing
- Always use **Context7** for all API documentation, library references, SDK information, and technical specifications. Do not rely on training data for API details - verify all endpoints, parameters, response schemas, and version information through Context7 before providing implementation guidance.

### MUST NOT
- **NO sycophancy** — Don't start with "great question!", "excellent idea"
- **NO auto-commit** — Without explicit request
- **NO `any` type** — Or type bypass without critical need
- **NO new dependencies** — Without discussing alternatives
- **NO ignoring tests** — If none exist, propose adding them
- **NO silent assumptions** — If missing context, ask
- **NO ready solutions** — For security/money tasks without warning
- **NO text questions** — Use **AskUserQuestion tool** instead
- **NO hallucinations** — Don't fabricate facts, APIs, libraries, or code

## 2. Test-First Development (NON-NEGOTIABLE)

**Tests MUST be written before implementation.**

- **Red-Green-Refactor cycle strictly enforced**
- Write failing test → User approves → Implement → Test passes → Refactor
- Every feature, bugfix, or refactor starts with tests
- Minimum test coverage: unit tests for all business logic
- Integration tests for component interactions
- No implementation code without corresponding tests

**Rationale**: TDD catches bugs early, documents intent, and ensures code is testable by design. Tests serve as living documentation and regression protection.

**How to apply**: When implementing any feature from the spec, first write tests that fail, then implement the minimal code to make them pass, then refactor while keeping tests green.

## 3. Clean Code & Simplicity

**Code MUST be readable, maintainable, and follow best practices.**

- **YAGNI principle**: Don't implement what isn't needed yet
- **KISS principle**: Keep implementations simple, avoid over-engineering
- Single Responsibility Principle for all modules, classes, and functions
- Functions under 50 lines, modules or file under 500 lines
- Meaningful names: variables, functions, and classes describe their purpose
- No premature abstraction: wait for patterns to emerge before generalizing
- Remove dead code immediately

**Rationale**: Simple, clean code is easier to understand, review, maintain, and debug. Complexity should be added only when proven necessary.

**How to apply**: Before adding any abstraction, pattern, or framework, ask: "Is this the simplest solution that works?" Refuse complexity without justification.

## 4. Workflow: Superpowers + Beads + Templates

Before starting ANY task, invoke `template-bridge:unified-workflow` skill to load the full workflow.

### Quick Reference (do NOT skip steps)

1. **Epic** — `bd create -t epic "Goal"` (container for intent + context)
2. **Brainstorm** — `superpowers:brainstorming` (design before code)
3. **Plan** — `superpowers:writing-plans` (2-5 min tasks)
4. **Sub-tasks** — `bd create` for each + `bd dep add` (parent-child, blocks)
5. **Isolate** — `superpowers:using-git-worktrees` (non-trivial work)
6. **Implement** — `bd ready` → pick → `bd update --claim` → TDD (RED → GREEN → REFACTOR). Use **MUST** use superpowers:test-driven-development skill for implementation.
7. **Review** — `superpowers:requesting-code-review`
8. **Verify** — `superpowers:verification-before-completion` (evidence before claims)
9. **Finish** — `superpowers:finishing-a-development-branch`
10. **Close** — `bd close <epic-id> --reason "Done"`

### Rules

- No production code without a failing test first
- No completion claims without running verification commands
- No work without a beads task
- **Always query Context7 before implementing with any library/framework** (`resolve-library-id` → `query-docs`)
- Check `template-bridge:template-catalog` when a specialist agent is needed
- Side quests: `bd create -t bug` + `bd dep add new current --type discovered-from`

# Project principles

## Python & uv Standards

**Use modern Python (3.9+) with uv as the package manager.**

- **Clean Code & Simplicity**: follow Python best practices
- **Package management**: All dependencies managed through `uv`
- **Virtual environments**: Use `uv venv` and `uv pip install`
- **Type hints**: Required for all function signatures and class attributes
- **Linting & formatting**: ruff for linting, black for formatting
- **Testing framework**: pytest for all tests
- **Project structure**: Standard Python project layout (src/, tests/, pyproject.toml)
- **Documentation**: Docstrings for public APIs, comments only for complex logic

**Rationale**: Consistent tooling and standards reduce friction, improve collaboration, and leverage modern Python ecosystem best practices. uv is significantly faster than pip and provides deterministic dependency resolution.

**How to apply**: When setting up the project, initialize with `uv init`. Add dependencies with `uv add`. Run tests with `uv run pytest`. Format with `uv run black .` and lint with `uv run ruff check .`

## Quality Gates

**All code MUST pass these gates before merging:**

1. **Tests pass**: `uv run pytest` exits with 0
2. **Type checking**: `uv run mypy src/` has no errors
3. **Linting**: `uv run ruff check .` has no errors
4. **Formatting**: `uv run black --check .` shows no changes needed

**Rationale**: Quality gates prevent regressions and maintain code standards without manual intervention.

**How to apply**: Run all quality gates locally before committing. CI pipeline enforces these gates automatically.

## Governance

**Constitution supersedes all other practices and preferences.**

- Amendments require documentation with rationale and migration plan
- All PRs must verify compliance with constitution principles
- Complexity MUST be justified with concrete requirements
- Use CLAUDE.md for runtime development guidance
- Constitution changes require version bump and team review


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
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