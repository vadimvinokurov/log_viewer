//! Thin IPC adapter. Real calls go through the generated tauri bindings;
//! tests and the headless visual-acceptance page (docs/PIPELINE.md §5) can
//! stub the adapter instead of the real webview.

import { commands } from "./bindings";
import type { FilterItem, FilterMode } from "./filtersTab";
import { type HighlightItem } from "./highlights";
import type { LoadInfo, SearchMatches, VisibilityState } from "./state";

/** Raw IPC contracts, exactly as the backend returns them
 *  (docs/notes/visibility-bridge.md). */
export interface RawIpc {
  /** Native file-open dialog; null when the user cancels (§2). */
  pickFile(lastDir: string): Promise<string | null>;
  loadFile(path: string): Promise<import("./bindings").LoadResult>;
  getRows(offset: number, limit: number): Promise<import("./bindings").RowDto[]>;
  /** §10.1 filters; mode ∈ plain|regex|simple|lineno. */
  addFilter(mode: string, pattern: string): Promise<null>;
  setFilterEnabled(id: number, on: boolean): Promise<null>;
  removeFilter(id: number): Promise<null>;
  /** §12 pins (panel comes with q1f.1; RPC symmetric with filters). */
  addPin(mode: string, pattern: string): Promise<null>;
  setPinEnabled(id: number, on: boolean): Promise<null>;
  removePin(id: number): Promise<null>;
  /** §12 rmp: removes every pin (the future command-line :rmp). */
  clearPins(): Promise<null>;
  /** §11 level toggle; level = lowercase long name (backend validates). */
  setLevelEnabled(level: string, on: boolean): Promise<null>;
  /** Categories panel (rhl.2); path = full category path ("app/main/db"). */
  setCategoryEnabled(path: string, on: boolean): Promise<null>;
  /** §8 search over the visible sequence (bead 2wu.1): mode ∈ plain|regex|simple; unknown mode → the
   *  backend rejects; an invalid pattern matches nothing. */
  searchVisible(mode: string, pattern: string): Promise<import("./bindings").SearchMatchDto>;
  /** §9 highlights (exx.2): modes as filters; an unknown mode is an Err. */
  addHighlight(mode: string, pattern: string): Promise<null>;
  setHighlightEnabled(id: number, on: boolean): Promise<null>;
  /** hex = css "#rrggbb", or null to reset to the palette rotation color. */
  setHighlightColor(id: number, hex: string | null): Promise<null>;
  removeHighlight(id: number): Promise<null>;
  /** §9 rmh wholesale removal (the cmdline epic wires the command). */
  clearHighlights(): Promise<null>;
  /** The single read command of the visibility bridge (§7). */
  visibilitySnapshot(): Promise<import("./bindings").VisibilitySnapshotDto>;
}

/** Normalized contracts consumed by the UI (camelCase, docs/STACK.md). */
export interface IpcClient {
  pickFile(lastDir: string): Promise<string | null>;
  loadFile(path: string): Promise<LoadInfo>;
  /**
   * get_rows rows with the §9 spans normalized in place: `start`/`len` are
   * JS string indexes of `message` (the RAW DTO carries UTF-8 byte offsets;
   * the conversion happens HERE once, the single normalization point).
   */
  getRows(offset: number, limit: number): Promise<import("./bindings").RowDto[]>;
  addFilter(mode: string, pattern: string): Promise<null>;
  setFilterEnabled(id: number, on: boolean): Promise<null>;
  removeFilter(id: number): Promise<null>;
  addPin(mode: string, pattern: string): Promise<null>;
  setPinEnabled(id: number, on: boolean): Promise<null>;
  removePin(id: number): Promise<null>;
  clearPins(): Promise<null>;
  setLevelEnabled(level: string, on: boolean): Promise<null>;
  setCategoryEnabled(path: string, on: boolean): Promise<null>;
  /** §9 highlight RPC (exx.2); symmetric with the filters. */
  addHighlight(mode: string, pattern: string): Promise<null>;
  setHighlightEnabled(id: number, on: boolean): Promise<null>;
  setHighlightColor(id: number, hex: string | null): Promise<null>;
  removeHighlight(id: number): Promise<null>;
  clearHighlights(): Promise<null>;
  /** §8 search over the visible sequence (bead 2wu.1). */
  searchVisible(mode: string, pattern: string): Promise<SearchMatches>;
  visibilitySnapshot(): Promise<VisibilityState>;
}

/** Wraps load_file's result into the state-shape LoadInfo. */
function fromBindings(load: {
  format: string;
  line_count: number;
  categories: { path: string; count: number }[];
  levels: { level: string; count: number }[];
  load_ms: number;
}): LoadInfo {
  return {
    format: load.format,
    lineCount: load.line_count,
    categories: load.categories,
    levels: load.levels,
    loadMs: load.load_ms,
  };
}

