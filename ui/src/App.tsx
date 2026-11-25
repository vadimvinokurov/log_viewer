import {
  useCallback,
  useEffect,
  useSyncExternalStore,
} from "react";
import { console_ } from "./uiConsole";
import { ipc } from "./ipcClient";
import { installHeadlessConsole } from "./headless";
import { LogTable } from "./LogTable";
import { LevelBar } from "./LevelBar.tsx";
import { levelBarState, fileTitle } from "./state";
import { buildTree } from "./categories";
import { SidePanel, usePanelHotkey } from "./SidePanel.tsx";
import { CategoriesTab } from "./CategoriesTab.tsx";
import { FiltersTab } from "./FiltersTab.tsx";
import { PinnedTab } from "./PinnedTab.tsx";
import { HighlightsTab } from "./HighlightsTab.tsx";
import { SearchPanel } from "./SearchPanel.tsx";
import { UpdateBanner } from "./UpdateBanner.tsx";
import { CmdLine } from "./CmdLine.tsx";
import { EmptyState } from "./EmptyState";
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
  // §13 command line slice (bead 7rf.1): one store, a second read surface.
  const command = useSyncExternalStore(console_.subscribe, console_.getCmdline);
  const busy = state.loadingFile !== null;

  useEffect(() => installHeadlessConsole(), []);

  // §10.1: Ctrl+Cmd+B collapses/reopens the side panel; the listener lives
  // with the shell because the panel unmounts when closed.
  const togglePanel = useCallback(() => {
    console_.togglePanel();
  }, []);
  usePanelHotkey(togglePanel);

  // §8 keydown rules (bead 2wu.1). The panel owns the arrows while open
  // (also when the focus sits in its input); while closed, plain Up/Down
  // move the selection over the visible rows, clamped at the edges (spec
  // interpretation: «обычная навигация»), and text fields keep caret
  // navigation. Esc closes; Ctrl/Cmd+F opens with a file loaded only.
  useEffect(() => {
    const handler = (e: KeyboardEvent): void => {
      // §13/: over the table pre-fills the field with ':' and focuses it
      // (§14 hotkey list). A ':' typed inside any text input (the cmdline
      // field itself, the panel searches) types normally.
      if (e.key === ":" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const source = e.target;
        if (
          !(
            source instanceof HTMLInputElement ||
            source instanceof HTMLTextAreaElement ||
            source instanceof HTMLSelectElement ||
            (source instanceof HTMLElement && source.isContentEditable)
          )
        ) {
          e.preventDefault();
          console_.activateCmdline();
          return;
        }
      }
      const current = console_.getState();
      // §14/§2.1 (bead n4y.2): Ctrl+R / Cmd+R reloads; preventDefault keeps
      // the webview from reloading the PAGE itself.
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "r") {
        e.preventDefault();
        if (current.file !== null && current.loadingFile === null) {
          void console_.load(current.file.path);
        }
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
        if (current.file !== null && current.search.open === false) {
          e.preventDefault();
          console_.openSearch();
        }
        return;
      }
      if (current.search.open) {
        if (e.key === "Escape") {
          e.preventDefault();
          console_.closeSearch();
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          console_.nextMatch(1);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          console_.nextMatch(-1);
        }
        return;
      }
      if ((e.key !== "ArrowDown" && e.key !== "ArrowUp") || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) {
        return;
      }
      const target = e.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return;
      }
      if (current.file === null || current.selection.selected.length === 0) {
        return;
      }
      const visibleCount = current.visibility?.visibleCount ?? current.file.load.lineCount;
      // The plain-arrow navigation moves the single selection from the
      // smallest selected index; it changes the selection only (scrolling
      // is the viewport anchor's business, §4).
      const from = Math.min(...current.selection.selected);
      const to = e.key === "ArrowDown" ? Math.min(from + 1, visibleCount - 1) : Math.max(from - 1, 0);
      if (to !== from) {
        e.preventDefault();
        console_.selectRow(to, "click");
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // §2 Open flow: the dialog starts in the console's lastDir — the §15
  // last_open_dir setting, seeded at console construction and updated here
  // by every successful open (console.load persists dirname too).
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

  // The file indicator lives in the NATIVE window title (2026-11-25 owner
  // decision, mock titlebar): "log.txt · 183 MB" — the bottom bar shows
  // Open/Reload/command line/levels only. Outside a real webview (headless
  // visual runs) there is no native window; the title effect is a no-op.
  useEffect(() => {
    const name = state.file?.name;
    const sizeBytes = state.file?.load.sizeBytes;
    if (name === undefined || sizeBytes === undefined) {
      return;
    }
    void (async () => {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().setTitle(fileTitle(name, sizeBytes));
      } catch {
        // headless/browser runs have no native title to set
      }
    })();
  }, [state.file]);

  const status = (() => {
    return busy ? `loading ${lastPathSegment(state.loadingFile ?? "")}…` : null;
  })();

  // §4/§7: the table paginates the VISIBLE sequence, so its row count is the
  // snapshot's visible count; only while the first snapshot is still in
  // flight does the load fallback apply. Epochs drive the table's resets.
  const rowCount = state.visibility?.visibleCount ?? state.file?.load.lineCount ?? 0;
  const bar = levelBarState(state.visibility);

  return (
    <div className="app">
      <div className="workspace">
        <main className="content">
          {/* Auto-update banner (plan 2026-11-25): floats top-center over
              the table; visible only in the phases bannerVisible() names. */}
          <UpdateBanner />
          {show ? (
            <DevShowcase name={show} />
          ) : state.file ? (
            <LogTable
              ref={(h) => console_.setTableHandle(h)}
              rowCount={rowCount}
              fileEpoch={state.fileEpoch}
              visibilityEpoch={state.visibilityEpoch}
              selection={state.selection}
              // §12: the snapshot's pin list drives the context menu's §4
              // Pin/Unpin presence (evaluation lives in pins.ts).
              pins={state.visibility?.pins ?? []}
              onRowClick={(i, kind) => {
                console_.selectRow(i, kind);
              }}
            />
          ) : (
            <div className="empty-state">
              <EmptyState />
            </div>
          )}
          {/* §8: the find bar floats top-right of the table while open. */}
          {state.file && state.search.open && (
            <div className="findbar-dock">
              <SearchPanel
                search={state.search}
                onQuery={(query) => console_.setSearchQuery(query)}
                // Clicking an active tumbler returns to plain: the console
                // maps any non-regex/simple value to the both-off state.
                onTumbler={(mode) => console_.setSearchMode(mode ?? "plain")}
                onNext={() => console_.nextMatch(1)}
                onPrev={() => console_.nextMatch(-1)}
                onClose={() => console_.closeSearch()}
              />
            </div>
          )}
        </main>
        {/* §10.1: the panel docks right beside the table, only with a file
            (furniture of the working surface like the LevelBar). */}
        {state.file && (
          <SidePanel
            panel={state.panel}
            onToggle={togglePanel}
            onTab={(tab) => console_.setPanelTab(tab)}
            onWidth={(px) => console_.setPanelWidth(px)}
            content={{
              categories: (
                <CategoriesTab
                  tree={buildTree(state.file.load.categories)}
                  flat={state.file.load.categories}
                  enabled={state.visibility?.categoriesEnabled ?? []}
                  search={state.panel.search}
                  expanded={state.panel.expanded}
                  onToggle={(path, on) => void console_.toggleCategory(path, on)}
                  onToggleAll={(on) => void console_.setAllCategories(on)}
                  onSearch={(query) => console_.setCategorySearch(query)}
                  onExpandAll={(expand) => console_.expandAllCategories(expand)}
                  onToggleExpand={(path) => console_.toggleExpansion(path)}
                />
              ),
              filters: (
                <FiltersTab
                  items={state.visibility?.filters ?? []}
                  onToggle={(id, on) => void console_.toggleFilter(id, on)}
                  onRemove={(id) => void console_.removeFilter(id)}
                />
              ),
              pinned: (
                <PinnedTab
                  items={state.visibility?.pins ?? []}
                  onToggle={(id, on) => void console_.setPinEnabled(id, on)}
                  onRemove={(id) => void console_.removePin(id)}
                />
              ),
              // §9 (exx.2): the color dot's system picker (webview
              // <input type="color">) drives set_highlight_color; the
              // console refetches the snapshot after each mutation.
              highlights: (
                <HighlightsTab
                  items={state.visibility?.highlights ?? []}
                  onToggle={(id, on) => void console_.setHighlightEnabled(id, on)}
                  onColor={(id, hex) => void console_.setHighlightColor(id, hex)}
                  onRemove={(id) => void console_.removeHighlight(id)}
                />
              ),
            }}
          />
        )}
      </div>
      <footer className="bottom-bar">
        {/* No file indicator here: "name · size" lives in the native window
            title (2026-11-25 owner decision, see the title effect above). */}
        <button className="bar-btn" onClick={openDialogAndLoad} disabled={busy}>
          Open
        </button>
        <button className="bar-btn" onClick={reload} disabled={busy || !state.file}>
          Reload
        </button>
        {/* §11.1/§13: the flat command input sits between Reload and the
            status area (see CmdLine.tsx for the keyboard rules). */}
        <CmdLine
          command={command}
          onText={(text) => console_.setCommandText(text)}
          onSubmit={() => void console_.submitCommand()}
          onClear={() => console_.clearCommand()}
          onRecall={(dir) => console_.recallCommandHistory(dir)}
        />
        {busy && <span className="status">{status}</span>}
        {state.error && <span className="error">{state.error}</span>}
        {/* §11: the six-level toggle bar on the right side of the bottom bar;
            hidden until the first visibility snapshot arrives. */}
        {bar && (
          <LevelBar
            counts={bar.counts}
            enabled={bar.enabled}
            onToggle={(level) => void console_.setLevel(level, !bar.enabled[level])}
          />
        )}
      </footer>
    </div>
  );
}
