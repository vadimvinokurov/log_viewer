//! Side panel shell (FUNCTIONAL_SPEC §10.1, bead rhl.2): the 4-tab strip
//! (Categories | Filters | Highlights | Pinned), Ctrl+B collapse and the
//! draggable splitter (width clamped by the reducer, 180-480 px). The panel
//! is furniture, not a mode — it stands open with the file (§10.1).
//! Presentational: state and actions come in as props; App wires the console.

import { useEffect, type MouseEvent as ReactMouseEvent, type ReactNode, type ReactElement } from "react";
import { type PanelTab, type PanelState } from "./state";

export interface SidePanelProps {
  panel: PanelState;
  /** Ctrl+B / Cmd+B (handled by the shell's usePanelHotkey, kept on props
   *  so a host can wire any toggle source). */
  onToggle(): void;
  /** A tab label clicked. */
  onTab(tab: PanelTab): void;
  /** Splitter drag; raw pixel width, the reducer clamps (180-480). */
  onWidth(px: number): void;
  /** Live tab content by tab name; Pinned is live since q1f.1, Highlights
   *  since exx.2. */
  content: Partial<Record<PanelTab, ReactNode>>;
}

const TAB_LABELS: readonly { tab: PanelTab; label: string }[] = [
  { tab: "categories", label: "Categories" },
  { tab: "filters", label: "Filters" },
  { tab: "highlights", label: "Highlights" },
  { tab: "pinned", label: "Pinned" },
];

/** Global Ctrl+B / Cmd+B listener (§10.1: collapses/expands the panel).
 *  Lives OUTSIDE the SidePanel element (App calls it): the panel unmounts
 *  when closed, and the hotkey must still reopen it. */
export function usePanelHotkey(onToggle: () => void): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent): void => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        onToggle();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onToggle]);
}

export function SidePanel({
  panel,
  onTab,
  onWidth,
  content,
}: SidePanelProps): ReactElement | null {
  if (!panel.open) {
    return null;
  }

  const onSplitterDown = (e: ReactMouseEvent): void => {
    e.preventDefault();
    const move = (event: MouseEvent): void => {
      onWidth(window.innerWidth - event.clientX);
    };
    const up = (): void => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

  const live = content[panel.tab];

  return (
    <aside className="side" style={{ width: panel.width }}>
      <nav className="tabs" role="tablist">
        {TAB_LABELS.map(({ tab, label }) => (
          <span
            key={tab}
            role="tab"
            aria-selected={panel.tab === tab}
            className={panel.tab === tab ? "on" : ""}
            onClick={() => onTab(tab)}
          >
            {label}
          </span>
        ))}
      </nav>
      {live ?? (
        <div
          className="side-note"
          data-panel-placeholder={panel.tab}
        >
          Pending: this tab has no live content yet.
        </div>
      )}
      <div
        className="side-splitter"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize panel"
        onMouseDown={onSplitterDown}
      />
    </aside>
  );
}
