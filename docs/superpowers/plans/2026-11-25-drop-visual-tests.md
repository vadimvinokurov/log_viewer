# Drop visual tests, goldens, live checks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove golden-PNG visual testing, the design oracle, and real-window
live verification from the repo, CI/release gates, and project rules; keep
`docs/UI_DESIGN.html` as a passive reference and keep the headless logic tests.

**Architecture:** Pure deletion + config/pipeline edits + rule/doc rewrites. No
new code. The ui/ test suite (`tsc -b`, vitest) and Rust workspace tests are
untouched, so every verification is a green run of what already exists plus
grep gates proving nothing references the deleted paths.

**Tech Stack:** npm workspace `ui/` (TypeScript, vite, vitest), Bash release
script, GitHub Actions workflow, Markdown/HTML docs.

**Spec:** `docs/superpowers/specs/2026-11-25-drop-visual-tests-design.md`

## Global Constraints

- Delete, do not archive: git history is the safety net; the working tree
  carries no dead test machinery (spec, Approaches §1).
- `ui/src/headless.ts` (text RPC) and `ui/src/uiConsole.test.ts` stay untouched.
- Rust workspace and `npm run build`/vitest remain the release evidence.
- Project files in English; conversation in Russian (CLAUDE.md rule 6).
- No pushes or tag work; local commits only (CLAUDE.md rule 8 → §6a excludes
  e2e from the gate list after Task 3).

## Review Focus

- **npm lockfile/dep drift** after removing `pixelmatch`/`playwright-core`/`pngjs` devDeps → `npm install --prefix ui` regenerates the lockfile and the full `npm --prefix ui test` run (Task 1) plus `npm --prefix ui run build` (Task 5) must stay green.
- **CI workflow breakage** after deleting the `goldens` job → YAML must parse (`ruby -ryaml`) and `build.needs` must reference only `[gate]` (Task 3).
- **Gate script drift** → `bash -n release_gates.sh` must pass and the `GATES` list must hold exactly the 3 remaining entries (Task 3).
- **Stale references to deleted paths** → grep `ui/e2e`, `design_check.mjs`, `live_check.mjs`, `render.mjs`, `npm run e2e` across CLAUDE.md, docs/, workflows, scripts after each removal task, zero hits outside `docs/superpowers/` (history) and PIPELINE.md §5 "retired" note (Tasks 1–4, final grep in Task 5).
- **Headless logic suite must keep passing** → `npm --prefix ui test` green after every package.json touch (Tasks 1, 5).

---

### Task 1: Remove the visual harness from `ui/`

**Files:**
- Delete: `ui/e2e/` (entire tree: render.mjs, states/, goldens/ 43 PNGs, showcase PNGs, design/ pairs)
- Modify: `ui/package.json` (remove `"e2e"` script; remove devDeps `pixelmatch`, `playwright-core`, `pngjs`)
- Modify: `ui/package-lock.json` (via `npm install`)

**Interfaces:**
- Produces: a `ui/` with only dev/build/test scripts (`dev`, `build`, `lint`, `preview`, `test`); vitest suite unchanged.

- [ ] **Step 1: Delete the harness tree**
  ```bash
  git rm -rq ui/e2e
  ```
- [ ] **Step 2: ui/package.json** — remove the `"e2e"` script line and the three devDependency entries (`pixelmatch`, `playwright-core`, `pngjs`).
- [ ] **Step 3: Sync the lockfile and verify the suite**
  ```bash
  npm install --prefix ui
  npm --prefix ui test
  ```
  Expected: install ok, vitest suite green (includes `uiConsole.test.ts`).
- [ ] Step 4: Verify no orphan references: grep -rn "pixelmatch\|playwright\|pngjs" ui/ --include="*.ts" --include="*.tsx" --include="*.json" → zero hits outside node_modules.
- [ ] **Step 5: Commit**
  ```bash
  git add -A ui/
  git commit -m "test(ui): drop golden PNG visual harness (owner decision)"
  ```

### Task 2: Remove design oracle and live-window driver

**Files:**
- Delete: `scripts/design_check.mjs`, `scripts/live_check.mjs`

**Interfaces:**
- Consumes: nothing. `scripts/` becomes empty (no other files there) — remove the directory if git leaves it.

- [ ] **Step 1: Delete and verify nothing references them**
  ```bash
  git rm -q scripts/design_check.mjs scripts/live_check.mjs
  grep -rn "design_check\|live_check" --include="*.mjs" --include="*.rs" --include="*.ts" --include="*.sh" . | grep -v node_modules
  ```
  Expected: no hits.
