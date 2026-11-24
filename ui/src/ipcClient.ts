//! Thin IPC adapter. Real calls go through the generated tauri bindings;
//! tests and the headless visual-acceptance page (docs/PIPELINE.md §5) can
//! stub the adapter instead of the real webview.

import { commands } from "./bindings";
import type { FilterItem, FilterMode } from "./filtersTab";
import type { LoadInfo, VisibilityState } from "./state";

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
  /** §11 level toggle; level = lowercase long name (backend validates). */
  setLevelEnabled(level: string, on: boolean): Promise<null>;
  /** Categories panel (rhl.2); path = full category path ("app/main/db"). */
  setCategoryEnabled(path: string, on: boolean): Promise<null>;
  /** The single read command of the visibility bridge (§7). */
  visibilitySnapshot(): Promise<import("./bindings").VisibilitySnapshotDto>;
}

/** Normalized contracts consumed by the UI (camelCase, docs/STACK.md). */
export interface IpcClient {
  pickFile(lastDir: string): Promise<string | null>;
  loadFile(path: string): Promise<LoadInfo>;
  getRows(offset: number, limit: number): Promise<import("./bindings").RowDto[]>;
  addFilter(mode: string, pattern: string): Promise<null>;
  setFilterEnabled(id: number, on: boolean): Promise<null>;
  removeFilter(id: number): Promise<null>;
  addPin(mode: string, pattern: string): Promise<null>;
  setPinEnabled(id: number, on: boolean): Promise<null>;
  removePin(id: number): Promise<null>;
  setLevelEnabled(level: string, on: boolean): Promise<null>;
  setCategoryEnabled(path: string, on: boolean): Promise<null>;
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
function toFilterItem(raw: { id: number; mode: string; pattern: string; enabled: boolean }): FilterItem {
  const mode = FILTER_MODES.find((candidate) => candidate === raw.mode) ?? "plain";
  return { id: raw.id, mode, pattern: raw.pattern, enabled: raw.enabled };
}

/** Normalizes visibility_snapshot's RAW shape into VisibilityState — the
 *  single renaming point between the IPC contract and the UI. */
function fromSnapshot(raw: {
  visible_count: number;
  levels: { level: string; enabled: boolean; count: number }[];
  filters: { id: number; mode: string; pattern: string; enabled: boolean }[];
  pins: { id: number; mode: string; pattern: string; enabled: boolean }[];
  categories_enabled: string[];
}): VisibilityState {
  return {
    visibleCount: raw.visible_count,
    levels: raw.levels.map((l) => ({ level: l.level, enabled: l.enabled, count: l.count })),
    filters: raw.filters.map(toFilterItem),
    pins: raw.pins.map(toFilterItem),
    categoriesEnabled: [...raw.categories_enabled],
  };
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
  async setLevelEnabled(level: string, on: boolean) {
    return commands.setLevelEnabled(level, on);
  },
  async setCategoryEnabled(path: string, on: boolean) {
    return commands.setCategoryEnabled(path, on);
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
    getRows: (offset: number, limit: number) => source.getRows(offset, limit),
    addFilter: (mode: string, pattern: string) => source.addFilter(mode, pattern),
    setFilterEnabled: (id: number, on: boolean) => source.setFilterEnabled(id, on),
    removeFilter: (id: number) => source.removeFilter(id),
    addPin: (mode: string, pattern: string) => source.addPin(mode, pattern),
    setPinEnabled: (id: number, on: boolean) => source.setPinEnabled(id, on),
    removePin: (id: number) => source.removePin(id),
    setLevelEnabled: (level: string, on: boolean) => source.setLevelEnabled(level, on),
    setCategoryEnabled: (path: string, on: boolean) => source.setCategoryEnabled(path, on),
    async visibilitySnapshot() {
      return fromSnapshot(await source.visibilitySnapshot());
    },
  };
}

export { commands };
