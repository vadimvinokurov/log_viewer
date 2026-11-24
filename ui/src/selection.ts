//! Row selection model (FUNCTIONAL_SPEC §4): click selects, ctrl/meta-click
//! toggles, shift-click extends from the pivot anchor. Pure logic with no
//! React - the table component applies these transitions to its state; the
//! clipboard helpers produce the text that Ctrl+C / the context menu put on
//! the clipboard (async write happens in the component later).

/** 0-based row indexes, sorted ascending, duplicate-free. */
export interface SelectionState {
  selected: number[];
  anchor: number | null;
}

export const EMPTY_SELECTION: SelectionState = { selected: [], anchor: null };

/** Plain click: exactly row i is selected; i becomes the new anchor.
 * (The previous selection is replaced, so `state` is intentionally unused.) */
export function select(_state: SelectionState, i: number): SelectionState {
  return { selected: [i], anchor: i };
}

/** Ctrl/meta click: add-or-remove row i; it becomes the anchor either way. */
export function toggle(state: SelectionState, i: number): SelectionState {
  const without = state.selected.filter((j) => j !== i);
  const selected =
    without.length === state.selected.length
      ? [...without, i].sort((a, b) => a - b)
      : without;
  return { selected, anchor: i };
}

/** Shift click: the anchor..i span (inclusive), unioned with the existing
 * selection. The anchor stays where it is (§4: the pivot survives repeated
 * shift-clicks); a missing anchor degrades to a plain select. */
export function range(state: SelectionState, i: number): SelectionState {
  if (state.anchor === null) {
    return select(state, i);
  }
  const lo = Math.min(state.anchor, i);
  const hi = Math.max(state.anchor, i);
  const span = new Set<number>();
  for (let j = lo; j <= hi; j++) {
    span.add(j);
  }
  return {
    selected: [...new Set([...state.selected, ...span])].sort((a, b) => a - b),
    anchor: state.anchor,
  };
}

/** Select every row of the table; the anchor is left untouched. */
export function all(state: SelectionState, rowCount: number): SelectionState {
  const selected = Array.from({ length: rowCount }, (_, j) => j);
  return { selected, anchor: state.anchor };
}

/** Ctrl+C / "Copy": the raw file lines of the selected rows, in selection
 * order, joined by \n (§4). */
export function rawCopyText(rows: readonly { raw: string }[]): string {
  return rows.map((row) => row.raw).join("\n");
}

/** "Copy Message": the Message column contents of the selected rows joined
 * by \n. */
export function messageCopyText(rows: readonly { message: string }[]): string {
  return rows.map((row) => row.message).join("\n");
}

/** Fetch ranges a copy needs for rows missing from the cache: consecutive
 * selected rows merge into one contiguous range; a fully cached run is
 * skipped. `selected` is 0-based and sorted; end is exclusive, clamped by
 * `rowCount`. */
export function missingRanges(
  selected: readonly number[],
  rowCount: number,
  cached: ReadonlySet<number>,
): { start: number; end: number }[] {
  const ranges: { start: number; end: number }[] = [];
  let run: number[] = [];
  const flush = (): void => {
    if (run.length && run.some((i) => !cached.has(i))) {
      ranges.push({ start: run[0], end: run[run.length - 1] + 1 });
    }
    run = [];
  };
  for (const i of selected) {
    if (i >= rowCount) {
      continue;
    }
    if (run.length && i === run[run.length - 1] + 1) {
      run.push(i);
    } else {
      flush();
      run = [i];
    }
  }
  flush();
  return ranges;
}
