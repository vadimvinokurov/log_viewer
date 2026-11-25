//! Pure widths logic for the resizable table columns (§4).

import { describe, expect, it } from "vitest";
import {
  DEFAULT_COLUMN_WIDTHS,
  MIN_COLUMN_PX,
  clampWidth,
  columnGridTemplate,
  columnTotal,
  effectiveWidths,
  parseColumnWidths,
  resetWidth,
  serializeColumnWidths,
  setWidth,
} from "./columnWidths.ts";

describe("clampWidth", () => {
  it("rounds and raises to the 20px floor", () => {
    expect(clampWidth(19.4)).toBe(20);
    expect(clampWidth(600)).toBe(600);
    expect(clampWidth(-5)).toBe(20);
  });

  it("collapses non-numbers to the floor", () => {
    expect(clampWidth(NaN)).toBe(20);
    expect(clampWidth(Infinity)).toBe(20);
  });
});

describe("setWidth / resetWidth", () => {
  it("stays immutable and stores the clamped value", () => {
    const input = { ...DEFAULT_COLUMN_WIDTHS };
    const next = setWidth(input, "time", -3);
    expect(input).toEqual(DEFAULT_COLUMN_WIDTHS);
    expect(next.time).toBe(20);
    expect(next.line).toBe(50);
  });

  it("resetWidth puts the key back to its §4 default", () => {
    const wide = setWidth(DEFAULT_COLUMN_WIDTHS, "category", 9999);
    expect(resetWidth(wide, "category")).toEqual(DEFAULT_COLUMN_WIDTHS);
  });
});

describe("effectiveWidths", () => {
  it("fills the window via the Message remainder", () => {
    const ws = effectiveWidths(DEFAULT_COLUMN_WIDTHS, 1400);
    expect(ws.message).toBe(1090);
    expect(columnTotal(ws)).toBe(1400);
  });

  it("keeps the user width when it overflows the window", () => {
    const ws = effectiveWidths(
      setWidth(DEFAULT_COLUMN_WIDTHS, "message", 1200),
      1400,
    );
    expect(ws.message).toBe(1200);
    expect(columnTotal(ws)).toBe(1510);
  });

  it("lets the other three columns overflow the window", () => {
    const ws = effectiveWidths(
      { line: 1000, time: 20, category: 20, message: 600 },
      900,
    );
    expect(ws.message).toBe(600);
    expect(columnTotal(ws)).toBe(1640);
  });

  it("holds the 20px floor in an exact-fit window", () => {
    expect(effectiveWidths(setWidth(DEFAULT_COLUMN_WIDTHS, "message", 20), 330)).toEqual({
      line: 50,
      time: 110,
      category: 150,
      message: 20,
    });
  });

  it("the stored user width below the remainder never surfaces (Review Focus 2)", () => {
    const ws = effectiveWidths(setWidth(DEFAULT_COLUMN_WIDTHS, "message", 30), 1400);
    expect(ws.message).toBe(1090);
  });
});

describe("columnGridTemplate", () => {
  it("renders integer px tracks", () => {
    expect(columnGridTemplate(effectiveWidths(DEFAULT_COLUMN_WIDTHS, 1400))).toBe(
      "50px 110px 150px 1090px",
    );
  });
});

describe("parseColumnWidths", () => {
  it("falls back to the defaults on null or wrong shapes", () => {
    expect(parseColumnWidths(null)).toEqual(DEFAULT_COLUMN_WIDTHS);
    expect(parseColumnWidths(undefined)).toEqual(DEFAULT_COLUMN_WIDTHS);
    expect(parseColumnWidths([60, 120, 160])).toEqual(DEFAULT_COLUMN_WIDTHS);
    expect(parseColumnWidths([60.4, 120, 160, "x"] as unknown)).toEqual(DEFAULT_COLUMN_WIDTHS);
    expect(parseColumnWidths("nonsense")).toEqual(DEFAULT_COLUMN_WIDTHS);
  });

  it("accepts a 4-entry array and clamps each entry", () => {
    expect(parseColumnWidths([60, 120, 160, 620])).toEqual({
      line: 60,
      time: 120,
      category: 160,
      message: 620,
    });
    expect(parseColumnWidths([0, 0, 0, 0])).toEqual({
      line: MIN_COLUMN_PX,
      time: MIN_COLUMN_PX,
      category: MIN_COLUMN_PX,
      message: MIN_COLUMN_PX,
    });
  });
});

describe("serializeColumnWidths", () => {
  it("round-trips through parse", () => {
    const ws = setWidth(DEFAULT_COLUMN_WIDTHS, "category", 250);
    expect(parseColumnWidths(serializeColumnWidths(ws))).toEqual(ws);
    expect(serializeColumnWidths(DEFAULT_COLUMN_WIDTHS)).toEqual([50, 110, 150, 600]);
  });
});
