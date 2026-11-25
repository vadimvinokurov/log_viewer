import { describe, expect, it } from "vitest";
import { ChunkPlanner, ROW_CHUNK } from "./table";

describe("row chunk planning (qt7.1, §4 virtualized load)", () => {
  it("chunk size is fixed and positive", () => {
    expect(ROW_CHUNK).toBeGreaterThan(0);
  });

  it("prefetches one chunk ahead and behind, aligned to boundaries", () => {
    const planner = new ChunkPlanner();
    // 980..1015 spans chunk 0 and the head of chunk 1; preload adds chunk 2.
    expect(planner.plan(980, 1015, 100_000)).toEqual([
      { start: 0, end: 1000 },
      { start: 1000, end: 2000 },
      { start: 2000, end: 3000 },
    ]);
  });

  it("prefetches the previous chunk when scrolling below the top", () => {
    const planner = new ChunkPlanner();
    // Visible chunk 3 -> preload chunks 2..4. The chunk CONTAINING the
    // visible range loads before its preloads: the rows on screen appear
    // after one round trip, not two (owner flicker report 2026-11-25).
    const ranges = planner.plan(3000, 3030, 100_000);
    expect(ranges).toEqual([
      { start: 3000, end: 4000 },
      { start: 2000, end: 3000 },
      { start: 4000, end: 5000 },
    ]);
  });

  it("does not request the same chunk twice before it lands", () => {
    const planner = new ChunkPlanner();
    const first = planner.plan(0, 30, 100_000);
    expect(first).toEqual([
      { start: 0, end: 1000 },
      { start: 1000, end: 2000 },
    ]);
    expect(planner.plan(0, 30, 100_000)).toEqual([]);
  });

  it("starts re-requesting a chunk only after it failed", () => {
    const planner = new ChunkPlanner();
    planner.plan(0, 30, 100_000);
    planner.markFailed(0);
    // Chunk 0 is retried; chunk 1 is still in flight.
    expect(planner.plan(0, 30, 100_000)).toEqual([{ start: 0, end: 1000 }]);
  });

  it("marks chunk loaded and stops planning it", () => {
    const planner = new ChunkPlanner();
    planner.plan(0, 30, 100_000);
    planner.markLoaded(0);
    planner.markLoaded(1);
    expect(planner.plan(0, 30, 100_000)).toEqual([]);
  });

  it("stops prefetching at the end of the file", () => {
    const planner = new ChunkPlanner();
    // File of 1200 lines: the chunk after 1000 ends at 1200, nothing beyond.
    expect(planner.plan(0, 30, 1200)).toEqual([
      { start: 0, end: 1000 },
      { start: 1000, end: 1200 },
    ]);
  });

  it("resets planning on a new file load", () => {
    const planner = new ChunkPlanner();
    planner.plan(0, 30, 100_000);
    planner.reset();
    expect(planner.plan(0, 30, 100_000)).toEqual([
      { start: 0, end: 1000 },
      { start: 1000, end: 2000 },
    ]);
  });
});
