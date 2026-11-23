import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { appReducer, initialAppState } from "./state";
import { ipc } from "./ipcClient";

function parentDir(path: string): string {
  const i = path.lastIndexOf("/");
  return i > 0 ? path.slice(0, i) : path;
}

function lastPathSegment(path: string): string {
  const i = Math.max(path.lastIndexOf("/"), 0);
  return path.slice(i === 0 ? 0 : i + 1);
}

/**
 * Shell for the open/load pipeline (FUNCTIONAL_SPEC §2, §2.1; UI design:
 * 38-px bottom bar). The table lands with qt7.1; until then a loaded file
 * shows a line-count stub so the pipeline is verifiable end to end.
 */
export default function App() {
  const [state, dispatch] = useReducer(appReducer, undefined, initialAppState);
  const [version, setVersion] = useState(0); // reload re-runs on demand
  const busy = state.loadingFile !== null;
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const loadPath = useCallback(
    async (path: string) => {
      dispatch({ kind: "load-request", path });
      try {
        const load = await ipc().loadFile(path);
        dispatch({ kind: "load-success", load, fileName: lastPathSegment(path) });
        dispatch({ kind: "remember-dialog-dir", dir: parentDir(path) });
      } catch (e) {
        dispatch({ kind: "load-error", message: String(e) });
      }
    },
    [],
  );

  const openDialogAndLoad = useCallback(async () => {
    const file = await openDialog({
      directory: false,
      multiple: false,
      defaultPath: state.lastDir || undefined,
    });
    if (typeof file === "string") {
      await loadPath(file);
    }
  }, [state.lastDir, loadPath]);

  const reload = useCallback(async () => {
    if (state.file && !busy) {
      // §2.1: file is re-read from disk; kept state (filters, levels,
      // categories by name, highlights) lives with later epics and is not
      // cleared here; pins and search are cleared by their own owners.
      setVersion((v) => v + 1);
      await loadPath(state.file.path);
    }
  }, [state.file, state.loadingFile, loadPath]);

  // Drag-and-drop: first dropped file wins (§2).
  useEffect(() => {
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      const first = e.dataTransfer?.files?.[0];
      if (first) {
        // Web browsers hide the real path; Tauri does expose it via FS APIs.
        // The dialog flow is the primary path; DnD resolves the path via the
        // webUtils API if available.
        const w = window as unknown as { __TAURI_INTERNALS__?: unknown };
        if (w.__TAURI_INTERNALS__) {
          import("@tauri-apps/api/webview")
            .then(({ getCurrentWebview }) => {
              const webview = getCurrentWebview();
              return webview.onDragDropEvent((event) => {
                if (event.payload.type === "drop") {
                  void loadPath(event.payload.paths[0] ?? "");
                }
              });
            })
            .catch(() => undefined);
        }
      }
    };
    window.addEventListener("drop", onDrop);
    return () => window.removeEventListener("drop", onDrop);
  }, [loadPath]);

  const status = useMemo(() => {
    if (busy) {
      return `loading ${lastPathSegment(state.loadingFile ?? "")}…`;
    }
    if (state.file) {
      const { lineCount, format, loadMs } = state.file.load;
      return `${state.file.name} · ${format} · ${lineCount.toLocaleString()} lines · ${loadMs} ms`;
    }
    return null;
  }, [busy, state.file, state.loadingFile ]);

  return (
    <div className="app">
      <main className="content">
        {state.screen === "empty" ? (
          <div className="empty-state" onDragOver={(e) => e.preventDefault()}>
            <p>Drop a log file here or click Open</p>
          </div>
        ) : (
          <div className="loaded-stub">
            {/* Placeholder until the table epic lands (qt7.1). Reload is
                re-issued with the version counter so §2.1 semantics stay
                observable. */}
            {`v${version} · ${status}`}
          </div>
        )}
      </main>
      <footer className="bottom-bar">
        <button className="bar-btn" onClick={openDialogAndLoad} disabled={busy}>
          Open
        </button>
        <button className="bar-btn" onClick={reload} disabled={busy || !state.file}>
          Reload
        </button>
        {status && <span className="status">{status}</span>}
        {state.error && <span className="error">{state.error}</span>}
        {/* Hidden native input is unused; the dialog plugin owns Open. */}
        <input ref={fileInputRef} type="file" hidden readOnly />
      </footer>
    </div>
  );
}
