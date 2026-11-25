//! LogTable harness + baseline tests (design 2026-11-25-flicker, task 2).
//! jsdom has no layout, so the harness feeds @tanstack/react-virtual what it
//! reads: a ResizeObserver stub with manual notification (metrics do NOT flow
//! without it — see task-2 report "adaptation") and defineProperty metrics on
//! the .table-scroll element. IPC is mocked with deferred promises the tests
//! resolve manually. The two tests pin CURRENT (pre-refactor) behavior; they
//! run green before the stamped-cache refactor and must stay green after.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import { createElement, createRef } from "react";
import type { RowDto as RawRowDto } from "./bindings";
import { DEFAULT_COLUMN_WIDTHS } from "./columnWidths";
import { LogTable, type LogTableHandle } from "./LogTable.tsx";
import { EMPTY_SELECTION } from "./selection";
import type { SelectionState } from "./selection";

// ---------------------------------------------------------------------------
// IPC mock: deferred get_rows per call, recorded for manual resolution.
// ---------------------------------------------------------------------------

interface PendingRequest {
  offset: number;
  limit: number;
  resolve: (rows: RawRowDto[]) => void;
  reject: (error: unknown) => void;
}

const h = vi.hoisted((): { requests: PendingRequest[] } => {
  const requests: PendingRequest[] = [];
  return { requests };
});

vi.mock("./ipcClient", () => ({
  ipc: () => ({
    getRows: (offset: number, limit: number): Promise<RawRowDto[]> => {
      let resolveFn!: (rows: RawRowDto[]) => void;
      let rejectFn!: (error: unknown) => void;
      const promise = new Promise<RawRowDto[]>((res, rej) => {
        resolveFn = res;
        rejectFn = rej;
      });
      h.requests.push({ offset, limit, resolve: resolveFn, reject: rejectFn });
      return promise;
    },
  }),
}));

/** Test-side resolution of one recorded get_rows request. */
function resolveRequest(request: PendingRequest, rows: RawRowDto[]): void {
  request.resolve(rows);
}

// ---------------------------------------------------------------------------
// ResizeObserver stub: instances register live; tests notify manually.
// ---------------------------------------------------------------------------

class ResizeObserverStub implements ResizeObserver {
  private static live: ResizeObserverStub[] = [];
  private readonly targets = new Set<Element>();
  private readonly cb: ResizeObserverCallback;

  constructor(cb: ResizeObserverCallback) {
    this.cb = cb;
    ResizeObserverStub.live.push(this);
  }

  observe(target: Element): void {
    this.targets.add(target);
  }

  unobserve(target: Element): void {
    this.targets.delete(target);
  }

  disconnect(): void {
    const idx = ResizeObserverStub.live.indexOf(this);
    if (idx >= 0) {
      ResizeObserverStub.live.splice(idx, 1);
    }
  }

  /** One synchronous notification pass over live observers that still have
   *  observed targets (jsdom never fires ResizeObserver on its own). */
  static notifyAll(): void {
    for (const ro of [...ResizeObserverStub.live]) {
      if (ro.targets.size > 0) {
        ro.cb([], ro);
      }
    }
  }
}

vi.stubGlobal("ResizeObserver", ResizeObserverStub);

// ---------------------------------------------------------------------------
// Fixtures + mount helper.
// ---------------------------------------------------------------------------

const aRawRow = (line: number): RawRowDto => ({
  line_no: line,
  time_display: "10:00:00.000",
  category: "app.sub",
  level: "info",
  message: `message body ${line}`,
  raw: `raw line ${line}`,
  spans: [],
});

const CHUNK_ROWS = 1000;

const chunkOf = (firstLine: number, count: number): RawRowDto[] =>
  Array.from({ length: count }, (_, i) => aRawRow(firstLine + i));

const VIEWPORT_ROWS = 5;

/** Renders the table, then stamps the .table-scroll element with the metrics
 *  the virtualizer reads (clientWidth/Height, scrollHeight, bounding rect)
 *  and fires the stubbed ResizeObservers so the item range is computed. */
