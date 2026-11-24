//! UI console: the text interface over the app state (building-testable-apps
//! rule 6). App renders from it, the headless harness acts on it - one
//! reducer, no window required. The load action runs through the same IPC
//! adapter as the button flow (stubbed in headless runs).

import { appReducer, expandedForToggleAll, initialAppState, type AppState, type AppEvent, type PanelTab, PANEL_TABS, type SearchMode } from "./state";
import type { VisibilityState } from "./state";
import { buildTree, propagateToggle, toggleAll } from "./categories";
import { ipc } from "./ipcClient";
import { exactPinIdsCovering } from "./pins";
import {
  remapSelection,
  resolveLineIndex,
  type LineAt,
  type ViewportInfo,
} from "./viewportAnchoring";

export interface ConsoleSnapshot {
  screen: AppState["screen"];
  error: string | null;
  loadingFile: string | null;
  file: { name: string; format: string; lineCount: number } | null;
  selection: { selected: number[]; anchor: number | null };
  /** Latest applied visibility snapshot (§7); null before the first one. */
  visibility: VisibilityState | null;
  /** §10.1 side panel state (rhl.2). */
  panel: {
    open: boolean;
    tab: PanelTab;
    width: number;
    search: string;
    expanded: string[];
  };
  /** §8 search panel state (bead 2wu.1). */
  search: {
    open: boolean;
    mode: SearchMode;
    query: string;
    /** The current match count N (only VISIBLE rows were searched). */
    total: number;
    /** 1-based rank of the current match (k of N); null when there are none. */
    currentRank: number | null;
    /** The current match's visible row index; null when there are none. */
    currentVisibleIndex: number | null;
  };
}

/** Copy column selection: raw file lines or the Message column (§4). */
export type CopyMode = "raw" | "message";

interface TableHandle {
  scrollToRow(lineNo: number): void;
  /** Builds the copy text for the selection (loading uncached rows),
   * writes it to the clipboard and returns it for assertions. */
  copy(mode: CopyMode): Promise<string>;
  /** Current viewport scroll state incl. the live anchor (§4, qt7.3);
   * null while no table is mounted. Assertions use this, never DOM. */
  viewport(): ViewportInfo | null;
}

class UiConsole {
  private state: AppState = initialAppState();
  private listeners = new Set<() => void>();
  private table: TableHandle | null = null;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getState = (): AppState => this.state;

  /** Full serialized snapshot for the text RPC. */
  getSnapshot = (): ConsoleSnapshot => {
    const f = this.state.file;
    const v = this.state.visibility;
    return {
      screen: this.state.screen,
      error: this.state.error,
      loadingFile: this.state.loadingFile,
      file: f ? { name: f.name, format: f.load.format, lineCount: f.load.lineCount } : null,
      selection: {
        selected: [...this.state.selection.selected],
        anchor: this.state.selection.anchor,
      },
      visibility: v
        ? {
            visibleCount: v.visibleCount,
            levels: v.levels.map((l) => ({ ...l })),
            filters: v.filters.map((i) => ({ ...i })),
            pins: v.pins.map((i) => ({ ...i })),
            categoriesEnabled: [...v.categoriesEnabled],
          }
        : null,
      panel: {
        open: this.state.panel.open,
        tab: this.state.panel.tab,
        width: this.state.panel.width,
        search: this.state.panel.search,
        expanded: [...this.state.panel.expanded],
      },
      search: this.searchSnapshot(),
    };
  }

  /** §8 counter for the snapshot: k of N / «0 of 0», k is 1-based (bead
   *  2wu.1); N counts only the VISIBLE matches of the current query. */
  private searchSnapshot(): ConsoleSnapshot["search"] {
    const s = this.state.search;
    const total = s.positions.length;
    const current =
      s.current !== null && s.current >= 0 && s.current < total
        ? s.current
        : null;
    return {
      open: s.open,
      mode: s.mode,
      query: s.query,
      total,
      currentRank: current === null ? null : current + 1,
      currentVisibleIndex: current === null ? null : s.positions[current] ?? null,
    };
  };

