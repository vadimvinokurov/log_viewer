//! qt7.3 tests: viewport anchoring on filter changes (§4) and selection
//! remapping by line number. Pure logic, no React, no IPC - lineAt is a fake
//! resolver over a monotonic synthetic visible sequence.

import { describe, expect, it } from "vitest";
import {
  ROW_HEIGHT_PX,
  anchorScrollTop,
  captureAnchor,
  remapSelection,
  resolveLineIndex,
  type LineAt,
} from "./viewportAnchoring";

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
    const bottom = 1000 * ROW_HEIGHT_PX - 900;
    expect(anchorScrollTop(null, anchor, 1000, 900)).toBe(bottom);
    // Even the bottom never goes negative on a short table.
    expect(anchorScrollTop(null, anchor, 10, 900)).toBe(0);
  });

  it("clamps into the scrollable range for both ends", () => {
    const bottom = 1000 * ROW_HEIGHT_PX - 900;
    expect(anchorScrollTop(0, anchor, 1000, 900)).toBe(0);
    const hugeOffset = { line: 105, offsetPx: -100000 };
    expect(anchorScrollTop(50, hugeOffset, 1000, 900)).toBe(bottom);
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
