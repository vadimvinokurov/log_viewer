//! uiConsole tests (dsq.3): visibility mutations through the console RPC
//! refetch the snapshot and dispatch it into the reducer; failures surface
//! through the existing error state. The module singleton is re-imported
//! fresh per test so the narrative runs stay isolated.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installHeadlessConsole } from "./headless";
import type { RawIpc } from "./ipcClient";
import type { RowDto, VisibilitySnapshotDto } from "./bindings";

/** The five §9 highlight RAW methods, no-op defaults (exx.2); the highlight
 *  describe swaps the ones it needs. */
const highlightNoops = (): Pick<
  RawIpc,
  "addHighlight" | "setHighlightEnabled" | "setHighlightColor" | "removeHighlight" | "clearHighlights"
> => ({
  addHighlight: async () => null,
  setHighlightEnabled: async () => null,
  setHighlightColor: async () => null,
  removeHighlight: async () => null,
  clearHighlights: async () => null,
});


/** RAW stub mirroring the contract shapes with an in-memory visibility model. */
function visibilityStub(options: { failMutation?: string } = {}): RawIpc {
  const enabledLevels: Record<string, boolean> = {
    critical: true,
    error: true,
    warning: true,
    msg: true,
    debug: true,
    trace: true,
  };
  const filters: { id: number; mode: string; pattern: string; enabled: boolean }[] = [];
  const pins: { id: number; mode: string; pattern: string; enabled: boolean }[] = [];
  const highlights: {
    id: number; mode: string; pattern: string; enabled: boolean;
    color_index: number; override_color: string | null;
  }[] = [];
  const counts: Record<string, number> = {
    critical: 1, error: 2, warning: 3, msg: 4, debug: 5, trace: 6,
  };
  const snapshot = () => ({
    visible_count: Object.values(enabledLevels).filter(Boolean).length ? 10 : 0,
    levels: Object.entries(enabledLevels).map(([level, enabled]) => ({
      level, enabled, count: counts[level] ?? 0,
    })),
    filters: filters.map((f, id) => ({ ...f, id })),
    pins: pins.map((p, id) => ({ ...p, id })),
    highlights: highlights.map((h, id) => ({ ...h, id })),
    categories_enabled: ["app/db"],
  });
  return {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: 12, categories: [], levels: [], load_ms: 1,
    }),
    getRows: async () => [],
    addFilter: async (mode: string, pattern: string) => {
      if (options.failMutation === "addFilter") throw new Error("no such mode");
      filters.push({ id: 0, mode, pattern, enabled: true });
      return null;
    },
    setFilterEnabled: async (id: number, on: boolean) => {
      const f = filters[id];
      if (!f) throw new Error("no such filter");
      f.enabled = on;
      return null;
    },
    removeFilter: async (id: number) => {
      if (!filters[id]) throw new Error("no such filter");
      filters.splice(id, 1);
      return null;
    },
    addPin: async (mode: string, pattern: string) => {
      pins.push({ id: 0, mode, pattern, enabled: true });
      return null;
    },
    setPinEnabled: async (id: number, on: boolean) => {
      const p = pins[id];
      if (!p) throw new Error("no such pin");
      p.enabled = on;
      return null;
    },
    removePin: async (id: number) => {
      if (!pins[id]) throw new Error("no such pin");
      pins.splice(id, 1);
      return null;
    },
    clearPins: async () => {
      pins.length = 0;
      return null;
    },
    addHighlight: async (mode: string, pattern: string) => {
      if (options.failMutation === "addHighlight") throw new Error("no such mode");
      highlights.push({
        id: 0, mode, pattern, enabled: true,
        color_index: highlights.length % 10, override_color: null,
      });
      return null;
    },
    setHighlightEnabled: async (id: number, on: boolean) => {
      const h = highlights[id];
      if (!h) throw new Error("no such highlight");
      h.enabled = on;
      return null;
    },
    setHighlightColor: async (id: number, hex: string | null) => {
      const h = highlights[id];
      if (!h) throw new Error("no such highlight");
      h.override_color = hex;
      return null;
    },
    removeHighlight: async (id: number) => {
      const h = highlights[id];
      if (!h) throw new Error("no such highlight");
      highlights.splice(id, 1);
      return null;
    },
    clearHighlights: async () => {
      highlights.length = 0;
      return null;
    },
    setLevelEnabled: async (level: string, on: boolean) => {
      if (!(level in enabledLevels)) throw new Error(`no such level: ${level}`);
      if (options.failMutation === "setLevel") throw new Error("ipc down");
      enabledLevels[level] = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    searchVisible: async () => ({ total: 0, positions: [] }),
    visibilitySnapshot: async () => snapshot(),
  };
}

type Console = typeof import("./uiConsole").console_;

/**
 * RAW stub over a synthetic visible sequence (contract shapes): 100 lines,
 * "trace" on every 8th line (n % 8 === 4). get_rows serves the visible
 * sequence (contract dsq.3), so index -> line_no is a 1-row probe and
 * line -> index is a binary search -- exactly what §4 remapping exercises.
 */
interface SequenceStub extends RawIpc {
  getRowsCalls(): number;
}

function sequenceStub(options: { failMutation?: string } = {}): SequenceStub {
  const LINE_COUNT = 100;
  const isTrace = (n: number): boolean => n % 8 === 4;
  const traceOn = { value: true };
  const visible = (n: number): boolean => !isTrace(n) || traceOn.value;

  /** index -> line_no over the current visible sequence. */
  const lineNoAt = (index: number): number | null => {
    let idx = 0;
    for (let n = 1; n <= LINE_COUNT; n++) {
      if (!visible(n)) continue;
      if (idx === index) return n;
      idx++;
    }
    return null;
  };

  let getRowsCalls = 0;
  const row = (n: number): RowDto => ({
    line_no: n,
    time_display: "10:00:00.000",
    category: "app/db",
    level: isTrace(n) ? "trace" : "msg",
    message: "line " + n,
    raw: "raw " + n,
    spans: [],
  });
  return {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: LINE_COUNT, categories: [], levels: [], load_ms: 1,
    }),
    getRows: async (offset: number, limit: number): Promise<RowDto[]> => {
      getRowsCalls++;
      const rows: RowDto[] = [];
      for (let i = offset; rows.length < limit; i++) {
        const n = lineNoAt(i);
        if (n === null) break;
        rows.push(row(n));
      }
      return rows;
    },
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    clearPins: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "trace") throw new Error(`no such level: ${level}`);
      if (options.failMutation === "setLevel") throw new Error("ipc down");
      traceOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    searchVisible: async () => ({ total: 0, positions: [] }),
    visibilitySnapshot: async (): Promise<VisibilitySnapshotDto> => ({
      visible_count: Array.from({ length: LINE_COUNT }, (_, i) => i + 1)
        .filter(visible).length,
      levels: ["critical", "error", "warning", "msg", "debug", "trace"].map(
        (level) => ({ level, enabled: level !== "trace" || traceOn.value, count: 1 }),
      ),
      filters: [],
      pins: [],
      highlights: [],
      categories_enabled: ["app/db"],
    }),
    getRowsCalls: () => getRowsCalls,
  };
}

async function freshConsole(stub: RawIpc): Promise<{ console_: Console }> {
  const target = window as unknown as Record<string, unknown>;
  target.__ipcStub = stub;
  vi.resetModules();
  const mod = await import("./uiConsole");
  return { console_: mod.console_ as Console };
}

