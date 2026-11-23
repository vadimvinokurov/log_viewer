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
