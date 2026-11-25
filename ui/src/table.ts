//! Chunk planning for the virtualized table load (FUNCTIONAL_SPEC §4, §16).
//!
//! Pure logic, tested without React: the table component asks a ChunkPlanner
//! which row ranges to fetch, feeds results through markLoaded/markFailed.
//! Rows are fetched from the core through the IPC command get_rows; loading
//! stays non-blocking (§2): the UI renders what it has and waits for chunks.

import type { RowDto as RawRowDto } from "./bindings";

/** Rows per IPC chunk: 1000 parse-on-demand rows are well under 50 ms (ktd.3). */
export const ROW_CHUNK = 1000;

export interface RowDto {
  line_no: number;
  time_display: string;
  category: string;
  level: string;
  message: string;
  raw: string;
}

/** A cached row with its visibility-epoch stamp (design 2026-11-25-flicker):
 *  rows written during epoch N carry N; a read of current truth accepts only
 *  entries whose stamp equals the reader's current epoch, so a category
 *  toggle never repaints from stale-epoch rows. */
export interface StampedRow {
  row: RowDto;
  epoch: number;
}

/** Which chunk indexes to fetch for a visible window (± 1 chunk preload). */
export class ChunkPlanner {
  private loaded = new Set<number>();
  private inFlight = new Set<number>();

  /** Chunk ranges to fetch now; an empty result means nothing is pending.
   *  Ranges are ordered by distance from the chunks covering the visible
   *  range: the on-screen chunks load before the preloads, so the rows the
   *  user is looking at appear after one round trip, not after two
   *  neighboring chunks (owner flicker report 2026-11-25: the epoch's blank
   *  flash lasted two round trips). */
  plan(visibleStart: number, visibleEnd: number, rowCount: number): { start: number; end: number }[] {
    const visibleFirst = Math.max(0, Math.floor(visibleStart / ROW_CHUNK));
    const visibleLast = Math.min(
      Math.floor((rowCount - 1) / ROW_CHUNK),
      Math.floor(visibleEnd / ROW_CHUNK),
    );
    const first = Math.max(0, visibleFirst - 1);
    const last = visibleLast + 1;
    const ranges: { start: number; end: number }[] = [];
    for (let chunk = first; chunk <= last; chunk++) {
      const start = chunk * ROW_CHUNK;
      const end = Math.min(start + ROW_CHUNK, rowCount);
      if (start >= rowCount || end <= start) {
        break; // past the end of the file
      }
      const idx = start / ROW_CHUNK;
      if (this.loaded.has(idx) || this.inFlight.has(idx)) {
        continue;
      }
      this.inFlight.add(idx);
      ranges.push({ start, end });
    }
    // Distance from the visible chunk range, ties break toward the earlier
    // chunk (deterministic order for the preload pair around the view).
    const distance = (chunkIndex: number): number =>
      chunkIndex < visibleFirst
        ? visibleFirst - chunkIndex
        : chunkIndex > visibleLast
          ? chunkIndex - visibleLast
          : 0;
    return ranges.sort(
      (a, b) =>
        distance(a.start / ROW_CHUNK) - distance(b.start / ROW_CHUNK) ||
        a.start - b.start,
    );
  }

  markLoaded(chunkStart: number): void {
    const idx = chunkStart / ROW_CHUNK;
    this.inFlight.delete(idx);
    this.loaded.add(idx);
  }

  markFailed(chunkStart: number): void {
    this.inFlight.delete(chunkStart / ROW_CHUNK);
  }

  reset(): void {
    this.loaded.clear();
    this.inFlight.clear();
  }

  /** Merged row cache: 0-based line index -> RowDto (from any chunk). */
  static toRow(raw: RawRowDto): RowDto {
    return {
      line_no: raw.line_no,
      time_display: raw.time_display,
      category: raw.category,
      level: raw.level,
      message: raw.message,
      raw: raw.raw,
    };
  }

  static fromChunk(chunk: RawRowDto[], start: number): Map<number, RowDto> {
    const rows = new Map<number, RowDto>();
    chunk.forEach((raw, offset) => rows.set(start + offset, ChunkPlanner.toRow(raw)));
    return rows;
  }

  /** Stamped rows of one chunk: 0-based line index -> stamped entry. Pure —
   *  the cache merges this output over its previous generation, so every
   *  applied range lands restamped with the caller's epoch (design
   *  2026-11-25-flicker). Entry reads (map.get) return the stamped entry
   *  itself regardless of stamp; current-truth reads go through
   *  currentStamped. */
  static fromChunkStamped(
    chunk: RawRowDto[],
    start: number,
    epoch: number,
  ): Map<number, StampedRow> {
    const rows = new Map<number, StampedRow>();
    chunk.forEach((raw, offset) =>
      rows.set(start + offset, { row: ChunkPlanner.toRow(raw), epoch }),
    );
    return rows;
  }

  /** Current-truth read gate: the entry at `index` only when its stamp equals
   *  the reader's current epoch, else undefined (treated as "not yet loaded"
   *  by the calling layer). */
  static currentStamped(
    map: Map<number, StampedRow>,
    index: number,
    currentEpoch: number,
  ): StampedRow | undefined {
    const entry = map.get(index);
    return entry !== undefined && entry.epoch === currentEpoch ? entry : undefined;
  }
}
