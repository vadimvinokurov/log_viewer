// Tests for the §9 highlights pure module (bead exx.2): the 10-color palette
// from the spec's named swatches, the resolved rule/span color, the
// canonical command text and the span-overlay segment math.

import { describe, expect, it } from "vitest";
import {
  HIGHLIGHT_ALPHA,
  HIGHLIGHT_HEX,
  highlightCommand,
  overlaySegments,
  resolvedColor,
} from "./highlights";

describe("HIGHLIGHT_HEX palette (§9, bead exx.2)", () => {
  it("holds the 10 rotation colors in the spec's named order", () => {
    expect(HIGHLIGHT_HEX).toHaveLength(10);
    expect(HIGHLIGHT_HEX[0]).toBe("#e8c34a"); // gold (the --pin token)
    expect(HIGHLIGHT_HEX[1]).toBe("#ff9f43"); // orange
    expect(HIGHLIGHT_HEX[2]).toBe("#ff7f6e"); // coral
    expect(HIGHLIGHT_HEX[3]).toBe("#c8b7f5"); // lavender
    expect(HIGHLIGHT_HEX[4]).toBe("#87ceeb"); // sky blue
    expect(HIGHLIGHT_HEX[9]).toBe("#ff9ec4"); // sunny pink
  });

  it("all entries are unique valid css hex colors", () => {
    expect(new Set(HIGHLIGHT_HEX).size).toBe(HIGHLIGHT_HEX.length);
    for (const hex of HIGHLIGHT_HEX) {
      expect(hex).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it("carries an overlay alpha per palette entry (docs/UI_DESIGN.html mark.h-*)", () => {
    expect(HIGHLIGHT_ALPHA).toHaveLength(10);
    expect(HIGHLIGHT_ALPHA[0]).toBe(0.38); // mark.h-gold
    for (const alpha of HIGHLIGHT_ALPHA.slice(1)) {
      expect(alpha).toBe(0.45); // mark.h-sky / mark.h-mint reference value
    }
  });
});

describe("resolvedColor (§9 palette rotation + override)", () => {
  it("uses the palette rotation color when there is no override", () => {
    expect(resolvedColor(0, null)).toBe("#e8c34a");
    expect(resolvedColor(4, null)).toBe("#87ceeb");
  });

  it("the override color wins (set_highlight_color contract)", () => {
    expect(resolvedColor(0, "#00aabb")).toBe("#00aabb");
  });

  it("an out-of-range index falls back to the first palette entry (defensive; the core rotates 0..9)", () => {
    expect(resolvedColor(99, null)).toBe("#e8c34a");
  });
});

describe("highlightCommand (§9/:h :hr :hs :hn, filtersTab canonical shape)", () => {
  it("renders the four rule kinds", () => {
    expect(highlightCommand({ mode: "plain", pattern: "timeout" })).toBe(":h timeout");
    expect(highlightCommand({ mode: "regex", pattern: "^retry" })).toBe(":hr ^retry");
    expect(highlightCommand({ mode: "simple", pattern: "x" })).toBe(":hs x");
    expect(highlightCommand({ mode: "lineno", pattern: "42" })).toBe(":hn 42");
  });
});

describe("overlaySegments (§9 render geometry)", () => {
  it("an empty span list renders nothing", () => {
    expect(overlaySegments(30, [])).toEqual([]);
  });

  it("one span yields one segment with its own composed background", () => {
    const segments = overlaySegments(30, [
      { start: 10, len: 5, color_index: 0, override_color: null },
    ]);
    expect(segments).toEqual([{ start: 10, len: 5, background: "rgba(232, 195, 74, 0.38)" }]);
  });

  it("the override color is resolved for the span background", () => {
    const segments = overlaySegments(30, [
      { start: 0, len: 4, color_index: 3, override_color: "#123456" },
    ]);
    expect(segments).toEqual([{ start: 0, len: 4, background: "rgba(18, 52, 86, 0.45)" }]);
  });

  it("disjoint spans keep their positions; nothing is merged", () => {
    const segments = overlaySegments(30, [
      { start: 2, len: 3, color_index: 6, override_color: null },
      { start: 12, len: 2, color_index: 0, override_color: null },
    ]);
    expect(segments).toEqual([
      { start: 2, len: 3, background: "rgba(152, 230, 184, 0.45)" },
      { start: 12, len: 2, background: "rgba(232, 195, 74, 0.38)" },
    ]);
  });

  it("spans split at each other's boundaries so overlapping text shows both", () => {
    // gold covers 0..6, sky covers 4..10: three elementary segments.
    const segments = overlaySegments(20, [
      { start: 0, len: 6, color_index: 0, override_color: null },
      { start: 4, len: 6, color_index: 4, override_color: null },
    ]);
    expect(segments.map((s) => [s.start, s.start + s.len])).toEqual([
      [0, 4],
      [4, 6],
      [6, 10],
    ]);
  });

  it("overlapping text composes the two translucent layers (gold under sky)", () => {
    const segments = overlaySegments(20, [
      { start: 0, len: 6, color_index: 0, override_color: null },
      { start: 4, len: 6, color_index: 4, override_color: null },
    ]);
    // gold 0..4 on its own …
    expect(segments[0]?.background).toBe("rgba(232, 195, 74, 0.38)");
    // sky after gold ends …
    expect(segments[2]?.background).toBe("rgba(135, 206, 235, 0.45)");
    // … and the 4..6 overlap stacks sky (0.45) over gold (0.38):
    // premR = .45*135 + .55*(.38*232) = 109.238; a = .45 + .55*.38 = 0.659
    // R = 109.238/.659 → 166; G = 133.455/.659 → 202; B = 121.216/.659 → 184
    expect(segments[1]?.background).toBe("rgba(166, 203, 184, 0.659)");
  });

  it("spans are painted in rule order: a later rule lies on top", () => {
    const segments = overlaySegments(10, [
      { start: 0, len: 5, color_index: 4, override_color: null }, // sky
      { start: 0, len: 5, color_index: 0, override_color: null }, // gold on top
    ]);
    // gold over sky: un-premultiplied from the source-over stack
    // premR = .38*232 + .62*(.45*135) = 125.825; a = .38 + .62*.45 = 0.659
    // R = 125.825/.659 = 190.9 → 191; G = 131.574/.659 → 200; B = 93.685/.659 → 142
    expect(segments).toEqual([{ start: 0, len: 5, background: "rgba(191, 200, 142, 0.659)" }]);
  });

  it("spans past the message end are clamped; zero-length spans vanish", () => {
    const segments = overlaySegments(8, [
      { start: 6, len: 100, color_index: 8, override_color: null },
      { start: 2, len: 0, color_index: 0, override_color: null },
    ]);
    expect(segments).toEqual([{ start: 6, len: 2, background: "rgba(127, 206, 127, 0.45)" }]);
  });
});

describe("hexToRgb (span overlay input)", () => {
  it("decomposes css hex pairs", async () => {
    const { hexToRgb } = await import("./highlights");
    expect(hexToRgb("#e8c34a")).toEqual([232, 195, 74]);
    expect(hexToRgb("#000000")).toEqual([0, 0, 0]);
  });
});
