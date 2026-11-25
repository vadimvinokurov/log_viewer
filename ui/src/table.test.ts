import { describe, expect, it } from "vitest";
import type { RowDto as RawRowDto } from "./bindings";
import { ChunkPlanner, ROW_CHUNK } from "./table";
import type { StampedRow } from "./table";

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

describe("stamped cache helpers (design 2026-11-25-flicker)", () => {
  const aRawRow = (line: number): RawRowDto => ({
    line_no: line,
    time_display: "10:00:00.000",
    category: "app.sub",
    level: "info",
    message: `message body ${line}`,
    raw: `raw line ${line}`,
    spans: [],
  });

  it("stamps entries; painted reads ignore the stamp", () => {
    // map.get is the painted/entry read: it returns the stamped entry itself,
    // whatever epoch it carries; currency is decided by the read gate.
    const map = ChunkPlanner.fromChunkStamped(
      [aRawRow(1), aRawRow(2), aRawRow(3)],
      0,
      5,
    );
    expect(map.get(2)?.row.line_no).toBe(3);
    expect(map.get(2)?.epoch).toBe(5);
  });

  it("current-truth read passes only current-epoch entries", () => {
    const map = ChunkPlanner.fromChunkStamped(
      [aRawRow(1), aRawRow(2), aRawRow(3)],
      0,
      5,
    );
    // Same epoch: the entry is current truth and goes through...
    expect(ChunkPlanner.currentStamped(map, 2, 5)).toEqual({
      row: ChunkPlanner.toRow(aRawRow(3)),
      epoch: 5,
    });
    // ...and the epoch has moved on (category toggle): the entry is stale.
    expect(ChunkPlanner.currentStamped(map, 2, 6)).toBeUndefined();
  });

  it("chunk apply replaces a range and restamps", () => {
    // Old generation: the same indexes hold rows from an earlier epoch (4).
    const seeded = new Map<number, StampedRow>();
    for (let i = 0; i < 10; i++) {
      seeded.set(i, { row: ChunkPlanner.toRow(aRawRow(-1)), epoch: 4 });
    }
    // A new chunk of 10 rows lands at start 0 under epoch 7. Applying the
    // fromChunkStamped output over the seeded map (the same merge a call
    // site performs) replaces every old row and restamps indexes 0..9.
    const chunk = Array.from({ length: 10 }, (_, i) => aRawRow(i + 1));
    const applied = new Map(seeded);
    for (const [i, entry] of ChunkPlanner.fromChunkStamped(chunk, 0, 7)) {
      applied.set(i, entry);
    }
    for (let i = 0; i < 10; i++) {
      expect(applied.get(i)?.row.line_no).toBe(i + 1);
      expect(applied.get(i)?.epoch).toBe(7);
    }
  });
});
