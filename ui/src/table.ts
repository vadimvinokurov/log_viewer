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

/** Which chunk indexes to fetch for a visible window (± 1 chunk preload). */
export class ChunkPlanner {
  private loaded = new Set<number>();
  private inFlight = new Set<number>();

  /** Chunk ranges to fetch now; an empty result means nothing is pending. */
  plan(visibleStart: number, visibleEnd: number, rowCount: number): { start: number; end: number }[] {
    const first = Math.max(0, Math.floor(visibleStart / ROW_CHUNK) - 1);
    const last = Math.floor(Math.max(0, Math.min(rowCount - 1, visibleEnd)) / ROW_CHUNK) + 1;
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
    return ranges;
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
}
