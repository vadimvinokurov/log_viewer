//! uiConsole tests (dsq.3): visibility mutations through the console RPC
//! refetch the snapshot and dispatch it into the reducer; failures surface
//! through the existing error state. The module singleton is re-imported
//! fresh per test so the narrative runs stay isolated.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installHeadlessConsole } from "./headless";
import { resolveCommand } from "./cmdline";
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
      format: "plain", line_count: 12, size_bytes: 883, categories: [], levels: [], load_ms: 1,
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
    clearFilters: async () => {
      filters.length = 0;
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
    setCategoriesBulk: async () => null,
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
      format: "plain", line_count: LINE_COUNT, size_bytes: 883, categories: [], levels: [], load_ms: 1,
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
    clearFilters: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "trace") throw new Error(`no such level: ${level}`);
      if (options.failMutation === "setLevel") throw new Error("ipc down");
      traceOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
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

  // §2.1 action 5 (bead n4y.2): loading a file closes the search panel.
  it("load closes the search panel", async () => {
    const { console_ } = await freshConsole(visibilityStub());
    await console_.load("/tmp/log.txt");
    console_.openSearch();
    console_.setSearchQuery("error");
    expect(console_.getSnapshot().search?.open).toBe(true);
    const snap = await console_.load("/tmp/log2.txt");
    expect(snap.search?.open).toBe(false);
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
    { path: "app" },
    { path: "app/main" },
    { path: "app/main/db" },
    { path: "app/main/api" },
    { path: "db" },
    { path: "db/pool" },
    { path: "uncategorized" },
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
  /** The bulk differentials, recorded verbatim for the one-call assertion. */
  const bulkCalls: { disable: string[]; enable: string[] }[] = [];
  const allowed = (cat: string): boolean => {
    if (!enabled.has(cat)) return false;
    let i = cat.indexOf("/");
    while (i !== -1) { if (!enabled.has(cat.slice(0, i))) return false; i = cat.indexOf("/", i + 1); }
    return true;
  };
  const stub: RawIpc & {
    setCategoryCalls(): string[];
    setCategoryBulkCalls(): { disable: string[]; enable: string[] }[];
  } = {
    ...highlightNoops(),
    pickFile: async () => null,
    loadFile: async () => ({
      format: "plain", line_count: 100, size_bytes: 883,
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
    clearFilters: async () => null,
    setLevelEnabled: async () => null,
    setCategoryEnabled: async (path, on) => {
      calls.push((on ? "+" : "-") + path);
      if (on) enabled.add(path); else enabled.delete(path);
      return null;
    },
    setCategoriesBulk: async (disable, enable) => {
      bulkCalls.push({ disable: [...disable], enable: [...enable] });
      for (const p of disable) enabled.delete(p);
      for (const p of enable) enabled.add(p);
      return null;
    },
    searchVisible: async () => ({ total: 0, positions: [] }),
    visibilitySnapshot: async () => ({
      // Row model without per-category counts (2026-11-25 owner decision):
      // each observed path stands in for its rows, so visible_count is the
      // number of allowed observed paths; tests assert transitions, not row
      // arithmetic.
      visible_count: CATEGORIES.filter((c) => allowed(c.path)).length,
      levels: [],
      filters: [],
      pins: [],
      highlights: [],
      categories_enabled: [...enabled].sort(),
    }),
    setCategoryCalls: () => calls,
    setCategoryBulkCalls: () => bulkCalls,
  };
  return stub;
}

/** The tree's paths in the byte-order sort category helpers emit. */
const TREE_PATHS = [
  "app", "app/main", "app/main/api", "app/main/db",
  "db", "db/pool", "uncategorized",
];
const CATEGORY_TOGGLE_ALL = TREE_PATHS;

describe("panel console actions (rhl.2, §10.1)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  it("the snapshot mirrors the panel slice", async () => {
    const { console_ } = await freshConsole(categoryStub());
    expect(console_.getSnapshot().panel).toEqual({
      open: true, tab: "categories", width: 280, search: "", expanded: [],
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

  it("expandAllCategories(expand=false) closes everything (2026-11-25 owner decision)", async () => {
    const { console_ } = await freshConsole(categoryStub());
    await console_.load("/tmp/log.txt");
    await console_.expandAllCategories(true);
    const expanded = console_.expandAllCategories(false).panel.expanded;
    expect(expanded).toEqual([]);
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

  it("toggleCategory(off) drives the propagateToggle differential through ONE bulk call and refetches", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const snap = await console_.toggleCategory("app", false);
    // down-propagation removes the node + its subtree paths; ancestors stay.
    // One wire call (disable, enable), not one call per path: a read can
    // never observe a mid-differential whitelist (bead 3af).
    expect(stub.setCategoryBulkCalls()).toEqual([
      { disable: ["app", "app/main", "app/main/api", "app/main/db"], enable: [] },
    ]);
    expect(stub.setCategoryCalls()).toEqual([]);
    expect(snap.visibility?.categoriesEnabled).toEqual(["db", "db/pool", "uncategorized"]);
    // app subtree paths drop out of the visible count (3 of the 7 observed
    // paths stay allowed — row model without counts).
    expect(snap.visibility?.visibleCount).toBe(3);
  });

  it("toggleCategory(on) adds the subtree + every ancestor prefix", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.toggleCategory("app", false);
    stub.setCategoryBulkCalls().length = 0;
    const snap = await console_.toggleCategory("app", true);
    expect(stub.setCategoryBulkCalls()).toEqual([
      { disable: [], enable: ["app", "app/main", "app/main/api", "app/main/db"] },
    ]);
    expect(snap.visibility?.visibleCount).toBe(7);
  });

  it("setAllCategories(on=false) unchecks everything via the All checkbox", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    const snap = await console_.setAllCategories(false);
    expect(stub.setCategoryBulkCalls()).toEqual([
      { disable: CATEGORY_TOGGLE_ALL, enable: [] },
    ]);
    expect(snap.visibility?.visibleCount).toBe(0);
  });

  it("setAllCategories(on=true) checks everything", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    await console_.setAllCategories(false);
    stub.setCategoryBulkCalls().length = 0;
    const snap = await console_.setAllCategories(true);
    expect(stub.setCategoryBulkCalls()).toEqual([
      { disable: [], enable: CATEGORY_TOGGLE_ALL },
    ]);
    expect(snap.visibility?.visibleCount).toBe(7);
  });

  it("toggleCategory without a loaded file is a safe no-op", async () => {
    const stub = categoryStub();
    const { console_ } = await freshConsole(stub);
    const snap = await console_.toggleCategory("app", false);
    expect(stub.setCategoryCalls()).toEqual([]);
    expect(snap.visibility ?? null).toBeNull();
  });

  it("a failing bulk category differential surfaces through the error state and keeps the snapshot", async () => {
    const stub = categoryStub();
    stub.setCategoriesBulk = async () => {
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
      format: "plain", line_count: LINE_COUNT, size_bytes: 883, categories: [], levels: [], load_ms: 1,
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
    clearFilters: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "msg") throw new Error(`no such level: ${level}`);
      msgOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
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
      format: "plain", line_count: LINE_COUNT, size_bytes: 883, categories: [], levels: [], load_ms: 1,
    }),
    getRows: async () => [],
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    clearPins: async () => null,
    clearFilters: async () => null,
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "msg") throw new Error(`no such level: ${level}`);
      msgOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
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
      format: "plain", line_count: 10, size_bytes: 883,
      categories: [{ path: "a" }, { path: "b" }],
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
    clearFilters: async () => null,
    setLevelEnabled: async () => null,
    setCategoryEnabled: async (path: string, on: boolean) => {
      if (path !== "a" && path !== "b") throw new Error("no such category");
      await new Promise((resolve) => setTimeout(resolve, 200));
      if (on) applied[path as "a" | "b"] = true;
      else applied[path as "a" | "b"] = false;
      return null;
    },
    // The bulk differential applies as ONE (delayed) wire call: a mid-burst
    // transient whitelist no longer exists (bead 3af); the window the old
    // armed-recompute probe used to race is the one this stub's 200 ms
    // delay still models for any OTHER one-by-one wire call.
    setCategoriesBulk: async (disable: string[], enable: string[]) => {
      await new Promise((resolve) => setTimeout(resolve, 200));
      for (const p of disable) applied[p as "a" | "b"] = false;
      for (const p of enable) applied[p as "a" | "b"] = true;
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
        format: "plain", line_count: LINE_COUNT, size_bytes: 883, categories: [], levels: [], load_ms: 1,
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
      clearFilters: async () => {
        calls.push({ fn: "clearFilters", args: [] });
        return null;
      },
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
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
      format: "plain", line_count: 42, size_bytes: 883,
      categories: [{ path: "app/db" }], levels: [], load_ms: 1,
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
    setCategoriesBulk: async () => null,
    clearPins: async () => null,
    clearFilters: async () => null,
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

describe("console command line (bead 7rf.1, §13/§13.1)", () => {
  /** RAW stub with an in-memory filter/pin/highlight model and a call log:
   *  line_count 12 (fn/hn/pn range 1..12); every wire call is recorded so
   *  the tests can assert that an invalid command makes ZERO calls. */
  interface CmdStub extends RawIpc {
    addFilterCalls(): { mode: string; pattern: string }[];
    addPinCalls(): { mode: string; pattern: string }[];
    addHighlightCalls(): { mode: string; pattern: string }[];
    clearCalls(): string[];
    /** The persistent history file's contents (bead 7rf.2): read by
     *  history_get, written by history_push (append + cap/dedupe server-side
     *  semantics already tested in the store's own tests). Mutating the
     *  returned array pre-seeds the store. */
    historyStore(): string[];
    historyGetCalls(): number;
    historyGet(): Promise<string[]>;
    historyPush(cmd: string): Promise<null>;
  }

  function cmdStub(options: { failHistoryGet?: boolean; failHistoryPush?: boolean } = {}): CmdStub {
    const lines: Record<string, { mode: string; pattern: string }[]> = {
      filters: [], pins: [], highlights: [],
    };
    const added: Record<string, { mode: string; pattern: string }[]> = {
      filters: [], pins: [], highlights: [],
    };
    const cleared: string[] = [];
    const counters: Record<string, number> = { filters: 0, pins: 0, highlights: 0 };
    const history: string[] = [];
    let getCalls = 0;
    return {
      addFilterCalls: () => added.filters,
      addPinCalls: () => added.pins,
      addHighlightCalls: () => added.highlights,
      clearCalls: () => cleared,
      historyStore: () => history,
      historyGetCalls: () => getCalls,
      pickFile: async () => null,
      loadFile: async () => ({
        format: "plain", line_count: 12, size_bytes: 883, categories: [], levels: [], load_ms: 1,
      }),
      getRows: async () => [],
      addFilter: async (mode: string, pattern: string) => {
        counters.filters += 1;
        added.filters.push({ mode, pattern });
        lines.filters.push({ mode, pattern });
        return null;
      },
      setFilterEnabled: async () => null,
      removeFilter: async () => null,
      addPin: async (mode: string, pattern: string) => {
        counters.pins += 1;
        added.pins.push({ mode, pattern });
        lines.pins.push({ mode, pattern });
        return null;
      },
      setPinEnabled: async () => null,
      removePin: async () => null,
      clearPins: async () => { cleared.push("clearPins"); lines.pins.length = 0; return null; },
      clearFilters: async () => { cleared.push("clearFilters"); lines.filters.length = 0; return null; },
      addHighlight: async (mode: string, pattern: string) => {
        counters.highlights += 1;
        added.highlights.push({ mode, pattern });
        lines.highlights.push({ mode, pattern });
        return null;
      },
      setHighlightEnabled: async () => null,
      setHighlightColor: async () => null,
      removeHighlight: async () => null,
      clearHighlights: async () => { cleared.push("clearHighlights"); lines.highlights.length = 0; return null; },
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
      historyGet: async () => {
        getCalls += 1;
        if (options.failHistoryGet) {
          throw new Error("history read failed");
        }
        return [...history];
      },
      historyPush: async (cmd: string) => {
        if (options.failHistoryPush) {
          throw new Error("history write failed");
        }
        history.push(cmd);
        return null;
      },
      searchVisible: async () => ({ total: 0, positions: [] }),
      visibilitySnapshot: async () => ({
        visible_count: 12,
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level, enabled: true, count: 2,
        })),
        filters: lines.filters.map((f, id) => ({ ...f, id, enabled: true })),
        pins: lines.pins.map((p, id) => ({ ...p, id, enabled: true })),
        highlights: lines.highlights.map((h, id) => ({
          ...h, id, enabled: true, color_index: 0, override_color: null,
        })),
        categories_enabled: ["app/db"],
      }),
    };
  }

  async function loaded(): Promise<{ console_: Console; stub: CmdStub }> {
    const stub = cmdStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    return { console_, stub };
  }

  it("adds pattern filters through the registry: :f / :fr / :fs", async () => {
    const { console_, stub } = await loaded();
    await console_.executeCommand(":f timeout");
    await console_.executeCommand("fr ^retry.*"); // the ':' is optional in the field
    await console_.executeCommand(":fs (\"auth\" OR \"login\")");
    expect(stub.addFilterCalls()).toEqual([
      { mode: "plain", pattern: "timeout" },
      { mode: "regex", pattern: "^retry.*" },
      { mode: "simple", pattern: "(\"auth\" OR \"login\")" },
    ]);
    const snap = console_.getSnapshot();
    expect(snap.error).toBeNull();
    expect(snap.visibility?.filters.map((f) => f.mode)).toEqual(["plain", "regex", "simple"]);
  });

  it("adds lineno filters, highlights and pins: :fn / :hn / :pn", async () => {
    const { console_, stub } = await loaded();
    await console_.executeCommand(":fn 12");
    await console_.executeCommand(":hn 7");
    await console_.executeCommand(":pn 3");
    expect(stub.addFilterCalls()).toEqual([{ mode: "lineno", pattern: "12" }]);
    expect(stub.addHighlightCalls()).toEqual([{ mode: "lineno", pattern: "7" }]);
    expect(stub.addPinCalls()).toEqual([{ mode: "lineno", pattern: "3" }]);
  });

  it("rmf/rmh/rmp clear wholesale with exactly one wire call each", async () => {
    const { console_, stub } = await loaded();
    await console_.executeCommand(":f timeout");
    await console_.executeCommand(":h timeout");
    await console_.executeCommand(":p cfg");
    await console_.executeCommand(":rmf");
    await console_.executeCommand(":rmh");
    await console_.executeCommand("rmp");
    expect(stub.clearCalls()).toEqual(["clearFilters", "clearHighlights", "clearPins"]);
    const snap = console_.getSnapshot();
    expect(snap.visibility?.filters).toEqual([]);
    expect(snap.visibility?.highlights).toEqual([]);
    expect(snap.visibility?.pins).toEqual([]);
  });

  it("an unknown command surfaces the verbatim error and makes NO wire call", async () => {
    const { console_, stub } = await loaded();
    const snap = await console_.executeCommand(":unknown value");
    expect(snap.error).toBe("Unknown command");
    expect(stub.addFilterCalls()).toEqual([]);
    expect(stub.addPinCalls()).toEqual([]);
    expect(stub.addHighlightCalls()).toEqual([]);
    expect(stub.clearCalls()).toEqual([]);
  });

  it("a missing argument and a range break surface an error with no partial execution", async () => {
    const { console_, stub } = await loaded();
    let snap = await console_.executeCommand(":f");
    expect(snap.error).toBe("Error: f requires a pattern");
    snap = await console_.executeCommand(":fn 13");
    expect(snap.error).toBe("Error: fn 13 out of range (1..12)");
    snap = await console_.executeCommand(":rmf oops");
    expect(snap.error).toBe("Error: rmf takes no arguments");
    expect(stub.addFilterCalls()).toEqual([]);
    expect(stub.clearCalls()).toEqual([]);
    // The failed commands kept the state intact.
    expect(snap.visibility?.filters).toEqual([]);
  });

  it("a back-end failure on a VALID command surfaces through the existing error channel", async () => {
    const { console_ } = await loaded();
    const target = window as unknown as Record<string, unknown>;
    const stub = target.__ipcStub as RawIpc;
    stub.addFilter = async () => { throw new Error("no such mode"); };
    const snap = await console_.executeCommand(":fr [bad");
    expect(snap.error).toContain("no such mode");
  });

  it("an empty submission is a no-op: no error, no wire call, nothing stored", async () => {
    const { console_, stub } = await loaded();
    const snap = await console_.executeCommand("   ");
    expect(snap.error).toBeNull();
    expect(stub.addFilterCalls()).toEqual([]);
    expect(console_.getCmdline().history).toEqual([]);
  });

  it("submissions clear the field and enter the in-session history with dedupe", async () => {
    const { console_ } = await loaded();
    console_.setCommandText(":f a");
    await console_.submitCommand();
    expect(console_.getCmdline().value).toBe("");
    console_.setCommandText("f b");
    await console_.submitCommand();
    console_.setCommandText("f b");
    await console_.submitCommand(); // consecutive duplicate
    expect(console_.getCmdline().history).toEqual([":f a", "f b"]);
    expect(console_.getCommandHistoryIndex()).toBe(2);
  });

  it("failed, invalid and unknown commands enter the history too (they were entered)", async () => {
    const { console_ } = await loaded();
    await console_.executeCommand(":f");
    await console_.executeCommand(":unknown 1");
    expect(console_.getCmdline().history).toEqual([":f", ":unknown 1"]);
  });

  it("recallHistory walks the history through the snapshot: up = older, down = newer, past the end = empty", async () => {
    const { console_ } = await loaded();
    await console_.executeCommand(":f a");
    await console_.executeCommand(":f b");
    expect(console_.getSnapshot().command.history).toEqual([":f a", ":f b"]);
    console_.recallCommandHistory(-1);
    expect(console_.getCmdline().value).toBe(":f b");
    console_.recallCommandHistory(-1);
    expect(console_.getCmdline().value).toBe(":f a");
    console_.recallCommandHistory(-1); // clamped at the oldest
    expect(console_.getCmdline().value).toBe(":f a");
    console_.recallCommandHistory(1);
    console_.recallCommandHistory(1);
    expect(console_.getSnapshot().command.value).toBe("");
    expect(console_.getSnapshot().command.historyIndex).toBe(2);
  });

  it("typing after a recall rewinds the cursor; the ':' activation pre-fills ':' and bumps focusTick", async () => {
    const { console_ } = await loaded();
    await console_.executeCommand(":f a");
    console_.recallCommandHistory(-1);
    console_.setCommandText(":f b");
    expect(console_.getCmdline().value).toBe(":f b");
    expect(console_.getCommandHistoryIndex()).toBe(1);
    const before = console_.getCmdline().focusTick;
    console_.activateCmdline();
    const cmd = console_.getCmdline();
    expect(cmd.value).toBe(":");
    expect(cmd.focusTick).toBe(before + 1);
    // Activation is not a history event.
    expect(cmd.history).toEqual([":f a"]);
  });
});

describe("persistent command history (bead 7rf.2, §13.2)", () => {
  /** RAW stub mirroring the history commands (bead 7rf.2) over a minimal
   *  visibility model: history_get reads the persisted file's contents,
   *  history_push appends to it; line_count 12 so the :f/:h commands execute
   *  for real. Call failures are opt-in (best-effort catch paths). */
  interface HistStub extends RawIpc {
    /** The persistent file's contents — mutate to pre-seed the store. */
    historyStore(): string[];
    historyGetCalls(): number;
    historyGet(): Promise<string[]>;
    historyPush(cmd: string): Promise<null>;
  }

  function histStub(
    options: { failHistoryGet?: boolean; failHistoryPush?: boolean } = {},
  ): HistStub {
    const filters: { mode: string; pattern: string; enabled: boolean }[] = [];
    const added: { mode: string; pattern: string }[] = [];
    const history: string[] = [];
    let getCalls = 0;
    return {
      pickFile: async () => null,
      loadFile: async () => ({
        format: "plain", line_count: 12, size_bytes: 883, categories: [], levels: [], load_ms: 1,
      }),
      getRows: async () => [],
      addFilter: async (mode: string, pattern: string) => {
        added.push({ mode, pattern });
        filters.push({ mode, pattern, enabled: true });
        return null;
      },
      setFilterEnabled: async () => null,
      removeFilter: async () => null,
      addPin: async () => null,
      setPinEnabled: async () => null,
      removePin: async () => null,
      clearPins: async () => null,
      clearFilters: async () => null,
      addHighlight: async () => null,
      setHighlightEnabled: async () => null,
      setHighlightColor: async () => null,
      removeHighlight: async () => null,
      clearHighlights: async () => null,
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
      historyGet: async () => {
        getCalls += 1;
        if (options.failHistoryGet) {
          throw new Error("history read failed");
        }
        return [...history];
      },
      historyPush: async (cmd: string) => {
        if (options.failHistoryPush) {
          throw new Error("history write failed");
        }
        history.push(cmd);
        return null;
      },
      searchVisible: async () => ({ total: 0, positions: [] }),
      visibilitySnapshot: async () => ({
        visible_count: 12,
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level, enabled: true, count: 2,
        })),
        filters: filters.map((f, id) => ({ ...f, id })),
        pins: [],
        highlights: [],
        categories_enabled: ["app/db"],
      }),
      historyStore: () => history,
      historyGetCalls: () => getCalls,
    };
  }

  async function loadedHistory(
    stub: HistStub = histStub(),
  ): Promise<{ console_: Console; stub: HistStub }> {
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    return { console_, stub };
  }

  it("a successful submit pushes the session's trimmed entry to the store", async () => {
    const { console_, stub } = await loadedHistory();
    console_.setCommandText("  :f a  ");
    await console_.submitCommand();
    expect(stub.historyStore()).toEqual([":f a"]);
    console_.setCommandText(":f b");
    await console_.submitCommand();
    expect(stub.historyStore()).toEqual([":f a", ":f b"]);
    // The session list and the store stay in step (the same trimmed text,
    // verbatim with its ':' as entered).
    expect(console_.getCmdline().history).toEqual([":f a", ":f b"]);
  });

  it("a consecutive duplicate and a no-op submission are never pushed", async () => {
    const { console_, stub } = await loadedHistory();
    await console_.executeCommand(":f b");
    await console_.executeCommand(":f b"); // consecutive duplicate in both lists
    await console_.executeCommand("   "); // a whitespace-only submission: nothing stored
    expect(stub.historyStore()).toEqual([":f b"]);
    expect(console_.getCmdline().history).toEqual([":f b"]);
    // ALL entered commands go to history (§13.2) — an invalid one too;
    // validate-then-execute changes the wire call, not the storage rule.
    await console_.executeCommand(":unknown 1");
    expect(stub.historyStore()).toEqual([":f b", ":unknown 1"]);
    expect(console_.getCmdline().history).toEqual([":f b", ":unknown 1"]);
    // A bare ':' submission follows the current storage rule too (a
    // non-empty trimmed text): stored once, pushed once.
    await console_.executeCommand(":");
    expect(stub.historyStore()).toEqual([":f b", ":unknown 1", ":"]);
  });

  it("loaded history seeds the recall cycle of a fresh console instance (reload)", async () => {
    const stub = histStub();
    stub.historyStore().push("f old", ":h message 31"); // the pre-existing ~/.logviewer store
    const { console_ } = await loadedHistory(stub);
    expect(stub.historyGetCalls()).toBeGreaterThanOrEqual(1);
    expect(console_.getCmdline().history).toEqual(["f old", ":h message 31"]);
    // The recall cursor stands at the empty draft past the seeded newest.
    expect(console_.getCommandHistoryIndex()).toBe(2);
    console_.recallCommandHistory(-1);
    expect(console_.getCmdline().value).toBe(":h message 31");
    console_.recallCommandHistory(-1);
    expect(console_.getCmdline().value).toBe("f old");
    console_.recallCommandHistory(-1); // clamped at the oldest
    expect(console_.getCmdline().value).toBe("f old");
    console_.recallCommandHistory(1);
    console_.recallCommandHistory(1);
    expect(console_.getCmdline().value).toBe(""); // empty draft after the newest
  });

  it("a failed read keeps the session list; a failed write keeps it too (best-effort)", async () => {
    const readerStub = histStub({ failHistoryGet: true });
    readerStub.historyStore().push("f old");
    const { console_: reader } = await loadedHistory(readerStub);
    // The read failure leaves the in-session list untouched.
    expect(reader.getCmdline().history).toEqual([]);
    expect(reader.getCommandHistoryIndex()).toBe(0);

    const { console_: writer, stub } = await loadedHistory(
      histStub({ failHistoryPush: true }),
    );
    await writer.executeCommand(":f a");
    expect(writer.getCmdline().history).toEqual([":f a"]); // the session keeps it
    expect(stub.historyStore()).toEqual([]); // the store write failed silently
    writer.recallCommandHistory(-1);
    expect(writer.getCmdline().value).toBe(":f a");
  });

  it("the store is read once per instance; a resubmitted recall is NOT pushed again", async () => {
    const { console_, stub } = await loadedHistory();
    const reads = stub.historyGetCalls();
    await console_.executeCommand(":f a");
    expect(stub.historyStore()).toEqual([":f a"]);
    // ↑ brings ":f a" back into the field; Enter resubmits it — the
    // consecutive duplicate is pushed neither into the session nor the store.
    console_.recallCommandHistory(-1);
    expect(console_.getCmdline().value).toBe(":f a");
    await console_.submitCommand();
    expect(stub.historyGetCalls()).toBe(reads); // recall never re-reads
    expect(stub.historyStore()).toEqual([":f a"]);
    expect(console_.getCmdline().history).toEqual([":f a"]);
  });
});

