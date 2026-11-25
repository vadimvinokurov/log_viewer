# Token-usage report — mined data draft (sessions)

resolution: superseded by docs/report-01-token-usage.html

Source: 15 top-level Claude Code transcripts in
`~/.claude/projects/-Users-vadimvinokurov-Work-log-viewer2/*.jsonl` (~110 MB)
+ 37 sidechain transcripts under the sessions' `subagents/` dirs (15 MB).
Window: 2026-11-22 22:35 → 2026-11-25 09:38.

## Method and caveats

- "Turn" = one unique assistant API response (`message.id`, deduped across the
  per-block export records of the same response).
- Weighted cost estimate: `cost_units = input + 1.25×cache_creation + 0.1×cache_read
  + 5×output`. **Estimate:** the weights are assumed (Anthropic-style), not measured.
- **Backend caveat (material):** all 4,849 turns run on a GLM backend
  (`glm-5.3-flash:cloud`); `cache_creation_input_tokens` = 0 everywhere. Fresh
  `input_tokens` is abnormally high and may absorb what would normally be
  cache-creation traffic. The input-vs-cache split is an estimate.
- All numbers are usage as recorded in the transcripts; actual billing not observable.

## 1. Session ranking by estimated weighted cost (main)

| # | Session | Window (UTC) | h | Turns | Input | Cache-read | Output | Cost units | Cost/h |
|---|---------|--------------|---|-------|-------|-----------|--------|-----------|--------|
| 1 | 9785223c | 11-23 20:15→11-24 05:00 | 8.7 | 561 | 70.7 M | 90.3 M | 96.7 k | 80.2 M | 9.2 M |
| 2 | 3de36a6d | 11-24 05:00→11-24 20:18 | 15.3 | 463 | 36.3 M | 79.9 M | 88.1 k | 44.7 M | 2.9 M |
| 3 | 405193b3 | 11-25 07:42→11-25 08:37 | 0.9 | 233 | 35.6 M | 21.6 M | 21.2 k | 37.8 M | 41.2 M |
| 4 | f3da036d | 11-25 04:57→11-25 06:38 | 1.7 | 346 | 25.1 M | 31.6 M | 48.2 k | 28.5 M | 17.0 M |
| 5 | 0203913a | 11-24 21:15→11-25 04:56 | 7.7 | 345 | 20.6 M | 32.4 M | 50.6 k | 24.1 M | 3.1 M |
| 6 | b3c8e200 | 11-25 06:38→11-25 07:42 | 1.1 | 326 | 13.7 M | 43.9 M | 77.7 k | 18.5 M | 17.3 M |
| 7 | 3767803b | 11-24 20:21→11-24 21:14 | 0.9 | 220 | 8.0 M | 14.0 M | 23.3 k | 9.5 M | 10.8 M |
| 8 | c5dcb43a | 11-23 20:02→11-23 20:11 | 0.2 | 63 | 5.6 M | 3.7 M | 7.6 k | 6.0 M | 40.1 M |
| 9 | b328d145 | 11-23 16:23→11-23 20:02 | 3.7 | 117 | 4.1 M | 7.4 M | 27.9 k | 5.0 M | 1.4 M |
| 10 | c07fb80d | 11-25 08:38→11-25 08:49 | 0.2 | 99 | 2.8 M | 5.2 M | 15.8 k | 3.4 M | 20.0 M |
| 11 | 30b13d1a | 11-25 08:49→11-25 09:26 | 0.6 | 126 | 2.5 M | 6.5 M | 15.9 k | 3.3 M | 5.3 M |
| 12 | 9744c6c1 | 11-22 22:35→11-22 22:40 | 0.1 | 28 | 1.9 M | 1.1 M | 2.2 k | 2.0 M | 24.2 M |
| 13 | e8dc6629 | 11-25 09:30→11-25 09:38 | 0.1 | 14 | 0.25 M | 0.30 M | 2.4 k | 0.29 M | 2.3 M |
| 14 | d81195a0 | 11-23 20:12→11-23 20:15 | 0.1 | 16 | 0.11 M | 0.44 M | 3.4 k | 0.17 M | 3.2 M |
| 15 | b06a7fff | 11-24 21:14→11-24 21:14 | 0.0 | 0 | 0 | 0 | 0 | 0 | — |

