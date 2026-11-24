// Pure update state machine (plan 2026-11-25-github-release-updater, Task 2).
// The updater is the app's ONLY network call (deliberate exception to spec
// §1 «no networking»); every failure path must leave the app fully usable —
// the AUTO silence rule lives in the console (Task 3), so this module records
// failures source-honestly and deterministically.

import { describe, expect, it } from "vitest";
import {
  bannerVisible,
  compareVersions,
  initialUpdateState,
  reduceUpdate,
  type UpdateState,
} from "./updates";

describe("compareVersions", () => {
  it("compares numerically, not lexicographically", () => {
    expect(compareVersions("1.20.0", "1.3.0")).toBe(1);
    expect(compareVersions("0.2.0", "0.10.0")).toBe(-1);
  });
  it("tolerates missing segments", () => {
    expect(compareVersions("1.2.0", "1.2")).toBe(0);
    expect(compareVersions("0.2", "0.2.0")).toBe(0);
    expect(compareVersions("0.2", "0.2.1")).toBe(-1);
  });
  it("a release outranks its own prerelease", () => {
    expect(compareVersions("1.0.0", "1.0.0-rc.1")).toBe(1);
    expect(compareVersions("1.0.0-rc.1", "1.0.0")).toBe(-1);
    expect(compareVersions("1.0.0-rc.1", "1.0.0-rc.1")).toBe(0);
  });
  it("equal versions compare as 0", () => {
    expect(compareVersions("0.1.0", "0.1.0")).toBe(0);
  });
});

describe("reduceUpdate", () => {
  const startState = (source: "auto" | "manual"): UpdateState =>
    reduceUpdate(initialUpdateState(), { kind: "update-check-start", source });

  it("manual check: checking → available", () => {
    let s = startState("manual");
    expect(s.phase).toBe("checking");
    expect(s.source).toBe("manual");
    s = reduceUpdate(s, { kind: "update-available", version: "0.2.0" });
    expect(s).toEqual({
      phase: "available",
      source: "manual",
      availableVersion: "0.2.0",
      error: null,
    });
  });

  it("manual check with nothing found lands on uptodate", () => {
    const s = reduceUpdate(startState("manual"), { kind: "update-none" });
    expect(s.phase).toBe("uptodate");
  });

  it("auto check with nothing found stays silent (idle)", () => {
    const s = reduceUpdate(startState("auto"), { kind: "update-none" });
    expect(s.phase).toBe("idle");
  });

  it("records failures source-honestly (auto silence enforced in the console)", () => {
    let s = startState("auto");
    s = reduceUpdate(s, { kind: "update-failed", error: "404" });
    expect(s).toMatchObject({ phase: "failed", error: "404", source: "auto" });
  });

  it("recheck while busy is a no-op", () => {
    const available = reduceUpdate(startState("manual"), {
      kind: "update-available",
      version: "0.2.0",
    });
    expect(
      reduceUpdate(available, { kind: "update-check-start", source: "auto" }),
    ).toEqual(available);
    const downloading = reduceUpdate(available, { kind: "update-download-start" });
    expect(
      reduceUpdate(downloading, { kind: "update-check-start", source: "manual" }),
    ).toEqual(downloading);
    const checking = startState("manual");
    expect(
      reduceUpdate(checking, { kind: "update-check-start", source: "auto" }),
    ).toEqual(checking);
  });

  it("download-start applies only from available", () => {
    const available = reduceUpdate(startState("manual"), {
      kind: "update-available",
      version: "0.2.0",
    });
    const downloading = reduceUpdate(available, { kind: "update-download-start" });
    expect(downloading.phase).toBe("downloading");
    // a stray download-start while checking is ignored
    expect(reduceUpdate(startState("manual"), { kind: "update-download-start" })).toEqual(
      startState("manual"),
    );
  });

  it("installed applies from a download in progress", () => {
    const available = reduceUpdate(startState("manual"), {
      kind: "update-available",
      version: "0.2.0",
    });
    const downloading = reduceUpdate(available, { kind: "update-download-start" });
    const installed = reduceUpdate(downloading, { kind: "update-installed" });
    expect(installed.phase).toBe("installed");
  });

  it("install failure carries the error", () => {
    const downloading = reduceUpdate(
      reduceUpdate(startState("manual"), { kind: "update-available", version: "0.2.0" }),
      { kind: "update-download-start" },
    );
    const failed = reduceUpdate(downloading, {
      kind: "update-failed",
      error: "signature verification failed",
    });
    expect(failed).toMatchObject({
      phase: "failed",
      error: "signature verification failed",
    });
  });

  it("dismiss resets everything", () => {
    const s = reduceUpdate(
      {
        phase: "failed",
        source: "manual",
        availableVersion: "0.2.0",
        error: "boom",
      },
      { kind: "update-dismiss" },
    );
    expect(s).toEqual(initialUpdateState());
  });
});

describe("bannerVisible", () => {
  it.each([
    ["available", true],
    ["downloading", true],
    ["installed", true],
    ["uptodate", true],
    ["failed", true],
    ["idle", false],
    ["checking", false],
  ] as const)("phase %s → %p", (phase, expected) => {
    expect(
      bannerVisible({ phase, source: "manual", availableVersion: null, error: null }),
    ).toBe(expected);
  });
});
