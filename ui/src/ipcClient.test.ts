//! ipcClient tests (dsq.3): a stub mirroring the RAW IPC shapes
//! (docs/notes/visibility-bridge.md) drives the adapter; the UI must see
//! normalized camelCase shapes and nothing else (single normalization point).

import { afterEach, describe, expect, it } from "vitest";
import { ipc, type RawIpc } from "./ipcClient";
import type { SearchMatches } from "./state";

const STUB_KEY = "__ipcStub";
type StubTarget = { [STUB_KEY]?: RawIpc };

const RAW_SNAPSHOT = {
  visible_count: 4213,
  levels: [
    { level: "critical", enabled: true, count: 1 },
    { level: "error", enabled: true, count: 240 },
    { level: "warning", enabled: false, count: 500 },
    { level: "msg", enabled: true, count: 3200 },
    { level: "debug", enabled: true, count: 270 },
    { level: "trace", enabled: true, count: 2 },
  ],
  filters: [
    { id: 0, mode: "plain", pattern: '"timeout"', enabled: true },
    { id: 1, mode: "regex", pattern: "^retry", enabled: false },
  ],
  pins: [{ id: 0, mode: "lineno", pattern: "12034", enabled: true }],
  categories_enabled: ["app/main/db", "app"],
};

function installStub(stub: RawIpc): void {
  (window as unknown as StubTarget)[STUB_KEY] = stub;
}

function removeStub(): void {
  delete (window as unknown as StubTarget)[STUB_KEY];
}

afterEach(removeStub);

describe("visibilitySnapshot normalization", () => {
  it("renames the RAW fields to the camelCase UI shape", async () => {
    installStub({ ...emptyRaw(), visibilitySnapshot: async () => RAW_SNAPSHOT });
    const snap = await ipc().visibilitySnapshot();
    expect(snap.visibleCount).toBe(4213);
    expect(snap.categoriesEnabled).toEqual(["app/main/db", "app"]);
    expect(snap.levels).toEqual(RAW_SNAPSHOT.levels);
  });

  it("maps filters/pins to FilterItem with the typed FilterMode", async () => {
    installStub({ ...emptyRaw(), visibilitySnapshot: async () => RAW_SNAPSHOT });
    const snap = await ipc().visibilitySnapshot();
    expect(snap.filters).toEqual([
      { id: 0, mode: "plain", pattern: '"timeout"', enabled: true },
      { id: 1, mode: "regex", pattern: "^retry", enabled: false },
    ]);
    expect(snap.pins).toEqual([{ id: 0, mode: "lineno", pattern: "12034", enabled: true }]);
  });

  it("spec interpretation: an unknown mode string falls back to plain (the backend rejects it at add_filter time)", async () => {
    installStub({
      ...emptyRaw(),
      visibilitySnapshot: async () => ({
        ...RAW_SNAPSHOT,
        filters: [{ id: 0, mode: "future-mode", pattern: "x", enabled: true }],
      }),
    });
    const snap = await ipc().visibilitySnapshot();
    expect(snap.filters[0]?.mode).toBe("plain");
    expect(snap.filters[0]?.pattern).toBe("x");
  });
});

describe("searchVisible (bead 2wu.1)", () => {
  it("passes the mode/pattern through and copies the DTO fields", async () => {
    const calls: { fn: string; args: unknown[] }[] = [];
    installStub({
      ...emptyRaw(),
      searchVisible: async (mode, pattern) => {
        calls.push({ fn: "searchVisible", args: [mode, pattern] });
        return { total: 2, positions: [3, 7] };
      },
    });
    const result = await ipc().searchVisible("regex", "^retry");
    expect(result).toEqual({ total: 2, positions: [3, 7] });
    expect(calls).toEqual([{ fn: "searchVisible", args: ["regex", "^retry"] }]);
  });

  it("an empty pattern resolves to the «0 of 0» shape from the backend", async () => {
    installStub({ ...emptyRaw(), searchVisible: async () => ({ total: 0, positions: [] }) });
    const result = await ipc().searchVisible("plain", "");
    expect(result).toEqual({ total: 0, positions: [] });
  });

  it("the normalized result is owned by the UI type, not the bindings alias", async () => {
    installStub({ ...emptyRaw(), searchVisible: async () => ({ total: 1, positions: [41] }) });
    const result: SearchMatches = await ipc().searchVisible("simple", "db");
    expect(result.positions).toEqual([41]);
  });
});

describe("mutation pass-through", () => {
  it("forwards arguments unchanged to the RAW commands and resolves null", async () => {
    const calls: { fn: string; args: unknown[] }[] = [];
    const rec = (fn: string) => async (...args: unknown[]) => {
      calls.push({ fn, args });
      return null;
    };
    installStub({
      ...emptyRaw(),
      addFilter: (mode, pattern) => rec("addFilter")(mode, pattern),
      setFilterEnabled: (id, on) => rec("setFilterEnabled")(id, on),
      removeFilter: (id) => rec("removeFilter")(id),
      addPin: (mode, pattern) => rec("addPin")(mode, pattern),
      setPinEnabled: (id, on) => rec("setPinEnabled")(id, on),
      removePin: (id) => rec("removePin")(id),
      setLevelEnabled: (level, on) => rec("setLevelEnabled")(level, on),
      setCategoryEnabled: (path, on) => rec("setCategoryEnabled")(path, on),
    });
    const client = ipc();
    await expect(client.addFilter("plain", "timeout")).resolves.toBeNull();
    await expect(client.setFilterEnabled(1, false)).resolves.toBeNull();
    await expect(client.removeFilter(0)).resolves.toBeNull();
    await expect(client.addPin("lineno", "5")).resolves.toBeNull();
    await expect(client.setPinEnabled(0, false)).resolves.toBeNull();
    await expect(client.removePin(0)).resolves.toBeNull();
    await expect(client.setLevelEnabled("trace", false)).resolves.toBeNull();
    await expect(client.setCategoryEnabled("app/db", false)).resolves.toBeNull();
    expect(calls).toEqual([
      { fn: "addFilter", args: ["plain", "timeout"] },
      { fn: "setFilterEnabled", args: [1, false] },
      { fn: "removeFilter", args: [0] },
      { fn: "addPin", args: ["lineno", "5"] },
      { fn: "setPinEnabled", args: [0, false] },
      { fn: "removePin", args: [0] },
      { fn: "setLevelEnabled", args: ["trace", false] },
      { fn: "setCategoryEnabled", args: ["app/db", false] },
    ]);
  });
});

function emptyRaw(): RawIpc {
  return {
    pickFile: async () => null,
    loadFile: async () => {
      throw new Error("not used in this test");
    },
    getRows: async () => [],
    addFilter: async () => null,
    setFilterEnabled: async () => null,
    removeFilter: async () => null,
    addPin: async () => null,
    setPinEnabled: async () => null,
    removePin: async () => null,
    setLevelEnabled: async () => null,
    setCategoryEnabled: async () => null,
    searchVisible: async () => ({ total: 0, positions: [] }),
    visibilitySnapshot: async () => ({
      visible_count: 0,
      levels: [],
      filters: [],
      pins: [],
      categories_enabled: [],
    }),
  };
}
