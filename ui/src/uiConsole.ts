//! UI console: the text interface over the app state (building-testable-apps
//! rule 6). App renders from it, the headless harness acts on it - one
//! reducer, no window required. The load action runs through the same IPC
//! adapter as the button flow (stubbed in headless runs).

import { appReducer, initialAppState, type AppState, type AppEvent } from "./state";
import { ipc } from "./ipcClient";

export interface ConsoleSnapshot {
  screen: AppState["screen"];
  error: string | null;
  loadingFile: string | null;
  file: { name: string; format: string; lineCount: number } | null;
}

interface TableHandle {
  scrollToRow(lineNo: number): void;
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
    return {
      screen: this.state.screen,
      error: this.state.error,
      loadingFile: this.state.loadingFile,
      file: f ? { name: f.name, format: f.load.format, lineCount: f.load.lineCount } : null,
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
      } catch (e) {
        this.dispatch({ kind: "load-error", message: String(e) });
      }
      return this.getSnapshot();
    })();
  };
}

export const console_ = new UiConsole();
