# qt7.3 — viewport anchor + selection remap: design (final)

Spec: §4 last bullet (filters change: selection preserved by line number;
viewport keeps its position relative to the anchor row — no jump), §8
(scroll-to-match centers the row). Resolution: `get_rows(offset, limit)` now
serves the visible sequence (dsq.3), and the visible sequence is monotonic in
line_no — so any line→visible-index query is resolvable in the UI WITHOUT new
IPC shapes, by binary search over 1-row probes (`get_rows(i, 1)`, ~log2(N)
round trips, each one row).

## New pure module `ui/src/viewportAnchoring.ts` (+ vitest)

```ts
interface Anchor { line: number; offsetPx: number }       // identity = 1-based line_no
captureAnchor(firstVisible: { index: number; line: number | null }, scrollTop: number): Anchor | null
resolveLineIndex(line: number, count: number, lineAt: (i: number) => Promise<number | null>): Promise<number | null>
  // binary search: first index whose line >= target; null only when target > last visible line
anchorScrollTop(index: number | null, anchor: Anchor, rowCount: number, viewportPx: number): number
  // index*ROW - anchor.offsetPx, clamped to [0, count*ROW - viewport]; null -> bottom
remapSelection(lineNos: number[], count: number, lineAt): Promise<number[]>
  // sorted resolve per target, nulls (hidden rows) keep the row selected - keep the entry as line-no
```

Anchor row hidden after the filter change: the binary search lands on the
nearest still-visible line AFTER it (the "nearest continuation" interpretation,
documented); none remaining -> scroll to the bottom.

## LogTable

- Live anchor ref: the existing scroll/render path stores the first virtual
  item's {index, line_no, offsetPx = vi.start - scrollTop} on every layout pass
  (rows not yet in the cache -> line null -> anchor null -> fallback: keep
  scrollTop as-is).
- `visibilityEpoch` layout effect (before the fetch effect): capture from the
  ref, resolve via lineAt (probes cached into the rows Map — valid for the new
  epoch; ChunkPlanner unaffected), set scrollTop only (§4: horizontal position
  untouched by any programmatic scroll — assert scrollLeft stays).
- `fileEpoch` keeps the full reset incl. scrollTop = 0 (§2). No new props.

## Selection remap by line number (§4 bullet) — console side

`uiConsole`: every visibility-mutating action (setLevel, addFilter,
toggleFilter, removeFilter, pins) with a non-empty selection first resolves the
selected indexes' line_nos against the CURRENT (pre-mutation) visible sequence
(cached rows or `get_rows(i, 1)`), sends the mutation, refetches the snapshot,
then binary-searches each line_no in the NEW sequence and dispatches
`{kind: "selection-remap", indexes}` (reducer: replaces selection.indexes,
keeps anchor behavior per selection.ts). Hidden rows keep their place in the
selection list as line-nos are not dropped (they simply do not resolve back;
store nothing for them — the visible-selection contract is about visible rows).
Empty selection: zero extra IPC.

## Text RPC for acceptance (rule 6)

TableHandle/console/`__headless` gain `viewport(): { scrollTop, scrollLeft,
anchor: {index, line} | null, anchorOffsetPx: number }` — assertions in tests
and e2e use this, never DOM poking.

## e2e (rule 4)

- State 17 `anchor-scrolled-refilter.mjs`: stub pre-filtered... stub loads, the
  state script scrolls, toggles a level off via __headless, asserts by numbers
  (viewport().anchor.line unchanged, anchorOffsetPx unchanged) AND commits a
  golden PNG of the held viewport.
- Existing states untouched unless goldens move.

## Not in this bead

- §8 search panel wiring (2wu.1) — only keeps using the same centering helper.
- Perf of probe calls (perf epic; a 20-row selection costs ~460 1-row probes).