Top 5 sessions carry 74% of weighted cost, top 3 carry 49%. `b06a7fff` is a
292 KB transcript with zero assistant responses (aborted before the first turn).

## 2. Subagents vs main

| Slice | Files | Turns | Input | Cache-read | Output | Cost units | Share |
|-------|-------|-------|-------|-----------|--------|-----------|-------|
| Main | 15 | 2,957 | 227.2 M | 338.2 M | 481 k | 263.5 M | 79.3% |
| Subagents | 37 | 1,892 | 54.6 M | 118.1 M | 489 k | 68.8 M | 20.7% |
| Total | 52 | 4,849 | 281.8 M | 456.3 M | 970 k | 332.3 M | 100% |

Subagents: ~39% of turns but ~50% of all output tokens — ≈2× the work per turn
(258 vs 163 output tokens/turn).

Cost per parent session (top): `3de36a6d` 16 subs / 1,393 turns / 58.8 M;
`9785223c` 11 / 377 / 7.5 M; `c07fb80d` 2 / 41 / 1.0 M; `e8dc6629` 3 / 40 / 0.6 M;
`0203913a` 3 / 29 / 0.6 M; `b3c8e200` 2 / 12 / 0.3 M.

Biggest single subagent: `3de36a6d` child, 233 turns, 12.5 M input, 29.0 M
cache-read, 15.8 M cost units — bigger than complete sessions #7–#10 combined.

## 3. Tool-call profile

| Tool | Main | Subs | Total |
|------|------|------|-------|
| Bash | 1,762 | 1,103 | 2,865 |
| Edit | 613 | 630 | 1,243 |
| Read | 270 | 405 | 675 |
| Write | 99 | 78 | 177 |
| Skill | 48 | 13 | 61 |
| Agent spawn | 37 | — | 37 |
| Playwright screenshot/navigate/evaluate | 73 | — | 73 |
| ToolSearch | 22 | 5 | 27 |
| SendMessage/TaskStop/Monitor/ScheduleWakeup | 42 | 6 | 48 |
| Artifact | 5 | — | 5 |

Bash + Edit ≈ 73% of all tool calls.
Gate/test Bash calls (`vitest run|cargo test|npm run build|npm run e2e|clippy`)
across main sessions: ~397. Heaviest: 9785223c 117 (48 cargo, 29 build, 28 vitest,
10 clippy), f3da036d 57, 3de36a6d 44, b3c8e200 42, 0203913a 42.
Each result re-enters the replaying context of a long session.

## 4. Largest tool results per session (bytes ≈ chars / base64)

- **9785223c** (25 PNG reads, 4.5 MB): Read /tmp/lv_live_final.png 625,892;
  ui_table_top.png 490,656; /tmp/lv_dialog4.png 401,492; lv_dialog2.png 401,480;
  lv_dialog3.png 401,440; lv_real_load.png 388,084; ui_table_deep3.png 387,252;
  goldens loaded-scrolled 365,588; 14-selection-menu 268,024; 13-selection 261,492.
- **3de36a6d** (text-only): beads export diff 22,986; live_check.mjs 12,161;
  LogTable.tsx 11,023; driver.rs 9,320; uiConsole.ts 5,986; spec §4+§8 extract 5,050.
- **405193b3** (Playwright-heavy, 4.8 MB): golden light-loaded.png 439,272 (+353,724
  repeat); 5× Playwright screenshots 315–422 KB each; goldens loaded 352,628,
  light-panel-categories 346,460.
- **f3da036d** (13 PNG reads, 1.7 MB): golden loaded.png read **6 times**
  (281,452 … 277,056 = 1.67 MB), then /tmp/top_new.png 26,636 etc.
- **0203913a**: icons/128x128.png 14,748; cmdline.ts 9,388; lib.rs 5,406; STACK.md 5,126;
  uiConsole.ts 5,025 + repeat 3,965; 4 Bash dumps ≤ 7 KB.
- **b3c8e200**: golden column-overflow.png 279,276; settings.rs 30,834;
  LogTable.tsx 25,849; 7 more ≤ 10.9 KB.
- **3767803b**: ipc.rs 12,617 + 5,872 + 4,272 (read 3×); uiConsole.test.ts 5,638;
  uiConsole.ts 5,609; beads diff 5,594; driver.rs 4,480; live_check.mjs 4,141+3,901.
