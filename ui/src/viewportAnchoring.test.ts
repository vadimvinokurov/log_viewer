//! qt7.3 tests: viewport anchoring on filter changes (§4) and selection
//! remapping by line number. Pure logic, no React, no IPC - lineAt is a fake
//! resolver over a monotonic synthetic visible sequence.

import { describe, expect, it } from "vitest";
import {
  ROW_HEIGHT_PX,
  TABLE_HEADER_PX,
  anchorForChange,
  anchorScrollTop,
  anchorUnchanged,
  captureAnchor,
  remapSelection,
  resolveLineIndex,
  type LineAt,
} from "./viewportAnchoring";

/** The design pins the row height (mock 97b7ed7: 13px mono + 3px); the
 *  virtualized offsets and the CSS `.row` heights must be one number. */
describe("ROW_HEIGHT_PX", () => {
  it("matches the 2026-11-25 mock decision: 18px rows", () => {
    expect(ROW_HEIGHT_PX).toBe(18);
  });
});

/** Visible line sequence 10, 20, 30 ... at one row per index. */
function lineSequence(step: number): LineAt {
  return async (i: number) => (i < 0 ? null : (i + 1) * step);
}

describe("captureAnchor", () => {
  it("records the anchor row identity and its offset from the viewport top", () => {
    // offsetPx = first item's start (index * row height) - scrollTop.
    expect(captureAnchor({ index: 100, line: 105 }, 2295)).toEqual({
      line: 105,
      offsetPx: 100 * ROW_HEIGHT_PX - 2295,
    });
  });

  it("returns null while the first row is not in the rows cache (line unknown)", () => {
    expect(captureAnchor({ index: 100, line: null }, 100)).toBeNull();
  });
});

describe("resolveLineIndex", () => {
  it("resolves an exact line to its 0-based index", async () => {
    expect(await resolveLineIndex(30, 5, lineSequence(10))).toBe(2);
  });

  it("resolves the first and the last line", async () => {
    expect(await resolveLineIndex(10, 5, lineSequence(10))).toBe(0);
    expect(await resolveLineIndex(50, 5, lineSequence(10))).toBe(4);
  });

  it("a hidden anchor lands on the nearest still-visible line after it (§4)", async () => {
    // Target 25: line 30 is the first visible line >= 25.
    expect(await resolveLineIndex(25, 5, lineSequence(10))).toBe(2);
    // A line before the first visible row anchors onto row 0.
    expect(await resolveLineIndex(1, 5, lineSequence(10))).toBe(0);
  });

  it("a line beyond the last visible line resolves to null", async () => {
    expect(await resolveLineIndex(55, 5, lineSequence(10))).toBeNull();
    expect(await resolveLineIndex(999, 5, lineSequence(10))).toBeNull();
  });

  it("an empty visible sequence resolves to null", async () => {
    expect(await resolveLineIndex(10, 0, lineSequence(10))).toBeNull();
  });

  it("needs ~log2(count) probes, not a linear scan", async () => {
    let calls = 0;
    const lineAt: LineAt = async (i) => {
      calls++;
      return (i + 1) * 10;
    };
    await resolveLineIndex(10 * 999, 1000, lineAt);
    expect(calls).toBeLessThanOrEqual(11); // ceil(log2(1000 + 1)) = 10
  });

  it("a null probe result past the end yields null instead of hanging", async () => {
    const lineAt: LineAt = async (i: number) => (i < 3 ? (i + 1) * 10 : null);
    expect(await resolveLineIndex(55, 5, lineAt)).toBeNull();
  });
});

describe("anchorScrollTop", () => {
  const anchor = { line: 105, offsetPx: 50 };

  it("puts the resolved anchor row at its captured viewport offset", () => {
    expect(anchorScrollTop(100, anchor, 1000, 900)).toBe(100 * ROW_HEIGHT_PX - 50);
  });

  it("a null resolution (nothing visible after the anchor) scrolls to the bottom", () => {
    // The scroller's content height includes the header row (LogTable renders
    // rows at translateY(start + ROW_HEIGHT_PX) with total += ROW_HEIGHT_PX),
    // so the true bottom is count*ROW + HEADER - viewport; a clamp computed
    // without it left the last content row (a bottom-edge anchor) below the
    // fold (owner repro 2026-11-25).
    const bottom = 1000 * ROW_HEIGHT_PX + TABLE_HEADER_PX - 900;
    expect(anchorScrollTop(null, anchor, 1000, 900)).toBe(bottom);
    // Even the bottom never goes negative on a short table.
    expect(anchorScrollTop(null, anchor, 10, 900)).toBe(0);
  });

  it("clamps into the scrollable range for both ends", () => {
    const bottom = 1000 * ROW_HEIGHT_PX + TABLE_HEADER_PX - 900;
    expect(anchorScrollTop(0, anchor, 1000, 900)).toBe(0);
    const hugeOffset = { line: 105, offsetPx: -100000 };
    expect(anchorScrollTop(50, hugeOffset, 1000, 900)).toBe(bottom);
  });
});

