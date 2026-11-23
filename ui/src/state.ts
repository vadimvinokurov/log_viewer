//! Application state machine for the shell (FUNCTIONAL_SPEC §2, §2.1).
//!
//! Pure logic: data structures in, data structures out; the App component
//! maps events to this reducer. Reload/filters semantics (§2.1) grow here as
//! the filter, search and highlights epics land; the file-open lifecycle is
//! the part this file owns today.

/// The load result as received over IPC (mirrors bindings `LoadResult`
/// structurally; tests run in plain vitest without generated types).
export interface LoadInfo {
  format: string;
  lineCount: number;
  categories: { path: string; count: number }[];
  levels: { level: string; count: number }[];
  loadMs: number;
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
}

export type AppEvent =
  | { kind: "load-request"; path: string }
  | { kind: "load-success"; load: LoadInfo; fileName: string }
  | { kind: "load-error"; message: string }
  | { kind: "remember-dialog-dir"; dir: string };

export function initialAppState(): AppState {
  return {
    screen: "empty",
    file: null,
    loadingFile: null,
    error: null,
    lastDir: "",
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
      };
    case "load-success":
      return {
        ...state,
        screen: "loaded",
        file: { name: event.fileName, path: event.fileName ? state.loadingFile ?? event.fileName : state.loadingFile ?? "", load: event.load },
        loadingFile: null,
        error: null,
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
  }
}
