import { describe, expect, it } from "vitest";
import {
  appReducer,
  clampPanelWidth,
  expandedForToggleAll,
  initialPanelState,
  levelBarState,
  type AppState,
  type VisibilityState,
  initialAppState,
} from "./state";

function loadedState(): AppState {
  return appReducer(initialAppState(), {
    kind: "load-success",
    load: { format: "plain", lineCount: 2, categories: [], levels: [], loadMs: 5 },
    fileName: "log.txt",
  });
}

/** Snapshot in the fixed §11 level order, as the backend guarantees it. */
export function snapshot(overrides: Partial<VisibilityState> = {}): VisibilityState {
  return {
    visibleCount: 12,
    levels: [
      { level: "critical", enabled: true, count: 1 },
      { level: "error", enabled: true, count: 2 },
      { level: "warning", enabled: true, count: 3 },
      { level: "msg", enabled: true, count: 4 },
      { level: "debug", enabled: true, count: 1 },
      { level: "trace", enabled: true, count: 1 },
    ],
    filters: [{ id: 0, mode: "plain", pattern: "timeout", enabled: true }],
    pins: [],
    categoriesEnabled: ["app/db"],
    ...overrides,
  };
}

describe("open/load pipeline (n4y.2, §2)", () => {
  it("starts empty with no error and no loading flag", () => {
    const s = initialAppState();
    expect(s.screen).toBe("empty");
    expect(s.error).toBeNull();
    expect(s.loadingFile).toBeNull();
  });

  it("load-request remembers the file and shows a loading screen", () => {
    const s = appReducer(initialAppState(), {
      kind: "load-request",
      path: "/tmp/log.txt",
    });
    expect(s.screen).toBe("empty-loading");
    expect(s.loadingFile).toBe("/tmp/log.txt");
  });

  it("load-success switches to loaded and clears the loading flag", () => {
    const s = appReducer(
      appReducer(initialAppState(), { kind: "load-request", path: "/tmp/log.txt" }),
      {
        kind: "load-success",
        load: { format: "plain", lineCount: 2, categories: [], levels: [], loadMs: 5 },
        fileName: "log.txt",
      },
    );
    expect(s.screen).toBe("loaded");
    expect(s.file?.name).toBe("log.txt");
    expect(s.file?.load.lineCount).toBe(2);
    expect(s.loadingFile).toBeNull();
  });

  it("load-error shows the message and does not lose the empty screen", () => {
    const s = appReducer(
      appReducer(initialAppState(), { kind: "load-request", path: "/missing" }),
      { kind: "load-error", message: "cannot open /missing" },
    );
    expect(s.screen).toBe("empty");
    expect(s.error).toBe("cannot open /missing");
    expect(s.loadingFile).toBeNull();
    expect(s.file).toBeNull();
  });

  it("an error after a successful load keeps the previous file (no data loss, §2)", () => {
    const s = appReducer(loadedState(), {
      kind: "load-error",
      message: "boom",
    });
    expect(s.error).toBe("boom");
    expect(s.screen).toBe("loaded");
    expect(s.file).not.toBeNull();
  });

  it("remember-dialog-dir stores the last opened directory", () => {
    const s = appReducer(initialAppState(), {
      kind: "remember-dialog-dir",
      dir: "/tmp/logs",
    });
    expect(s.lastDir).toBe("/tmp/logs");
  });

  it("new load request clears the previous error, not the loaded file (§2)", () => {
    const failing = appReducer(loadedState(), { kind: "load-error", message: "boom" });
    const s = appReducer(failing, { kind: "load-request", path: "/next.txt" });
    expect(s.error).toBeNull();
    expect(s.file).not.toBeNull();
    // §2: current content stays visible until the new result is applied.
    expect(s.screen).toBe("loaded");
    expect(s.loadingFile).toBe("/next.txt");
  });
});

