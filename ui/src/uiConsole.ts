//! UI console: the text interface over the app state (building-testable-apps
//! rule 6). App renders from it, the headless harness acts on it - one
//! reducer, no window required. The load action runs through the same IPC
//! adapter as the button flow (stubbed in headless runs).

import { appReducer, initialAppState, type AppState, type AppEvent } from "./state";
import type { VisibilityState } from "./state";
import { ipc } from "./ipcClient";

export interface ConsoleSnapshot {
  screen: AppState["screen"];
  error: string | null;
  loadingFile: string | null;
  file: { name: string; format: string; lineCount: number } | null;
  selection: { selected: number[]; anchor: number | null };
  /** Latest applied visibility snapshot (§7); null before the first one. */
  visibility: VisibilityState | null;
}

/** Copy column selection: raw file lines or the Message column (§4). */
export type CopyMode = "raw" | "message";

interface TableHandle {
  scrollToRow(lineNo: number): void;
  /** Builds the copy text for the selection (loading uncached rows),
   * writes it to the clipboard and returns it for assertions. */
  copy(mode: CopyMode): Promise<string>;
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
    };
  };

  dispatch = (event: AppEvent): void => {
    this.state = appReducer(this.state, event);
    this.listeners.forEach((l) => l());
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

  /** Refetches visibility_snapshot and applies it to the reducer. */
  private refreshVisibility = async (): Promise<void> => {
    try {
      const snapshot = await ipc().visibilitySnapshot();
      this.dispatch({ kind: "visibility", snapshot });
    } catch (e) {
      // §2: an error shows a message, the loaded data is not lost.
      this.dispatch({ kind: "load-error", message: String(e) });
    }
  };

  /** Runs one visibility mutation, then refetches and applies the snapshot;
   *  a failed mutation surfaces through the existing error state. */
  private mutateVisibility = async (
    mutator: () => Promise<unknown>,
  ): Promise<ConsoleSnapshot> => {
    try {
      await mutator();
    } catch (e) {
      this.dispatch({ kind: "load-error", message: String(e) });
      return this.getSnapshot();
    }
    await this.refreshVisibility();
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

  /** §12 pin RPC — symmetric with filters; the pins panel is q1f.1. */
  addPin = (mode: string, pattern: string): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().addPin(mode, pattern));
  setPinEnabled = (id: number, on: boolean): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().setPinEnabled(id, on));
  removePin = (id: number): Promise<ConsoleSnapshot> =>
    this.mutateVisibility(() => ipc().removePin(id));
}

export const console_ = new UiConsole();
