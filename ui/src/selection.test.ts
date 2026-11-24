import { describe, expect, it } from "vitest";
import {
  all,
  EMPTY_SELECTION,
  messageCopyText,
  missingRanges,
  range,
  rawCopyText,
  select,
  toggle,
  type SelectionState,
} from "./selection";

/** Hand-computed §4 cases; row indexes are 0-based throughout. */
describe("selection (FUNCTIONAL_SPEC §4 multi-select)", () => {
  describe("select (plain click: replaces)", () => {
    it("selects a single row on an empty selection", () => {
      expect(select(EMPTY_SELECTION, 0)).toEqual({ selected: [0], anchor: 0 });
    });

    it("replaces any previous selection and moves the anchor", () => {
      const prior: SelectionState = { selected: [2, 5, 6], anchor: 5 };
      expect(select(prior, 9)).toEqual({ selected: [9], anchor: 9 });
    });

    it("does not mutate the previous state", () => {
      const prior: SelectionState = { selected: [2, 5, 6], anchor: 5 };
      const next = select(prior, 9);
      expect(prior.selected).toEqual([2, 5, 6]);
      expect(prior.anchor).toBe(5);
      expect(next.selected).not.toBe(prior.selected);
    });
  });

  describe("toggle (ctrl/meta click: add-or-remove)", () => {
    it("adds a new row onto the selection", () => {
      const prior: SelectionState = { selected: [2, 5], anchor: 2 };
      expect(toggle(prior, 9)).toEqual({ selected: [2, 5, 9], anchor: 9 });
    });

    it("removes a row that was already selected", () => {
      const prior: SelectionState = { selected: [2, 5, 9], anchor: 9 };
      expect(toggle(prior, 5)).toEqual({ selected: [2, 9], anchor: 5 });
    });

    it("removes the last remaining row and leaves an empty selection", () => {
      const prior: SelectionState = { selected: [5], anchor: 5 };
      expect(toggle(prior, 5)).toEqual({ selected: [], anchor: 5 });
    });

    it("keeps the result sorted and duplicate-free", () => {
      const prior: SelectionState = { selected: [7], anchor: 7 };
      expect(toggle(prior, 3)).toEqual({ selected: [3, 7], anchor: 3 });
      const again = toggle({ selected: [3, 7], anchor: 3 }, 3);
      expect(again.selected).toEqual([7]);
    });
  });

  describe("range (shift-click from the pivot anchor)", () => {
    it("unions the anchor..i span with the existing selection", () => {
      const prior: SelectionState = { selected: [1, 10], anchor: 3 };
      expect(range(prior, 7)).toEqual({
        selected: [1, 3, 4, 5, 6, 7, 10],
        anchor: 3,
      });
    });

    it("spans downward when i is above the anchor", () => {
      const prior: SelectionState = { selected: [], anchor: 7 };
      expect(range(prior, 3)).toEqual({ selected: [3, 4, 5, 6, 7], anchor: 7 });
    });

    it("keeps the pivot anchor for a following shift-click", () => {
      const prior: SelectionState = { selected: [3, 4, 5, 6, 7], anchor: 7 };
      expect(range(prior, 9)).toEqual({
        selected: [3, 4, 5, 6, 7, 8, 9],
        anchor: 7,
      });
    });

    it("collapses to a plain click when there is no anchor yet", () => {
      expect(range(EMPTY_SELECTION, 4)).toEqual({ selected: [4], anchor: 4 });
    });
  });

  describe("all (select every row)", () => {
    it("spans 0..rowCount-1 and keeps the anchor", () => {
      const prior: SelectionState = { selected: [2, 5], anchor: 5 };
      expect(all(prior, 4)).toEqual({ selected: [0, 1, 2, 3], anchor: 5 });
    });

    it("yields an empty selection for an empty table", () => {
      expect(all(EMPTY_SELECTION, 0)).toEqual({ selected: [], anchor: null });
    });
  });
});

describe("copy helpers (§4 raw lines vs Message contents)", () => {
  it("joins raw file lines with newlines", () => {
    const rows = [{ raw: "raw a" }, { raw: "raw b" }, { raw: "raw c" }];
    expect(rawCopyText(rows)).toBe("raw a\nraw b\nraw c");
  });

  it("adds no trailing newline for a single row", () => {
    expect(rawCopyText([{ raw: "raw only" }])).toBe("raw only");
  });

  it("returns an empty string for an empty selection", () => {
    expect(rawCopyText([])).toBe("");
  });

  it("joins Message contents with newlines", () => {
    const rows = [{ message: "alpha" }, { message: "beta" }];
    expect(messageCopyText(rows)).toBe("alpha\nbeta");
  });

  it("keeps newlines already inside messages and adds separators between rows", () => {
    const rows = [{ message: "a\nb" }, { message: "c" }];
    expect(messageCopyText(rows)).toBe("a\nb\nc");
  });
});

describe("missingRanges (copy loads uncached rows, §4)", () => {
  it("returns nothing when every selected row is already cached", () => {
    const cached = new Set([2, 3, 5]);
    expect(missingRanges([3, 5, 2], 6, cached)).toEqual([]);
  });

  it("merges adjacent selected rows into contiguous fetch ranges", () => {
    const cached = new Set<number>();
    expect(missingRanges([10, 11, 12, 40, 42], 100, cached)).toEqual([
      { start: 10, end: 13 },
      { start: 40, end: 41 },
      { start: 42, end: 43 },
    ]);
  });

  it("caches already-fetched rows inside a partially loaded span", () => {
    const cached = new Set([11]);
    expect(missingRanges([10, 11, 12], 100, cached)).toEqual([{ start: 10, end: 13 }]);
  });
});