  dispatch = (event: AppEvent): void => {
    // §8 freshness invariant (bead 2wu.1, live round 2): the search slice's
    // inputs are the visible sequence (epoch), the mode and the query.
    // EVERY dispatch that moves one of them re-arms the recompute here —
    // the single enforcement point, so no action path (present or future)
    // can forget to refresh an open panel's matches.
    const before = {
      epoch: this.state.visibilityEpoch,
      query: this.state.search.query,
      mode: this.state.search.mode,
      open: this.state.search.open,
    };
    this.state = appReducer(this.state, event);
    this.listeners.forEach((l) => l());
    const moved =
      before.epoch !== this.state.visibilityEpoch ||
      before.query !== this.state.search.query ||
      before.mode !== this.state.search.mode ||
      before.open !== this.state.search.open;
    if (moved && this.state.search.open && this.hasSearchQuery()) {
      this.scheduleSearchRefresh();
    }
  };

  /** Register the table so `scrollToRow` reaches the real component. */
  setTableHandle = (handle: TableHandle | null): void => {
    this.table = handle;
  };

  scrollToRow = (lineNo: number): number | null => {
    if (this.table) {
      this.table.scrollToRow(lineNo);
      return this.state.file?.load.lineCount ?? null;
    }
    return null;
  };

  /** Viewport state through the table handle (§4 text RPC, qt7.3). */
  viewport = (): ViewportInfo | null => {
    return this.table ? this.table.viewport() : null;
  };

  /** §4 row-selection transitions (the reducer holds the transitions). */
  selectRow = (
    index: number,
    kind: "click" | "toggle" | "range",
  ): ConsoleSnapshot => {
    this.dispatch(
      kind === "click"
        ? { kind: "selection-click", index }
        : kind === "toggle"
          ? { kind: "selection-toggle", index }
          : { kind: "selection-range", index },
    );
    return this.getSnapshot();
  };

  /** Copy the current selection; resolves to the text that was written. */
  copy = (mode: CopyMode): Promise<string> => {
    if (!this.table) {
      return Promise.resolve("");
    }
    return this.table.copy(mode);
  };

  /** load(path): resolves with the resulting snapshot (success or error). */
  load = (path: string): Promise<ConsoleSnapshot> => {
    return (async () => {
      this.dispatch({ kind: "load-request", path });
      try {
        const load = await ipc().loadFile(path);
        this.dispatch({
          kind: "load-success",
          load,
          fileName: path.split("/").pop() ?? path,
        });
        // The fresh file's visibility follows the load result (§7); a failed
        // fetch is caught inside and surfaces through the error state.
        await this.refreshVisibility();
      } catch (e) {
        this.dispatch({ kind: "load-error", message: String(e) });
      }
      return this.getSnapshot();
    })();
  };

  /** Refetches visibility_snapshot and applies it to the reducer. The §8
   *  freshness recompute (open panel + query) schedules through the
   *  dispatch hook — the epoch change alone moves the search's inputs. */
  private refreshVisibility = async (): Promise<void> => {
    try {
      const snapshot = await ipc().visibilitySnapshot();
      this.dispatch({ kind: "visibility", snapshot });
    } catch (e) {
      // §2: an error shows a message, the loaded data is not lost.
      this.dispatch({ kind: "load-error", message: String(e) });
    }
  };

  /** 1-row probe of the visible sequence (contract dsq.3): get_rows(i, 1)
   *  resolves the line_no of 0-based row i, or null past the end. Probes are
   *  the console's only resolution path (the row cache lives in LogTable). */
  private lineAt: LineAt = async (index: number) => {
    const chunk = await ipc().getRows(index, 1);
    const row = chunk[0];
    return row ? row.line_no : null;
  };

