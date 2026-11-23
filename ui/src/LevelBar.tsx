import type { ReactElement } from "react";
import {
  LEVEL_LABELS,
  LEVEL_ORDER,
  formatCount,
  type EnabledLevels,
  type Level,
  type LevelCounts,
} from "./levelBar";

/**
 * Level toggle bar (FUNCTIONAL_SPEC §11): six buttons on the right side of
 * the 38-px bottom bar - colored dot, caption, live count. Counts carry the
 * ignore-level-toggles semantics from the visibility engine: how many rows
 * of a level would be visible under current filters/categories if the level
 * were enabled. Counts and toggles arrive as props; the IPC wiring (live
 * counters) is a later bead (IPC visibility bridge), §2.1 reload survives
 * there too.
 */
export interface LevelBarProps {
  counts: LevelCounts;
  enabled: EnabledLevels;
  onToggle(level: Level): void;
}

/* Anatomy mirrors the UI_DESIGN `.lv` rule: 27-px flat button, an 8-px
   colored dot, the 500-weight caption, and the count in the data mono font.
   Styles are inline because LevelBar must not touch shared index.css. */
const BTN = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  height: 27,
  padding: "0 9px",
  borderRadius: 6,
  border: "none",
  background: "transparent",
  cursor: "pointer",
  fontFamily: "var(--font-chrome)",
  fontSize: 11.5,
  fontWeight: 500,
  lineHeight: 1,
  fontVariantNumeric: "tabular-nums",
} as const;

const DOT = {
  width: 8,
  height: 8,
  borderRadius: "50%",
  flex: "none",
} as const;

const COUNT = {
  color: "var(--dim)",
  fontFamily: "var(--font-data)",
  fontSize: 11,
  fontWeight: 500,
  lineHeight: 1,
} as const;

/* Per-level colors from index.css tokens (UI design palette, §3.1). MSG is
   neutral by design: a muted dot with the default ink caption. */
const LEVEL_COLOR: Record<Level, { dot: string; text: string }> = {
  critical: { dot: "var(--critical)", text: "var(--critical)" },
  error: { dot: "var(--error)", text: "var(--error)" },
  warning: { dot: "var(--warning)", text: "var(--warning)" },
  msg: { dot: "var(--muted)", text: "var(--ink)" },
  debug: { dot: "var(--debug)", text: "var(--debug)" },
  trace: { dot: "var(--trace)", text: "var(--trace)" },
};

export function LevelBar(props: LevelBarProps): ReactElement {
  return (
    <div
      role="group"
      aria-label="Log levels"
      style={{ display: "flex", gap: 4, marginLeft: "auto" }}
    >
      {LEVEL_ORDER.map(level => {
        const enabled = props.enabled[level];
        const text = formatCount(props.counts[level]);
        const colors = LEVEL_COLOR[level];
        return (
          <button
            key={level}
            type="button"
            aria-pressed={enabled}
            aria-label={LEVEL_LABELS[level]}
            onClick={() => props.onToggle(level)}
            style={{
              ...BTN,
              color: colors.text,
              // Inactive levels dim (design .lv.off: opacity .38) and
              // strike through both the caption and the count.
              textDecoration: enabled ? undefined : "line-through",
              textDecorationThickness: "1px",
              opacity: enabled ? undefined : 0.38,
              fontWeight: level === "critical" ? 600 : BTN.fontWeight,
            }}
          >
            <span aria-hidden style={{ ...DOT, background: colors.dot }} />
            <span>{LEVEL_LABELS[level]}</span>
            {text === "" ? undefined : (
              <span
                data-level-count={level}
                style={{
                  ...COUNT,
                  // §11: inactive levels dim with a strikethrough count.
                  textDecorationLine: enabled ? undefined : "line-through",
                }}
              >
                {text}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