- [ ] **Step 2: Commit**
  ```bash
  git commit -m "test: remove design oracle and live-window driver (owner decision)"
  ```

### Task 3: Pipeline — release gates script and CI workflow

**Files:**
- Modify: `release_gates.sh` (drop the e2e gate; fix header comments)
- Modify: `.github/workflows/release.yml` (drop the `goldens` job; `build.needs: [gate]`; drop the golden comments in the `gate` job)

**Interfaces:**
- Produces: `GATES` = exactly three entries: `cargo test --workspace`, `npm --prefix ui run build`, `npm --prefix ui test`.

- [ ] **Step 1: release_gates.sh** — remove the `"npm --prefix ui run e2e"` entry and its two comment lines; update the header comment (drop the "plus the golden gate" clause: gates mirror job `gate` only).
- [ ] **Step 2: release.yml** — delete the whole `goldens:` job block and the two comment blocks referencing goldens (in `gate` job); change `needs: [gate, goldens]` to `needs: [gate]`.
- [ ] **Step 3: Verify both files**
  ```bash
  bash -n release_gates.sh
  ruby -ryaml -e 'YAML.load_file(".github/workflows/release.yml"); puts "yaml ok"'
  grep -n "needs:" .github/workflows/release.yml   # build job: needs: [gate]
  ```
  Expected: syntax ok, yaml ok, one `needs:` = `[gate]`.
- [ ] **Step 4: Commit**
  ```bash
  git add release_gates.sh .github/workflows/release.yml
  git commit -m "ci: drop golden e2e gate from release script and workflow"
  ```

### Task 4: Rules and docs

**Files:**
- Modify: `CLAUDE.md` (rules 3, 4, 5, 7, 9)
- Modify: `docs/PIPELINE.md` (§5 rewrite, §6a gate list)

**Interfaces:**
- Produces: rules that no longer mandate golden/live/PNG workflows; PIPELINE.md §5 keeps text-RPC-first + thin-layer, adds a short "visual acceptance retired" note dated 2026-11-25.

- [ ] **Step 1: CLAUDE.md**
  - Rule 3 exception note: drop the "and the whole-screen state goldens from `ui/e2e/render.mjs`" clause and the parked-migration bead reference (migration decision is moot once goldens are gone); keep the `ui-development` image-budget sentence scoped to "no UI work is planned".
  - Rule 4: replace the PNG-acceptance bullet with a single line: visual acceptance was retired (owner, 2026-11-25) — UI is stable; `docs/UI_DESIGN.html` is the passive reference if a visual question ever comes up.
  - Rule 5: replace the milestone live-check with: headless-first still governs any future UI change, but live-window and goldens verification are dropped; UI is stable and not under test.
  - Rule 7: the "banked automation" bullet — design/live scripts removed; the "scoped gates" bullet — drop "+ e2e" from the full-gate list.
  - Rule 9: remove `+ npm run e2e` from the gate sentence; keep the rest (script, marker, §6a).
- [ ] **Step 2: docs/PIPELINE.md**
  - §5: remove the visual-acceptance bullet and all golden-history bullets; keep text-RPC-first and thin-layer bullets; add one "Visual acceptance retired (owner, 2026-11-25)" note: goldens/live checks/design oracle removed, `docs/UI_DESIGN.html` stays as a passive reference, git history holds the machinery.
  - §6a: gate list item `ui: npm run e2e` removed; item 3's live-check sentence replaced by "live-window verification is retired (owner, 2026-11-25)".
- [ ] **Step 3: Commit**
  ```bash
  git add CLAUDE.md docs/PIPELINE.md
  git commit -m "docs: retire visual acceptance and live checks from rules and pipeline"
  ```

### Task 5: Final gates and verification

**Files:** none created; verification only.

- [ ] **Step 1: Full JS gate** (Rust untouched by this cleanup):
  ```bash
  npm --prefix ui run build
  npx --prefix ui vitest run
  ```
  Expected: tsc + vite build green; vitest full suite green.
- [ ] **Step 2: Stale-reference grep** (the Review Focus gate):
  ```bash
  grep -rn "ui/e2e\|design_check\|live_check\|render.mjs\|npm run e2e" CLAUDE.md docs/ .github/ scripts/ ui/package.json 2>/dev/null
  ```
  Expected: zero hits outside `docs/superpowers/` (spec+plan) and the PIPELINE.md §5 "retired" note.
- [ ] **Step 3: Report** — changed files, gate outputs, commit list; suggest next commands (`git status`, optional push on explicit request).
