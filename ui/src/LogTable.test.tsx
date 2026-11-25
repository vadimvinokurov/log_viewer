//! LogTable harness + tests (design 2026-11-25-flicker). jsdom has no layout,
//! so the harness feeds @tanstack/react-virtual what it reads: a ResizeObserver
//! stub with manual notification (metrics do NOT flow without it — see task-2
//! report "adaptation") and defineProperty metrics on the .table-scroll
//! element. IPC is mocked with deferred promises the tests resolve manually.
//! Task 2 landed the harness + two baseline pins; task 3 adds the visibility-
//! epoch behavior tests (RED before the wipe removal, GREEN after).

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
  /** Set by the test-side resolution helpers (settle helpers rely on it). */
  resolved: boolean;
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
      h.requests.push({
        offset,
        limit,
        resolved: false,
        resolve: resolveFn,
        reject: rejectFn,
      });
      return promise;
    },
  }),
}));

/** Test-side resolution of one recorded get_rows request. */
function resolveRequest(request: PendingRequest, rows: RawRowDto[]): void {
  request.resolved = true;
  request.resolve(rows);
}

/** First recorded request (the mount-time chunk fetch). */
function firstRequest(): PendingRequest {
  const request = h.requests[0];
  if (!request) {
    throw new Error("harness: no recorded request");
  }
  return request;
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
 *  and fires the stubbed ResizeObservers so the item range is computed.
 *  `rerender` patches the epoch props (task-3 tests' driver). */
interface TablePropsPatch {
  rowCount?: number;
  fileEpoch?: number;
  visibilityEpoch?: number;
  selection?: SelectionState;
}

function mountTable(overrides?: TablePropsPatch): {
  ref: React.RefObject<LogTableHandle | null>;
  container: HTMLElement;
  rerender: (patch: TablePropsPatch) => void;
} {
  const ref = createRef<LogTableHandle>();
  const props = {
    rowCount: overrides?.rowCount ?? CHUNK_ROWS,
    fileEpoch: 1,
    visibilityEpoch: 1,
    selection: overrides?.selection ?? EMPTY_SELECTION,
  };
  const tableElement = (p: typeof props) =>
    createElement(LogTable, {
      rowCount: p.rowCount,
      fileEpoch: p.fileEpoch,
      visibilityEpoch: p.visibilityEpoch,
      selection: p.selection,
      pins: [],
      columnWidths: DEFAULT_COLUMN_WIDTHS,
      onColumnSet: vi.fn(),
      onColumnCommit: vi.fn(),
      onColumnReset: vi.fn(),
      onRowClick: vi.fn(),
      ref,
    });
  const rendered = render(tableElement(props));
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
  return {
    ref,
    container: rendered.container,
    rerender: (patch: TablePropsPatch): void => {
      Object.assign(props, patch);
      rendered.rerender(tableElement(props));
    },
  };
}

// ---------------------------------------------------------------------------
// Settle helpers: deferred IPC + chained probes.
// ---------------------------------------------------------------------------

/** `.cell-line` texts of the painted rows, in paint order. */
function cellLines(container: HTMLElement): string[] {
  return Array.from(
    container.querySelectorAll(".row .cell-line"),
    (el) => el.textContent ?? "",
  );
}

/** Settles the deferred requests while new ones appear (chained probes):
 *  every unresolved request is answered with `lineFor`'s data —
 *  index i (0-based visible index) -> 1-based line of the sequence the test
 *  defines. Bounded passes; throws if requests never settle. */
async function settleMatching(
  lineFor: (index: number) => number,
  matches: (r: PendingRequest) => boolean,
): Promise<void> {
  for (let pass = 0; pass < 100; pass++) {
    const pending = h.requests.filter((r) => !r.resolved && matches(r));
    if (pending.length === 0) {
      return;
    }
    await act(async () => {
      for (const request of pending) {
        resolveRequest(request, chunkOf(lineFor(request.offset), request.limit));
      }
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }
  throw new Error("harness: deferred requests never settled");
}

/** Resolves every still-in-flight request (chunk + probes). */
async function settleAll(lineFor: (index: number) => number): Promise<void> {
  await settleMatching(lineFor, () => true);
}

/** Resolves only single-row probe requests: chunk requests stay in flight,
 *  so a test can count the anchor-search probes BEFORE the covering chunk
 *  lands (with the chunk in cache, the search would hit it instead of
 *  probing — see test 5). */
async function settleProbes(lineFor: (index: number) => number): Promise<void> {
  await settleMatching(lineFor, (r) => r.limit === 1);
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

// ---------------------------------------------------------------------------
// Task 3 (design 2026-11-25-flicker): visibility-epoch behavior. Sequences
// are defined by lineFor mapping index (0-based visible index) -> 1-based
// line; "epoch 2" below means one visibilityEpoch bump.
// ---------------------------------------------------------------------------

describe("LogTable through visibility bumps (task 3, design 2026-11-25-flicker)", () => {
  /** The initial mount paints rowCount = 1000 rows of lines 1..1000; with a
   *  5-row viewport + 10 overscan the painted slice is lines 1..15. */
  const paintedSlice = (offset: number): string[] =>
    Array.from({ length: VIEWPORT_ROWS + 10 }, (_, i) => String(offset + i + 1));

  it("1. cells keep old text through a visibility bump until the new chunk lands", async () => {
    const { container, rerender } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    const painted = cellLines(container);
    rerender({ visibilityEpoch: 2 });
    // BEFORE the new chunks resolve: every painted cell still shows the old
    // sequence (stale-while-revalidate). Under the pre-fix wipe these are "".
    expect(cellLines(container)).toEqual(painted);
    // The new sequence's chunks land: per-chunk overwrite repaints.
    await settleAll((index) => index + 2);
    expect(cellLines(container)).toEqual(paintedSlice(1));
  });

  it("2. two bumps with deferred chunks; epoch drop keeps painted rows", async () => {
    const { container, rerender } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, 1000));
    });
    const painted = cellLines(container);
    rerender({ visibilityEpoch: 2 });
    rerender({ visibilityEpoch: 3 });
    // Epoch 2's chunk resolves after epoch 3 superseded it: the epoch stamp
    // drops it — the painted old rows survive (the pre-fix wipe blanked).
    const e2Chunk = h.requests.find((r) => !r.resolved && r.limit === CHUNK_ROWS);
    if (!e2Chunk) {
      throw new Error("harness: epoch-2 chunk request missing");
    }
    await act(async () => {
      resolveRequest(e2Chunk, chunkOf(2, CHUNK_ROWS));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(cellLines(container)).toEqual(painted);
    // The current epoch's chunk lands: per-chunk overwrite paints seq 3.
    await settleAll((index) => 30 + index);
    expect(cellLines(container)).toEqual(paintedSlice(29));
  });

  it("3. rowCount -> 0 rerender: no rows, no crash, viewport anchor null", async () => {
    const { container, ref, rerender } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    rerender({ rowCount: 0, visibilityEpoch: 2 });
    expect(container.querySelectorAll(".row").length).toBe(0);
    expect(ref.current?.viewport()).toEqual({
      scrollTop: 0,
      scrollLeft: 0,
      anchor: null,
      anchorOffsetPx: 0,
    });
    await settleProbes((index) => index + 2);
    await settleAll((index) => index + 2);
  });

  it("4. anchor skip-gate keeps anchor + skips the probe storm", async () => {
    const { rerender, ref } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    const viewportBefore = ref.current?.viewport();
    if (!viewportBefore) {
      throw new Error("harness: no viewport info");
    }
    const start = h.requests.length;
    rerender({ visibilityEpoch: 2 });
    // Identical composition queued below — until then the painted rows and
    // the captured anchor must survive the mid-refetch state untouched.
    expect(ref.current?.viewport()).toEqual(viewportBefore);
    await settleAll((index) => index + 1);
    // Identical sequence landed: at most the one gate probe beyond the chunk
    // refill; the pre-fix code binary-searched ~log2(count) probes per bump.
    const duringTransition = h.requests.length - start;
    expect(duringTransition).toBeLessThanOrEqual(2);
    expect(ref.current?.viewport()).toEqual(viewportBefore);
  });

  it("5. anchor restore runs on equal-count composition change", async () => {
    const { rerender, ref } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    const start = h.requests.length;
    rerender({ visibilityEpoch: 2 });
    // Probes only (chunk held in flight): the gate falls through to the
    // binary search, whose probe count is ~log2(count) — not the skip.
    await settleProbes((index) => index + 2);
    const probes = h.requests.slice(start).filter((r) => r.limit === 1);
    expect(probes.length).toBeGreaterThanOrEqual(10); // ceil(log2(1001)) = 10
    await settleAll((index) => index + 2);
    // The search resolved the anchor onto the nearest continuation: the new
    // row at the resolved index carries line 2 (chunk index 0, lineFor 0+2).
    expect(ref.current?.viewport()?.anchor?.line).toBe(2);
  });

  it("8. probed stale index holds fresh truth (stamp-aware overwrite)", async () => {
    const { rerender, ref } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    // One visibility bump; the gate probe (and the search it triggers, the
    // anchor line moved) lands FRESH current-epoch entries at the probed
    // indexes while the covering chunk request is still in flight.
    rerender({ visibilityEpoch: 2 });
    await settleProbes((index) => index + 2);
    // The fresh entry must have replaced the stale stamp-1 one...
    const before = h.requests.length;
    rerender({ selection: { selected: [0], anchor: 0 } });
    const handle = ref.current;
    if (!handle) {
      throw new Error("harness: no LogTable handle");
    }
    // ...so an epoch-gated read (copy -> resolveRows) serves it with no
    // re-fetch. Under the pre-fix prev.has guard the probe result was
    // discarded — copy paid a fresh get_rows for the same index repeatedly.
    const text = await handle.copy("raw");
    expect(h.requests.length).toBe(before);
    expect(text).toBe("raw line 2");
  });

  it("6. copy mid-refetch returns the new sequence", async () => {
    const { rerender, ref } = mountTable({
      selection: { selected: [0], anchor: 0 },
    });
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    rerender({ visibilityEpoch: 2 });
    const handle = ref.current;
    if (!handle) {
      throw new Error("harness: no LogTable handle");
    }
    let settled = false;
    const copyPromise = handle.copy("raw").then((text) => {
      settled = true;
      return text;
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // Mid-refetch the copy-driven fetch is in flight: not resolved (and
    // never to the old raw text — the copy path gates by epoch).
    expect(settled).toBe(false);
    const copyFetch = [...h.requests]
      .reverse()
      .find((r) => !r.resolved && r.limit === 1 && r.offset === 0);
    if (!copyFetch) {
      throw new Error("harness: copy-driven fetch missing");
    }
    await act(async () => {
      resolveRequest(copyFetch, [aRawRow(2)]);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    await settleAll((index) => index + 2);
    await expect(copyPromise).resolves.toBe("raw line 2");
  });

  it("7. fileEpoch bump still wipes the painted rows", async () => {
    const { container, rerender } = mountTable();
    await act(async () => {
      resolveRequest(firstRequest(), chunkOf(1, CHUNK_ROWS));
    });
    rerender({ fileEpoch: 2 });
    // A new file must never paint old-file rows: the wipe stays here.
    expect(cellLines(container)).toEqual(
      Array.from({ length: VIEWPORT_ROWS + 10 }, () => ""),
    );
    await settleAll((index) => index + 51);
    expect(cellLines(container)).toEqual(paintedSlice(50));
  });
});