describe("console visibility actions (dsq.3, §7)", () => {  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  it("load refetches the visibility snapshot after load-success", async () => {
    const { console_ } = await freshConsole(visibilityStub());
    const snap = await console_.load("/tmp/log.txt");
    expect(snap.screen).toBe("loaded");
    expect(snap.visibility?.visibleCount).toBe(10);
    expect(snap.visibility?.categoriesEnabled).toEqual(["app/db"]);
    expect(snap.visibility?.levels).toHaveLength(6);
  });

  it("setLevel re-dispatches a fresh snapshot with the level off", async () => {
    const { console_ } = await freshConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    const before = console_.getSnapshot().visibility;
    expect(before?.levels.find((l) => l.level === "trace")?.enabled).toBe(true);
    const after = await console_.setLevel("trace", false);
    // §11 counts ignore level toggles: the counter stays.
    const trace = after.visibility?.levels.find((l) => l.level === "trace");
    expect(trace?.enabled).toBe(false);
    expect(trace?.count).toBe(6);
  });

  it("filter actions flow through the console RPC (add / toggle / remove)", async () => {
    const { console_ } = await freshConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    let snap = await console_.addFilter("plain", "timeout");
    expect(snap.visibility?.filters).toEqual([
      { id: 0, mode: "plain", pattern: "timeout", enabled: true },
    ]);
    snap = await console_.addFilter("regex", "^retry");
    snap = await console_.toggleFilter(1, false);
    expect(snap.visibility?.filters.map((f) => f.enabled)).toEqual([true, false]);
    snap = await console_.removeFilter(0);
    expect(snap.visibility?.filters.map((f) => f.pattern)).toEqual(["^retry"]);
    snap = await console_.removeFilter(0);
    expect(snap.visibility?.filters).toEqual([]);
  });

  it("pin actions are symmetric with filters (q1f.1 owns the panel)", async () => {
    const { console_ } = await freshConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    let snap = await console_.addPin("lineno", "42");
    expect(snap.visibility?.pins).toEqual([
      { id: 0, mode: "lineno", pattern: "42", enabled: true },
    ]);
    snap = await console_.setPinEnabled(0, false);
    expect(snap.visibility?.pins[0]?.enabled).toBe(false);
    snap = await console_.removePin(0);
    expect(snap.visibility?.pins).toEqual([]);
  });

  it("a failing mutation surfaces through the existing error state and keeps the snapshot", async () => {
    const { console_ } = await freshConsole(
      visibilityStub({ failMutation: "setLevel" }),
    );
    await console_.load("/tmp/log.txt");
    const before = console_.getSnapshot().visibility;
    const after = await console_.setLevel("trace", false);
    expect(after.error).toBe("Error: ipc down");
    expect(after.visibility).toEqual(before);
  });

  it("an out-of-range id errors instead of mutating (backend contract)", async () => {
    const { console_ } = await freshConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    const after = await console_.toggleFilter(9, true);
    expect(after.error).toBe("Error: no such filter");
  });

  it("a failed visibility fetch after a load surfaces the error without dropping the file", async () => {
    const stub = visibilityStub();
    stub.visibilitySnapshot = async () => {
      throw new Error("snapshot failed");
    };
    const { console_ } = await freshConsole(stub);
    const snap = await console_.load("/tmp/log.txt");
    expect(snap.error).toBe("Error: snapshot failed");
    expect(snap.file).not.toBeNull();
    expect(snap.visibility).toBeNull();
  });
});

describe("selection remap on visibility mutations (§4, qt7.3)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
    vi.restoreAllMocks();
  });

  it("re-resolves the selection by line numbers across the mutation", async () => {
    const { console_ } = await freshConsole(sequenceStub());
    await console_.load("/tmp/log.txt");
    const s0 = console_.selectRow(9, "click"); // visible[9] = line 10
    expect(s0.selection.selected).toEqual([9]);
    const s1 = await console_.setLevel("trace", false);
    // Pre-mutation the console resolved line_no 10; in the new sequence the
    // only trace line below it is line 4, so line 10 sits at index 8.
    expect(s1.selection).toEqual({ selected: [8], anchor: 8 });
  });

  it("hidden selected rows drop out and coincidental targets do not duplicate", async () => {
    const { console_ } = await freshConsole(sequenceStub());
    await console_.load("/tmp/log.txt");
    console_.selectRow(3, "click"); // line 4 (trace) -> hidden by the toggle
    console_.selectRow(99, "toggle"); // line 100 (trace) -> beyond the end
    console_.selectRow(11, "toggle"); // line 12 (trace) -> resolves to line 5
    const after = await console_.setLevel("trace", false);
    // Line 4 continues onto line 5 (index 3); hidden line 12 continues onto
    // line 13 (index 10); line 100 has no visible line after it and is
    // dropped (visible-selection contract).
    // Lines 4 and 12 both continue onto their nearest still-visible line;
    // line 100 has no visible line after it and is dropped (visible-
    // selection contract). The anchor is index 11 (line 12, the last
    // toggle pivot) and follows its remap onto index 10.
    expect(after.selection.selected).toEqual([3, 10]);
    expect(after.selection.anchor).toBe(10);
  });

  it("an empty selection costs zero extra get_rows probes", async () => {
    const stub = sequenceStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const before = stub.getRowsCalls();
    await console_.setLevel("trace", false);
    expect(stub.getRowsCalls()).toBe(before);
  });

  it("a non-empty selection exercises the probe path", async () => {
    const stub = sequenceStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.selectRow(9, "click");
    await console_.setLevel("trace", false);
    expect(stub.getRowsCalls()).toBeGreaterThan(0);
  });

  it("a failing mutation keeps the selection untouched (no remap on error)", async () => {
    const { console_ } = await freshConsole(
      sequenceStub({ failMutation: "setLevel" }),
    );
    await console_.load("/tmp/log.txt");
    console_.selectRow(9, "click");
    const after = await console_.setLevel("trace", false);
    expect(after.error).toBe("Error: ipc down");
    expect(after.selection).toEqual({ selected: [9], anchor: 9 });
  });
});

describe("viewport text RPC (§4, qt7.3)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  it("reads null while no table is mounted", async () => {
    const { console_ } = await freshConsole(sequenceStub());
    expect(console_.viewport()).toBeNull();
  });

  it("is exposed through the headless console", async () => {
    const reset = installHeadlessConsole();
    try {
      const headless = (window as unknown as Record<string, unknown>)
        .__headless as { viewport: () => unknown } | undefined;
      expect(headless?.viewport()).toBeNull();
    } finally {
      reset();
    }
  });

  it("mirrors the panel actions on window.__headless (rhl.2)", async () => {
    const reset = installHeadlessConsole();
    try {
      const headless = (window as unknown as Record<string, unknown>)
        .__headless as Record<string, unknown> | undefined;
      expect(headless).not.toBeUndefined();
      for (const name of [
        "toggleCategory", "setAllCategories", "togglePanel", "setPanelTab",
        "setPanelWidth", "setCategorySearch", "expandAllCategories",
        "toggleExpansion",
      ]) {
        expect(typeof headless?.[name]).toBe("function");
      }
    } finally {
      reset();
    }
  });
});

/** RAW stub with a real categories tree: load_file returns the flat list,
 *  set_category_enabled flips a whitelist the visibility engine mirrors
 *  (row visible = exact path AND every prefix enabled). */
