# Drop visual tests, goldens, and live checks

Date: 2026-11-25 · Status: approved (owner)

## Intent

The UI is stable and no longer under active development. Visual acceptance
(golden PNG pixel-diff) and real-window live verification are dropped from the
project and the pipeline. `docs/UI_DESIGN.html` stays in the repo as a passive
reference document ("just in case"); it is no longer used by any automated check.

## Goals

- Remove all golden-PNG / pixel-diff testing from the repo and CI/release gates.
- Remove live-window verification entirely.
- Update project rules and docs so no rule or gate references the removed
  machinery.

## Non-goals

- Unit/logic tests are untouched: `ui/src/headless.ts` (text RPC,
  `window.__headless`) and `ui/src/uiConsole.test.ts` stay — they are vitest
  logic tests on state snapshots, not visual tests.
- Core (Rust) tests, lints, `npm run build`, vitest suite — all stay in gates.
- No beads/Dolt sync changes.

## Anti-goal

- Keeping a "dormant" copy of the harness in the repo. Git history preserves
  everything; the working tree should not carry dead test machinery.

## What gets removed

- `ui/e2e/` entirely: `render.mjs`, `states/*.mjs`, `goldens/` (43 PNGs),
  showcase PNGs, `design/` pairs.
- `scripts/design_check.mjs` (pixel diff of showcases vs `docs/UI_DESIGN.html`)
  and `scripts/live_check.mjs` (real-window driver). Owner confirmed both.
- The `e2e` script in `ui/package.json`.
- The `npm --prefix ui run e2e` step in `release_gates.sh`.
- The `goldens` job in `.github/workflows/release.yml` (and its `needs` wiring).
- Rules/docs updates: CLAUDE.md (rules 3 exception note, 4 PNG bullet, 5 live
  checks, 7 e2e/design-oracle mentions, 9 e2e in release gates),
  `docs/PIPELINE.md` (§5 visual acceptance, §6a golden step, golden history
  bullets stay as history but marked as retired).

## Kept

- `docs/UI_DESIGN.html` — passive document, no script consumes it.
- `window.__headless` text RPC + `uiConsole.test.ts` — logic testing continues
  in vitest.
- `release_gates.sh` keeps `cargo test --workspace`, `npm run build`, full
  `npx vitest run`; those are the release evidence.

## Approaches considered

1. **Delete everything visual (chosen)** — working tree carries no dead code;
   history is the safety net.
2. Disable in pipeline but keep harness in repo — rejected: dead code with
   running cost every `bd`/gate reading, contradicts the owner's "drop from
   the project".
3. Keep design oracle, drop goldens — rejected by owner: UI no longer changes,
   the doc stays as reference alone.

## Open to the builder

- Exact wording of CLAUDE.md rewrites (keep the owner-decision dates).
- Whether PIPELINE.md golden-history bullets are moved under a "retired"
  section vs trimmed — prefer a short "retired" note over full deletion, so
  the history of decisions stays readable.