describe("row selection state (§4, qt7.2)", () => {
  const base = { format: "plain", lineCount: 20, categories: [], levels: [], loadMs: 5 };

  it("starts with an empty selection", () => {
    expect(initialAppState().selection).toEqual({ selected: [], anchor: null });
  });

  it("click selects one row and sets the anchor", () => {
    const s = appReducer(loadedState(), { kind: "selection-click", index: 4 });
    expect(s.selection).toEqual({ selected: [4], anchor: 4 });
  });

  it("toggle adds and removes a row, replacing the anchor each time", () => {
    const s0 = appReducer(loadedState(), { kind: "selection-toggle", index: 3 });
    const s1 = appReducer(s0, { kind: "selection-toggle", index: 7 });
    expect(s1.selection.selected).toEqual([3, 7]);
    expect(s1.selection.anchor).toBe(7);
    const s2 = appReducer(s1, { kind: "selection-toggle", index: 3 });
    expect(s2.selection.selected).toEqual([7]);
    expect(s2.selection.anchor).toBe(3);
  });

  it("range extends from the anchor and keeps the anchor", () => {
    const s0 = appReducer(loadedState(), { kind: "selection-click", index: 3 });
    const s1 = appReducer(s0, { kind: "selection-range", index: 7 });
    expect(s1.selection.selected).toEqual([3, 4, 5, 6, 7]);
    expect(s1.selection.anchor).toBe(3);
  });

  it("load-success resets the selection: indexes are per file", () => {
    const s0 = appReducer(loadedState(), { kind: "selection-click", index: 4 });
    const s1 = appReducer(s0, { kind: "load-request", path: "/next.txt" });
    expect(s1.selection).toEqual({ selected: [], anchor: null });
    const s2 = appReducer(s1, {
      kind: "load-success",
      load: { ...base, lineCount: 100 },
      fileName: "next.txt",
    });
    expect(s2.selection).toEqual({ selected: [], anchor: null });
  });
});

describe("visibility state (§7, dsq.3)", () => {
  it("starts with no visibility snapshot and zero epochs", () => {
    const s = initialAppState();
    expect(s.visibility).toBeNull();
    expect(s.visibilityEpoch).toBe(0);
    expect(s.fileEpoch).toBe(0);
  });

  it("visibility event stores the snapshot and bumps the visibility epoch", () => {
    const s0 = appReducer(initialAppState(), { kind: "visibility", snapshot: snapshot() });
    expect(s0.visibility).toEqual(snapshot());
    expect(s0.visibilityEpoch).toBe(1);
    expect(s0.fileEpoch).toBe(0);
    const s1 = appReducer(s0, {
      kind: "visibility",
      snapshot: snapshot({ visibleCount: 5 }),
    });
    expect(s1.visibility?.visibleCount).toBe(5);
    expect(s1.visibilityEpoch).toBe(2);
  });

  it("selection-remap replaces the indexes by line number and moves the anchor (§4, qt7.3)", () => {
    const s0 = appReducer(loadedState(), { kind: "selection-click", index: 3 });
    const s1 = appReducer(s0, {
      kind: "selection-remap",
      indexes: [2, 5, 9],
      anchor: 2,
    });
    expect(s1.selection).toEqual({ selected: [2, 5, 9], anchor: 2 });
  });

  it("selection-remap with an unresolvable anchor clears it but keeps the indexes", () => {
    const s0 = appReducer(loadedState(), { kind: "selection-click", index: 3 });
    const s1 = appReducer(s0, {
      kind: "selection-remap",
      indexes: [0],
      anchor: null,
    });
    expect(s1.selection).toEqual({ selected: [0], anchor: null });
  });

  it("selection-remap bumps neither epoch (visibility-epoch handles the refill)", () => {
    const s = appReducer(loadedState(), {
      kind: "selection-remap",
      indexes: [1],
      anchor: 1,
    });
    expect(s.visibilityEpoch).toBe(0);
    expect(s.fileEpoch).toBe(1);
  });

  it("visibility events keep the selection untouched (qt7.3 owns remapping)", () => {
    const s0 = appReducer(loadedState(), { kind: "selection-click", index: 4 });
    const s1 = appReducer(s0, { kind: "visibility", snapshot: snapshot() });
    expect(s1.selection).toEqual(s0.selection);
    expect(s1.selection.selected).toEqual([4]);
  });

  it("load-success resets visibility and bumps the file epoch", () => {
    const s0 = appReducer(initialAppState(), { kind: "visibility", snapshot: snapshot() });
    const s1 = appReducer(s0, { kind: "load-request", path: "/next.txt" });
    const s2 = appReducer(s1, {
      kind: "load-success",
      load: { format: "plain", lineCount: 100, categories: [], levels: [], loadMs: 5 },
      fileName: "next.txt",
    });
    expect(s2.visibility).toBeNull();
    expect(s2.fileEpoch).toBe(1);
    expect(s2.visibilityEpoch).toBe(1); // unchanged: no fresh snapshot yet
  });

  it("selection events bump neither epoch", () => {
    const s = appReducer(loadedState(), { kind: "selection-toggle", index: 1 });
    expect(s.visibilityEpoch).toBe(0);
    expect(s.fileEpoch).toBe(1);
  });
});