function categoryStub() {
  const CATEGORIES = [
    { path: "app", count: 0 },
    { path: "app/main", count: 0 },
    { path: "app/main/db", count: 40 },
    { path: "app/main/api", count: 20 },
    { path: "db", count: 0 },
    { path: "db/pool", count: 20 },
    { path: "uncategorized", count: 20 },
  ];
  const everyPath = (cs: { path: string }[]): string[] =>
    [...new Set(cs.flatMap(({ path }) => {
      const prefixes: string[] = [];
      let i = path.indexOf("/");
      while (i !== -1) { prefixes.push(path.slice(0, i)); i = path.indexOf("/", i + 1); }
      return [...prefixes, path];
    }))].sort();
  const enabled = new Set(everyPath(CATEGORIES));
  const calls: string[] = [];
  const allowed = (cat: string): boolean => {
    if (!enabled.has(cat)) return false;
    let i = cat.indexOf("/");
    while (i !== -1) { if (!enabled.has(cat.slice(0, i))) return false; i = cat.indexOf("/", i + 1); }
    return true;
  };
  const stub: RawIpc & { setCategoryCalls(): string[] } = {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: 100,
      categories: CATEGORIES, levels: [], load_ms: 1,
    }),
    getRows: async () => [],
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    clearPins: async () => null,
    setLevelEnabled: async () => null,
    setCategoryEnabled: async (path, on) => {
      calls.push((on ? "+" : "-") + path);
      if (on) enabled.add(path); else enabled.delete(path);
      return null;
    },
    searchVisible: async () => ({ total: 0, positions: [] }),
    visibilitySnapshot: async () => ({
      visible_count: CATEGORIES.filter((c) => c.count > 0 && allowed(c.path))
        .reduce((sum, c) => sum + c.count, 0),
      levels: [],
      filters: [],
      pins: [],
      highlights: [],
      categories_enabled: [...enabled].sort(),
    }),
    setCategoryCalls: () => calls,
  };
  return stub;
}

/** The tree's paths in the byte-order sort category helpers emit. */
const TREE_PATHS = [
  "app", "app/main", "app/main/api", "app/main/db",
  "db", "db/pool", "uncategorized",
];
const CATEGORY_TOGGLE_ALL_OFF = TREE_PATHS.map((p) => "-" + p);
const CATEGORY_TOGGLE_ALL_ON = TREE_PATHS.map((p) => "+" + p);

describe("panel console actions (rhl.2, §10.1)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  it("the snapshot mirrors the panel slice", async () => {
    const { console_ } = await freshConsole(categoryStub());
    expect(console_.getSnapshot().panel).toEqual({
      open: true, tab: "categories", width: 220, search: "", expanded: [],
    });
  });

  it("togglePanel / setPanelTab / setPanelWidth / setCategorySearch are pure dispatches", async () => {
    const { console_ } = await freshConsole(categoryStub());
    let panel = console_.togglePanel().panel;
    expect(panel.open).toBe(false);
    panel = console_.setPanelTab("filters").panel;
    expect(panel.tab).toBe("filters");
    panel = console_.setPanelWidth(300).panel;
    expect(panel.width).toBe(300);
    // splitter drag clamps into the 180-480 band (spec interpretation)
    panel = console_.setPanelWidth(50).panel;
    expect(panel.width).toBe(180);
    panel = console_.setPanelWidth(1000).panel;
    expect(panel.width).toBe(480);
    panel = console_.setCategorySearch("db").panel;
    expect(panel.search).toBe("db");
  });

  it("setPanelTab rejects an unknown tab (text RPC string boundary)", async () => {
    const { console_ } = await freshConsole(categoryStub());
    expect(console_.setPanelTab("settings").panel.tab).toBe("categories");
  });

  it("toggleExpansion flips one path without IPC", async () => {
    const { console_ } = await freshConsole(categoryStub());
    const panel = console_.toggleExpansion("app").panel;
    expect(panel.expanded).toEqual(["app"]);
  });

  it("expandAllCategories uses the loaded file's tree (all paths incl. prefixes)", async () => {
    const { console_ } = await freshConsole(categoryStub());
    await console_.load("/tmp/log.txt");
    const expanded = console_.expandAllCategories(true).panel.expanded;
    expect(expanded).toEqual([
      "app", "app/main", "app/main/api", "app/main/db",
      "db", "db/pool", "uncategorized",
    ]);
  });

  it("expandAllCategories(expand=false) collapses to the roots", async () => {
    const { console_ } = await freshConsole(categoryStub());
    await console_.load("/tmp/log.txt");
    await console_.expandAllCategories(true);
    const expanded = console_.expandAllCategories(false).panel.expanded;
    expect(expanded).toEqual(["app", "db", "uncategorized"]);
  });

  it("load resets the expansion to the new file's root-level paths", async () => {
    const { console_ } = await freshConsole(categoryStub());
    await console_.load("/tmp/log.txt");
    await console_.expandAllCategories(true);
    expect(console_.getSnapshot().panel.expanded.length).toBeGreaterThan(3);
    const { console_: fresh } = await freshConsole(categoryStub());
    const snap = await fresh.load("/tmp/log.txt");
    expect(snap.panel.expanded).toEqual(["app", "db", "uncategorized"]);
  });

  it("toggleCategory(off) drives the propagateToggle differential through set_category_enabled and refetches", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const snap = await console_.toggleCategory("app", false);
    // down-propagation removes the node + its subtree paths; ancestors stay.
    expect(stub.setCategoryCalls()).toEqual([
      "-app", "-app/main", "-app/main/api", "-app/main/db",
    ]);
    expect(snap.visibility?.categoriesEnabled).toEqual(["db", "db/pool", "uncategorized"]);
    // app/main rows drop out of the visible count (40 + 20 of 100).
    expect(snap.visibility?.visibleCount).toBe(40);
  });

  it("toggleCategory(on) adds the subtree + every ancestor prefix", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.toggleCategory("app", false);
    stub.setCategoryCalls().length = 0;
    const snap = await console_.toggleCategory("app", true);
    expect(stub.setCategoryCalls()).toEqual([
      "+app", "+app/main", "+app/main/api", "+app/main/db",
    ]);
    expect(snap.visibility?.visibleCount).toBe(100);
  });

  it("setAllCategories(on=false) unchecks everything via the All checkbox", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const snap = await console_.setAllCategories(false);
    expect(stub.setCategoryCalls()).toEqual(CATEGORY_TOGGLE_ALL_OFF);
    expect(snap.visibility?.visibleCount).toBe(0);
  });

  it("setAllCategories(on=true) checks everything", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.setAllCategories(false);
    stub.setCategoryCalls().length = 0;
    const snap = await console_.setAllCategories(true);
    expect(stub.setCategoryCalls()).toEqual(CATEGORY_TOGGLE_ALL_ON);
    expect(snap.visibility?.visibleCount).toBe(100);
  });

  it("toggleCategory without a loaded file is a safe no-op", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    const snap = await console_.toggleCategory("app", false);
    expect(stub.setCategoryCalls()).toEqual([]);
    expect(snap.visibility ?? null).toBeNull();
  });

  it("a failing set_category_enabled surfaces through the error state and keeps the snapshot", async () => {
    const stub = categoryStub();
    stub.setCategoryEnabled = async () => {
      throw new Error("ipc down");
    };
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const before = console_.getSnapshot().visibility;
    const after = await console_.toggleCategory("app", false);
    expect(after.error).toBe("Error: ipc down");
    expect(after.visibility).toEqual(before);
  });
});

