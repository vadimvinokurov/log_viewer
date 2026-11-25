# Design: category toggle flicker — stale-while-revalidate table refill

Owner bug report, 2026-11-25: with category `redstone` checked and line ~123187 on screen,
toggling the `script` category flashes the whole table empty on every toggle, even when the
on-screen row composition is unchanged.

## Intent

A visibility change (categories / filters / levels / pins / highlights — all share the
`visibilityEpoch` path) must never blank the log table. Updates apply quietly.

## Root cause (verified)

- `ui/src/LogTable.tsx:203-209` — a `useLayoutEffect` keyed on `[visibilityEpoch]` synchronously
  wipes the rows/spans maps; until the first `get_rows` chunk resolves, every on-screen cell
  renders as an empty string and the level tint disappears.
- `ui/src/LogTable.tsx:252-279` — anchor restore runs on every epoch bump and resolves the anchor
  with ~17–21 sequential awaited 1-row IPC probes (`viewportAnchoring.ts:90-107`), each committing
  a React render while the viewport is mostly blank.
- Backend walk latency (`src-tauri/src/ipc.rs:275-293`) opens the time window in which the blank
  state is visible rather than sub-frame.
- Prior symptomatic fix (fetch on-screen chunks first, `table.ts:31-68`) removed one of two blank
  round trips but left the wipe itself in place — the wipe is the bug.

## Goals

- No empty/blank paint of on-screen rows on any `visibilityEpoch` bump.
- On-screen chunks refill first (keep the existing prioritized fetch order).
- Reduce the anchor-restore commit storm.

## Non-goals

- No backend re-walk optimization (full-file walk per toggle stays for now).
- No composition-fingerprint fast-path (option B) — possible later addition, must not be needed for this fix.
- UI visual acceptance stays retired (owner, 2026-11-25); headless tests only.

## Approaches

- **A — stale-while-revalidate (chosen).** Keep painted rows across epoch transitions; replace
  content per chunk as it arrives. Kills the blank state for all toggles, not just no-op ones.
- **B — backend composition fingerprint fast-path (rejected as primary).** Only toggles that
  change nothing visible would skip the wipe; the reported `script` toggle changes the visible
  sequence globally, so the wipe would remain.
- **Symptomatic masking (spinner / dim-on-stale / more ordering) — rejected.** The 2026-11-25
  ordering fix already proved partial fixes don't close the flash; data removal must not happen
  at all.

## Design

1. The epoch `useLayoutEffect` keeps `rows`/`spans` intact; it only invalidates the fetch planner
   (requeue on-screen chunks first, then the rest) and picks up the new `visibleCount`.
2. Every resolved chunk overwrites exactly its index range in the maps (data served from the new
   snapshot's sequence, so overwritten regions are authoritative). Unfetched regions may briefly
   show stale rows — accepted trade-off over emptiness.
3. Anchor restore runs only when the anchor can actually move (visible composition / rowCount
   changed); when it runs, probes fetch windows (`get_rows(mid, 2K+1)`) instead of single rows to
   cut the sequential probe count.
   *(Amendment, task 3, 2026-11-25: windowed probes superseded by the skip-gate
   `anchorUnchanged(lineAt(captured.index), anchor.line)` — at most one probe instead of
   ~log2(count) when the row at the captured index still carries the anchor line. Windowed
   probing would complicate the shared `resolveLineIndex` search used by selection remap for
   no further gain, since the gate already collapses the unchanged-composition case, which is
   the owner's reported scenario, to a single probe.)*
4. Level tint keeps deriving from painted row data, so it stays continuous through refill.

## Acceptance (headless-first, numbers not screenshots)

- Vitest (pure logic): after an epoch bump the rows map is not cleared; chunk apply replaces only
  its index range; anchor probing is batched/skipped per rule 3.
- Via `window.__headless`: apply a category toggle while rows are on screen — the on-screen
  painted-row count must never pass through 0 between snapshots; after refill the visible line
  numbers match the expected visible sequence.
- Anchor: after a toggle that does not move the anchor, the anchor line stays in the same viewport
  position with no (or ≤1 batched) probe round trips.

## Left to the builder

- Exact planner invalidation API shape.
- Whether stale off-screen rows get dimmed (default: no dimming).
- Where probe-window batching lives (`viewportAnchoring.ts`).