  /** Pre-mutation resolve (§4): the selected indexes' and the pivot's line
   *  numbers against the CURRENT visible sequence, before the mutation's
   *  refetch makes those indexes stale. */
  private resolveRemapInput = async (
    selected: number[],
  ): Promise<{ lines: number[]; anchorLine: number | null }> => {
    const lineAt = this.lineAt;
    const anchor = this.state.selection.anchor;
    const lines: number[] = [];
    for (const index of selected) {
      const line = await lineAt(index);
      if (line !== null) {
        lines.push(line);
      }
    }
    const anchorLine = anchor === null ? null : await lineAt(anchor);
    return { lines, anchorLine };
  };

  /** Runs one visibility mutation, then refetches and applies the snapshot;
   *  a failed mutation surfaces through the existing error state. With a
   *  non-empty selection the selection is remapped by line numbers across
   *  the change (§4, qt7.3); an empty selection costs zero extra IPC.
   *  The mutating critical section covers the wire calls AND the snapshot
   *  refetch (the search recompute defers while it is up). */
  private mutateVisibility = async (
    mutator: () => Promise<unknown>,
  ): Promise<ConsoleSnapshot> => {
    const selected = [...this.state.selection.selected].sort((a, b) => a - b);
    const remap = selected.length
      ? await this.resolveRemapInput(selected)
      : null;
    this.mutating += 1;
    try {
      try {
        await mutator();
      } catch (e) {
        this.dispatch({ kind: "load-error", message: String(e) });
        return this.getSnapshot();
      }
      await this.refreshVisibility();
    } finally {
      this.mutating -= 1;
    }
    if (remap) {
      const count = this.state.visibility?.visibleCount ?? 0;
      const lineAt = this.lineAt;
      const indexes = await remapSelection(remap.lines, count, lineAt);
      const anchor =
        remap.anchorLine === null
          ? null
          : await resolveLineIndex(remap.anchorLine, count, lineAt);
      // Hidden pivot: the anchor clears, the remapped indexes stay.
      this.dispatch({ kind: "selection-remap", indexes, anchor });
    }
    return this.getSnapshot();
  };