// ---- §8 search panel (bead 2wu.1) ----

/** RAW stub over 10 fully visible lines ("line 1".."line 10") with an
 *  approximate searchVisible (case-insensitive substring for plain/simple,
 *  anchored-JS regex for regex; an invalid pattern matches nothing — the
 *  exact mode semantics are backend logic, the stub only needs to be
 *  deterministic). */
interface SearchStub extends RawIpc {
  searchVisibleCalls(): { mode: string; pattern: string }[];
}

function searchStub(): SearchStub {
  const LINE_COUNT = 10;
  const messageOf = (n: number): string => "line " + n;
  // All lines are level "msg"; the toggle reshapes the visible sequence the
  // search must stay scoped to (live bug 2 regression).
  const msgOn = { value: true };
  const visible = (): boolean => msgOn.value;
  const calls: { mode: string; pattern: string }[] = [];
  return {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: LINE_COUNT, categories: [], levels: [], load_ms: 1,
    }),
    getRows: async (offset: number, limit: number): Promise<RowDto[]> => {
      const rows: RowDto[] = [];
      for (let i = offset; i < Math.min(offset + limit, LINE_COUNT); i++) {
        const n = i + 1;
        rows.push({
          line_no: n,
          time_display: "10:00:00.000",
          category: "app/db",
          level: "msg",
          message: messageOf(n),
          raw: "raw " + n,
          spans: [],
        });
      }
      return rows;
    },
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    clearPins: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "msg") throw new Error(`no such level: ${level}`);
      msgOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    searchVisible: async (mode: string, pattern: string) => {
      calls.push({ mode, pattern });
      if (typeof pattern !== "string") throw new Error("pattern: not a string");
      if (pattern === "") return { total: 0, positions: [] };
      // A case-insensitive substring for plain/simple; an anchored JS regex
      // for regex (broken pattern matches nothing — backend contract).
      const hit = (message: string): boolean => {
        if (mode === "regex") {
          try {
            return new RegExp(pattern, "i").test(message);
          } catch {
            return false;
          }
        }
        return message.toLowerCase().includes(pattern.toLowerCase());
      };
      const positions: number[] = [];
      let index = 0;
      for (let n = 1; n <= LINE_COUNT; n++) {
        if (!visible()) break;
        if (hit(messageOf(n))) positions.push(index);
        index++;
      }
      return { total: positions.length, positions };
    },
    visibilitySnapshot: async (): Promise<VisibilitySnapshotDto> => ({
      visible_count: msgOn.value ? LINE_COUNT : 0,
      levels: ["critical", "error", "warning", "msg", "debug", "trace"].map(
        (level) => ({ level, enabled: level !== "msg" || msgOn.value, count: 1 }),
      ),
      filters: [],
      pins: [],
      highlights: [],
      categories_enabled: ["app/db"],
    }),
    searchVisibleCalls: () => calls,
  };
}

describe("search actions (bead 2wu.1, §8)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const settle = async () => {
    await vi.advanceTimersByTimeAsync(250);
    await vi.advanceTimersByTimeAsync(0);
  };

  it("openSearch with no loaded file is a no-op", async () => {
    const { console_ } = await freshConsole(searchStub());
    const snap = console_.openSearch();
    expect(snap.search.open).toBe(false);
  });

  it("setSearchQuery recomputes after the 250ms debounce and starts at-or-below the selection", async () => {
    const { console_ } = await freshConsole(searchStub());
    await console_.load("/tmp/log.txt");
    console_.selectRow(3, "click"); // visible[3] = line 4
    console_.openSearch();
    console_.setSearchQuery("line 1");
    await settle();
    // "line 1" matches line 1 (index 0) and line 10 (index 9); at-or-below
    // the selection (index 3) the first match is index 9.
    const snap = console_.getSnapshot();
    expect(snap.search.total).toBe(2);
    expect(snap.search.currentVisibleIndex).toBe(9);
    expect(snap.search.currentRank).toBe(2);
    // §8 action 2: the first match becomes the selection.
    expect(snap.selection.selected).toEqual([9]);
  });

  it("an empty selection starts from the first match", async () => {
    const { console_ } = await freshConsole(searchStub());
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await settle();
    const snap = console_.getSnapshot();
    expect(snap.search.total).toBe(10);
    expect(snap.search.currentRank).toBe(1);
    expect(snap.search.currentVisibleIndex).toBe(0);
  });

  it("an empty query renders «0 of 0» without an IPC call", async () => {
    const stub = searchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("");
    await settle();
    const snap = console_.getSnapshot();
    expect(snap.search).toMatchObject({ total: 0, currentRank: null, currentVisibleIndex: null });
    expect(stub.searchVisibleCalls().length).toBe(0);
  });

  it("mode changes map to the RPC mode; plain = both tumblers off", async () => {
    const stub = searchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchMode("regex");
    // Anchored regex: only line 1 matches exactly.
    console_.setSearchQuery("^line 1$");
    await settle();
    expect(stub.searchVisibleCalls()[0]).toEqual({ mode: "regex", pattern: "^line 1$" });
    expect(console_.getSnapshot().search.total).toBe(1);
    // A plain (both-off) search treats the same text as a literal substring
    // and matches nothing; an unknown mode falls back defensively.
    console_.setSearchMode("bogus");
    await settle();
    expect(stub.searchVisibleCalls()[1]).toEqual({ mode: "plain", pattern: "^line 1$" });
    expect(console_.getSnapshot().search.total).toBe(0);
  });

  it("typing debounces: bursts issue one recompute, the last query wins", async () => {
    const stub = searchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line 1");
    await vi.advanceTimersByTimeAsync(100);
    console_.setSearchQuery("line 2");
    await settle();
    expect(stub.searchVisibleCalls()).toEqual([{ mode: "plain", pattern: "line 2" }]);
  });

  it("a stale recompute response after a newer query is discarded", async () => {
    const stub = searchStub();
    let resolveSlow: (result: { total: number; positions: number[] }) => void = () => {};
    stub.searchVisible = async (_mode: string, pattern: string) => {
      if (pattern === "slow") {
        return new Promise((resolve) => {
          resolveSlow = resolve;
        });
      }
      return { total: 0, positions: [] };
    };
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("slow");
    await settle();
    console_.setSearchQuery("fast");
    await settle();
    const settled = console_.getSnapshot();
    resolveSlow({ total: 7, positions: [0, 1, 2, 3, 4, 5, 6] });
    await settle();
    const snap = console_.getSnapshot();
    expect(snap.search.total).toBe(0);
    expect(snap.selection.selected).toEqual(settled.selection.selected);
  });

  it("nextMatch cycles cyclically and selects the match row", async () => {
    const { console_ } = await freshConsole(searchStub());
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line 1"); // matches indexes 0 and 9
    await settle();
    let snap = console_.nextMatch(-1);
    // 0 - 1 wraps to the last match (index 9 = line 10).
    expect(snap.search.currentVisibleIndex).toBe(9);
    expect(snap.search.currentRank).toBe(2);
    expect(snap.selection.selected).toEqual([9]);
    snap = console_.nextMatch(1);
    // 9 + 1 wraps back to the first match (index 0 = line 1).
    expect(snap.search.currentVisibleIndex).toBe(0);
    expect(snap.search.currentRank).toBe(1);
    expect(snap.selection.selected).toEqual([0]);
  });

  it("nextMatch with no matches is a no-op; closed panel never cycles", async () => {
    const { console_ } = await freshConsole(searchStub());
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("no-such-text");
    await settle();
    expect(console_.nextMatch(1).search.total).toBe(0);
  });

  it("closeSearch closes without losing the query; reopening recomputes", async () => {
    const stub = searchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line 3");
    await settle();
    expect(stub.searchVisibleCalls()).toHaveLength(1);
    const closed = console_.closeSearch();
    expect(closed.search.open).toBe(false);
    expect(closed.search.query).toBe("line 3");
    console_.openSearch();
    await settle();
    // The reopened panel rescan keeps the same query (stale positions are
    // refreshed against the current visibility).
    expect(stub.searchVisibleCalls().map((c) => c.pattern)).toEqual(["line 3", "line 3"]);
    const snap = console_.getSnapshot();
    expect(snap.search.open).toBe(true);
    expect(snap.search.total).toBe(1);
  });

  it("a failing searchVisible surfaces through the error state", async () => {
    const stub = searchStub();
    stub.searchVisible = async () => {
      throw new Error("bad regex");
    };
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("x(");
    await settle();
    expect(console_.getSnapshot().error).toBe("Error: bad regex");
  });
});

