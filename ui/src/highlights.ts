// Pure logic for the §9 highlights (bead exx.2): the 10-color palette, the
// resolved rule/span color, the canonical command text (:h :hr :hs :hn) and
// the span-overlay segment math used by the Message column. No React here.

import type { FilterMode } from "./filtersTab";

/**
 * §9 palette (10 colors, round-robin per rule). The first nine hexes are the
 * spec's named swatches in their given order; the design reference (spec §9
 * swatch table) names only nine, so the tenth entry was derived from the
 * docs/UI_DESIGN.html token sheet as `blue` = the accent token's dark
 * variant #4da3e8 — the only remaining saturated color family that is not
 * reserved for a level (§3.1), and its lightness sits beside `sky` #87ceeb.
 */
export const HIGHLIGHT_HEX: readonly string[] = [
  "#e8c34a", // gold      (the --pin token in the design sheet)
  "#ff9f43", // orange
  "#ff7f6e", // coral
  "#c8b7f5", // lavender
  "#87ceeb", // sky blue
  "#4da3e8", // blue      (derived 10th: docs/UI_DESIGN.html accent, dark)
  "#98e6b8", // mint
  "#3fbfbf", // teal
  "#7fce7f", // green
  "#ff9ec4", // sunny pink
];

/**
 * Overlay alpha per palette entry, parallel to HIGHLIGHT_HEX. The design
 * reference (docs/UI_DESIGN.html mark.h-gold / mark.h-sky / mark.h-mint)
 * tints gold at 38% and the others at 45%; 0.45 is the reference default.
 */
export const HIGHLIGHT_ALPHA: readonly number[] = [
  0.38, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45,
];

/** One §9 highlight rule of the visibility snapshot (camelCase UI shape;
 *  the RAW HighlightDto is normalized once in ipcClient.ts). */
export interface HighlightItem {
  id: number;
  mode: FilterMode;
  pattern: string;
  enabled: boolean;
  colorIndex: number;
  overrideColor: string | null;
}

/** One span of a message row: matches the get_rows row's field naming
 *  (RowDto keeps snake_case); `start`/`len` are JS string indexes of the
 *  message — the RAW SpanDto carries BYTE offsets, converted once in
 *  ipcClient.ts. `override_color` is the raw field as the stubs/backend
 *  send it (absent = no override). */
export interface HighlightSpan {
  start: number;
  len: number;
  color_index: number;
  override_color?: string | null;
}

/** The rule's display color: the user override when set, otherwise the
 *  palette rotation slot (§9). An out-of-range index falls back to slot 0
 *  defensively (the core rotates 0..9). */
export function resolvedColor(colorIndex: number, overrideColor: string | null): string {
  if (overrideColor !== null) {
    return overrideColor;
  }
  return HIGHLIGHT_HEX[colorIndex] ?? HIGHLIGHT_HEX[0];
}

/** Command prefix per highlight mode (§9 chips, §10.1 panel display) — the
 *  same canonical shape as the filtersTab prefixes. */
const HIGHLIGHT_PREFIX: Record<FilterMode, string> = {
  plain: ":h ",
  regex: ":hr ",
  simple: ":hs ",
  lineno: ":hn ",
};

/** Canonical command string that created the rule, e.g. `:hr ^retry`, `:hn 42`. */
export function highlightCommand(item: { mode: FilterMode; pattern: string }): string {
  return HIGHLIGHT_PREFIX[item.mode] + item.pattern;
}

/** A rendered overlay piece of the Message column: a half-open range with
 *  the fully composed background (all overlapping layers stacked). */
export interface OverlaySegment {
  start: number;
  len: number;
  /** Deterministic CSS color, `rgba(r, g, b, a)`. */
  background: string;
}

/** Decomposes a css hex color into rgb components (0-255). */
export function hexToRgb(hex: string): [number, number, number] {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
}

/** Rounds color channels and keeps the alpha at 3 decimals so the composed
 *  strings are byte-stable (the pixel goldens are diffed byte-wise). */
function rgbaOf(r: number, g: number, b: number, a: number): string {
  return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${Math.round(a * 1000) / 1000})`;
}

/**
 * Render geometry for the Message cell (§9): spans arrive unmerged in rule
 * order, so the message text is cut into elementary segments at the spans'
 * boundaries and each segment composes every layer lying on it (later
 * rules painted over earlier ones — ordinary source-over compositing). An
 * `hn` (lineno) rule arrives from the core as a whole-message span, so the
 * geometry is identical for all four modes.
 */
export function overlaySegments(
  messageLength: number,
  spans: readonly HighlightSpan[],
): OverlaySegment[] {
  if (spans.length === 0) {
    return [];
  }
  // Elementary boundaries: every span edge clamped into the message, sorted
  // and deduped (a zero-length or out-of-range span contributes nothing).
  const points = new Set<number>([0, messageLength]);
  for (const span of spans) {
    const from = Math.max(0, span.start);
    const to = Math.min(messageLength, span.start + span.len);
    if (to > from) {
      points.add(from);
      points.add(to);
    }
  }
  const sorted = [...points].sort((a, b) => a - b);

  const segments: OverlaySegment[] = [];
  for (let i = 0; i + 1 < sorted.length; i++) {
    const start = sorted[i] as number;
    const end = sorted[i + 1] as number;
    // Rule order is paint order: first pass, the text shows through.
    let r = 0;
    let g = 0;
    let b = 0;
    let a = 0;
    for (const span of spans) {
      const from = Math.max(0, span.start);
      const to = Math.min(messageLength, span.start + span.len);
      if (from > start || to <= start || to < end) {
        continue;
      }
      const [cr, cg, cb] = hexToRgb(
        resolvedColor(span.color_index, span.override_color ?? null),
      );
      const alpha = HIGHLIGHT_ALPHA[span.color_index] ?? 0.45;
      r = cr * alpha + r * (1 - alpha);
      g = cg * alpha + g * (1 - alpha);
      b = cb * alpha + b * (1 - alpha);
      a = alpha + a * (1 - alpha);
    }
    if (a > 0) {
      // Un-premultiply so a single layer keeps its own css color at its own
      // alpha (the design's color-mix look); the painted pixel is identical
      // to stacking the translucent rects.
      segments.push({
        start,
        len: end - start,
        background: rgbaOf(r / a, g / a, b / a, a),
      });
    }
  }
  return segments;
}
