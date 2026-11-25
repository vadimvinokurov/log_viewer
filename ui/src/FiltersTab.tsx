//! Filters tab of the side panel (FUNCTIONAL_SPEC §10.1): one row per filter
//! with an on/off checkbox, the canonical command text that created it
//! (":f pattern", ":fr", ":fs", ":fn N") and a delete button. Off entries
//! are dimmed. This component is presentational: the IPC bridge will feed
//! it the Tauri-side filter list; toggling/removing only emits callbacks
//! (visibility recompute lands with the wiring task).

import type { CSSProperties, ReactElement } from "react";
import { filterCommand, type FilterItem } from "./filtersTab";

export type { FilterItem, FilterMode } from "./filtersTab";

export interface FiltersTabProps {
  items: FilterItem[];
  /** Checkbox flipped; `on` is the checkbox's new state (§10.1). */
  onToggle(id: number, on: boolean): void;
  /** Delete button pressed for one filter. */
  onRemove(id: number): void;
}

/* Row anatomy mirrors the design study (docs/UI_DESIGN.html "Categories
   panel", third frame): checkbox, command text, right-aligned delete.
   Styles are inline because index.css is outside this task's file list. */
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
/* The side panel is a fixed 280-px column (2026-11-25 mock e5bf7e3, v1
   splitter parity); command text ellipsis-clips against that width. */
const LIST: CSSProperties = {
  width: 280,
};

export function FiltersTab({ items, onToggle, onRemove }: FiltersTabProps): ReactElement {
  if (items.length === 0) {
    // spec interpretation: §10.1 does not define the empty-list text; a muted
    // placeholder keeps the tab self-explanatory without inventing chrome.
    return (
      <div className="filters-list" style={LIST}>
        <div style={{ ...ROW, color: "var(--muted)", fontSize: 12.5 }}>(no filters)</div>
      </div>
    );
  }
  return (
    <div className="filters-list" style={LIST}>
      {items.map((item) => {
        const cmd = filterCommand(item);
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