describe("search live-check fixes (bead 2wu.1)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const settle = async () => {
    await vi.advanceTimersByTimeAsync(250);
    await vi.advanceTimersByTimeAsync(0);
  };

  it("live bug 1: a missing argument at the headless mirror is coerced — the RAW invoke never sees a non-string pattern", async () => {
    const stub = searchStub();
    const { console_ } = await freshConsole(stub);
    const { installHeadlessConsole } = await import("./headless");
    const uninstall = installHeadlessConsole();
    try {
      await console_.load("/tmp/log.txt");
      console_.openSearch();
      const mirror = (
        window as unknown as {
          __headless: {
            setSearchQuery: (q?: unknown) => unknown;
            setSearchMode: (m?: unknown) => unknown;
          };
        }
      ).__headless;
      mirror.setSearchQuery(); // /eval probe with a missing argument
      mirror.setSearchMode();
      await settle();
      const snap = console_.getSnapshot();
      // The empty pattern short-circuits locally per contract: no invoke.
      expect(stub.searchVisibleCalls()).toEqual([]);
      expect(snap.search.query).toBe("");
      expect(snap.error).toBeNull();
    } finally {
      uninstall();
    }
  });

  it("live bug 2: a visibility change while the panel is open recomputes the (now stale) matches", async () => {
    // The search stub's 10 lines are all level "msg"; toggling it changes
    // the visible sequence the search must be scoped to.
    const stub = searchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await settle();
    expect(console_.getSnapshot().search.total).toBe(10);
    expect(stub.searchVisibleCalls()).toHaveLength(1);
    // Visibility shrinks under the open panel: the matches must rescan.
    await console_.setLevel("msg", false);
    await settle();
    expect(stub.searchVisibleCalls()).toHaveLength(2);
    expect(console_.getSnapshot().search.total).toBe(0);
    // …and grow again.
    await console_.setLevel("msg", true);
    await settle();
    expect(stub.searchVisibleCalls()).toHaveLength(3);
    expect(console_.getSnapshot().search.total).toBe(10);
  });

  it("live bug 2: a late result from before a visibility change never lands (swapped resolves)", async () => {
    const stub = searchStub();
    const pending: ((r: { total: number; positions: number[] }) => void)[] = [];
    stub.searchVisible = async () =>
      new Promise((resolve) => {
        pending.push(resolve);
      });
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await settle();
    expect(pending).toHaveLength(1); // refresh #1 in flight (old visibility: 10)
    await console_.setLevel("msg", false); // visibility event -> schedules refresh #2
    await settle();
    expect(pending).toHaveLength(2);
    // Swapped resolve order: the NEWER call first, the older one late.
    pending[1]?.({ total: 0, positions: [] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(0);
    pending[0]?.({ total: 9, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8] });
    await settle();
    // The late stale result must NOT overwrite the newer one.
    expect(console_.getSnapshot().search.total).toBe(0);
    expect(console_.getSnapshot().selection.selected).toEqual([]);
  });
});

// ---- §8 freshness invariant (bead 2wu.1, live round 2) ----

/** Deferred searchVisible whose result total FREEZES AT INVOKE TIME from
 *  the invoke-time visibility (the backend computes the scan on the
 *  sequence it sees; with 1M+ rows a scan resolves seconds later). The
 *  manual resolvers let the tests swap response order. */
interface DeferredSearchStub extends RawIpc {
  pending: {
    pattern: string;
    total: number;
    resolve: (result: { total: number; positions: number[] }) => void;
  }[];
}

function deferredSearchStub(): DeferredSearchStub {
  const LINE_COUNT = 10;
  const msgOn = { value: true };
  const messageOf = (n: number): string => "line " + n;
  const pending: DeferredSearchStub["pending"] = [];
  return {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: LINE_COUNT, categories: [], levels: [], load_ms: 1,
    }),
    getRows: async () => [],
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    clearPins: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "msg") throw new Error(`no such level: ${level}`);
      msgOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    searchVisible: async (mode: string, pattern: string) => {
      void mode;
      if (typeof pattern !== "string") throw new Error("pattern: not a string");
      if (pattern === "") return { total: 0, positions: [] };
      const positions: number[] = [];
      if (msgOn.value) {
        for (let n = 1; n <= LINE_COUNT; n++) {
          if (messageOf(n).toLowerCase().includes(pattern.toLowerCase())) {
            positions.push(n - 1);
          }
        }
      }
      const result = { total: positions.length, positions: [...positions] };
      return new Promise((resolve) => {
        pending.push({ pattern, total: result.total, resolve });
      });
    },
    visibilitySnapshot: async (): Promise<VisibilitySnapshotDto> => ({
      visible_count: msgOn.value ? LINE_COUNT : 0,
      levels: ["critical", "error", "warning", "msg", "debug", "trace"].map(
        (level) => ({ level, enabled: level !== "msg" || msgOn.value, count: 1 }),
      ),
      filters: [],
      pins: [],
      highlights: [],
      categories_enabled: ["app/db"],
    }),
    pending,
  };
}

