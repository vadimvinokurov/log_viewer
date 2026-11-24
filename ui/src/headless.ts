//! Headless text interface of the UI (building-testable-apps rule 6: text RPC
//! must cover every interactive capability without a window).
//!
//! The console is always registered on `window.__headless` (insignificant in
//! production, the harness uses it instead of poking the DOM). Read access
//! returns state snapshots; actions go through the same reducer the UI uses.

import { console_ } from "./uiConsole";

/** Installs `window.__headless`; returns an uninstaller. */
export function installHeadlessConsole(): () => void {
  const target = window as unknown as Record<string, unknown>;
  target.__headless = {
    version: () => "1",
    /** Current UI state snapshot (selection included). */
    state: () => console_.getSnapshot(),
    /** Open+load flow without any dialog: the argument is the path. */
    load: (path: string) => console_.load(path),
    /** Scroll so the 1-based line is centered; resolves to the row count. */
    scrollToRow: (lineNo: number) => console_.scrollToRow(lineNo),
    /** §4 row selection: kind = click | toggle | range (from modifiers). */
    select: (index: number, kind: "click" | "toggle" | "range") =>
      console_.selectRow(index, kind),
    /** §4 copy: the selection's raw lines ("raw") or Message column. */
    copy: (mode: "raw" | "message") => console_.copy(mode),
    /** Installs an IPC stub for headless visual runs. */
    stubIpc: (stub: unknown) => {
      (window as unknown as Record<string, unknown>).__ipcStub = stub;
    },
  };
  return () => {
    delete target.__headless;
  };
}
