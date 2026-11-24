//! Pinned tab of the side panel (FUNCTIONAL_SPEC §10.1/§12, q1f.1): one row
//! per pin rule with an on/off checkbox, the canonical command text that
//! created it (":p pattern", ":pr", ":ps", ":pn N") and a delete button. Off
//! entries are dimmed. Anatomy mirrors FiltersTab (docs/UI_DESIGN.html);
//! reload clears the whole list (§2.1 — the snapshot empties).

import type { CSSProperties, ReactElement } from "react";
import { pinCommand, type PinItem } from "./pins";

export type { PinItem, PinMode } from "./pins";

export interface PinnedTabProps {
  items: PinItem[];
  /** Checkbox flipped; `on` is the checkbox's new state (§10.1). */
  onToggle(id: number, on: boolean): void;
  /** Delete button pressed for one pin. */
  onRemove(id: number): void;
}

/* Row anatomy mirrors the FiltersTab row (docs/UI_DESIGN.html list tabs);
   styles are inline because index.css is outside this task's file list. */
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
const REMOVE: CSSProperties = {
  flex: "none",
  padding: "0 2px",
  background: "none",
  border: "none",
  color: "var(--dim)",
  font: "inherit",
  cursor: "pointer",
};
const LIST: CSSProperties = {
  width: 220,
};

export function PinnedTab({ items, onToggle, onRemove }: PinnedTabProps): ReactElement {
  if (items.length === 0) {
    // spec interpretation: §10.1 does not define the empty-list text; a muted
    // placeholder keeps the tab self-explanatory without inventing chrome.
    return (
      <div className="filters-list" style={LIST}>
        <div style={{ ...ROW, color: "var(--muted)", fontSize: 12.5 }}>(no pins)</div>
      </div>
    );
  }
  return (
    <div className="filters-list" style={LIST}>
      {items.map((item) => {
        const cmd = pinCommand(item);
        return (
          <div
            key={item.id}
            className={`filter-row${item.enabled ? "" : " dimmed"}`}
            style={item.enabled ? ROW : { ...ROW, opacity: 0.45 }}
          >
            <input
              type="checkbox"
              aria-label={cmd}
              style={{ flex: "none", margin: 0, accentColor: "var(--accent)" }}
              checked={item.enabled}
              onChange={(e) => onToggle(item.id, e.target.checked)}
            />
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