  /** §11 level toggle; level = lowercase long name, the backend rejects
   *  unknown names (the text RPC is a string boundary, like the backend). */
  setLevel = (level: string, on: boolean): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().setLevelEnabled(level, on));

  /** §10.1 filter RPC (mode ∈ plain|regex|simple|lineno, as the backend). */
  addFilter = (mode: string, pattern: string): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().addFilter(mode, pattern));
  toggleFilter = (id: number, on: boolean): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().setFilterEnabled(id, on));
  removeFilter = (id: number): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().removeFilter(id));

  /** §12 pin RPC — symmetric with filters; the Pinned tab is q1f.1. */
  addPin = (mode: string, pattern: string): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().addPin(mode, pattern));
  setPinEnabled = (id: number, on: boolean): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().setPinEnabled(id, on));
  removePin = (id: number): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().removePin(id));

  /** The selected indexes' 1-based line numbers against the CURRENT visible
   *  sequence, ascending (1-row probes; unresolvable indexes drop out). */
  private resolveSelectionLines = async (): Promise<number[]> => {
    const lines: number[] = [];
    for (const index of [...this.state.selection.selected].sort((a, b) => a - b)) {
      const line = await this.lineAt(index);
      if (line !== null) {
        lines.push(line);
      }
    }
    return lines;
  };

  /** §12 pin selection (q1f.1): one add_pin("lineno", "<line>") per selected
   *  row, batched inside ONE mutating critical section — a single snapshot
   *  refetch covers the whole batch (the 2wu.1 lesson). Line resolution runs
   *  inside the section too: the visible sequence is still pre-mutation.
   *  An empty selection is a no-op without IPC. */
  pinSelected = (): Promise<ConsoleSnapshot> => {
    if (this.state.selection.selected.length === 0) {
      return Promise.resolve(this.getSnapshot());
    }
    return this.mutateVisibility(async () => {
      for (const line of await this.resolveSelectionLines()) {
        await ipc().addPin("lineno", String(line));
      }
    });
  };

  /** §12 unpin selection (q1f.1): remove_pin for every EXACT-ROW pin whose
   *  line number is among the selection's line numbers (from the menu's row
   *  cache when given, probed otherwise); broad and disabled pins stay.
   *  Nothing covering -> no-op without IPC (the pure decision lives in
   *  pins.ts). */
  unpinSelected = (selectedLines?: number[]): Promise<ConsoleSnapshot> => {
    return (async () => {
      const lines = selectedLines ?? (await this.resolveSelectionLines());
      const ids = exactPinIdsCovering(this.state.visibility?.pins ?? [], lines);
      if (ids.length === 0) {
        return this.getSnapshot();
      }
      return this.mutateVisibility(async () => {
        for (const id of ids) {
          await ipc().removePin(id);
        }
      });
    })();
  };

  /** §12 :rmp equivalent — clears every pin with one refetch. */
  clearAllPins = (): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().clearPins());

  // ---- §10.1 side panel (bead rhl.2) ----

  /** Pure panel dispatches: Ctrl+B, tab strip, splitter, tree search. */
  togglePanel = (): ConsoleSnapshot => {
    this.dispatch({ kind: "panel-toggle" });
    return this.getSnapshot();
  };

  /** Tab switch; the text RPC is a string boundary (the reducer's types
   *  cannot express an unknown tab), so unknown names fall back. */
  setPanelTab = (tab: string): ConsoleSnapshot => {
    const known = PANEL_TABS.find((candidate) => candidate === tab) ?? "categories";
    this.dispatch({ kind: "panel-tab", tab: known });
    return this.getSnapshot();
  };

  setPanelWidth = (px: number): ConsoleSnapshot => {
    this.dispatch({ kind: "panel-width", width: px });
    return this.getSnapshot();
  };

  setCategorySearch = (query: string): ConsoleSnapshot => {
    this.dispatch({ kind: "panel-search", query });
    return this.getSnapshot();
  };

  toggleExpansion = (path: string): ConsoleSnapshot => {
    this.dispatch({ kind: "panel-expansion-toggle", path });
    return this.getSnapshot();
  };

  /** Expand/collapse-all over the loaded file's tree (§10 action 5). */
  expandAllCategories = (expand: boolean): ConsoleSnapshot => {
    this.dispatch({ kind: "panel-expanded", expanded: expandedForToggleAll(this.flatCategories(), expand) });
    return this.getSnapshot();
  };

  /** The loaded file's flat category list; empty before a load (actions
   *  that need the tree no-op safely). */
  private flatCategories = (): { path: string; count: number }[] =>
    this.state.file?.load.categories ?? [];

  /** §10 category toggle: applies propagateToggle's differential through
   *  raw set_category_enabled (one call per path), then refetches the
   *  snapshot through mutateVisibility (selection remap included). */
  toggleCategory = (path: string, on: boolean): Promise<ConsoleSnapshot> => {
    const flat = this.flatCategories();
    if (flat.length === 0) {
      return Promise.resolve(this.getSnapshot());
    }
    const { add, remove } = propagateToggle([path], buildTree(flat), on);
    return this.mutateVisibility(async () => {
      for (const p of remove) {
        await ipc().setCategoryEnabled(p, false);
      }
      for (const p of add) {
        await ipc().setCategoryEnabled(p, true);
      }
    });
  };

  /** All-checkbox toggle over every tree path (toggleAll differential). */
  setAllCategories = (on: boolean): Promise<ConsoleSnapshot> => {
    const flat = this.flatCategories();
    if (flat.length === 0) {
      return Promise.resolve(this.getSnapshot());
    }
    const { add, remove } = toggleAll(flat, on);
    return this.mutateVisibility(async () => {
      for (const p of remove) {
        await ipc().setCategoryEnabled(p, false);
      }
      for (const p of add) {
        await ipc().setCategoryEnabled(p, true);
      }
    });
  };

  // ---- §8 search panel (bead 2wu.1) ----

  /** The slice's query as the RAW invoke must see it — always a string.
   *  Live-check fix: the headless mirror is a JS boundary where the TS
   *  parameter types do not hold (a missing argument arrives as
   *  undefined), and an undefined query reached Tauri as a null `pattern`
   *  ("invalid args pattern … expected a string"). */
  private safeQuery = (): string => {
    const query = this.state.search.query;
    return typeof query === "string" ? query : "";
  };

  /** The query is truthy enough to recompute: non-empty string. */
  private hasSearchQuery = (): boolean => this.safeQuery() !== "";

  /** 250 ms debounce of the searchVisible recompute (bead 2wu.1 design:
   *  no positions cap, the UI debounces instead). */
  private searchTimer: ReturnType<typeof setTimeout> | null = null;
  /** Bumped on every recompute start; a late response with a stale token is
   *  discarded instead of overwriting the newest matches. */
  private searchToken = 0;

  private cancelSearchRefresh = (): void => {
    if (this.searchTimer !== null) {
      clearTimeout(this.searchTimer);
      this.searchTimer = null;
    }
  };

  private scheduleSearchRefresh = (): void => {
    this.cancelSearchRefresh();
    this.searchTimer = setTimeout(() => {
      this.searchTimer = null;
      void this.refreshMatches();
    }, 250);
  };

  /** Depth of the visibility-mutation critical section (live round 3):
   *  while a differential mid-applies — the console issues its
   *  set_category_enabled / setLevel wire calls one by one inside one
   *  mutateVisibility round with a single snapshot refetch at the end —
   *  the shell's visible cache is transiently partial between the wire
   *  calls. A recompute firing in that window scans (and the shell then
   *  caches for the whole multi-second 1M+ row scan) a mid-burst state
   *  whose total lands under the still-current epoch. */
  private mutating = 0;

  /** §8: Ctrl+F opens (a file must be loaded); the tumblers/query survive a
   *  close, so reopening rescans the same query against the current
   *  visibility and restarts from the selection downward. */
  openSearch = (): ConsoleSnapshot => {
    if (this.state.file === null) {
      return this.getSnapshot();
    }
    this.dispatch({ kind: "search-open" });
    // The open transition schedules through the dispatch hook (the panel is
    // open and the query is non-empty at this point).
    return this.getSnapshot();
  };

  /** §8: Esc closes; the arrows return to row navigation (App keydown). */
  closeSearch = (): ConsoleSnapshot => {
    this.cancelSearchRefresh();
    this.dispatch({ kind: "search-close" });
    return this.getSnapshot();
  };

  /** Tumbler state at the text-RPC boundary: "regex" | "simple" set that
   *  tumbler, anything else (including "plain") = both off (bead 2wu.1:
   *  clicking an active tumbler returns to plain; the UI never sends an
   *  unknown mode, so unknown strings fall back defensively). */
  setSearchMode = (mode: string): ConsoleSnapshot => {
    const known: SearchMode = mode === "regex" || mode === "simple" ? mode : null;
    this.dispatch({ kind: "search-mode", mode: known });
    return this.getSnapshot();
  };

  /** Typing dispatches immediately; positions refetch 250 ms after the
   *  last keystroke (scheduling through the dispatch hook). A missing/
   *  non-string argument (the headless mirror is an untyped JS boundary)
   *  coerces to "" — the boundary never stores, and the RAW invoke never
   *  sees, a non-string pattern. */
  setSearchQuery = (query: string): ConsoleSnapshot => {
    const value = typeof query === "string" ? query : "";
    this.dispatch({ kind: "search-query", query: value });
    return this.getSnapshot();
  };

  /** §8 cyclic match navigation: dir +1 = next, -1 = previous; the match's
   *  row becomes the selection (the ordinary click event, §4) and centers
   *  in the viewport via the table handle. A no-op without matches. */
  nextMatch = (dir: number): ConsoleSnapshot => {
    const s = this.state.search;
    if (!s.open || s.positions.length === 0 || s.current === null) {
      return this.getSnapshot();
    }
    const direction = dir >= 0 ? 1 : -1;
    const next = (s.current + direction + s.positions.length) % s.positions.length;
    this.dispatch({ kind: "search-current", current: next });
    this.followMatch(next);
    return this.getSnapshot();
  };

  /** The starting rule of every recompute (bead 2wu.1): the first match is
   *  looked up at-or-below the current selection's visible index — the
   *  smallest selected index; an empty selection starts from the top. */
  private selectionStartIndex = (): number => {
    const selected = this.state.selection.selected;
    return selected.length === 0 ? 0 : Math.min(...selected);
  };

  /** searchVisible recompute: replaces the slice's matches, derives the
   *  current match from the starting rule and selects/centers it (§8
   *  action 2: scroll and highlight the first match). An empty (or
   *  non-string — coerced) query or a closed panel clears the matches
   *  («0 of 0») WITHOUT an invoke: the empty pattern short-circuits
   *  locally per the backend contract. */
  private refreshMatches = async (): Promise<void> => {
    const search = this.state.search;
    if (!search.open || this.state.file === null) {
      return;
    }
    if (this.mutating > 0) {
      // Mid-differential: the recompute re-arms itself (and the mutation's
      // end-of-round snapshot dispatch re-arms it anyway); scanning a
      // partially-applied differential is exactly the live round-3 drift.
      this.scheduleSearchRefresh();
      return;
    }
    const query = this.safeQuery();
    if (query === "") {
      this.dispatch({ kind: "search-result", positions: [], current: null });
      return;
    }
    const token = ++this.searchToken;
    // The epoch at invoke time: the result belongs to the visible sequence
    // the backend saw when the scan started (with 1M+ rows it resolves
    // seconds later).
    const startEpoch = this.state.visibilityEpoch;
    let result: { total: number; positions: number[] };
    try {
      result = await ipc().searchVisible(search.mode ?? "plain", query);
    } catch (e) {
      // §2 error path: a failed recompute surfaces as a message, the
      // previous matches stay.
      this.dispatch({ kind: "load-error", message: String(e) });
      return;
    }
    if (token !== this.searchToken) {
      // A newer recompute owns the slice; it re-reads state at its own
      // resolution.
      return;
    }
    if (!this.state.search.open) {
      return;
    }
    if (this.state.visibilityEpoch !== startEpoch) {
      // Live round 2: the visible sequence moved under the scan — the
      // result belongs to an older sequence and must NOT land. The
      // correcting recompute reschedules HERE (self-healing: even when the
      // epoch change's own schedule was lost, nothing lands stale and
      // nothing stays one recompute behind).
      this.scheduleSearchRefresh();
      return;
    }
    const start = this.selectionStartIndex();
    // The current match is the first position at-or-below the start (its
    // INDEX into positions; positions are ascending). Cyclic read: when no
    // match sits at-or-below, the search wraps to the first match (§8).
    const foundIndex = result.positions.findIndex((p) => p >= start);
    const current =
      result.positions.length === 0
        ? null
        : foundIndex === -1
          ? 0
          : foundIndex;
    this.dispatch({ kind: "search-result", positions: result.positions, current });
    if (current !== null) {
      this.followMatch(current);
    }
  };

  /** A match becomes the selection (the click event, multi-select untouched)
   *  and centers via the existing scrollToRow table handle; no table
   *  (unit/headless runs) skips the scroll silently. */
  private followMatch = (matchIndex: number): void => {
    const visibleIndex = this.state.search.positions[matchIndex];
    if (visibleIndex === undefined) {
      return;
    }
    this.dispatch({ kind: "selection-click", index: visibleIndex });
    if (!this.table) {
      return;
    }
    void (async () => {
      const lineNo = await this.lineAt(visibleIndex);
      if (lineNo !== null && this.table) {
        this.table.scrollToRow(lineNo);
      }
    })();
  };
}

export const console_ = new UiConsole();