describe("console command line live-round (bead 7rf.1, §13.1 branches + error lifetime)", () => {
  /** The same RAW stub shape as the cmdline describe (line_count 12). */
  function cmdStub(): RawIpc & { addFilterCalls(): { mode: string; pattern: string }[] } {
    const filters: { mode: string; pattern: string }[] = [];
    const added: { mode: string; pattern: string }[] = [];
    return {
      addFilterCalls: () => added,
      pickFile: async () => null,
      loadFile: async () => ({
        format: "plain", line_count: 12, size_bytes: 883, categories: [], levels: [], load_ms: 1,
      }),
      getRows: async () => [],
      addFilter: async (mode: string, pattern: string) => {
        added.push({ mode, pattern });
        filters.push({ mode, pattern });
        return null;
      },
      setFilterEnabled: async () => null,
      removeFilter: async () => null,
      addPin: async () => null,
      setPinEnabled: async () => null,
      removePin: async () => null,
      clearPins: async () => null,
      clearFilters: async () => null,
      addHighlight: async () => null,
      setHighlightEnabled: async () => null,
      setHighlightColor: async () => null,
      removeHighlight: async () => null,
      clearHighlights: async () => null,
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
      searchVisible: async () => ({ total: 0, positions: [] }),
      visibilitySnapshot: async () => ({
        visible_count: 12,
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level, enabled: true, count: 2,
        })),
        filters: filters.map((f, id) => ({ ...f, id, enabled: true })),
        pins: [],
        highlights: [],
        categories_enabled: ["app/db"],
      }),
    };
  }

  async function loaded(): Promise<{ console_: Console; stub: ReturnType<typeof cmdStub> }> {
    const stub = cmdStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("/tmp/log.txt");
    return { console_, stub };
  }

  it("a successful command clears the previous error (the message is the LAST command's)", async () => {
    const { console_ } = await loaded();
    const failed = await console_.executeCommand(":unknown value");
    expect(failed.error).toBe("Unknown command");
    const ok = await console_.executeCommand(":fn 1");
    expect(ok.error).toBe(""); // cleared through the load-error channel (falsy in the footer)
    expect(ok.visibility?.filters).toEqual([
      { id: 0, mode: "lineno", pattern: "1", enabled: true },
    ]);
    // Clearing never fires while a load is in flight (the event would drop
    // the loading marker): covered by the busy guard in the console.
  });

  it(":fn 999999 on a 12-line file is the verbatim range error with NO filter added", async () => {
    const { console_, stub } = await loaded();
    const snap = await console_.executeCommand(":fn 999999");
    expect(snap.error).toBe("Error: fn 999999 out of range (1..12)");
    expect(stub.addFilterCalls()).toEqual([]);
    expect(snap.visibility?.filters).toEqual([]);
  });

  it("a non-integer arg is the arg-format error for fn/hn/pn with no wire call", async () => {
    const { console_, stub } = await loaded();
    let snap = await console_.executeCommand(":fn abc");
    expect(snap.error).toBe("Error: fn requires a line number");
    snap = await console_.executeCommand(":hn 12.5");
    expect(snap.error).toBe("Error: hn requires a line number");
    snap = await console_.executeCommand(":pn -3");
    expect(snap.error).toBe("Error: pn -3 out of range (1..12)"); // -3 is an integer: range branch
    expect(stub.addFilterCalls()).toEqual([]);
  });

  it("an integer inside 1..line_count still executes (fn 1 adds the lineno filter)", async () => {
    const { console_, stub } = await loaded();
    const snap = await console_.executeCommand(":fn 1");
    expect(snap.error).toBeNull(); // no error at all on a clean success
    expect(stub.addFilterCalls()).toEqual([{ mode: "lineno", pattern: "1" }]);
  });
});

