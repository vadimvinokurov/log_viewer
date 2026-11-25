# Category-toggle flicker — stale-while-revalidate table refill: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kill the full-table blank flash on any visibility epoch change (categories, filters, levels, pins): the `LogTable` row cache survives epoch bumps (stale-while-revalidate), while every read that needs the *current* visible sequence reads only current-epoch entries.

**Architecture:** Row-cache entries become visibility-epoch-stamped (`{row, epoch}`). Painted render reads any-epoch entries (stale rows show until the on-screen chunks refetch — never blank). Probe/copy/anchor-capture reads are epoch-gated "current-truth" reads, so anchoring and copy stay correct against the new sequence. The anchor binary search is skipped when the row at the captured anchor index still carries the anchor line (composition unchanged at the anchor ⇒ keeping scrollTop is exact).

**Tech stack:** React 18 + @tanstack/react-virtual, Vitest + RTL in jsdom, TypeScript strict (tsc -b).

**Spec:** `docs/superpowers/specs/2026-11-25-category-toggle-flicker-design.md` — implements §Design items 1, 2, 4 and the skip part of item 3; item 3's windowed probes are superseded by the skip-gate (amended in Task 3).

## Global constraints

- Gates from `ui/`: scoped `npx vitest run src/<file>.test.ts` while iterating; full `npx vitest run` + `npm run build` before every commit.
- Pure logic in pure modules with vitest tests; components only wire (rule 4).
- No `test_logs/` content in any file (rule 1) — synthetic fixtures only.
- English project files and commits; commits end with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

## Review Focus (pinned by tests in Task 3 unless named)

1. Two rapid back-to-back epoch bumps — rows never render empty; a late-resolving OLD-epoch chunk must not overwrite NEW-epoch content (in-flight chunk epoch-drop stays). Test: "two bumps with deferred chunks".
2. Visibility change emptying the sequence (rowCount → 0): no rows render, no crash. Test: Task 3.
3. Equal-count composition change at the anchor: the skip-gate must NOT trigger; the binary search runs. Test: Task 3.
4. Copy mid-refetch never returns old-sequence text (gated resolveRows). Test: Task 3.
5. File switch (fileEpoch) must still fully wipe — retention is visibility-scoped; old-file rows must never appear. Test: Task 3.

## Files

- Modify: `ui/src/table.ts` + `ui/src/table.test.ts` — stamped-cache pure helpers + tests.
- Modify: `ui/src/LogTable.tsx` — stamped state, gated reads, retained maps, anchor skip-gate. The only component touched; App/state/uiConsole/backend untouched.
- Create: `ui/src/LogTable.test.tsx` — first LogTable-level test harness (jsdom, stubbed metrics + deferred IPC stub).

## Task 1 — table.ts: stamped-cache pure helpers

**Files:** modify `ui/src/table.ts`, `ui/src/table.test.ts`.

**Interfaces (exact — static members of `ChunkPlanner`):**

```ts
export interface StampedRow { row: RowDto; epoch: number }
// (module-level type; ChunkPlanner gains two statics:)
static fromChunkStamped(chunk: RawRowDto[], start: number, epoch: number): Map<number, StampedRow>
static currentStamped(
  map: Map<number, StampedRow>, index: number, currentEpoch: number,
): StampedRow | undefined
```

- [ ] **Step 1:** failing tests in `ui/src/table.test.ts`, new describe block
  `"stamped cache helpers (design 2026-11-25-flicker)"` with a local
  `aRawRow(line: number): RawRowDto` builder (`spans: []`, category/level
  fixed strings). Tests:
  1. `stamps entries; painted reads ignore the stamp` — build with epoch 5;
     assert `map.get(2).row.line_no` and `epoch === 5` (entry read is the
     stamped entry itself).
  2. `current-truth read passes only current-epoch entries` — epoch 5 map;
     `currentStamped(map, 2, 5)` returns the entry; `currentStamped(map, 2, 6)`
     returns `undefined`.
  3. `chunk apply replaces a range and restamps` — seed a map with entries
     stamped 4 at indexes 0..9, apply `fromChunkStamped(chunk(10), 0, 7)`;
     assert all 0..9 stamped 7 and old rows replaced.