describe("levelBarState (§11 mapping)", () => {
  it("returns null while no snapshot is known (empty bar state)", () => {
    expect(levelBarState(null)).toBeNull();
  });

  it("maps the fixed-order levels to counts and enabled flags", () => {
    const bar = levelBarState(
      snapshot({
        levels: [
          { level: "critical", enabled: true, count: 7 },
          { level: "error", enabled: true, count: 96 },
          { level: "warning", enabled: true, count: 1000 },
          { level: "msg", enabled: true, count: 24000 },
          { level: "debug", enabled: false, count: 405 },
          { level: "trace", enabled: true, count: 681 },
        ],
      }),
    );
    expect(bar).not.toBeNull();
    expect(bar?.counts).toEqual({
      critical: 7,
      error: 96,
      warning: 1000,
      msg: 24000,
      debug: 405,
      trace: 681,
    });
    expect(bar?.enabled).toEqual({
      critical: true,
      error: true,
      warning: true,
      msg: true,
      debug: false,
      trace: true,
    });
  });

  it("spec interpretation: a level missing from the snapshot counts 0 and stays enabled", () => {
    const bar = levelBarState(
      snapshot({
        levels: [
          { level: "msg", enabled: true, count: 12 },
          { level: "error", enabled: false, count: 3 },
        ],
      }),
    );
    expect(bar?.counts.critical).toBe(0);
    expect(bar?.counts.msg).toBe(12);
    expect(bar?.counts.trace).toBe(0);
    expect(bar?.enabled.error).toBe(false);
    expect(bar?.enabled.trace).toBe(true);
  });
});

