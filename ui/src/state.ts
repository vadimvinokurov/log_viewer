//! Application state machine for the shell (FUNCTIONAL_SPEC §2, §2.1).
//!
//! Pure logic: data structures in, data structures out; the App component
//! maps events to this reducer. Reload/filters semantics (§2.1) grow here as
//! the filter, search and highlights epics land; the file-open lifecycle is
//! the part this file owns today.

/// The load result as received over IPC (mirrors bindings `LoadResult`
/// structurally; tests run in plain vitest without generated types).
import { EMPTY_SELECTION, range, select, toggle, type SelectionState } from "./selection";
import { LEVEL_ORDER, type EnabledLevels, type Level, type LevelCounts } from "./levelBar";
import type { FilterItem } from "./filtersTab";

export interface LoadInfo {
  format: string;
  lineCount: number;
  categories: { path: string; count: number }[];
  levels: { level: string; count: number }[];
  loadMs: number;
}

/** One level entry of the visibility snapshot (camelCase, §7/§11). */
export interface VisibilityLevel {
  level: string;
  enabled: boolean;
  /** §11 counter: rows visible under current filters/categories if this
   *  level were enabled (ignores the level toggles). */
  count: number;
}

/**
 * Normalized visibility snapshot (docs/notes/visibility-bridge.md contract;
 * normalization happens only in ipcClient.ts). Filters/pins reuse the
 * FiltersTab item shape so the panel renders straight from state.
 */
export interface VisibilityState {
  visibleCount: number;
  levels: VisibilityLevel[];
  filters: FilterItem[];
  pins: FilterItem[];
  categoriesEnabled: string[];
}

export interface LoadedFile {
  name: string;
  path: string;
  load: LoadInfo;
}

/**
 * Screen states:
 *  - empty: no file, nothing loading (§2 empty state);
 *  - empty-loading: no previous file, load in progress, UI responsive;
 *  - loaded: a previous file is shown; a load in progress or a failed load
 *    never loses it (§2 "no data loss", §2.1 reload keeps old content until
 *    the new result arrives).
 */
export type Screen = "empty" | "empty-loading" | "loaded";

export interface AppState {
  screen: Screen;
  file: LoadedFile | null;
  /** Path currently being loaded, if any. */
  loadingFile: string | null;
  /** Last user-visible error message (§2: error, no data loss). */
  error: string | null;
  /** Directory used by the last successful Open (§2, §15 last_open_dir). */
  lastDir: string;
  /** Selected rows, 0-based, with the shift-click anchor (§4). */
  selection: SelectionState;
  /** Latest visibility snapshot; null until the first one arrives (§7). */
  visibility: VisibilityState | null;
  /** Bumped on every applied snapshot: the table's chunk-cache reset signal
   *  (equal-count changes must still refill, contract dsq.3). */
  visibilityEpoch: number;
  /** Bumped on every load-success: the table's full-reset signal (§4). */
  fileEpoch: number;
}

export type AppEvent =
  | { kind: "load-request"; path: string }
  | { kind: "load-success"; load: LoadInfo; fileName: string }
  | { kind: "load-error"; message: string }
  | { kind: "remember-dialog-dir"; dir: string }
  | { kind: "selection-click"; index: number }
  | { kind: "selection-toggle"; index: number }
  | { kind: "selection-range"; index: number }
  | { kind: "selection-remap"; indexes: number[]; anchor: number | null }
  | { kind: "visibility"; snapshot: VisibilityState };

export function initialAppState(): AppState {
  return {
    screen: "empty",
    file: null,
    loadingFile: null,
    error: null,
    lastDir: "",
    selection: EMPTY_SELECTION,
    visibility: null,
    visibilityEpoch: 0,
    fileEpoch: 0,
  };
}

export function appReducer(state: AppState, event: AppEvent): AppState {
  switch (event.kind) {
    case "load-request":
      return {
        ...state,
        // §2: the window stays responsive and the current content stays
        // visible until the new result is applied.
        screen: state.file === null ? "empty-loading" : "loaded",
        loadingFile: event.path,
        error: null,
        // Row indexes are per file: the selection does not survive a load.
        selection: initialAppState().selection,
      };
    case "load-success":
      return {
        ...state,
        screen: "loaded",
        file: { name: event.fileName, path: event.fileName ? state.loadingFile ?? event.fileName : state.loadingFile ?? "", load: event.load },
        loadingFile: null,
        error: null,
        // A new file makes the old snapshot stale; the fresh one arrives
        // right after through the visibility event.
        visibility: null,
        fileEpoch: state.fileEpoch + 1,
      };
    case "load-error":
      return {
        ...state,
        // §2: an error shows a message, data is not lost.
        screen: state.file === null ? "empty" : "loaded",
        error: event.message,
        loadingFile: null,
      };
    case "remember-dialog-dir":
      return { ...state, lastDir: event.dir };
    // §4 row-selection transitions; the pure transitions live in selection.ts.
    case "selection-click":
      return { ...state, selection: select(state.selection, event.index) };
    case "selection-toggle":
      return { ...state, selection: toggle(state.selection, event.index) };
    case "selection-range":
      return { ...state, selection: range(state.selection, event.index) };
    // §4 (qt7.3): after a visibility change the console re-resolves the
    // selection by line number and dispatches the new indexes here. The
    // anchor follows the remapped pivot (null when it cannot resolve); the
    // epochs stay untouched - the visibility event owns the table refill.
    case "selection-remap":
      return {
        ...state,
        selection: { selected: event.indexes, anchor: event.anchor },
      };
    // §7 visibility bridge: mutation actions reapply the refetched snapshot.
    // The selection stays untouched — qt7.3 remaps it by line_no.
    case "visibility":
      return { ...state, visibility: event.snapshot, visibilityEpoch: state.visibilityEpoch + 1 };
  }
}

export interface LevelBarData {
  counts: LevelCounts;
  enabled: EnabledLevels;
}

/** Maps the snapshot's level list onto the fixed six-level bar (§11).
 *  Spec interpretation: a level missing from the snapshot counts 0 and stays
 *  enabled — the backend sends the full fixed order, so this is defensive. */
export function levelBarState(visibility: VisibilityState | null): LevelBarData | null {
  if (visibility === null) {
    return null;
  }
  const byLevel = new Map(visibility.levels.map((l) => [l.level, l]));
  // Record<Level, number> needs all six keys; the literal mirrors LEVEL_ORDER
  // without a cast (strict-types rule).
  const counts: Record<Level, number> = { critical: 0, error: 0, warning: 0, msg: 0, debug: 0, trace: 0 };
  const enabled: Record<Level, boolean> = { critical: true, error: true, warning: true, msg: true, debug: true, trace: true };
  for (const level of LEVEL_ORDER) {
    const entry = byLevel.get(level);
    counts[level] = entry ? entry.count : 0;
    enabled[level] = entry ? entry.enabled : true;
  }
  return { counts, enabled };
}