- [ ] **Step 2:** `npx vitest run src/table.test.ts` → 3 FAIL
  ("fromChunkStamped is not a function" or TS error).
- [ ] **Step 3:** implement the two statics + `StampedRow` in `ui/src/table.ts`
  (reuse `ChunkPlanner.toRow`; `currentStamped` is a stamp equality check).
- [ ] **Step 4:** `npx vitest run src/table.test.ts` → PASS.
- [ ] **Step 5:** full gates (`npx vitest run`, `npm run build`) and commit:
  `feat(ui): visibility-stamped row cache helpers (table.ts)`

## Task 2 — LogTable: stamped cache + gated reads (behavior-preserving refactor)

The visibility-epoch wipe of rows/spans stays in this task; every commit must
keep the app coherent. The stamped shape and the read gates land first so
Task 3 stays a two-line behavior change.

**Files:** modify `ui/src/LogTable.tsx`; create `ui/src/LogTable.test.tsx`.

**Wiring decisions (each is a fixed call):**

- Row state type: `Map<number, StampedRow>`; every write stamps with the
  current visibility epoch (`epochsRef.current.visibility`; in `lineAt` the
  probe cache uses `epochAtCall.visibility`). Chunk applies in the fetch loop
  merge `fromChunkStamped` output; `ChunkPlanner.toRow` stays for `lineAt`.
- Gated "current-truth" reads go through `ChunkPlanner.currentStamped(map, i,
  epochsRef.current.visibility)`:
  - the `lineAt` cache read;
  - `resolveRows` (copy + pin menu): merged map built from gated entries
    only, `missingRanges` over the gated key set, fetches fill the gaps;
  - the live-anchor capture and the pivot-line check (`selection.anchor`
    row): stale entries read as `line: null` (restore then keeps scrollTop).
- Ungated painted reads: the render map (`rows.get(vi.index)?.row` in the
  row class and all four cells, `renderMessage`) — stale-while-revalidate
  display; the level tint derives from the painted row, so it stays.
- The visibility-epoch wipe of rows/spans stays as-is in this task.

**Harness recipe (LogTable.test.tsx):** jsdom has no layout, so the harness
stubs what @tanstack/react-virtual reads: stub `ResizeObserver` via
`vi.stubGlobal` with a class whose `observe` stores the callback (notify
manually); define `clientHeight`, `clientWidth`, `scrollHeight` and
`getBoundingClientRect` on the `.table-scroll` element with defineProperty.
IPC: `vi.mock("./ipcClient")` with deferred promises the test resolves
manually. Fixtures: `aRawRow(line)` per Task 1 plus `spans: []`. The test
contract: with row height 18 and clientHeight 18*N, the rendered `.row`
elements show that many line numbers. If metrics do not flow into the
virtualizer under the installed @tanstack/react-virtual version, adapt the
metrics flow to its node_modules source (timebox ~30 min) — the behavior
tests below are the contract, not the harness mechanics. Known-fragile
point, flagged and timeboxed.

- [ ] **Step 1:** create `ui/src/LogTable.test.tsx` with the harness recipe
  plus two baseline tests pinning CURRENT behavior (green before refactor):
  1. `rows appear after the covering chunk lands` — viewport height 18*5,
     resolve the deferred chunk covering the visible range, assert the
     `.cell-line` texts are the chunk's line numbers.
  2. `copy resolves the selection's rows` — mount with selection
     `{selected: [0], anchor: 0}` and ref handle; `await ref.copy("raw")`
     returns the raw text of the IPC-served rows in index order.
- [ ] **Step 2:** `npx vitest run src/LogTable.test.tsx` → PASS (baseline).
- [ ] **Step 3:** apply the wiring decisions above; scoped test stays green.
- [ ] **Step 4:** full gates and commit:
  `refactor(ui): LogTable rows cache is visibility-stamped with gated reads`

## Task 3 — the fix: retain rows across visibility epochs + anchor skip-gate

**Files:** modify `ui/src/LogTable.tsx`, `ui/src/LogTable.test.tsx`,
`ui/src/viewportAnchoring.test.ts` optional;
design-doc amendment in
`docs/superpowers/specs/2026-11-25-category-toggle-flicker-design.md`.

**Interfaces (exact):**

