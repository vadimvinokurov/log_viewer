//! Thin IPC adapter. Real calls go through the generated tauri bindings;
//! tests and the headless visual-acceptance page (docs/PIPELINE.md §5) can
//! stub the adapter instead of the real webview.

import { commands } from "./bindings";
import type { LoadInfo } from "./state";

/** Raw IPC contracts, exactly as the backend returns them. */
interface RawIpc {
  /** Native file-open dialog; null when the user cancels (§2). */
  pickFile(lastDir: string): Promise<string | null>;
  loadFile(path: string): Promise<import("./bindings").LoadResult>;
  getRows(offset: number, limit: number): Promise<import("./bindings").RowDto[]>;
}

/** Normalized contracts consumed by the UI (camelCase, docs/STACK.md). */
export interface IpcClient {
  pickFile(lastDir: string): Promise<string | null>;
  loadFile(path: string): Promise<LoadInfo>;
  getRows(offset: number, limit: number): Promise<import("./bindings").RowDto[]>;
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
  };
}

export { commands };