/** §4/§7 (owner bug report, 2026-11-25): with a selection pivot on screen
 *  the anchor is the pivot — the selected row must not shift when filters
 *  or categories change; the qt7.3 top-row anchor let rows inserted above
 *  the selection push it out of the viewport. */
describe("anchorForChange (selection-anchored restore)", () => {
  const top = { index: 100, line: 105 };
  const viewportPx = 900;

  it("an on-screen selection pivot anchors instead of the top row", () => {
    // scrollTop 1500, viewport 1500..2400; pivot index 85 (start 1530) sits
    // 30px below the viewport top — on screen.
    const pivot = { index: 85, line: 71 };
    const live = anchorForChange(top, pivot, 1500, viewportPx);
    expect(live).toEqual({
      index: 85,
      anchor: { line: 71, offsetPx: 85 * ROW_HEIGHT_PX - 1500 },
    });
  });

  it("an off-screen pivot leaves the top-row anchor in charge", () => {
    // Pivot wholly above (offset −1410) and wholly below (+3900): nothing
    // visible around either to preserve.
    expect(anchorForChange(top, { index: 5, line: 6 }, 1500, viewportPx))
      .toEqual({ index: 100, anchor: { line: 105, offsetPx: 300 } });
    expect(anchorForChange(top, { index: 300, line: 95 }, 1500, viewportPx))
      .toEqual({ index: 100, anchor: { line: 105, offsetPx: 300 } });
  });

  it("a pivot row partially visible at the top edge still anchors", () => {
    // Start 9px above the top edge (offset −9 > −ROW): partially drawn row
    // still intersects the viewport, so it anchors.
    const pivot = { index: 100, line: 101 };
    const live = anchorForChange(top, pivot, 1809, viewportPx);
    expect(live?.index).toBe(100);
  });

  it("a pivot whose line is unknown (not in the rows cache) falls back", () => {
    const scrollTop = 100 * ROW_HEIGHT_PX - 300;
    expect(anchorForChange(top, { index: 60, line: null }, scrollTop, viewportPx))
      .toEqual({ index: 100, anchor: { line: 105, offsetPx: 300 } });
  });

  it("no selection (pivot null) is exactly the qt7.3 top-row capture", () => {
    const scrollTop = 100 * ROW_HEIGHT_PX - 300;
    expect(anchorForChange(top, null, scrollTop, viewportPx)).toEqual({
      index: 100,
      anchor: { line: 105, offsetPx: 300 },
    });
  });

  it("an unknown top-row line with no usable pivot yields null (restore keeps scrollTop)", () => {
    const scrollTop = 100 * ROW_HEIGHT_PX - 300;
    expect(anchorForChange({ index: 100, line: null }, null, scrollTop, viewportPx)).toBeNull();
  });
});

/** Task 3 (design 2026-11-25-flicker): the anchor-restore skip-gate —
 *  when the row at the captured anchor index still carries the anchor line,
 *  keeping scrollTop keeps the anchor row at its captured offset, so the
 *  whole restore (and its ~log2(count) probe search) is skipped. */
describe("anchorUnchanged (anchor-restore skip-gate)", () => {
  it("true when the row at the captured index still carries the anchor line", () => {
    expect(anchorUnchanged(105, 105)).toBe(true);
  });

  it("false when the line moved (composition changed at the anchor)", () => {
    expect(anchorUnchanged(106, 105)).toBe(false);
    expect(anchorUnchanged(104, 105)).toBe(false);
  });

  it("false when the line is unknown (null -> fall through to the full search)", () => {
    expect(anchorUnchanged(null, 105)).toBe(false);
  });
});

describe("remapSelection", () => {
  it("resolves every selected line number into the new visible indexes", async () => {
    expect(await remapSelection([10, 30], 5, lineSequence(10))).toEqual([0, 2]);
  });

  it("keeps the selection sorted after remapping", async () => {
    expect(await remapSelection([30, 10], 5, lineSequence(10))).toEqual([0, 2]);
  });

  it("drops selected rows hidden by the change (they cannot resolve back, §4)", async () => {
    // Line 55 is beyond the end, 99 as well; only 20 and 30 resolve.
    expect(await remapSelection([20, 55, 99, 30], 5, lineSequence(10))).toEqual([1, 2]);
  });

  it("collapses hidden rows that would remap onto the same visible row", async () => {
    // Lines 21 and 29 are both hidden; both resolve onto line 30 (index 2).
    expect(await remapSelection([21, 29, 50], 5, lineSequence(10))).toEqual([2, 4]);
  });

  it("an empty selection or an empty sequence remaps to nothing", async () => {
    expect(await remapSelection([], 5, lineSequence(10))).toEqual([]);
    expect(await remapSelection([10], 0, lineSequence(10))).toEqual([]);
  });
});
