//! Thin IPC adapter. Real calls go through the generated tauri bindings;
//! tests and the headless visual-acceptance page (docs/PIPELINE.md §5) can
//! stub the adapter instead of the real webview.

import { commands } from "./bindings";
import type { LoadInfo } from "./state";

export interface IpcClient {
  loadFile(path: string): Promise<LoadInfo>;
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

export const realIpc: IpcClient = {
  async loadFile(path: string) {
    return fromBindings(await commands.loadFile(path));
  },
};

/**
 * The active client. Tests and headless runs set `window.__ipcStub` before
 * the page loads; when present it replaces the real bindings calls.
 */
export function ipc(): IpcClient {
  const stub = (window as unknown as { __ipcStub?: IpcClient }).__ipcStub;
  return stub ?? realIpc;
}

export { commands };