const FILTER_MODES: readonly FilterMode[] = ["plain", "regex", "simple", "lineno"];

/** The backend rejects unknown modes at add_filter time (contract), so an
 *  unexpected snapshot mode is defensive only; it falls back to "plain"
 *  instead of an `as` cast (strict-types rule). */
function toFilterMode(raw: string): FilterMode {
  return FILTER_MODES.find((candidate) => candidate === raw) ?? "plain";
}

function toFilterItem(raw: { id: number; mode: string; pattern: string; enabled: boolean }): FilterItem {
  return { id: raw.id, mode: toFilterMode(raw.mode), pattern: raw.pattern, enabled: raw.enabled };
}

/** §9 highlight rule of the snapshot: the filter shape plus the palette
 *  rotation slot and the optional user color override. */
function toHighlightItem(raw: {
  id: number;
  mode: string;
  pattern: string;
  enabled: boolean;
  color_index: number;
  override_color?: string | null;
}): HighlightItem {
  return {
    id: raw.id,
    mode: toFilterMode(raw.mode),
    pattern: raw.pattern,
    enabled: raw.enabled,
    colorIndex: raw.color_index,
    overrideColor: raw.override_color ?? null,
  };
}

/** UTF-8 byte-width of one JS string unit (lone surrogates cannot occur in
 *  the text the backend sends — Rust strings are valid UTF-8). */
function utf8Width(cp: number): number {
  if (cp < 0x80) return 1;
  if (cp < 0x800) return 2;
  if (cp <= 0xffff) return 3;
  return 4;
}

/** Maps the message's byte offsets to JS string code-unit indexes: one walk
 *  over the text, byte offset -> index of the code point starting there. */
function byteIndexMap(message: string): Map<number, number> {
  const map = new Map<number, number>([[0, 0]]);
  let byte = 0;
  let index = 0;
  for (let i = 0; i < message.length; ) {
    const cp = message.codePointAt(i);
    if (cp === undefined) {
      break;
    }
    const units = cp > 0xffff ? 2 : 1;
    byte += utf8Width(cp);
    index += units;
    i += units;
    map.set(byte, index);
  }
  return map;
}

interface RawSpan {
  start: number;
  len: number;
  color_index: number;
  override_color?: string | null;
}

interface NormalizedSpan {
  start: number;
  len: number;
  color_index: number;
  override_color: string | null;
}

/** §9 SINGLE normalization point (exx.2): the RAW SpanDto carries BYTE
 *  offsets inside the message text; the UI consumes JS string indexes.
 *  One walk of the message builds the offset map, every span converts
 *  through it in O(1). */
function normalizeSpans(spans: readonly RawSpan[] | undefined, message: string): NormalizedSpan[] {
  if (!spans || spans.length === 0) {
    return [];
  }
  const offsets = byteIndexMap(message);
  // The map ends with the full message's byte length (its end offset), so a
  // boundary at/past the end walks down to it and resolves to the full
  // length; a boundary that lands mid-code-point (cannot occur from the
  // backend's char-aligned matchers) rounds down to the code-point start.
  const resolve = (target: number): number => {
    let offset = target;
    while (offset > 0 && !offsets.has(offset)) {
      offset--;
    }
    return offsets.get(offset) ?? 0;
  };
  return spans.map((raw) => {
    const start = resolve(raw.start);
    const end = resolve(raw.start + raw.len);
    return {
      start,
      len: Math.max(0, end - start),
      color_index: raw.color_index,
      override_color: raw.override_color ?? null,
    };
  });
}

/** Normalizes visibility_snapshot's RAW shape into VisibilityState — the
 *  single renaming point between the IPC contract and the UI. */
function fromSnapshot(raw: {
  visible_count: number;
  levels: { level: string; enabled: boolean; count: number }[];
  filters: { id: number; mode: string; pattern: string; enabled: boolean }[];
  pins: { id: number; mode: string; pattern: string; enabled: boolean }[];
  categories_enabled: string[];
  highlights: {
    id: number;
    mode: string;
    pattern: string;
    enabled: boolean;
    color_index: number;
    override_color?: string | null;
  }[];
}): VisibilityState {
  return {
    visibleCount: raw.visible_count,
    levels: raw.levels.map((l) => ({ level: l.level, enabled: l.enabled, count: l.count })),
    filters: raw.filters.map(toFilterItem),
    pins: raw.pins.map(toFilterItem),
    highlights: raw.highlights.map(toHighlightItem),
    categoriesEnabled: [...raw.categories_enabled],
  };
}

/** §8 search result (bead 2wu.1): the DTO already carries the UI field
 *  names (total/positions), so the normalization keeps the shape and takes
 *  ownership of the copy — the UI type, not the bindings alias, is consumed. */