describe("side panel slice (rhl.2, §10.1)", () => {
  it("panel defaults: open, categories tab, 220 px, empty search, nothing expanded", () => {
    const p = initialPanelState();
    expect(p).toEqual({ open: true, tab: "categories", width: 220, search: "", expanded: [] });
  });

  it("panel-toggle flips open without touching the rest", () => {
    const s0 = appReducer(initialAppState(), { kind: "panel-toggle" });
    expect(s0.panel.open).toBe(false);
    const s1 = appReducer(s0, { kind: "panel-toggle" });
    expect(s1.panel.open).toBe(true);
    // Ctrl+B only toggles: tab, width, search, expansion survive.
    expect(s1.panel.tab).toBe("categories");
    expect(s1.panel.width).toBe(220);
  });

  it("panel-tab switches the active tab", () => {
    const s = appReducer(initialAppState(), { kind: "panel-tab", tab: "filters" });
    expect(s.panel.tab).toBe("filters");
  });

  it("panel-width clamps into the 180-480 px band (splitter drag bounds)", () => {
    expect(appReducer(initialAppState(), { kind: "panel-width", width: 50 }).panel.width).toBe(180);
    expect(appReducer(initialAppState(), { kind: "panel-width", width: 900 }).panel.width).toBe(480);
    expect(appReducer(initialAppState(), { kind: "panel-width", width: 300 }).panel.width).toBe(300);
  });

  it("clampPanelWidth is the pure clamp used by the reducer", () => {
    expect(clampPanelWidth(0)).toBe(180);
    expect(clampPanelWidth(200)).toBe(200);
    expect(clampPanelWidth(10000)).toBe(480);
  });

  it("panel-search stores the query verbatim", () => {
    const s = appReducer(initialAppState(), { kind: "panel-search", query: "db" });
    expect(s.panel.search).toBe("db");
  });

  it("panel-expansion-toggle adds and removes one path", () => {
    const s0 = appReducer(initialAppState(), { kind: "panel-expansion-toggle", path: "app" });
    expect(s0.panel.expanded).toEqual(["app"]);
    const s1 = appReducer(s0, { kind: "panel-expansion-toggle", path: "db" });
    expect(s1.panel.expanded).toEqual(["app", "db"]);
    const s2 = appReducer(s1, { kind: "panel-expansion-toggle", path: "app" });
    expect(s2.panel.expanded).toEqual(["db"]);
  });

  it("load-success resets expansion to the loaded file's top-level paths", () => {
    const s = loadedWithCategories({ categories: [
      { path: "app/main/db", count: 1 },
      { path: "app/harness", count: 1 },
      { path: "db/pool", count: 1 },
      { path: "uncategorized", count: 1 },
    ] });
    expect(s.panel.expanded).toEqual(["app", "db", "uncategorized"]);
    expect(s.panel.open).toBe(true);
    expect(s.panel.tab).toBe("categories");
  });

  it("expansion survives every rebuild except file reload", () => {
    const s0 = appReducer(initialAppState(), {
      kind: "panel-expansion-toggle",
      path: "app/main",
    });
    const loaded = appReducer(s0, {
      kind: "load-success",
      load: { format: "plain", lineCount: 0, categories: [], levels: [], loadMs: 1 },
      fileName: "x.log",
    });
    // file reload resets expansion
    expect(loaded.panel.expanded).toEqual([]);
    const expandedAgain = appReducer(loaded, { kind: "panel-expansion-toggle", path: "app" });
    const s1 = appReducer(expandedAgain, { kind: "visibility", snapshot: snapshot() });
    // visibility rebuild keeps it
    expect(s1.panel.expanded).toEqual(["app"]);
  });

  it("expandedForToggleAll: expand installs every tree path incl. prefix paths", () => {
    const flat = [
      { path: "app/main/db", count: 1 },
      { path: "db/pool", count: 1 },
    ];
    expect(expandedForToggleAll(flat, true)).toEqual([
      "app", "app/main", "app/main/db", "db", "db/pool",
    ]);
  });

  it("expandedForToggleAll: collapse keeps only the roots expanded (§10 action 5)", () => {
    const flat = [
      { path: "app/main/db", count: 1 },
      { path: "app/main/config/runtime", count: 1 },
      { path: "db/pool", count: 1 },
      { path: "uncategorized", count: 1 },
    ];
    expect(expandedForToggleAll(flat, false)).toEqual([
      "app", "db", "uncategorized",
    ]);
  });
});

function loadedWithCategories(overrides: { categories?: { path: string; count: number }[] } = {}): AppState {
  return appReducer(initialAppState(), {
    kind: "load-success",
    load: {
      format: "plain",
      lineCount: 2,
      categories: overrides.categories ?? [],
      levels: [],
      loadMs: 5,
    },
    fileName: "log.txt",
  });
}