describe("last open dir persistence (bead vk9.2, §2/§15)", () => {
  /** RAW stub with the settings commands over a minimal visibility model:
   *  settings_get returns the persisted last_open_dir, set_last_open_dir
   *  records its calls (and updates the stored value). Failures are
   *  opt-in (the best-effort catch paths). */
  interface SettingsStub extends RawIpc {
    settingsGet(): Promise<{
      history_size: number;
      last_open_dir: string;
      default_categories_enabled: boolean;
    }>;
    setLastOpenDir(dir: string): Promise<null>;
    setLastOpenDirCalls(): string[];
    /** The stored setting as the (stubbed) backend holds it. */
    settingsStore(): string;
  }

  function settingsStub(
    options: { failSettingsGet?: boolean; failSet?: boolean; failLoad?: boolean } = {},
  ): SettingsStub {
    const stored = { lastOpenDir: "/tmp/logs" };
    const setCalls: string[] = [];
    return {
      pickFile: async () => null,
      loadFile: async () => {
        if (options.failLoad) throw new Error("load failed");
        return {
          format: "plain", line_count: 12, size_bytes: 883, categories: [], levels: [], load_ms: 1,
        };
      },
      getRows: async () => [],
      addFilter: async () => null,
      setFilterEnabled: async () => null,
      removeFilter: async () => null,
      addPin: async () => null,
      setPinEnabled: async () => null,
      removePin: async () => null,
      clearPins: async () => null,
      clearFilters: async () => null,
      addHighlight: async () => null,
      setHighlightEnabled: async () => null,
      setHighlightColor: async () => null,
      removeHighlight: async () => null,
      clearHighlights: async () => null,
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
    setCategoriesBulk: async () => null,
      searchVisible: async () => ({ total: 0, positions: [] }),
      visibilitySnapshot: async () => ({
        visible_count: 12,
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level, enabled: true, count: 2,
        })),
        filters: [],
        pins: [],
        highlights: [],
        categories_enabled: ["app/db"],
      }),
      settingsGet: async () => {
        if (options.failSettingsGet) throw new Error("settings read failed");
        return {
          history_size: 20,
          last_open_dir: stored.lastOpenDir,
          default_categories_enabled: true,
        };
      },
      setLastOpenDir: async (dir: string) => {
        setCalls.push(dir);
        if (options.failSet) throw new Error("settings write failed");
        stored.lastOpenDir = dir;
        return null;
      },
      setLastOpenDirCalls: () => setCalls,
      settingsStore: () => stored.lastOpenDir,
    };
  }

  it("a fresh console seeds the Open-dialog start dir from the settings at construction", async () => {
    const { console_ } = await freshConsole(settingsStub());
    // The seeded dir must land on BOTH the snapshot (the text RPC) and the
    // reducer slice (which the App's Open flow passes to pickFile).
    await vi.waitFor(() => {
      expect(console_.getSnapshot().settings.lastOpenDir).toBe("/tmp/logs");
    });
    await vi.waitFor(() => {
      expect(console_.getState().lastDir).toBe("/tmp/logs");
    });
  });

  it("a failed settings read leaves the default empty dir (best-effort)", async () => {
    const { console_ } = await freshConsole(settingsStub({ failSettingsGet: true }));
    await console_.load("log.txt"); // flush the construction's read attempt; a bare name writes nothing
    expect(console_.getSnapshot().settings.lastOpenDir).toBe("");
    expect(console_.getState().lastDir).toBe("");
  });

  it("a successful open persists the file's directory and updates the slice", async () => {
    const stub = settingsStub();
    const { console_ } = await freshConsole(stub);
    // Load a file in a DIFFERENT dir than the seeded one.
    const snap = await console_.load("/other/dir/run.log");
    expect(stub.setLastOpenDirCalls()).toEqual(["/other/dir"]); // the file's dirname
    expect(stub.settingsStore()).toBe("/other/dir"); // the (stubbed) store took it
    expect(snap.settings.lastOpenDir).toBe("/other/dir");
    expect(console_.getState().lastDir).toBe("/other/dir");
    expect(snap.error).toBeNull(); // the persistence never surfaces as an error
  });

  it("a failed set_last_open_dir write is best-effort: the slice still updates, no error", async () => {
    const stub = settingsStub({ failSet: true });
    const { console_ } = await freshConsole(stub);
    const snap = await console_.load("/other/dir/run.log");
    expect(stub.setLastOpenDirCalls()).toEqual(["/other/dir"]);
    expect(snap.settings.lastOpenDir).toBe("/other/dir");
    expect(snap.error).toBeNull();
  });

  it("a failed open never touches the setting", async () => {
    const stub = settingsStub({ failLoad: true });
    const { console_ } = await freshConsole(stub);
    await console_.load("/other/dir/run.log");
    expect(stub.setLastOpenDirCalls()).toEqual([]);
    // The seeded value survives the failed open.
    expect(console_.getState().lastDir).toBe("/tmp/logs");
  });

  it("a path without a directory writes nothing and keeps the previous dir", async () => {
    const stub = settingsStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("run.log");
    expect(stub.setLastOpenDirCalls()).toEqual([]);
    expect(console_.getState().lastDir).toBe("/tmp/logs");
  });
});

