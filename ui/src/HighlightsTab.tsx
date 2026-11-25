//! Highlights tab of the side panel (FUNCTIONAL_SPEC §10.1, bead exx.2):
//! one row per highlight rule with an on/off checkbox, the canonical command
//! text that created it (":h pattern", ":hr", ":hs", ":hn N"), a color dot
//! (click opens the SYSTEM color picker through the webview's
//! <input type="color">, §9; §10.1 shows no bulk-removal button — rmh is
//! command-line only) and a delete button. Off entries are dimmed and a
//! disabled rule paints nothing (§9). Presentational like FiltersTab; the
//! IPC bridge feeds it the snapshot's highlight list.

import type { CSSProperties, ReactElement } from "react";
import { highlightCommand, resolvedColor, type HighlightItem } from "./highlights";

export type { HighlightItem } from "./highlights";

export interface HighlightsTabProps {
  items: HighlightItem[];
  /** Checkbox flipped; `on` is the checkbox's new state (§10.1). */
  onToggle(id: number, on: boolean): void;
  /** The system color picker returned a "#rrggbb" for one rule. */
  onColor(id: number, hex: string): void;
  /** Delete button pressed for one rule. */
  onRemove(id: number): void;
}

/* Row anatomy mirrors the design study (docs/UI_DESIGN.html "Categories
   panel", third frame: checkbox, command text with ellipsis, right-aligned
   delete) with the color dot in place of the command prefix (§10.1). Styles
   are inline because index.css is outside this task's file list. */
const ROW: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 7,
  height: 23,
  padding: "0 12px",
  whiteSpace: "nowrap",
};
const COMMAND: CSSProperties = {
  flex: 1,
  minWidth: 0,
  overflow: "hidden",
  textOverflow: "ellipsis",
  fontFamily: "var(--font-data)",
  fontSize: 12.5,
};
const DOT: CSSProperties = {
  flex: "none",
  width: 11,
  height: 11,
  borderRadius: "50%",
  border: "1px solid var(--border-strong)",
  cursor: "pointer",
};
const PICKER: CSSProperties = {
  // The webview's system picker input; visually hidden, the dot's label
  // click opens it (§9: color change via the system color picker).
  position: "absolute",
  left: 0,
  width: 1,
  height: 1,
  opacity: 0,
  border: "none",
  padding: 0,
};
const DOT_CELL: CSSProperties = {
  position: "relative",
  flex: "none",
  display: "inline-block",
  width: 11,
  height: 11,
};
const REMOVE: CSSProperties = {
  flex: "none",
  padding: "0 2px",
  background: "none",
  border: "none",
  color: "var(--dim)",
  font: "inherit",
  cursor: "pointer",
};
/* The side panel is a fixed 280-px column (2026-11-25 mock e5bf7e3, v1
   splitter parity); command text ellipsis-clips against that width. */
const LIST: CSSProperties = {
  width: 280,
};

export function HighlightsTab({ items, onToggle, onColor, onRemove }: HighlightsTabProps): ReactElement {
  if (items.length === 0) {
    // spec interpretation: like the Filters/Pinned tabs, an empty list keeps
    // the tab self-explanatory without inventing chrome.
    return (
      <div className="filters-list" style={LIST}>
        <div style={{ ...ROW, color: "var(--muted)", fontSize: 12.5 }}>(no highlights)</div>
      </div>
    );
  }
  return (
    <div className="filters-list" style={LIST}>
      {items.map((item, index) => {
        const cmd = highlightCommand(item);
        const color = resolvedColor(item.colorIndex, item.overrideColor);
        return (
          <div
            key={item.id}
            className={`filter-row${item.enabled ? "" : " dimmed"}`}
            style={item.enabled ? ROW : { ...ROW, opacity: 0.45 }}
            data-highlight-id={item.id}
          >
            <input
              type="checkbox"
              aria-label={cmd}
              style={{ flex: "none", margin: 0, accentColor: "var(--accent)" }}
              checked={item.enabled}
              onChange={(e) => onToggle(item.id, e.target.checked)}
            />
            {/* The dot is the picker's visual face: its label click opens
                the system color dialog in the real webview. */}
            <label style={DOT_CELL} title={color}>
              <span
                className="color-dot"
                style={{ ...DOT, display: "block", background: color }}
              />
              <input
                type="color"
                aria-label={`Color of ${cmd}`}
                data-highlight-color-input={index}
                style={PICKER}
                value={color}
                onChange={(e) => onColor(item.id, e.target.value)}
              />
            </label>
            <span className="command" style={COMMAND} title={cmd}>
              {cmd}
            </span>
            <button
              type="button"
              aria-label={`Remove ${cmd}`}
              style={REMOVE}
              onClick={() => onRemove(item.id)}
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