describe("search freshness invariant (live round 2): the slice is never one recompute behind", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const settle = async () => {
    await vi.advanceTimersByTimeAsync(250);
    await vi.advanceTimersByTimeAsync(0);
  };

  it("a dropped post-mutation schedule heals: a stale-epoch result never lands, a fresh one follows", async () => {
    const stub = deferredSearchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await settle();
    expect(stub.pending).toHaveLength(1);
    stub.pending[0]?.resolve({ total: 10, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(10);

    // Visibility mutation #1: the recompute (issued against the SHRUNK
    // sequence, slow backend) is in flight, unresolved.
    await console_.setLevel("msg", false);
    await settle();
    expect(stub.pending).toHaveLength(2);

    // Visibility mutation #2 — and its post-mutation schedule is LOST
    // (the live round-2 symptom: timer control outside the console's
    // reach). Nothing may rely on that schedule to correct the slice.
    await console_.setLevel("msg", true);
    vi.clearAllTimers();
    await settle();

    // The stale recompute (issued pre-mutation-#2, frozen at the shrunken
    // sequence) resolves late. It must NOT land; the heal reschedules.
    stub.pending[1]?.resolve({ total: 0, positions: [] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(10);
    // The healed recompute ran against the CURRENT (restored) sequence.
    expect(stub.pending).toHaveLength(3);
    stub.pending[2]?.resolve({ total: 10, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(10);
  });

  it("interleaving A (query-scheduled then visibility-scheduled): converges to search_visible(current sequence, latest query); late stale never lands", async () => {
    const stub = deferredSearchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await settle();
    stub.pending[0]?.resolve({ total: 10, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(10);

    await console_.setLevel("msg", false); // schedules recompute #2 (slow, "line" @ off = 0)
    await settle();
    console_.setSearchQuery("1");          // #3: "1" @ off = 0
    await settle();
    expect(stub.pending).toHaveLength(3);

    // Swapped resolutions: the NEWER (#3) first, the stale #2 late.
    stub.pending[2]?.resolve({ total: 0, positions: [] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(0);
    stub.pending[1]?.resolve({ total: 0, positions: [] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(0);
    expect(console_.getSnapshot().search.query).toBe("1");

    // …and the reversed order: #2's stale-epoch result is discarded, #3
    // lands the same converged value.
    await console_.setLevel("msg", true); // restore, one more recompute
    await settle();
    expect(stub.pending).toHaveLength(4);
    stub.pending[3]?.resolve({ total: 2, positions: [0, 9] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(2);
  });

  it("interleaving B (visibility-scheduled with an in-flight query recompute): both resolve orders converge", async () => {
    const stub = deferredSearchStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await settle();
    expect(stub.pending).toHaveLength(1); // #1 in flight (issued @ on: 10)
    await console_.setLevel("msg", false); // #2 scheduled + issued (@ off: 0)
    await settle();
    expect(stub.pending).toHaveLength(2);

    // The pre-mutation #1 resolves after the post-mutation #2's token bump:
    // discarded without landing; the slice ends at the current sequence.
    stub.pending[1]?.resolve({ total: 0, positions: [] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(0);
    stub.pending[0]?.resolve({ total: 10, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(0);

    // Reverse order: #1's stale-epoch result discarded (also by token — #2
    // already owns the slice), #2 lands 0. Same convergence.
    await console_.setLevel("msg", true); // #3 scheduled + issued (@ on: 10)
    await settle();
    expect(stub.pending).toHaveLength(3);
    stub.pending[0]?.resolve({ total: 10, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] });
    await settle();
    // (already consumed by its earlier resolve — a second resolve is a
    // no-op on the settled promise; the assertion below covers the slice.)
    expect(console_.getSnapshot().search.total).toBe(0);
    stub.pending[2]?.resolve({ total: 10, positions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] });
    await settle();
    expect(console_.getSnapshot().search.total).toBe(10);
  });
});

// ---- §8 mid-burst scan guard (bead 2wu.1, live round 3) ----

/** Slow-wire category stub over 10 rows ("a" = lines 1-5, "b" = lines 6-10);
 *  each set_category_enabled applies after 200 ms (a real wire call is
 *  milliseconds, but a 1M-row file's search scan holds the shell lock for
 *  seconds and can land between two burst wire calls). searchVisible
 *  computes from the applied state AT INVOKE TIME and records the count —
 *  a mid-burst scan shows up as a partial count (5) in the log. */
interface BurstStub extends RawIpc {
  searchInvokes: number[];
}

function categoryBurstStub(): BurstStub {
  const applied: { a: boolean; b: boolean } = { a: true, b: true };
  const categoryOf = (n: number): "a" | "b" => (n <= 5 ? "a" : "b");
  const visible = (n: number): boolean => applied[categoryOf(n)];
  const searchInvokes: number[] = [];
  return {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: 10,
      categories: [{ path: "a", count: 5 }, { path: "b", count: 5 }],
      levels: [], load_ms: 1,
    }),
    getRows: async () => [],
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    clearPins: async () => null,
    setLevelEnabled: async () => null,
    setCategoryEnabled: async (path: string, on: boolean) => {
      if (path !== "a" && path !== "b") throw new Error("no such category");
      await new Promise((resolve) => setTimeout(resolve, 200));
      if (on) applied[path as "a" | "b"] = true;
      else applied[path as "a" | "b"] = false;
      return null;
    },
    searchVisible: async (mode: string, pattern: string) => {
      void mode;
      if (typeof pattern !== "string") throw new Error("pattern: not a string");
      if (pattern === "") return { total: 0, positions: [] };
      const positions: number[] = [];
      let index = 0;
      for (let n = 1; n <= 10; n++) {
        if (!visible(n)) continue;
        if (("line " + n).toLowerCase().includes(pattern.toLowerCase())) {
          positions.push(index);
        }
        index++;
      }
      searchInvokes.push(positions.length);
      return { total: positions.length, positions };
    },
    visibilitySnapshot: async (): Promise<VisibilitySnapshotDto> => ({
      visible_count: [applied.a, applied.b].filter(Boolean).length * 5,
      levels: ["critical", "error", "warning", "msg", "debug", "trace"].map(
        (level) => ({ level, enabled: true, count: 1 }),
      ),
      filters: [],
      pins: [],
      highlights: [],
      categories_enabled: (["a", "b"] as const).filter((c) => applied[c]),
    }),
    searchInvokes,
  };
}

describe("search mid-burst scan guard (live round 3)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("the debounced recompute never scans between a burst's wire calls; the final-epoch total lands", async () => {
    const stub = categoryBurstStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("line");
    await vi.advanceTimersByTimeAsync(300);
    expect(console_.getSnapshot().search.total).toBe(10);
    expect(stub.searchInvokes).toEqual([10]);

    // Burst 1: hide everything (two 200 ms wire calls) — the slice follows.
    const hide = console_.setAllCategories(false);
    await vi.advanceTimersByTimeAsync(500);
    await hide;
    await vi.advanceTimersByTimeAsync(300);
    expect(stub.searchInvokes).toEqual([10, 0]);
    expect(console_.getSnapshot().search.total).toBe(0);

    // Burst 2: the restore, with a recompute ARMED (a cheap no-op
    // mutation's snapshot schedules it) right before the burst. Its timer
    // fires WHILE burst 2's differential is mid-application (the first
    // wire call has applied, the second has not) — it must NOT scan that
    // transient state; the mutation's own snapshot re-arms it, and the
    // final (restored) total lands.
    const arm = console_.setLevel("msg", true);
    await arm;
    const restore = console_.setAllCategories(true);
    await vi.advanceTimersByTimeAsync(280); // wire call 1 applied at +200, the armed timer at +250
    await vi.advanceTimersByTimeAsync(300); // wire call 2 applied at +400
    await restore;
    await vi.advanceTimersByTimeAsync(300);
    await vi.advanceTimersByTimeAsync(300);
    expect(stub.searchInvokes).toEqual([10, 0, 10]);
    expect(console_.getSnapshot().search.total).toBe(10);
    expect(console_.getSnapshot().error).toBeNull();
  });
});

describe("pin selection actions (q1f.1, §12)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  /** Sequence + pins stub with STABLE pin ids (backend contract): index i of
   *  the all-visible 100-line sequence resolves to line i+1 by a 1-row probe. */
  function pinSeqStub(): RawIpc & {
    calls: { fn: string; args: unknown[] }[];
    snapshotCalls(): number;
  } {
    const LINE_COUNT = 100;
    const pins: { id: number; mode: string; pattern: string; enabled: boolean }[] = [];
    let nextId = 0;
    const calls: { fn: string; args: unknown[] }[] = [];
    let snapshots = 0;
    const row = (n: number): RowDto => ({
      line_no: n,
      time_display: "10:00:00.000",
      category: "app/db",
      level: "msg",
      message: "line " + n,
      raw: "raw " + n,
      spans: [],
    });
    return {
      calls,
      snapshotCalls: () => snapshots,
      ...highlightNoops(),
      pickFile: async () => null,
      loadFile: async () => ({
        format: "plain", line_count: LINE_COUNT, categories: [], levels: [], load_ms: 1,
      }),
      getRows: async (offset: number, limit: number): Promise<RowDto[]> => {
        const rows: RowDto[] = [];
        for (let i = offset; rows.length < limit && i < LINE_COUNT; i++) {
          rows.push(row(i + 1));
        }
        return rows;
      },
      addFilter: async () => null,
      setFilterEnabled: async () => null,
      removeFilter: async () => null,
      addPin: async (mode: string, pattern: string) => {
        calls.push({ fn: "addPin", args: [mode, pattern] });
        pins.push({ id: nextId++, mode, pattern, enabled: true });
        return null;
      },
      setPinEnabled: async (id: number, on: boolean) => {
        calls.push({ fn: "setPinEnabled", args: [id, on] });
        const pin = pins.find((p) => p.id === id);
        if (!pin) throw new Error("no such pin");
        pin.enabled = on;
        return null;
      },
      removePin: async (id: number) => {
        calls.push({ fn: "removePin", args: [id] });
        const at = pins.findIndex((p) => p.id === id);
        if (at === -1) throw new Error("no such pin");
        pins.splice(at, 1);
        return null;
      },
      clearPins: async () => {
        calls.push({ fn: "clearPins", args: [] });
        pins.length = 0;
        return null;
      },
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
      searchVisible: async () => ({ total: 0, positions: [] }),
      visibilitySnapshot: async () => {
        snapshots++;
        return {
          visible_count: LINE_COUNT,
          levels: [],
          filters: [],
          pins: pins.map((p) => ({ ...p })),
          highlights: [],
          categories_enabled: ["app/db"],
        };
      },
    };
  }

  it("pinSelected batches one add_pin per selected line into ONE refetch", async () => {
    const stub = pinSeqStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    expect(stub.snapshotCalls()).toBe(1);
    console_.selectRow(2, "click"); // line 3
    console_.selectRow(4, "toggle"); // line 5
    const snap = await console_.pinSelected();
    expect(stub.calls).toEqual([
      { fn: "addPin", args: ["lineno", "3"] },
      { fn: "addPin", args: ["lineno", "5"] },
    ]);
    expect(stub.snapshotCalls()).toBe(2); // one refetch for the whole batch
    expect(snap.visibility?.pins).toEqual([
      { id: 0, mode: "lineno", pattern: "3", enabled: true },
      { id: 1, mode: "lineno", pattern: "5", enabled: true },
    ]);
  });

  it("pinSelected with an empty selection is a no-op without IPC", async () => {
    const stub = pinSeqStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const snap = await console_.pinSelected();
    expect(stub.calls).toEqual([]);
    expect(stub.snapshotCalls()).toBe(1);
    expect(snap).toEqual(console_.getSnapshot());
  });

  it("unpinSelected removes ONLY the exact-row pins covering the given lines; broad and disabled pins stay", async () => {
    const stub = pinSeqStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.addPin("lineno", "3"); // id 0: exact, covers line 3
    await console_.addPin("lineno", "7"); // id 1: exact, disabled -> inert
    await console_.addPin("plain", "raw"); // id 2: broad -> the menu never removes it
    await console_.setPinEnabled(1, false);
    expect(stub.snapshotCalls()).toBe(5);
    const snap = await console_.unpinSelected([3, 7]);
    expect(stub.calls.slice(4)).toEqual([{ fn: "removePin", args: [0] }]);
    expect(stub.snapshotCalls()).toBe(6);
    expect(snap.visibility?.pins).toEqual([
      { id: 1, mode: "lineno", pattern: "7", enabled: false },
      { id: 2, mode: "plain", pattern: "raw", enabled: true },
    ]);
  });

  it("unpinSelected() without lines resolves the selection's line numbers by probe", async () => {
    const stub = pinSeqStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.addPin("lineno", "3"); // id 0
    await console_.addPin("lineno", "9"); // id 1
    console_.selectRow(2, "click"); // line 3
    const snap = await console_.unpinSelected();
    expect(stub.calls.slice(2)).toEqual([{ fn: "removePin", args: [0] }]);
    expect(snap.visibility?.pins.map((p) => p.pattern)).toEqual(["9"]);
  });

  it("unpinSelected with no covering exact pin is a no-op without IPC", async () => {
    const stub = pinSeqStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.addPin("lineno", "9");
    const snap = await console_.unpinSelected([3, 7]);
    expect(stub.calls).toEqual([{ fn: "addPin", args: ["lineno", "9"] }]);
    expect(stub.snapshotCalls()).toBe(2);
    expect(snap).toEqual(console_.getSnapshot());
  });

  it("clearAllPins calls clear_pins once with a single refetch and empties the snapshot", async () => {
    const stub = pinSeqStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.addPin("lineno", "3");
    await console_.addPin("plain", "raw");
    const snap = await console_.clearAllPins();
    expect(stub.calls).toEqual([
      { fn: "addPin", args: ["lineno", "3"] },
      { fn: "addPin", args: ["plain", "raw"] },
      { fn: "clearPins", args: [] },
    ]);
    expect(stub.snapshotCalls()).toBe(4);
    expect(snap.visibility?.pins).toEqual([]);
  });
});

describe("highlight console actions (exx.2, §9)", () => {
  let calls: { fn: string; args: unknown[] }[];

  async function stubConsole(stub: RawIpc): Promise<Console> {
    return (await freshConsole(stub)).console_;
  }

  beforeEach(() => {
    calls = [];
  });

  it("add/setEnabled/setColor/remove/clear flow through the RAW commands", async () => {
    const rec = (fn: string) => async (...args: unknown[]) => {
      calls.push({ fn, args });
      return null;
    };
    const console_ = await stubConsole(visibilityStub());
    // Wrap the installed stub's highlight methods to record the RAW calls.
    const raw = (window as unknown as Record<string, unknown>).__ipcStub as RawIpc;
    raw.addHighlight = rec("addHighlight");
    raw.setHighlightEnabled = rec("setHighlightEnabled");
    raw.setHighlightColor = rec("setHighlightColor");
    raw.removeHighlight = rec("removeHighlight");
    raw.clearHighlights = rec("clearHighlights");
    await console_.load("/tmp/log.txt");
    calls = [];
    await console_.addHighlight("plain", "timeout");
    await console_.setHighlightEnabled(0, false);
    await console_.setHighlightColor(0, "#00aabb");
    await console_.setHighlightColor(0, null);
    await console_.removeHighlight(0);
    await console_.clearAllHighlights();
    expect(calls).toEqual([
      { fn: "addHighlight", args: ["plain", "timeout"] },
      { fn: "setHighlightEnabled", args: [0, false] },
      { fn: "setHighlightColor", args: [0, "#00aabb"] },
      { fn: "setHighlightColor", args: [0, null] },
      { fn: "removeHighlight", args: [0] },
      { fn: "clearHighlights", args: [] },
    ]);
  });

  it("the snapshot's highlights come back normalized and reachable on the text RPC", async () => {
    const console_ = await stubConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    await console_.addHighlight("lineno", "42");
    await console_.addHighlight("regex", "^retry");
    await console_.setHighlightEnabled(1, false);
    await console_.setHighlightColor(0, "#123456");
    const snap = console_.getSnapshot();
    expect(snap.visibility?.highlights).toEqual([
      { id: 0, mode: "lineno", pattern: "42", enabled: true, colorIndex: 0, overrideColor: "#123456" },
      { id: 1, mode: "regex", pattern: "^retry", enabled: false, colorIndex: 1, overrideColor: null },
    ]);
  });

  it("a failing highlight mutation surfaces through the error state and keeps the snapshot", async () => {
    const console_ = await stubConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    await console_.addHighlight("plain", "x");
    const before = console_.getSnapshot();
    const raw = (window as unknown as Record<string, unknown>).__ipcStub as RawIpc;
    raw.addHighlight = async () => {
      throw new Error("no such mode");
    };
    const snap = await console_.addHighlight("no-such-mode", "y");
    expect(snap.error).toContain("no such mode");
    expect(snap.visibility).toEqual(before.visibility);
  });

  it("the headless mirror exposes the five actions (addHighlight/setHighlightEnabled/setHighlightColor/removeHighlight/clearHighlights)", async () => {
    const console_ = await stubConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    const reset = installHeadlessConsole();
    try {
      const headless = (window as unknown as Record<string, unknown>)
        .__headless as Record<string, unknown> | undefined;
      expect(headless).not.toBeUndefined();
      for (const name of [
        "addHighlight", "setHighlightEnabled", "setHighlightColor",
        "removeHighlight", "clearHighlights",
      ]) {
        expect(typeof headless?.[name]).toBe("function");
      }
      const mirror = headless as {
        addHighlight(mode: string, pattern: string): Promise<unknown>;
        setHighlightEnabled(id: number, on: boolean): Promise<unknown>;
        setHighlightColor(id: number, hex: string | null): Promise<unknown>;
        removeHighlight(id: number): Promise<unknown>;
        clearHighlights(): Promise<unknown>;
      };
      await mirror.addHighlight("plain", "timeout");
      await mirror.setHighlightEnabled(0, false);
      await mirror.setHighlightColor(0, "#ff00ff");
      await mirror.removeHighlight(0);
      await mirror.addHighlight("lineno", "7");
      await mirror.clearHighlights();
      const snap = console_.getSnapshot();
      expect(snap.visibility?.highlights).toEqual([]);
      expect(snap.error).toBeNull();
    } finally {
      reset();
    }
  });
});

// ---- load/visibility snapshot guarantee (live round 4) ----

/** Stub whose visibilitySnapshot answers from a scripted queue: the first
 *  call resolves with `firstCount` (immediately, or deferred until
 *  `releaseFirst`), every later call with `later`. All snapshots report
 *  every level enabled, no filters/pins and the full category whitelist —
 *  only `visible_count` varies. */
interface LoadStub extends RawIpc {
  servedCounts: number[];
  setLevelCalls: string[];
  releaseFirst: (count: number) => void;
}

function loadStub(options: {
  firstCount: number;
  deferFirst?: boolean;
  laterCount: number;
}): LoadStub {
  const servedCounts: number[] = [];
  const setLevelCalls: string[] = [];
  let release: ((count: number) => void) | null = null;
  // A release may arrive before the deferred refetch is issued (the console
  // serializes its operations on microtasks): park it and apply on issue.
  let pendingRelease: number | null = null;
  const fullWhitelist = ["app", "app/db"];
  const snapshot = (count: number): VisibilitySnapshotDto => ({
    visible_count: count,
    levels: ["critical", "error", "warning", "msg", "debug", "trace"].map(
      (level) => ({ level, enabled: true, count: 1 }),
    ),
    filters: [],
    pins: [],
    highlights: [],
    categories_enabled: [...fullWhitelist],
  });
  return {
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: 42,
      categories: [{ path: "app/db", count: 42 }], levels: [], load_ms: 1,
    }),
    getRows: async () => [],
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      setLevelCalls.push(level + ":" + String(on));
      return null;
    },
    setCategoryEnabled: async () => null,
    clearPins: async () => null,
    addHighlight: async () => null,
    setHighlightEnabled: async () => null,
    setHighlightColor: async () => null,
    removeHighlight: async () => null,
    clearHighlights: async () => null,
    searchVisible: async () => ({ total: 0, positions: [] }),
    visibilitySnapshot: async (): Promise<VisibilitySnapshotDto> => {
      if (servedCounts.length === 0) {
        servedCounts.push(options.firstCount);
        if (options.deferFirst) {
          return new Promise((resolve) => {
            const settle = (count: number) => {
              servedCounts[servedCounts.length - 1] = count;
              resolve(snapshot(count));
            };
            release = settle;
            if (pendingRelease !== null) {
              const parked = pendingRelease;
              pendingRelease = null;
              settle(parked);
            }
          });
        }
        return snapshot(options.firstCount);
      }
      servedCounts.push(options.laterCount);
      return snapshot(options.laterCount);
    },
    servedCounts,
    setLevelCalls,
    releaseFirst: (count: number) => {
      const r = release;
      if (r === null) {
        pendingRelease = count;
        return;
      }
      r(count);
    },
  };
}

describe("load/visibility snapshot guarantee (live round 4)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  it("stuck-0 shell cache after a load heals: an impossible snapshot (0 visible, nothing disabled) triggers an idempotent rebuild round", async () => {
    const stub = loadStub({ firstCount: 0, laterCount: 42 });
    const { console_ } = await freshConsole(stub);
    const snap = await console_.load("/tmp/log.txt");
    // The returned snapshot must reflect the post-load backend state, not
    // the stale cached mid-load one (visibleCount 0 while everything is
    // enabled is impossible for a 42-row file).
    expect(snap.error).toBeNull();
    expect(snap.visibility?.visibleCount).toBe(42);
    expect(console_.getSnapshot().visibility?.visibleCount).toBe(42);
    expect(stub.setLevelCalls).toEqual(["critical:true"]);
  });

  it("a late in-flight refetch over an overlapping load never lands stale; both loads return the fresh state", async () => {
    const stub = loadStub({ firstCount: 0, deferFirst: true, laterCount: 42 });
    const { console_ } = await freshConsole(stub);
    // Overlapping loads (the driver's retried /load requests hit the page
    // like this): B's snapshot refetch may resolve before A's.
    const loadA = console_.load("/tmp/first.txt");
    const loadB = console_.load("/tmp/second.txt");
    // A's refetch resolves LATE with the stale (0) content…
    stub.releaseFirst(0);
    const [snapA, snapB] = await Promise.all([loadA, loadB]);
    // …but its landing must not regress the state, and neither load's
    // returned snapshot may precede its own backend state.
    expect(console_.getSnapshot().visibility?.visibleCount).toBe(42);
    expect(snapA.visibility?.visibleCount).toBe(42);
    expect(snapB.visibility?.visibleCount).toBe(42);
  });

  it("the reload path: a second load returns the fresh visibility too (plausible snapshots land untouched)", async () => {
    const stub = loadStub({ firstCount: 42, laterCount: 42 });
    const { console_ } = await freshConsole(stub);
    const first = await console_.load("/tmp/log.txt");
    expect(stub.setLevelCalls).toEqual([]); // no heal on a plausible snapshot
    expect(first.visibility?.visibleCount).toBe(42);
    const second = await console_.load("/tmp/log.txt");
    expect(second.visibility?.visibleCount).toBe(42);
    expect(stub.servedCounts).toEqual([42, 42]);
  });
});