describe("update lifecycle through the store (plan 2026-11-25, Task 3)", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  /** RAW UpdaterCommands stub mirroring the plugin call shapes; the console
   *  seam resolves through window.__ipcStub (all three methods = stub wins). */
  function updaterStub(options?: {
    update?: { version: string; currentVersion: string } | null;
    failCheck?: string;
    failInstall?: string;
  }) {
    return {
      version: "0.1.0",
      relaunches: 0,
      check: async () => {
        if (options?.failCheck) throw new Error(options.failCheck);
        return options?.update === undefined
          ? { version: "0.2.0", currentVersion: "0.1.0" }
          : options.update;
      },
      downloadAndInstall: async () => {
        if (options?.failInstall) throw new Error(options.failInstall);
      },
      relaunch: async () => void (window as unknown as Record<string, unknown>).__updater_relaunches,
    };
  }
  type UpdaterStub = ReturnType<typeof updaterStub>;

  async function fresh(
    updater: UpdaterStub,
  ): Promise<{ console_: Console; updater: UpdaterStub }> {
    const target = window as unknown as Record<string, unknown>;
    target.__ipcStub = updater;
    vi.resetModules();
    const mod = await import("./uiConsole");
    return { console_: mod.console_ as Console, updater };
  }

  it("manual check flows: checking → available → installed + relaunch", async () => {
    const { console_ } = await fresh(updaterStub());
    const snap = await console_.checkForUpdates("manual");
    expect(snap.update.phase).toBe("available");
    expect(snap.update.availableVersion).toBe("0.2.0");
    await console_.installUpdate();
    const after = console_.getUpdate();
    expect(after.phase).toBe("installed");
  });

  it("auto check failure stays completely silent (Review Focus 1/2)", async () => {
    const { console_ } = await fresh(updaterStub({ failCheck: "404" }));
    await console_.checkForUpdates("auto");
    expect(console_.getUpdate()).toEqual({
      phase: "idle",
      source: "auto",
      availableVersion: null,
      error: null,
    });
  });

  it("auto success stays silent too", async () => {
    const { console_ } = await fresh(updaterStub({ update: null }));
    await console_.checkForUpdates("auto");
    expect(console_.getUpdate().phase).toBe("idle");
  });

  it("manual check failure lands on the failed banner (Review Focus 3)", async () => {
    const { console_ } = await fresh(updaterStub({ failCheck: "404" }));
    await console_.checkForUpdates("manual");
    const s = console_.getUpdate();
    expect(s.phase).toBe("failed");
    expect(s.error).toContain("404");
  });

  it("install failure shows an error and dismiss resets", async () => {
    const { console_ } = await fresh(updaterStub({ failInstall: "signature verification failed" }));
    await console_.checkForUpdates("manual");
    await console_.installUpdate();
    const s = console_.getUpdate();
    expect(s.phase).toBe("failed");
    expect(s.error).toContain("signature");
    expect(console_.dismissUpdate().update).toMatchObject({ phase: "idle" });
  });

  it("installUpdate is a no-op outside the available phase", async () => {
    // failCheck silences the constructor's auto probe (→ idle); after the
    // settle wait, no check is in flight and a bare install is a no-op.
    const { console_ } = await fresh(updaterStub({ failCheck: "404" }));
    await new Promise((r) => setTimeout(r, 0));
    const snap = await console_.installUpdate();
    expect(snap.update.phase).toBe("idle");
  });

  it("cmdline check-updates triggers a manual check (§13.1 system command)", async () => {
    const { console_ } = await fresh(updaterStub());
    const snap = await console_.executeCommand("check-updates");
    expect(snap.update.phase).toBe("available");
  });

  it("cmdline check-updates with an argument errors and never touches the wire", async () => {
    const { console_ } = await fresh(updaterStub({ failCheck: "404" }));
    await new Promise((r) => setTimeout(r, 0)); // let the auto probe settle
    const snap = await console_.executeCommand("check-updates now");
    expect(snap.error).toBe("Error: check-updates takes no arguments");
    expect(console_.getUpdate().phase).toBe("idle");
  });

  it("a stale auto result arriving after a dismiss is ignored", async () => {
    // the plugin promise races the user: dismiss (idle) → auto result must
    // not resurrect the banner (update-available applies only from checking)
    const { console_ } = await fresh(updaterStub());
    void console_.checkForUpdates("auto");
    console_.dismissUpdate();
    await new Promise((r) => setTimeout(r, 0));
    expect(console_.getUpdate().phase).toBe("idle");
  });
});

