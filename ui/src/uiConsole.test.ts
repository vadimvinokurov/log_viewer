//! uiConsole tests (dsq.3): visibility mutations through the console RPC
//! refetch the snapshot and dispatch it into the reducer; failures surface
//! through the existing error state. The module singleton is re-imported
//! fresh per test so the narrative runs stay isolated.

import { beforeEach, describe, expect, it, vi } from "vitest";
import { installHeadlessConsole } from "./headless";
import type { RawIpc } from "./ipcClient";
import type { RowDto, VisibilitySnapshotDto } from "./bindings";

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
    categories_enabled: ["app/db"],
  });
  return {
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
    setLevelEnabled: async (level: string, on: boolean) => {
      if (!(level in enabledLevels)) throw new Error(`no such level: ${level}`);
      if (options.failMutation === "setLevel") throw new Error("ipc down");
      enabledLevels[level] = on;
      return null;
    },
    setCategoryEnabled: async () => null,
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
  });
  return {
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
    setLevelEnabled: async (level: string, on: boolean) => {
      if (level !== "trace") throw new Error(`no such level: ${level}`);
      if (options.failMutation === "setLevel") throw new Error("ipc down");
      traceOn.value = on;
      return null;
    },
    setCategoryEnabled: async () => null,
    visibilitySnapshot: async (): Promise<VisibilitySnapshotDto> => ({
      visible_count: Array.from({ length: LINE_COUNT }, (_, i) => i + 1)
        .filter(visible).length,
      levels: ["critical", "error", "warning", "msg", "debug", "trace"].map(
        (level) => ({ level, enabled: level !== "trace" || traceOn.value, count: 1 }),
      ),
      filters: [],
      pins: [],
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
});
