import { describe, expect, it } from "vitest";
import {
  appReducer,
  type AppState,
  initialAppState,
} from "./state";

function loadedState(): AppState {
  return appReducer(initialAppState(), {
    kind: "load-success",
    load: { format: "plain", lineCount: 2, categories: [], levels: [], loadMs: 5 },
    fileName: "log.txt",
  });
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
