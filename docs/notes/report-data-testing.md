# Report data — testing inventory (from mining agent, 2026-11-25)

resolution: superseded by docs/report-03-testing.html

## Testing layer inventory (log_viewer2)

| Layer | Size | Value |
|---|---|---|
| 1. Rust core unit tests (in-crate `#[cfg(test)]`, TDD) | 8 src files, 127 cases (parser 31, visibility 20, simple_query 21, highlights 15, settings 15, matching 14, categories 7, workspace 3, lib 1) | Load-bearing |
| 2. Parser/scanner golden fixtures (committed synthetic) | `crates/logviewer-core/tests/fixtures/` — 9 .log files; scanner_golden 8 tests, settings_golden 5 (temp dirs); scanner_big 1 `#[ignore]`d perf smoke over real test_logs | Load-bearing |
| 3. Dual-path oracle (naive vs optimized) | visibility.rs naive walk + naive category-allowed; scanner offsets naive; ~4 equivalence tests | Load-bearing but narrow (3 algorithms only; regex/fancy-regex fallback not oracled) |
| 4. Tauri shell Rust tests | src-tauri: ipc.rs 31, driver.rs 7, lib.rs 2 — real async IPC wrappers; cargo test regenerates specta bindings | Load-bearing |
| 5. Headless text RPC `window.__headless` (ui/src/headless.ts) | ~45 actions/snapshots; uiConsole.test.ts 106 cases | Keystone — visual harness, component data, and live driver all ride on it |
| 6. Pure TS vitest units | 12 `.test.ts` files, 226 cases (state 45, categories 35, cmdline 22, selection 21, viewportAnchoring 18, …) | Load-bearing |
| 7. Component vitest (testing-library) | 7 `.test.tsx`, 55 cases | Marginal-to-useful (thin components; partly redundant with 5+8) |
| 8. Golden-PNG visual acceptance | ui/e2e/render.mjs (152 lines), 19 state generators → 43 states, 43 goldens, 1400×900 headless Chrome, IPC stubbed per state, pixelmatch, `--update-goldens`; 9 documented rebaselines | Load-bearing; CI runs it on macos-latest (mac Chrome capture platform) |
| 9. Design oracle (docs/UI_DESIGN.html vs app `?show=`) | scripts/design_check.mjs, 3 element pairs, threshold 5 % | Marginal — only 3 of ~10 elements, not in npm scripts/CI |
| 10. Live real-window driver | scripts/live_check.mjs (738 lines) + native driver server (driver.rs); numbers-only assertions, no-retry semantics; real test_logs file through real IPC | Load-bearing but **trimmed**: 14 named checks cover only pins (h), highlights (i), cmdline (j); older milestone flows lost |
| 11. Criterion benchmarks over real corpus | benches/corpus.rs (skips if test_logs absent) + BENCHMARKS.md baselines (big: visibility 154→75.7 ms) | Valuable, but **no regression gate** |
| 12. CI parity (release.yml) | gate (ubuntu): cargo test workspace + tsc -b build + vitest; goldens job (macOS); build mac-univ + win-NSIS | Good; missing: oxlint, design oracle, benchmarks |

## Top gaps

1. No parser fuzzing/property testing (§3 disambiguation guarded by fixed fixtures only).
2. No benchmark regression threshold; benches can't run in CI (needs uncommitted test_logs).
3. Live-check drift: milestone scenarios are replaced, not accumulated — verified older flows have no persistent named checks.
4. Design oracle coverage decay (3 pairs, no gate wiring).
5. No accessibility testing (aria exists incidentally; no axe, no tab-order).
6. Golden maintenance cost: any whole-app restyle re-baselines all 43; local Chrome-version/font drift is an unowned flake source.
7. Loading/error visual states barely covered (only cmdline error, `error.png`).

## Top skill recommendations for vvv-claude-kit

1. **headless-text-rpc** — capability first in `__headless`, same reducer for test actions, boundary-arg coercion, stub shapes mirror raw IPC, new state + uiConsole case before markup.
2. **golden-rebaseline** — read diff % first; `--update-goldens` only for intended changes with written per-state before/after; 0.000 % diffs mean logic moved; rebaseline note is part of the task.
3. **live-check** — milestone rule: `cargo tauri dev` + live_check.mjs; numbers-only assertions; extend the named-check list permanently; no retries on mutating batches.
4. **dual-path-oracle** — every optimization ships a naive reference + `*_matches_the_naive_reference` equivalence test, kept permanently; record before/after factors in BENCHMARKS.md.
5. **design-oracle** (extend ui-development) — every design frame gets a `?show=` variant + PAIRS entry; run before closing visual tasks.
6. **benchmark-gates** — scoped criterion runs with `--baseline prev`; no perf claims without a table row; groups must skip cleanly without test_logs.
