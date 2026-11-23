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
    /** Current UI state snapshot. */
    state: () => console_.getSnapshot(),
    /** Open+load flow without any dialog: the argument is the path. */
    load: (path: string) => console_.load(path),
    /** Scroll so the 1-based line is centered; resolves to the row count. */
    scrollToRow: (lineNo: number) => console_.scrollToRow(lineNo),
    /** Installs an IPC stub for headless visual runs. */
    stubIpc: (stub: unknown) => {
      (window as unknown as Record<string, unknown>).__ipcStub = stub;
    },
  };
  return () => {
    delete target.__headless;
  };
}
