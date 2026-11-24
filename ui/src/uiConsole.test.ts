//! uiConsole tests (dsq.3): visibility mutations through the console RPC
//! refetch the snapshot and dispatch it into the reducer; failures surface
//! through the existing error state. The module singleton is re-imported
//! fresh per test so the narrative runs stay isolated.

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RawIpc } from "./ipcClient";

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

async function freshConsole(stub: RawIpc): Promise<{ console_: Console }> {
  const target = window as unknown as Record<string, unknown>;
  target.__ipcStub = stub;
  vi.resetModules();
  const mod = await import("./uiConsole");
  return { console_: mod.console_ as Console };
}

describe("console visibility actions (dsq.3, §7)", () => {
  beforeEach(() => {
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
