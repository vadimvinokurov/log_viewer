/**
 * Level button bar logic (FUNCTIONAL_SPEC §11, UI design "bottom bar"): the
 * fixed six-level order and the count formatting used by LevelBar. Pure
 * module - the component (LevelBar.tsx) and the IPC wiring (a later bead)
 * stay thin.
 */

/** Fixed bottom-bar button order (§11): CRITICAL, ERROR, WARNING, MSG, DEBUG, TRACE. */
export const LEVEL_ORDER = ["critical", "error", "warning", "msg", "debug", "trace"] as const;

export type Level = (typeof LEVEL_ORDER)[number];

/** Counts of rows that would be visible if the level were enabled (§11). */
export type LevelCounts = Record<Level, number>;

/** Which levels are currently on (§2.1: disabled levels survive reload). */
export type EnabledLevels = Record<Level, boolean>;

/** Bottom-bar captions per level, matching the UI_DESIGN mock. */
export const LEVEL_LABELS: Record<Level, string> = {
  critical: "CRITICAL",
  error: "ERROR",
  warning: "WARNING",
  msg: "MSG",
  debug: "DEBUG",
  trace: "TRACE",
};

const THIN_SPACE = " ";

// spec interpretation: the UI_DESIGN mock shows "2 041" (grouped digits),
// "96k", "405k", "681k" and "4.2M" - so the buckets are: < 10 000 digits
// grouped with a thin space, < 1 000 000 whole "k", from 1e6 one-decimal
// "M". The mock itself types an ASCII space; the thin space is the narrower
// glyph the design intent ("2 041" reads as one compact unit) asks for.
export function formatCount(n: number): string {
  if (!Number.isFinite(n) || n <= 0) {
    // Count 0 -> the button shows no count (§11); junk input counts as 0.
    return "";
  }
  if (n < 10_000) {
    return String(Math.trunc(n)).replace(/\B(?=(\d{3})+(?!\d))/g, THIN_SPACE);
  }
  if (n < 1_000_000) {
    const k = Math.round(n / 1000);
    if (k < 1000) {
      return String(k) + "k";
    }
    // 999 500..999 999 would round to "1000k" - promote into the M bucket.
  }
  return (Math.round(n / 100_000) / 10).toFixed(1) + "M";
}