function mountTable(overrides?: {
  rowCount?: number;
  selection?: SelectionState;
}): { ref: React.RefObject<LogTableHandle | null>; container: HTMLElement } {
  const ref = createRef<LogTableHandle>();
  const element = createElement(LogTable, {
    rowCount: overrides?.rowCount ?? CHUNK_ROWS,
    fileEpoch: 1,
    visibilityEpoch: 1,
    selection: overrides?.selection ?? EMPTY_SELECTION,
    pins: [],
    columnWidths: DEFAULT_COLUMN_WIDTHS,
    onColumnSet: vi.fn(),
    onColumnCommit: vi.fn(),
    onColumnReset: vi.fn(),
    onRowClick: vi.fn(),
    ref,
  });
  const rendered = render(element);
  const scroll = rendered.container.querySelector(".table-scroll");
  if (!(scroll instanceof HTMLElement)) {
    throw new Error("harness: .table-scroll not found");
  }
  const heightPx = VIEWPORT_ROWS * 18;
  Object.defineProperty(scroll, "clientWidth", {
    configurable: true,
    get: () => 400,
  });
  Object.defineProperty(scroll, "clientHeight", {
    configurable: true,
    get: () => heightPx,
  });
  Object.defineProperty(scroll, "scrollHeight", {
    configurable: true,
    get: () => heightPx + 10 * heightPx,
  });
  Object.defineProperty(scroll, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      x: 0,
      y: 0,
      width: 400,
      height: heightPx,
      top: 0,
      right: 400,
      bottom: heightPx,
      left: 0,
      toJSON: () => ({}),
    }),
  });
  // Push the metrics through the stubbed observers (rect observer of the
  // virtualizer + the table's own viewport-width observer).
  act(() => {
    ResizeObserverStub.notifyAll();
  });
  return { ref, container: rendered.container };
}

beforeEach(() => {
  h.requests.length = 0;
});

afterEach(cleanup);

describe("LogTable baseline behavior (task 2, design 2026-11-25-flicker)", () => {
  it("rows appear after the covering chunk lands", async () => {
    const { container } = mountTable();
    // The only visible chunk (rowCount = one chunk) was requested...
    expect(h.requests.length).toBe(1);
    const request = h.requests[0];
    if (!request) {
      throw new Error("harness: chunk request missing");
    }
    expect(request.offset).toBe(0);
    expect(request.limit).toBe(CHUNK_ROWS);
    // ...and once it lands, the visible line numbers come from it.
    await act(async () => {
      resolveRequest(request, chunkOf(1, CHUNK_ROWS));
    });
    const texts = Array.from(
      container.querySelectorAll(".row .cell-line"),
      (el) => el.textContent ?? "",
    );
    // 5 viewport rows + 10 overscan = 15 virtualized rows.
    expect(texts.length).toBe(15);
    expect(texts.slice(0, VIEWPORT_ROWS)).toEqual(["1", "2", "3", "4", "5"]);
    expect(texts).toEqual(
      Array.from({ length: texts.length }, (_, i) => String(i + 1)),
    );
  });

  it("copy resolves the selection's rows", async () => {
    const { ref } = mountTable({ selection: { selected: [0], anchor: 0 } });
    // The chunk fetch (limit 1000) is in flight from the mount effect.
    expect(h.requests.length).toBe(1);
    const handle = ref.current;
    if (!handle) {
      throw new Error("harness: no LogTable handle");
    }
    const copyPromise = handle.copy("raw");
    // copy() misses nothing in the cache... except row 0 itself: the one-row
    // get_rows fills the gap while the big chunk stay pending.
    const request = h.requests.find((r) => r.limit === 1);
    if (!request) {
      throw new Error("harness: no single-row request from copy");
    }
    expect(request.offset).toBe(0);
    act(() => {
      resolveRequest(request, [aRawRow(1)]);
    });
    const text = await copyPromise;
    expect(text).toBe("raw line 1");
  });
});
