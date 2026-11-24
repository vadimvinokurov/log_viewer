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
    /** §4 viewport state incl. the anchor (qt7.3): scrollTop, scrollLeft,
     *  anchor {index, line} and its captured offset; null without a table. */
    viewport: () => console_.viewport(),
    /** §4 row selection: kind = click | toggle | range (from modifiers). */
    select: (index: number, kind: "click" | "toggle" | "range") =>
      console_.selectRow(index, kind),
    /** §4 copy: the selection's raw lines ("raw") or Message column. */
    copy: (mode: "raw" | "message") => console_.copy(mode),
    /** §11 level toggle: level = lowercase long name ("critical".."trace"). */
    setLevel: (level: string, on: boolean) => console_.setLevel(level, on),
    /** §10.1 filters: mode ∈ plain|regex|simple|lineno. */
    addFilter: (mode: string, pattern: string) => console_.addFilter(mode, pattern),
    toggleFilter: (id: number, on: boolean) => console_.toggleFilter(id, on),
    removeFilter: (id: number) => console_.removeFilter(id),
    /** §12 pins (panel comes with q1f.1; the RPC is symmetric with filters). */
    addPin: (mode: string, pattern: string) => console_.addPin(mode, pattern),
    setPinEnabled: (id: number, on: boolean) => console_.setPinEnabled(id, on),
    removePin: (id: number) => console_.removePin(id),
    /** §10 categories (rhl.2): apply the propagateToggle differential and
     *  refetch the snapshot. */
    toggleCategory: (path: string, on: boolean) => console_.toggleCategory(path, on),
    /** All-checkbox toggle over every category. */
    setAllCategories: (on: boolean) => console_.setAllCategories(on),
    /** §10.1 panel: Ctrl+B toggle, tab switch (categories|filters|
     *  highlights|pinned), splitter width, tree search, expand/collapse-all,
     *  one-node expansion flip. */
    togglePanel: () => console_.togglePanel(),
    setPanelTab: (tab: string) => console_.setPanelTab(tab),
    setPanelWidth: (px: number) => console_.setPanelWidth(px),
    setCategorySearch: (query: string) => console_.setCategorySearch(query),
    expandAllCategories: (expand: boolean) => console_.expandAllCategories(expand),
    toggleExpansion: (path: string) => console_.toggleExpansion(path),
    /** §8 search (bead 2wu.1): open/close (Ctrl+F / Esc), tumblers
     *  ("regex" | "simple"; anything else = both off = plain), the debounced
     *  query, and cyclic match stepping (dir -1 | 1). The mirror coerces
     *  the arguments: this is an untyped JS boundary, a missing argument
     *  must become the empty query / plain mode, never a null RAW pattern. */
    openSearch: () => console_.openSearch(),
    closeSearch: () => console_.closeSearch(),
    setSearchMode: (mode?: unknown) => console_.setSearchMode(typeof mode === "string" ? mode : ""),
    setSearchQuery: (query?: unknown) => console_.setSearchQuery(typeof query === "string" ? query : ""),
    nextMatch: (dir?: unknown) => console_.nextMatch(typeof dir === "number" ? dir : 0),
    /** Installs an IPC stub for headless visual runs. */
    stubIpc: (stub: unknown) => {
      (window as unknown as Record<string, unknown>).__ipcStub = stub;
    },
  };
  return () => {
    delete target.__headless;
  };
}