describe("update cmdline validation", () => {
  it.each([
    ["check-updates", true],
    ["check-updates ", true],
    [":check-updates", true],
    ["check-updates now", false],
  ])("%s valid=%p", (text, ok) => {
    expect(resolveCommand(text, 10).ok).toBe(ok);
  });
});

describe("concurrent update checks (final review I-1): a stale probe never clobbers a live one", () => {
  beforeEach(() => {
    delete (window as unknown as Record<string, unknown>).__ipcStub;
  });

  /** Stub whose check() defers EVERY call; test code resolves calls FIFO:
   *  settleAuto/settleManual drive the constructor probe and the manual call. */
  function scriptedStub() {
    const deferreds: Array<(v: unknown) => void> = [];
    return {
      calls: () => deferreds.length,
      settleAuto: (payload: unknown) => deferreds[0]?.(payload),
      settleManual: (payload: unknown) => deferreds[1]?.(payload),
      check: async () => new Promise((resolve) => deferreds.push(resolve)),
      downloadAndInstall: async () => undefined,
      relaunch: async () => undefined,
    };
  }

  async function fresh(stub: ReturnType<typeof scriptedStub>) {
    const target = window as unknown as Record<string, unknown>;
    target.__ipcStub = stub;
    vi.resetModules();
    const mod = await import("./uiConsole");
    return { console_: mod.console_ as Console, stub };
  }

  it("scenario (a): stale auto null must not turn a manual check into uptodate", async () => {
    const { console_, stub } = await fresh(scriptedStub());
    const manual = console_.checkForUpdates("manual");
    // re-arm happened (manual) while the auto probe is still deferred
    expect(console_.getUpdate().phase).toBe("checking");
    // the STALE auto probe resolves null (e.g. server hiccup)...
    stub.settleAuto(null);
    await new Promise((r) => setTimeout(r, 0));
    // its answer must be dropped, not shown as "You're on the latest version."
    expect(console_.getUpdate().phase).not.toBe("uptodate");
    // the REAL manual result is offered later and must still apply
    stub.settleManual({ version: "0.2.0", currentVersion: "0.1.0" });
    await manual;
    expect(console_.getUpdate()).toMatchObject({
      phase: "available",
      availableVersion: "0.2.0",
    });
  });

  it("scenario (b): a stale auto failure must not erase an in-flight manual check", async () => {
    const { console_, stub } = await fresh(scriptedStub());
    const manual = console_.checkForUpdates("manual");
    expect(console_.getUpdate().phase).toBe("checking");
    // the stale auto probe FAILS
    stub.settleAuto(new Error("boom"));
    await new Promise((r) => setTimeout(r, 0));
    // the manual check must still be live, not reset to a silent idle
    expect(console_.getUpdate().phase).toBe("checking");
    stub.settleManual({ version: "0.2.0", currentVersion: "0.1.0" });
    await manual;
    expect(console_.getUpdate().phase).toBe("available");
  });
});

