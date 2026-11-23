import {
  useCallback,
  useEffect,
  useSyncExternalStore,
} from "react";
import { console_ } from "./uiConsole";
import { ipc } from "./ipcClient";
import { installHeadlessConsole } from "./headless";
import { LogTable } from "./LogTable";
import DevShowcase from "./devShowcase";

function lastPathSegment(path: string): string {
  const i = Math.max(path.lastIndexOf("/"), 0);
  return path.slice(i === 0 ? 0 : i + 1);
}

/**
 * Shell (FUNCTIONAL_SPEC §2, §2.1; UI design: 38-px bottom bar). State and
 * actions flow through the uiConsole store, which is also the headless text
 * interface (installHeadlessConsole) - one reducer, two front doors.
 */
export default function App() {
  const show = new URLSearchParams(window.location.search).get("show");
  const state = useSyncExternalStore(console_.subscribe, console_.getState);
  const busy = state.loadingFile !== null;

  useEffect(() => installHeadlessConsole(), []);

  const openDialogAndLoad = useCallback(async () => {
    const file = await ipc().pickFile(state.lastDir);
    if (file) {
      void console_.load(file);
    }
  }, [state.lastDir]);

  const reload = useCallback(() => {
    if (state.file && !busy) {
      // §2.1: file is re-read from disk; kept state (filters, levels,
      // categories by name, highlights) lives with later epics.
      void console_.load(state.file.path);
    }
  }, [state.file, busy]);

  // Drag-and-drop: first dropped file wins (§2). Tauri exposes real paths
  // through the drag-drop event, not the DOM drop event.
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    void (async () => {
      try {
        const { getCurrentWebview } = await import("@tauri-apps/api/webview");
        const webview = getCurrentWebview();
        unlisten = await webview.onDragDropEvent((event) => {
          if (event.payload.type === "drop") {
            const path = event.payload.paths[0];
            if (path) {
              void console_.load(path);
            }
          }
        });
      } catch {
        // Outside a real webview (headless visual runs): drag-drop is absent.
      }
    })();
    return () => unlisten?.();
  }, []);

  const status = (() => {
    return busy ? `loading ${lastPathSegment(state.loadingFile ?? "")}…` : null;
  })();

  return (
    <div className="app">
      <main className="content">
        {show ? (
          <DevShowcase name={show} />
        ) : state.file ? (
          <LogTable
            ref={(h) => console_.setTableHandle(h)}
            rowCount={state.file.load.lineCount}
          />
        ) : (
          <div className="empty-state">
            <p>Drop a log file here or click Open</p>
          </div>
        )}
      </main>
      <footer className="bottom-bar">
        <span className="file-name">{state.file?.name}</span>
        <button className="bar-btn" onClick={openDialogAndLoad} disabled={busy}>
          Open
        </button>
        <button className="bar-btn" onClick={reload} disabled={busy || !state.file}>
          Reload
        </button>
        {busy && <span className="status">{status}</span>}
        {state.file && !busy && (
          <span className="status">
            {state.file.name} · {state.file.load.format} ·{" "}
            {state.file.load.lineCount.toLocaleString("en-US")} lines · {state.file.load.loadMs} ms
          </span>
        )}
        {state.error && <span className="error">{state.error}</span>}
      </footer>
    </div>
  );
}
