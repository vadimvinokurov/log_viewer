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
import type { HighlightItem } from "./highlights";
import {
  DEFAULT_COLUMN_WIDTHS,
  resetWidth,
  setWidth,
  type ColumnKey,
  type ColumnWidths,
} from "./columnWidths.ts";

export interface LoadInfo {
  format: string;
  lineCount: number;
  /** Byte size of the backing file (UI file slot: "name · size"). */
  sizeBytes: number;
  categories: { path: string }[];
  levels: { level: string; count: number }[];
  loadMs: number;
}

/** Humanized byte size for the file slot ("name · size" per the UI design):
 *  decimal units, whole KB/MB like the mock «842 MB», one decimal in GB. */
export function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`;
  if (bytes < 1_000_000) return `${Math.round(bytes / 1000)} KB`;
  if (bytes < 1_000_000_000) return `${Math.round(bytes / 1_000_000)} MB`;
  return `${(bytes / 1_000_000_000).toFixed(1)} GB`;
}

/** The native window title per the UI design titlebar (2026-11-25 owner
 *  decision: the file indicator lives in the WINDOW TITLE, not in the
 *  bottom bar): "log.txt · 183 MB". */
export function fileTitle(name: string, sizeBytes: number): string {
  return `${name} · ${formatBytes(sizeBytes)}`;
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
 * Normalized visibility snapshot (fixed RAW IPC contract;
 * normalization happens only in ipcClient.ts). Filters/pins reuse the
 * FiltersTab item shape so the panel renders straight from state.
 */
export interface VisibilityState {
  visibleCount: number;
  levels: VisibilityLevel[];
  filters: FilterItem[];
  pins: FilterItem[];
  /** §9 highlight rules (exx.2); they SURVIVE reload (§2.1, unlike pins). */
  highlights: HighlightItem[];
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
  /** §10.1 side panel (rhl.2). */
  panel: PanelState;
  /** Resizable table columns (§4 defaults; design 2026-11-25): the USER
   *  widths — effective widths render from them in LogTable. */
  columnWidths: ColumnWidths;
  /** §8 search panel (bead 2wu.1). */
  search: SearchState;
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
  | { kind: "visibility"; snapshot: VisibilityState }
  // §10.1 side panel (rhl.2): pure UI state, no IPC behind the last four.
  | { kind: "panel-toggle" }
  | { kind: "panel-tab"; tab: PanelTab }
  | { kind: "panel-width"; width: number }
  | { kind: "panel-search"; query: string }
  | { kind: "panel-expansion-toggle"; path: string }
  | { kind: "panel-expanded"; expanded: string[] }
  // §8 search panel (bead 2wu.1): pure slice events; the match recomputation
  // lives in the console (IPC + debounce), never in the reducer.
  | { kind: "search-open" }
  | { kind: "search-close" }
  | { kind: "search-mode"; mode: SearchMode }
  | { kind: "search-query"; query: string }
  | { kind: "search-result"; positions: number[]; current: number | null }
  | { kind: "search-current"; current: number }
  // Resizable table columns (design 2026-11-25-column-resize): pure slice
  // events; the clamps live in the pure columnWidths module. The load event
  // carries the already-normalized widths from the settings round-trip.
  | { kind: "column-set"; key: ColumnKey; width: number }
  | { kind: "column-reset"; key: ColumnKey }
  | { kind: "column-load"; widths: ColumnWidths };

/** §10.1 panel tabs, in the designed order (docs/UI_DESIGN.html). */
export type PanelTab = "categories" | "filters" | "highlights" | "pinned";
export const PANEL_TABS: readonly PanelTab[] = ["categories", "filters", "highlights", "pinned"];

export interface PanelState {
  open: boolean;
  tab: PanelTab;
  width: number;
  /** Tree search query (§10); "" = no search active. */
  search: string;
  /** Expanded tree node paths. Tri-state and visibility are never stored. */
  expanded: string[];
}

// ---- §8 search panel (bead 2wu.1) ----

/**
 * §8 tumbler state: null = both tumblers off = plain substring; otherwise
 * exactly one of regex | simple is on (the tumblers are mutually exclusive;
 * clicking an active tumbler returns to plain, bead 2wu.1 interpretation).
 * The slice never stores "plain" — the console maps it to the RPC mode
 * string when it calls searchVisible.
 */
export type SearchMode = "regex" | "simple" | null;

/** The §8 search result (normalized in ipcClient): positions are 0-based
 *  indexes of the VISIBLE sequence, ascending. */
export interface SearchMatches {
  total: number;
  positions: number[];
}

export interface SearchState {
  open: boolean;
  mode: SearchMode;
  query: string;
  /** Current matches over the visible sequence; replaced on each recompute. */
  positions: number[];
  /** Index into positions of the current match; null when there are none. */
  current: number | null;
}

export function initialSearchState(): SearchState {
  return { open: false, mode: null, query: "", positions: [], current: null };
}

/** Spec interpretation (bead rhl.2, restyled 2026-11-25 mock e5bf7e3): the
 *  panel stands open, 280 px (logs UI_DESIGN mock, v1 splitter parity),
 *  bounds 180-480 px. */
export const PANEL_MIN_WIDTH = 180;
export const PANEL_MAX_WIDTH = 480;
export const PANEL_DEFAULT_WIDTH = 280;

export function clampPanelWidth(px: number): number {
  if (px < PANEL_MIN_WIDTH) {
    return PANEL_MIN_WIDTH;
  }
  return px > PANEL_MAX_WIDTH ? PANEL_MAX_WIDTH : px;
}

export function initialPanelState(): PanelState {
  return { open: true, tab: "categories", width: PANEL_DEFAULT_WIDTH, search: "", expanded: [] };
}

/** Expansion default at load: the synthetic All root (2026-11-25: All is a
 *  foldable parent of the top level) plus the root-level paths (no "/"),
 *  sorted, deduped — top-level nodes expanded, children collapsed (bead rhl.2
 *  spec interpretation). An empty file keeps the empty set. */
export function defaultExpanded(categories: readonly { path: string }[]): string[] {
  if (categories.length === 0) {
    return [];
  }
  const roots = new Set<string>([""]);
  for (const { path } of categories) {
    const i = path.indexOf("/");
    roots.add(i === -1 ? path : path.slice(0, i));
  }
  return [...roots].sort();
}

/** expand/collapse-all targets straight from the flat list (§10 action 5):
 *  expand installs every tree path including the implicit prefixes; collapse
 *  closes everything except the All root — it stays expanded so the top-level
 *  rows remain visible below the All row, each collapsed (2026-11-25 owner
 *  decision; a fully collapsed All would hide the whole top level). */
export function expandedForToggleAll(
  categories: readonly { path: string }[],
  expand: boolean,
): string[] {
  if (expand) {
    const paths = new Set<string>();
    // the All root opens together with the top level (2026-11-25)
    if (categories.length > 0) {
      paths.add("");
    }
    for (const { path } of categories) {
      paths.add(path);
      let i = path.indexOf("/");
      while (i !== -1) {
        paths.add(path.slice(0, i));
        i = path.indexOf("/", i + 1);
      }
    }
    return [...paths].sort();
  }
  return categories.length > 0 ? [""] : [];
}

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
    panel: initialPanelState(),
    search: initialSearchState(),
    columnWidths: { ...DEFAULT_COLUMN_WIDTHS },
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
        // §10 action 5: expansion does NOT survive a file reload — it
        // resets to the new file's root-level paths. The rest of the
        // panel state (open/tab/width/search) survives.
        panel: { ...state.panel, expanded: defaultExpanded(event.load.categories) },
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
    // §10.1 panel transitions (rhl.2): pure UI state.
    case "panel-toggle":
      return { ...state, panel: { ...state.panel, open: !state.panel.open } };
    case "panel-tab":
      return { ...state, panel: { ...state.panel, tab: event.tab } };
    case "panel-width":
      return { ...state, panel: { ...state.panel, width: clampPanelWidth(event.width) } };
    case "panel-search":
      return { ...state, panel: { ...state.panel, search: event.query } };
    case "panel-expansion-toggle": {
      const expanded = state.panel.expanded.includes(event.path)
        ? state.panel.expanded.filter((p) => p !== event.path)
        : [...state.panel.expanded, event.path].sort();
      return { ...state, panel: { ...state.panel, expanded } };
    }
    case "panel-expanded":
      return { ...state, panel: { ...state.panel, expanded: [...event.expanded].sort() } };
    // Resizable table columns (design 2026-11-25-column-resize).
    case "column-set":
      return { ...state, columnWidths: setWidth(state.columnWidths, event.key, event.width) };
    case "column-reset":
      return { ...state, columnWidths: resetWidth(state.columnWidths, event.key) };
    case "column-load":
      return { ...state, columnWidths: { ...event.widths } };
    // §8 search panel (bead 2wu.1): open/close keep mode, query and the
    // latest positions (reopening rescans the same query through the
    // console); a mode switch does not clear the previous matches — the
    // debounced recompute replaces them.
    case "search-open":
      return { ...state, search: { ...state.search, open: true } };
    case "search-close":
      return { ...state, search: { ...state.search, open: false } };
    case "search-mode":
      return { ...state, search: { ...state.search, mode: event.mode } };
    case "search-query":
      return { ...state, search: { ...state.search, query: event.query } };
    case "search-result":
      return {
        ...state,
        search: { ...state.search, positions: [...event.positions], current: event.current },
      };
    case "search-current":
      return { ...state, search: { ...state.search, current: event.current } };
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