- **c5dcb43a** (6 PNGs, 1.8 MB): ui-light.png 370,064; ui-dark.png 363,592;
  cat-right.png 342,780; cat-panels.png 293,240 + repeat 149,264; cat-default 287,856.
- **b328d145**: FUNCTIONAL_SPEC.md 33,484; beads ref 4,449; 7 small Bash section peeks.
- **c07fb80d**: golden panel-categories.png 426,472; categories.ts 12,044;
  CategoriesTab.tsx 7,781.
- **30b13d1a**: CategoriesTab.test.tsx 10,353; categories.ts 9,567;
  CategoriesTab.tsx 7,522; beads export noise 7,022.
- **9744c6c1**: ui_light.png 310,632; ui_light2.png 298,748; ui_dark2.png 294,004;
  FUNCTIONAL_SPEC.md 33,484 + _2.md 27,026.
- **d81195a0 / e8dc6629**: max 8.2 KB.

Images: **26 image results, 14.5 MB base64, 58 Read calls on .png/.jpg** in main
sessions. Estimate: ≈ 10–13 MB pixel data ≈ 4–6 M token-equivalents.

## 5. Degenerate loops (3+ consecutive same-tool/same-target)

Total: **359 calls** (~10.9% of all main-session tool calls). Worst offenders:

| Session | Run | Tool | Repetition |
|---------|-----|------|-----------|
| b328d145 | 24× +9× +5× +3×… | Edit | docs/FUNCTIONAL_SPEC.html (59 loop calls) |
| 405193b3 | 23× | Edit | docs/UI_DESIGN.html |
| 405193b3 | 14× | Edit | ui/src/index.css |
| 405193b3 | 13× | Bash | identical `git -C … show origin/…` |
| 3de36a6d | 27× | Bash | identical live_check wrapper; 14× python3 heredoc edit of live_check.mjs |
| 9785223c | 7× | Bash | python3 heredoc vs scripts/design_check.mjs; 6× osascript; 6× `cargo tauri dev` |
| b3c8e200 | 7× 7× 5× 5× | Edit | uiConsole.ts, LogTable.tsx, state.ts, index.css (53 loop calls) |
| c5dcb43a | 12× 9× 6× 4× | Edit | docs/UI_DESIGN.html (34 loop calls in 0.2 h) |
| 9744c6c1 | 8× | Edit | design/ui_concept.html |
| f3da036d | 6× | Read | same golden loaded.png |
| 9785223c | 4× 4× 4× 4× | Edit | state.ts, LogTable.tsx, App.tsx, logviewer-core |

The 9785223c/3de36a6d heredoc-escape loops are the pattern rule 7 banned; the
b328d145/405193b3/c5dcb43a doc-edit Edit chains are the same pattern one tool over.

## 6. Recurring cost patterns, ranked

| Rank | Pattern | Footprint |
|------|---------|-----------|
| 1 | Fresh non-cache input re-sent per turn | 281.8 M tokens; 95 k/turn avg; 153 k/turn worst (405193b3); 84.8% of est. cost. May absorb cache writes (backend caveat). |
| 2 | Conversation replay (cache-read) | 456.3 M tokens; 161 k/turn in 9785223c; the "long-turns replay tail" lever. |
| 3 | Output | 970 k tokens (~0.9 k/turn); 1.5% of est. cost — cost is 100% input-side. |
| 4 | Image tool results | 26 results, 14.5 MB base64; incl. duplicate golden re-reads. |
| 5 | Degenerate loops | 359 calls; worst 27× identical Bash; 53–59 loop calls/session in b328d145, b3c8e200. |
| 6 | Repeated gate runs | ~397 test/build calls; many identical repeats (27× live_check wrapper, 13× same git show). |
| 7 | Same-file re-reads | ipc.rs 3×, uiConsole.ts 3–4×, golden loaded.png 6×. |

## 7. Headline aggregates

- **281.8 M input + 456.3 M cache-read + 970 k output** tokens; 4,849 responses;
  52 transcripts; est. weighted cost **332 M units**.
- Main vs subagents: 79% / 21% of est. cost.
- Average main turn: ≈ 77 k input + 114 k cache-read ≈ **191 k tokens read per
  assistant response** before tool results.
