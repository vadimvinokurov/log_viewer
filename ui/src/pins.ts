//! Pure pin logic (FUNCTIONAL_SPEC §12 + §4 menu presence, q1f.1). No React
//! here: PinnedTab.tsx renders, this module defines the canonical command
//! strings and the context-menu availability evaluation over the snapshot's
//! pin list. The item shape reuses the filters canonicalizer's (the IPC
//! adapter normalizes both to the same FilterItem).

import { type FilterItem, type FilterMode } from "./filtersTab";

export type PinItem = FilterItem;
export type PinMode = FilterMode;

/** Command prefix per pin mode (§12: p / pr / ps / pn N). */
const PIN_PREFIX: Record<PinMode, string> = {
  plain: ":p ",
  regex: ":pr ",
  simple: ":ps ",
  lineno: ":pn ",
};

/** Canonical command string that created the pin, e.g. `:pn 5`. */
export function pinCommand(item: PinItem): string {
  return PIN_PREFIX[item.mode] + item.pattern;
}

/** A selected row as the menu evaluation sees it: its 1-based line number
 *  and cached raw text (broad pins match the raw line, §12). */
export interface SelectedRow {
  line: number;
  raw: string;
}

/** Menu availability result, §4 interpretation): Pin is
 *  available while at least one selected row is NOT pinned, Unpin when at
 *  least one IS; exactPinIds names the exact-row pins covering the
 *  selection (Unpin removes only those). */
export interface PinMenuState {
  canPin: boolean;
  canUnpin: boolean;
  exactPinIds: number[];
}

/** Disabled pins are inert: an off rule pins nothing (§12 the checkbox
 *  turns the pin's action on/off). // spec interpretation */
function active(pins: readonly PinItem[]): PinItem[] {
  return pins.filter((p) => p.enabled);
}

/** Whether one active pin covers one selected row.
 *  - lineno (exact-row): the pattern parses to the row's line number.
 *  - plain / regex (broad): the pattern matches the row's cached raw text;
 *    an invalid regex covers nothing (backend contract for patterns).
 *  - simple: NOT evaluated UI-side (the simple engine is Rust-side) - it
 *    neither pins a row for the menu nor enables Unpin (documented
 *    limitation). */
function pinCoversRow(pin: PinItem, selected: SelectedRow): boolean {
  if (pin.mode === "lineno") {
    return /^\d+$/.test(pin.pattern.trim()) && Number(pin.pattern.trim()) === selected.line;
  }
  if (pin.mode === "plain") {
    return selected.raw.includes(pin.pattern);
  }
  if (pin.mode === "regex") {
    try {
      return new RegExp(pin.pattern).test(selected.raw);
    } catch {
      return false;
    }
  }
  return false; // simple: not evaluated (see above)
}

/** Ids of the enabled exact-row (lineno) pins whose line number is among
 *  `lines`, deduplicated in snapshot order. The menu's Unpin removes ONLY
 *  these - broad rules stay (per-one removal goes through the panel). */
export function exactPinIdsCovering(
  pins: readonly PinItem[],
  lines: readonly number[],
): number[] {
  const ids = new Set<number>();
  for (const pin of active(pins)) {
    if (pin.mode !== "lineno") {
      continue;
    }
    const trimmed = pin.pattern.trim();
    if (!/^\d+$/.test(trimmed)) {
      continue;
    }
    const line = Number(trimmed);
    if (lines.includes(line)) {
      ids.add(pin.id);
    }
  }
  return [...ids];
}

/** §4 menu presence over the current selection : evaluates the
 *  snapshot's pin list UI-side against the selected rows. */
export function pinMenuState(
  pins: readonly PinItem[],
  selectedRows: readonly SelectedRow[],
): PinMenuState {
  if (selectedRows.length === 0) {
    return { canPin: false, canUnpin: false, exactPinIds: [] };
  }
  const evaluating = active(pins).filter((p) => p.mode !== "simple");
  const covered = selectedRows.map((selected) =>
    evaluating.some((pin) => pinCoversRow(pin, selected)),
  );
  return {
    canPin: covered.some((c) => !c),
    canUnpin: covered.some(Boolean),
    exactPinIds: exactPinIdsCovering(pins, selectedRows.map((r) => r.line)),
  };
}