function fromSearch(raw: { total: number; positions: number[] }): SearchMatches {
  return { total: raw.total, positions: [...raw.positions] };
}

/** Converts the byte offsets of one get_rows chunk's spans (exx.2): each row
 *  is copied with its spans in JS string indexes; a row without spans is
 *  returned unchanged (defensive over older stubs). */
function fromChunkRows(rows: Awaited<ReturnType<RawIpc["getRows"]>>): typeof rows {
  return rows.map((row) =>
    row.spans && row.spans.length > 0
      ? { ...row, spans: normalizeSpans(row.spans, row.message) }
      : row,
  );
}

export const realIpc: RawIpc = {
  async pickFile(lastDir: string) {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const file = await open({
      directory: false,
      multiple: false,
      defaultPath: lastDir || undefined,
    });
    return typeof file === "string" ? file : null;
  },
  async loadFile(path: string) {
    return commands.loadFile(path);
  },
  async getRows(offset: number, limit: number) {
    return commands.getRows(offset, limit);
  },
  async addFilter(mode: string, pattern: string) {
    return commands.addFilter(mode, pattern);
  },
  async setFilterEnabled(id: number, on: boolean) {
    return commands.setFilterEnabled(id, on);
  },
  async removeFilter(id: number) {
    return commands.removeFilter(id);
  },
  async addPin(mode: string, pattern: string) {
    return commands.addPin(mode, pattern);
  },
  async setPinEnabled(id: number, on: boolean) {
    return commands.setPinEnabled(id, on);
  },
  async removePin(id: number) {
    return commands.removePin(id);
  },
  async clearPins() {
    return commands.clearPins();
  },
  async setLevelEnabled(level: string, on: boolean) {
    return commands.setLevelEnabled(level, on);
  },
  async setCategoryEnabled(path: string, on: boolean) {
    return commands.setCategoryEnabled(path, on);
  },
  async addHighlight(mode: string, pattern: string) {
    return commands.addHighlight(mode, pattern);
  },
  async setHighlightEnabled(id: number, on: boolean) {
    return commands.setHighlightEnabled(id, on);
  },
  async setHighlightColor(id: number, hex: string | null) {
    return commands.setHighlightColor(id, hex);
  },
  async removeHighlight(id: number) {
    return commands.removeHighlight(id);
  },
  async clearHighlights() {
    return commands.clearHighlights();
  },
  async searchVisible(mode: string, pattern: string) {
    return commands.searchVisible(mode, pattern);
  },
  async visibilitySnapshot() {
    return commands.visibilitySnapshot();
  },
};

/**
 * The active client. Tests and headless runs set `window.__ipcStub` via the
 * headless console; the stub mirrors the RAW IPC shapes (snake_case payloads
 * like load_file's LoadResult), and normalization to the UI shapes happens
 * HERE, once, for both the real and stubbed paths.
 */
export function ipc(): IpcClient {
  const stub = (window as unknown as { __ipcStub?: RawIpc }).__ipcStub;
  const source = stub ?? realIpc;
  return {
    pickFile: (lastDir: string) => source.pickFile(lastDir),
    async loadFile(path: string) {
      return fromBindings(await source.loadFile(path));
    },
    async getRows(offset: number, limit: number) {
      return fromChunkRows(await source.getRows(offset, limit));
    },
    addFilter: (mode: string, pattern: string) => source.addFilter(mode, pattern),
    setFilterEnabled: (id: number, on: boolean) => source.setFilterEnabled(id, on),
    removeFilter: (id: number) => source.removeFilter(id),
    addPin: (mode: string, pattern: string) => source.addPin(mode, pattern),
    setPinEnabled: (id: number, on: boolean) => source.setPinEnabled(id, on),
    removePin: (id: number) => source.removePin(id),
    clearPins: () => source.clearPins(),
    setLevelEnabled: (level: string, on: boolean) => source.setLevelEnabled(level, on),
    setCategoryEnabled: (path: string, on: boolean) => source.setCategoryEnabled(path, on),
    addHighlight: (mode: string, pattern: string) => source.addHighlight(mode, pattern),
    setHighlightEnabled: (id: number, on: boolean) => source.setHighlightEnabled(id, on),
    setHighlightColor: (id: number, hex: string | null) => source.setHighlightColor(id, hex),
    removeHighlight: (id: number) => source.removeHighlight(id),
    clearHighlights: () => source.clearHighlights(),
    async searchVisible(mode: string, pattern: string) {
      return fromSearch(await source.searchVisible(mode, pattern));
    },
    async visibilitySnapshot() {
      return fromSnapshot(await source.visibilitySnapshot());
    },
  };
}

export { commands };