```ts
// viewportAnchoring.ts — decision helper, testable without React:
/** True when the restore can be skipped entirely: the row at the captured
 *  anchor index still carries the anchor line, so keeping scrollTop keeps
 *  the anchor row at its captured offset (composition unchanged there). */
export function anchorUnchanged(lineAtAnchorIndex: number | null, anchorLine: number): boolean;
```

- [ ] **Step 1 (RED):** component tests in LogTable.test.tsx (deferred IPC):
  1. `cells keep old text through a visibility bump until the new chunk lands`
     — mount, load initial chunks (lines 1..N); queue NEW chunks for epoch 2
     as deferred promises; rerender with `{visibilityEpoch: 2}`; BEFORE
     resolving: all visible `.cell-line` texts still equal the old lines
     (under the wipe they render "" — RED); resolve; assert the new lines.
  2. `two bumps with deferred chunks` — epoch 2 deferred, epoch 3 deferred;
     resolve both in arrival order... assert: after epoch 3's chunks land,
     cells show epoch-3 lines even though epoch-2's deferred chunks resolved
     after (epoch drop keeps them from overwriting).
  3. `rowCount -> 0 rerender` — `{rowCount: 0, visibilityEpoch: +1}` — no
     rows, no crash, viewport() anchor null.
  4. `anchor skip-gate keeps scrollTop and skips the probe storm` — after
     initial load, rerender epoch+1 with IDENTICAL chunk data (composition
     unchanged): assert getRows call count during the transition is <= 2
     (gate probe at most; under the storm it is >= log2(count)) and the
     viewport() scrollTop/anchor are unchanged.
  5. `anchor restore runs on equal-count composition change` — epoch+1,
     same rowCount, different line at the captured anchor index: getRows
     calls >= log2(count) (the search runs) and the anchor line resolves to
     the new sequence row carrying that line (nearest continuation).
  6. `copy mid-refetch returns the new sequence` — selection on index 0;
     rerender epoch+1 with new-sequence deferred chunks; BEFORE resolving,
     `copy("raw")` must NOT resolve to the old raw text; after resolving the
     copy-driven fetch, it returns the new-sequence raw line.
  7. `fileEpoch bump still wipes` — rerender `{fileEpoch: +1, rowCount:
     same}` with deferred new-file chunks: BEFORE resolving, cells are empty
     (old-file rows must never show); after resolving, new-file lines.
- [ ] **Step 2:** `npx vitest run src/LogTable.test.tsx` → tests 1, 2, 4 FAIL
  (wipe blanks; storm probes); 3, 6, 7 may pass already — keep them as
  regression pins.
- [ ] **Step 3 (GREEN):**
  - epoch effect on `[visibilityEpoch]`: keep `plannerRef.current.reset()` +
    `inFlightRef.current = false`; REMOVE the rows/spans wipe (rowsRef
    mirror comment updated: the mirror tracks painted data of any epoch).
  - anchor restore effect: before `resolveLineIndex`,
    `if (anchorUnchanged(await lineAt(captured.index), captured.anchor.line)) return;`
    (when `captured.index >= rowCount`, lineAt probes and returns null ->
    the gate falls through to the full search).
  - `renderMessage`/render stays (stamped unwrap already landed in Task 2).
- [ ] **Step 4:** unit test for `anchorUnchanged` in viewportAnchoring.test.ts
  (line equal -> true; null -> false; different -> false); run scoped.
- [ ] **Step 5:** full gates (`npx vitest run`, `npm run build`).
- [ ] **Step 6:** append the amendment to the design doc §Design item 3:
  windowed probes superseded by the skip-gate
  (`anchorUnchanged(lineAt(captured.index), anchor.line)` — one probe at
  most instead of ~log2(count); windowed probing would complicate the
  shared search used by selection remap for no further gain).
- [ ] **Step 7:** commit: `fix(ui): table keeps painted rows across epochs, anchor skips unchanged restores`

## Done when

- All plan checkboxes ticked; Task 3's tests 1, 2, 4 are RED before Step 3
  and GREEN after; the baseline tests stay green throughout.
- Full gates green from `ui/`: `npx vitest run` + `npm run build`.
- The owner's repro no longer blanks: toggle script on/off with redstone on —
  the table paints stale rows while refetching, per-chunk overwrite, anchor
  stable when composition near it is unchanged.
