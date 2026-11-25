//! Viewport anchoring on visibility changes (FUNCTIONAL_SPEC §4 last bullet,
//! bead qt7.3). Pure logic: the table captures an {anchor row, offset} pair
//! before a filter/level change and restores scrollTop so the same anchor row
//! sits at the same viewport position afterwards. The visible sequence is
//! monotonic in line_no, so line→index queries resolve by binary search over
//! 1-row probes (get_rows(i, 1)) without new IPC shapes (contract dsq.3).
//! Scroll-to-row centering (§8) reuses resolveLineIndex + anchorScrollTop.

export const ROW_HEIGHT_PX = 18; // 13px glyph + 3px breathing (mock 97b7ed7);
// lives here so the virtualizer offsets and the CSS `.row` height agree —
// this pure module may compute scroll offsets without importing the table.

/** Resolves the 1-based line_no of visible row i (0-based), or null when the
 *  row is outside the sequence or otherwise unavailable. */
export type LineAt = (i: number) => Promise<number | null>;

/** The identity of the top visible row + how far it sits from the viewport
 *  top (positive above the top edge... negative below); 1-based line_no. */
export interface Anchor {
  line: number;
  offsetPx: number;
}

/** The viewport text-RPC shape (rule 6, qt7.3): scroll state plus the live
 *  anchor - the first visible row's identity and its captured viewport
 *  offset. Assertions in unit tests and e2e read this, never the DOM. */
export interface ViewportInfo {
  scrollTop: number;
  scrollLeft: number;
  anchor: { index: number; line: number } | null;
  anchorOffsetPx: number;
}

/** Captures the anchor from the current layout pass. A null first-row line
 *  (row not yet in the rows cache) yields null: restore then keeps scrollTop
 *  as-is instead of guessing. offsetPx = first row's start (index*ROW) minus
 *  the current scrollTop. */
export function captureAnchor(
  firstVisible: { index: number; line: number | null },
  scrollTop: number,
): Anchor | null {
  if (firstVisible.line === null) {
    return null;
  }
  return {
    line: firstVisible.line,
    offsetPx: firstVisible.index * ROW_HEIGHT_PX - scrollTop,
  };
}

/** §4/§7 (owner bug report, 2026-11-25): with a selection pivot on screen
 *  the anchor row is the pivot — the selected row must not shift when
 *  categories/filters change (the qt7.3 top-row anchor let rows inserted
 *  above the selection push it out of the viewport). An off-screen pivot,
 *  no selection, or a pivot whose row line is unknown anchor the top
 *  visible row exactly as before (qt7.3) — there is nothing visible around
 *  an off-screen anchor to keep in place, and the table must not jump. */
export function anchorForChange(
  top: { index: number; line: number | null },
  pivot: { index: number; line: number | null } | null,
  scrollTop: number,
  viewportPx: number,
): { index: number; anchor: Anchor } | null {
  const offset = pivot === null ? 0 : pivot.index * ROW_HEIGHT_PX - scrollTop;
  const onScreen =
    pivot !== null &&
    pivot.line !== null &&
    offset > -ROW_HEIGHT_PX &&
    offset < viewportPx;
  const chosen = onScreen ? pivot : top;
  const anchor = captureAnchor(chosen, scrollTop);
  return anchor === null ? null : { index: chosen.index, anchor };
}

/**
 * Binary search: the first 0-based visible index whose line_no >= `line`
 * (upper bound). The anchor row hidden by the change therefore lands on the
 * nearest still-visible line AFTER it ("nearest continuation"); only a line
 * beyond the last visible line resolves to null (the caller scrolls to the
 * bottom). Runs in ~log2(count) 1-row probes.
 */
export async function resolveLineIndex(
  line: number,
  count: number,
  lineAt: LineAt,
): Promise<number | null> {
  let lo = 0;
  let hi = count; // exclusive
  while (lo < hi) {
    const mid = lo + Math.floor((hi - lo) / 2);
    const midLine = await lineAt(mid);
    if (midLine === null || midLine < line) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo === count ? null : lo;
}

/** The scrollTop that puts visible row `index` at the anchor's captured
 *  viewport offset, clamped to the scrollable range; a null resolution
 *  (nothing visible at or after the anchor) goes to the bottom. Horizontal
 *  position is not touched - callers must assign scrollTop only (§4). */
export function anchorScrollTop(
  index: number | null,
  anchor: Anchor,
  rowCount: number,
  viewportPx: number,
): number {
  const max = Math.max(0, rowCount * ROW_HEIGHT_PX - viewportPx);
  const target =
    index === null ? max : index * ROW_HEIGHT_PX - anchor.offsetPx;
  return Math.max(0, Math.min(target, max));
}

/**
 * Remaps selected 1-based line numbers into the NEW visible sequence (§4
 * bullet: the selection survives filter changes by line number). Each entry
 * resolves through resolveLineIndex; a hidden row cannot resolve back into
 * the visible-index list (the selection contract is about visible rows), so
 * it is dropped - including entries that would resolve onto the same still-
 * visible row (dedupe). Result: sorted, duplicate-free 0-based indexes.
 */
export async function remapSelection(
  lineNos: number[],
  count: number,
  lineAt: LineAt,
): Promise<number[]> {
  const resolved = new Set<number>();
  for (const line of lineNos) {
    const index = await resolveLineIndex(line, count, lineAt);
    if (index !== null) {
      resolved.add(index);
    }
  }
  return [...resolved].sort((a, b) => a - b);
}