describe("column-widths persistence (design 2026-11-25-column-resize)", () => {
  /** RAW stub in the §15 pattern: settings_get carries `column_widths`,
   *  set_column_widths records its calls. `withSetter` off = the stub does
   *  NOT know the new command (commit must degrade to a no-op fallback). */
  interface ColumnWidthsStub extends RawIpc {
    /** RAW §15 shapes (the stub carries them; RawIpc does not declare
     *  settings commands). setColumnWidths is optional: withSetter off
     *  exercises the seam's no-op fallback. */
    settingsGet(): Promise<{ history_size: number; last_open_dir: string; default_categories_enabled: boolean }>;
    setLastOpenDir(dir: string): Promise<null>;
    setColumnWidths?(widths: number[] | null): Promise<null>;
    columnWidthsCalls(): (number[] | null)[];
  }

  function columnWidthsStub(
    options: { withSetter?: boolean; column_widths?: number[] | null } = {},
  ): ColumnWidthsStub {
    const calls: (number[] | null)[] = [];
    return {
      pickFile: async () => null,
      loadFile: async () => ({
        format: "plain", line_count: 12, size_bytes: 883, categories: [], levels: [], load_ms: 1,
      }),
      getRows: async () => [],
      addFilter: async () => null,
      setFilterEnabled: async () => null,
      removeFilter: async () => null,
      addPin: async () => null,
      setPinEnabled: async () => null,
      removePin: async () => null,
      clearPins: async () => null,
      clearFilters: async () => null,
      addHighlight: async () => null,
      setHighlightEnabled: async () => null,
      setHighlightColor: async () => null,
      removeHighlight: async () => null,
      clearHighlights: async () => null,
      setLevelEnabled: async () => null,
      setCategoryEnabled: async () => null,
      setCategoriesBulk: async () => null,
      searchVisible: async () => ({ total: 0, positions: [] }),
      visibilitySnapshot: async () => ({
        visible_count: 12,
        levels: ["critical", "error", "warning", "msg", "debug", "trace"].map((level) => ({
          level, enabled: true, count: 2,
        })),
        filters: [],
        pins: [],
        highlights: [],
        categories_enabled: ["app/db"],
      }),
      settingsGet: async () => ({
        history_size: 20,
        last_open_dir: "",
        default_categories_enabled: true,
        column_widths: options.column_widths ?? null,
      }) as never,
      setLastOpenDir: async () => null,
      ...(options.withSetter === false
        ? {}
        : {
            setColumnWidths: async (widths: number[] | null) => {
              calls.push(widths);
              return null as never;
            },
          }),
      columnWidthsCalls: () => calls,
    };
  }

  it("a fresh console seeds the column widths from the settings at construction", async () => {
    const { console_ } = await freshConsole(
      columnWidthsStub({ column_widths: [60, 120, 160, 620] }),
    );
    await vi.waitFor(() => {
      expect(console_.getSnapshot().columnWidths).toEqual({
        line: 60, time: 120, category: 160, message: 620,
      });
    });
  });

  it("null persisted widths seed the §4 defaults", async () => {
    const { console_ } = await freshConsole(columnWidthsStub({ column_widths: null }));
    await console_.load("log.txt"); // flush the construction's read attempt
    expect(console_.getSnapshot().columnWidths).toEqual({
      line: 50, time: 110, category: 150, message: 600,
    });
  });

  it("setColumnWidth updates the snapshot slice and clamps to the floor", () => {
    return vi.waitFor(async () => {
      const { console_ } = await freshConsole(columnWidthsStub());
      const set = console_.setColumnWidth("category", 250);
      expect(set.columnWidths.category).toBe(250);
      expect(console_.getSnapshot().columnWidths).toEqual({
        line: 50, time: 110, category: 250, message: 600,
      });
    });
  });

  it("setColumnWidth with an unknown key changes nothing (string boundary)", () => {
    return vi.waitFor(async () => {
      const { console_ } = await freshConsole(columnWidthsStub());
      const before = console_.getSnapshot().columnWidths;
      const after = console_.setColumnWidth("nope", 1);
      expect(after.columnWidths).toEqual(before);
    });
  });

  it("resetColumnWidth restores the §4 default for the key", () => {
    return vi.waitFor(async () => {
      const { console_ } = await freshConsole(columnWidthsStub());
      console_.setColumnWidth("time", 400);
      const after = console_.resetColumnWidth("time");
      expect(after.columnWidths.time).toBe(110);
    });
  });

  it("commitColumnWidths persists the serialized 4-entry array", async () => {
    const stub = columnWidthsStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("log.txt"); // flush the construction's read attempt
    console_.setColumnWidth("category", 250);
    console_.commitColumnWidths();
    await vi.waitFor(() => {
      expect(stub.columnWidthsCalls()).toEqual([[50, 110, 250, 600]]);
    });
  });

  it("commitColumnWidths with a stub lacking the setter resolves without throwing", async () => {
    const { console_ } = await freshConsole(columnWidthsStub({ withSetter: false }));
    await console_.load("log.txt");
    console_.setColumnWidth("category", 250);
    expect(() => console_.commitColumnWidths()).not.toThrow();
    await new Promise((r) => setTimeout(r, 5));
  });

  // Review findings 1: the reset must persist ("save at the end of a drag
  // / on reset", design 2026-11-25-column-resize).
  it("a reset persists the reset widths (review finding 1)", async () => {
    const stub = columnWidthsStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("log.txt"); // flush the construction's read attempt
    console_.setColumnWidth("category", 250);
    console_.commitColumnWidths();
    await vi.waitFor(() => expect(stub.columnWidthsCalls()).toEqual([[50, 110, 250, 600]]));
    console_.resetColumnWidth("category");
    await vi.waitFor(() =>
      expect(stub.columnWidthsCalls()).toEqual([[50, 110, 250, 600], [50, 110, 150, 600]]),
    );
  });

  it("an unknown-key reset still commits nothing (review finding 1, boundary)", async () => {
    const stub = columnWidthsStub();
    const { console_ } = await freshConsole(stub);
    await console_.load("log.txt");
    console_.resetColumnWidth("nope");
    await new Promise((r) => setTimeout(r, 20));
    expect(stub.columnWidthsCalls()).toEqual([]);
  });
});
