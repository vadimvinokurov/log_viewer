//! Pure column-widths logic for the resizable table (§4). No viewport,
//! DOM or React imports: the reducer (state.ts), the console (uiConsole.ts)
//! and the table (LogTable.tsx) all consume this module.

/** The four §4 columns, in render order. */
export type ColumnKey = "line" | "time" | "category" | "message";

/** User widths per column: what the owner dragged, not what renders. */
export interface ColumnWidths {
  line: number;
  time: number;
  category: number;
  message: number;
}

export const COLUMN_KEYS: readonly ColumnKey[] = [
  "line",
  "time",
  "category",
  "message",
];

/** §4 "Ширины по умолчанию" (design decision: all four, 2026-11-25). */
export const DEFAULT_COLUMN_WIDTHS: ColumnWidths = {
  line: 50,
  time: 110,
  category: 150,
  message: 600,
};

/** Design decision: every column's minimum is 20px. */
export const MIN_COLUMN_PX = 20;

/** Round and clamp to [MIN_COLUMN_PX, ∞); NaN/±Infinity collapse to the floor. */
export function clampWidth(px: number): number {
  if (typeof px !== "number" || !Number.isFinite(px)) {
    return MIN_COLUMN_PX;
  }
  const rounded = Math.round(px);
  return rounded < MIN_COLUMN_PX ? MIN_COLUMN_PX : rounded;
}

/** Immutably replaces one column's width (clamped). */
export function setWidth(
  widths: ColumnWidths,
  key: ColumnKey,
  px: number,
): ColumnWidths {
  return { ...widths, [key]: clampWidth(px) };
}

/** Immutably restores one column to its §4 default. */
export function resetWidth(widths: ColumnWidths, key: ColumnKey): ColumnWidths {
  return { ...widths, [key]: DEFAULT_COLUMN_WIDTHS[key] };
}

/** The widths that actually render: Message fills the window remainder
 *  (design: the drag handle physically stops at the remainder), so while
 *  the user-sum fits the window the table fills it exactly. A user width
 *  dragged below the remainder never surfaces as overflow. When the other
 *  three alone overflow the window the floor holds Message at the user
 *  width. */
export function effectiveWidths(
  widths: ColumnWidths,
  viewportWidth: number,
): ColumnWidths {
  const others = widths.line + widths.time + widths.category;
  const remainder = viewportWidth - others;
  const message =
    remainder >= widths.message
      ? remainder
      : Math.max(widths.message, MIN_COLUMN_PX);
  return { ...widths, message };
}

/** Sum of the given widths (the grid-template total / scroll width driver). */
export function columnTotal(ws: ColumnWidths): number {
  return ws.line + ws.time + ws.category + ws.message;
}

/** The CSS grid-template-columns value for one widths object (integer px). */
export function columnGridTemplate(ws: ColumnWidths): string {
  return `${Math.round(ws.line)}px ${Math.round(ws.time)}px ${Math.round(ws.category)}px ${Math.round(ws.message)}px`;
}

/** Raw persisted shape (`column_widths`): 4 numeric entries or null. */
export function serializeColumnWidths(
  ws: ColumnWidths,
): [number, number, number, number] {
  return [ws.line, ws.time, ws.category, ws.message];
}

/** Normalizes the RAW persisted value: null / undefined / any shape without
 *  exactly four finite numbers falls back to the §4 defaults, valid entries
 *  clamp to the floor. The single normalization point for the settings
 *  round-trip (design: "the IPC adapter is the single normalization point"
 *  — here the settings seam). */
export function parseColumnWidths(raw: unknown): ColumnWidths {
  if (
    !Array.isArray(raw) ||
    raw.length !== COLUMN_KEYS.length ||
    !raw.every((value) => typeof value === "number" && Number.isFinite(value))
  ) {
    return { ...DEFAULT_COLUMN_WIDTHS };
  }
  const [line, time, category, message] = raw as [number, number, number, number];
  return {
    line: clampWidth(line),
    time: clampWidth(time),
    category: clampWidth(category),
    message: clampWidth(message),
  };
}
