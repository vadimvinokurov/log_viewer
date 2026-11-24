import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ChunkPlanner, type RowDto } from "./table";
import { missingRanges, messageCopyText, rawCopyText } from "./selection";
import type { SelectionState } from "./selection";
import type { ContextMenuProps } from "./ContextMenu";
import { ContextMenu } from "./ContextMenu";
import { ipc } from "./ipcClient";
import type { CopyMode } from "./uiConsole";
import {
  ROW_HEIGHT_PX,
  anchorScrollTop,
  captureAnchor,
  resolveLineIndex,
  type Anchor,
  type ViewportInfo,
} from "./viewportAnchoring";
// The row height lives in the pure anchoring module now (§4); re-exported
// for the existing import sites.
export { ROW_HEIGHT_PX };

export interface LogTableHandle {
  /** Scroll so that the 1-based line number is centered in the viewport. */
  scrollToRow(lineNo: number): void;
  /** Copy the selection (raw lines or Message column, §4); resolves to
   * the text that was put on the clipboard. */
  copy(mode: CopyMode): Promise<string>;
  /** Viewport scroll state incl. the live anchor (§4, qt7.3); assertions
   * use this text RPC, never the DOM. Null without a mounted viewport. */
  viewport(): ViewportInfo | null;
}

interface Props {
  rowCount: number;
  /** Bumped when a new file was loaded: full reset incl. scrollTop = 0 (§4). */
  fileEpoch: number;
  /** Bumped on every applied visibility snapshot (§7): chunk cache and rows
   *  map reset only; scrollTop stays (the anchor is qt7.3's job, §4). */
  visibilityEpoch: number;
  selection: SelectionState;
  /** Row click: kind comes from the modifiers (§4 click/ctrl/shift). */
  onRowClick(index: number, kind: "click" | "toggle" | "range"): void;
}

/**
 * The main table (§4): four columns, fixed 23-px rows, pixel virtualization
 * over millions of rows via chunked get_rows loads. Level colors whole-row
 * text (§3.1); line number, time and uncategorized-message neutrals come
 * from the design tokens. Selection/context menu/copy land in qt7.2.
 */
export const LogTable = forwardRef<LogTableHandle, Props>(function LogTable(
  { rowCount, fileEpoch, visibilityEpoch, selection, onRowClick },
  ref,
) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const plannerRef = useRef(new ChunkPlanner());
  const [rows, setRows] = useState<Map<number, RowDto>>(new Map());
  const inFlightRef = useRef(false);
  // Live mirror of the rows cache for callbacks that must not re-create
  // across renders (the line probes below, §4 qt7.3).
  const rowsRef = useRef<Map<number, RowDto>>(rows);
  useLayoutEffect(() => {
    rowsRef.current = rows;
  }, [rows]);
  // Live anchor: identity and captured offset of the current first visible
  // row; the visibility-epoch step restores scrollTop from it (§4, qt7.3).
  interface LiveAnchor {
    index: number;
    anchor: Anchor;
  }
  const anchorRef = useRef<LiveAnchor | null>(null);
  // Current epoch pair in a ref: the in-flight fetch loop cannot read the
  // effect closure for the freshest value once a newer effect has re-run.
  const epochsRef = useRef({ file: fileEpoch, visibility: visibilityEpoch });
  useLayoutEffect(() => {
    epochsRef.current = { file: fileEpoch, visibility: visibilityEpoch };
  }, [fileEpoch, visibilityEpoch]);
  // Viewport coords where the context menu stands (§4: nothing selected -
  // no menu; selection is non-empty when the menu fires its commands).
  const [menuPos, setMenuPos] = useState<{ x: number; y: number } | null>(null);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT_PX,
    overscan: 10,
  });

  // New file (file epoch): throw away the cache, restart chunk planning and
  // also reset the scroll — a new file starts at the top (§4). Selection
  // indexes are per file (the reducer clears them at load-request).
  // Layout effects so the reset beats the chunk-fetch effect below in the
  // same commit — otherwise the planner still looks loaded and nothing
  // refetches (this regressed with the dsq.3 visibility epoch).
  useLayoutEffect(() => {
    plannerRef.current.reset();
    rowsRef.current = new Map(); // mirror cleared in the same flush: a probe
    // started by the anchor restore below must not read the old sequence.
    setRows(new Map());
    inFlightRef.current = false;
    setMenuPos(null);
    // A new file starts at the top and has no usable anchor (§2/§4).
    anchorRef.current = null;
    if (scrollRef.current && scrollRef.current.scrollTop !== 0) {
      scrollRef.current.scrollTop = 0;
    }
  }, [fileEpoch]);

  // Visibility change (§7): get_rows indexes the visible sequence, so the
  // chunk cache and rows map refill; the anchor step below repositions the
  // viewport. The signal is an epoch, not rowCount: equal-count changes must
  // still refill.
  useLayoutEffect(() => {
    plannerRef.current.reset();
    rowsRef.current = new Map(); // mirror cleared with the state (see fileEpoch)
    setRows(new Map());
    inFlightRef.current = false;
  }, [visibilityEpoch]);

  /** Resolves a visible row's 1-based line_no by index: from the rows cache
   *  or one get_rows(i, 1) probe; probes land in the rows cache (§4 qt7.3 -
   *  they are valid for the current epoch, which cleared the cache). */
  const lineAt = useCallback(async (index: number): Promise<number | null> => {
    const cached = rowsRef.current.get(index);
    if (cached) {
      return cached.line_no;
    }
    const epochAtCall = { ...epochsRef.current };
    try {
      const chunk = await ipc().getRows(index, 1);
      const raw = chunk[0];
      if (!raw) {
        return null;
      }
      const dto = ChunkPlanner.toRow(raw);
      // Cache only while the epoch still matches the call's: a probe raced
      // across an epoch bump resolved against the old sequence.
      if (
        epochAtCall.file === epochsRef.current.file &&
        epochAtCall.visibility === epochsRef.current.visibility
      ) {
        setRows((prev) =>
          prev.has(index) ? prev : new Map(prev).set(index, dto),
        );
      }
      return dto.line_no;
    } catch {
      return null;
    }
  }, []);

  // §4 qt7.3 anchor restore: on a visibility change, keep the anchor row at
  // its captured viewport offset. Runs before the fetch effect in the same
  // commit. Fallbacks: without a captured anchor (first row not in the rows
  // cache at capture time) nothing happens - scrollTop stays as-is; when the
  // anchor line plus everything after it is hidden, index resolves to null
  // and anchorScrollTop sends the viewport to the bottom.
  useLayoutEffect(() => {
    const captured = anchorRef.current;
    const viewport = scrollRef.current;
    if (!captured || !viewport) {
      return;
    }
    let cancelled = false;
    void (async () => {
      const index = await resolveLineIndex(
        captured.anchor.line,
        rowCount,
        lineAt,
      );
      if (cancelled) {
        return;
      }
      // scrollTop only - horizontal position is never programmatic (§4).
      viewport.scrollTop = anchorScrollTop(
        index,
        captured.anchor,
        rowCount,
        viewport.clientHeight,
      );
    })();
    return () => {
      cancelled = true;
    };
  }, [visibilityEpoch, rowCount, lineAt]);

  // Visual items of the current layout pass (also the fetch effect's input).
  const virtualItems = virtualizer.getVirtualItems();

  // §4 qt7.3: the live anchor ref updates on every layout pass, after the
  // restore step above ran (so a same-commit visibility bump first sees the
  // pre-refilter anchor).
  useLayoutEffect(() => {
    const viewport = scrollRef.current;
    const first = virtualItems[0];
    if (!viewport || !first) {
      anchorRef.current = null;
      return;
    }
    const captured = captureAnchor(
      {
        index: first.index,
        line: rowsRef.current.get(first.index)?.line_no ?? null,
      },
      viewport.scrollTop,
    );
    anchorRef.current = captured === null ? null : { index: first.index, anchor: captured };
  }, [virtualItems, rows]);

  /** §4 copy: raw lines (Ctrl+C / Copy) or the Message column. Rows missing
   * from the visible cache are fetched first. Resolves to the copy text. */
  const copy = async (mode: CopyMode): Promise<string> => {
    const indexes = [...selection.selected].sort((a, b) => a - b);
    if (!indexes.length) {
      return "";
    }
    const merged = new Map(rows);
    for (const range of missingRanges(indexes, rowCount, new Set(rows.keys()))) {
      const chunk = await ipc().getRows(range.start, range.end - range.start);
      ChunkPlanner.fromChunk(chunk, range.start).forEach((row, idx) =>
        merged.set(idx, row),
      );
    }
    const selectedRows = indexes
      .map((i) => merged.get(i))
      .filter((row): row is RowDto => row !== undefined);
    const text =
      mode === "raw" ? rawCopyText(selectedRows) : messageCopyText(selectedRows);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Headless/plain-browser contexts may reject the clipboard; the text
      // is still resolved for assertions (the e2e/live stubs read it).
    }
    return text;
  };

  // §4 §8 scroll-to-row: center the given 1-based line in the viewport. The
  // line resolves through the VISIBLE sequence (it shifts under filters),
  // via binary-search probes like every line→index query (qt7.3). A line
  // that is not visible (or past the end) is not scrolled to.
  const scrollToRow = useCallback(
    (lineNo: number): void => {
      void (async () => {
        const viewport = scrollRef.current;
        const index = await resolveLineIndex(lineNo, rowCount, lineAt);
        const half = Math.floor((viewport?.clientHeight ?? 0) / 2);
        if (!viewport || index === null) {
          return;
        }
        // Identical px math to the pre-anchoring helper: index*ROW - h/2,
        // clamped by the anchoring formula; scrollTop only (§4).
        viewport.scrollTop = anchorScrollTop(
          index,
          { line: lineNo, offsetPx: half },
          rowCount,
          viewport.clientHeight,
        );
      })();
    },
    [rowCount, lineAt],
  );

  const viewportInfo = useCallback((): ViewportInfo | null => {
    const viewport = scrollRef.current;
    if (!viewport) {
      return null;
    }
    const live = anchorRef.current;
    return {
      scrollTop: viewport.scrollTop,
      scrollLeft: viewport.scrollLeft,
      anchor: live ? { index: live.index, line: live.anchor.line } : null,
      anchorOffsetPx: live ? live.anchor.offsetPx : 0,
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      scrollToRow,
      copy,
      viewport: viewportInfo,
    }),
    [rowCount, copy, scrollToRow, viewportInfo],
  );

  // §4: Ctrl+C (also Cmd+C on macOS) copies the selection's raw lines.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "c" || e.key === "с") && selection.selected.length) {
        e.preventDefault();
        void copy("raw");
      } else if (e.key === "Escape") {
        setMenuPos(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selection, copy]);

  // Fetch chunks when the visible window moves (and after a chunk resolves).
  // The loop is epoch-aware: a file or visibility epoch bump during an
  // in-flight get_rows invalidates that chunk (it indexes the OLD sequence),
  // so the result is discarded - otherwise stale rows pollute the fresh
  // lines cache and the anchor's binary-search probes resolve off them.
  useLayoutEffect(() => {
    if (rowCount === 0) {
      return;
    }
    const loadNext = () => {
      if (!virtualItems.length || inFlightRef.current) {
        return;
      }
      const first = virtualItems[0].index;
      const last = virtualItems[virtualItems.length - 1].index;
      const ranges = plannerRef.current.plan(first, last, rowCount);
      if (!ranges.length) {
        return;
      }
      inFlightRef.current = true;
      void (async () => {
        try {
          for (const range of ranges) {
            const chunk = await ipc().getRows(range.start, range.end - range.start);
            if (
              epochsRef.current.file !== fileEpoch ||
              epochsRef.current.visibility !== visibilityEpoch
            ) {
              // The epoch moved while this chunk was in flight: its indexes
              // no longer address the current sequence. Drop it (the fresh
              // epoch's fetch effect is already planning its own chunks).
              break;
            }
            setRows((prev) => {
              const next = new Map(prev);
              ChunkPlanner.fromChunk(chunk, range.start).forEach((row, idx) =>
                next.set(idx, row),
              );
              return next;
            });
            plannerRef.current.markLoaded(range.start);
          }
        } catch {
          ranges.forEach((r) => plannerRef.current.markFailed(r.start));
        } finally {
          inFlightRef.current = false;
          const stale =
            epochsRef.current.file !== fileEpoch ||
            epochsRef.current.visibility !== visibilityEpoch;
          if (!stale) {
            loadNext();
          }
        }
      })();
    };
    loadNext();
    // Epochs are deps too: an equal-count file or visibility change resets
    // the planner above but keeps rowCount/virtualItems, so the refetch
    // would otherwise never trigger.
  }, [virtualItems, rowCount, fileEpoch, visibilityEpoch]);

  // §4: horizontal scroll by mouse-wheel tilt only; the wheel handler applies
  // a horizontal delta when it dominates the vertical one. Trackpad two-finger
  // horizontal flicks are treated the same (spec interpretation; §4 rules
  // block trackpad gestures - distinguishing them from wheel tilt is not
  // possible in the webview, so the behavior is unified).
  const onWheel = (e: React.WheelEvent) => {
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
      const viewport = scrollRef.current;
      if (viewport && viewport.scrollWidth > viewport.clientWidth) {
        e.preventDefault();
        viewport.scrollLeft += e.deltaX;
      }
    }
  };

  const onRowActivate = (index: number, e: React.MouseEvent) => {
    // Menu closes on any row interaction; the click kind follows §4:
    // shift = extend from anchor, ctrl/cmd = toggle, plain = select one.
    setMenuPos(null);
    onRowClick(
      index,
      e.shiftKey ? "range" : e.metaKey || e.ctrlKey ? "toggle" : "click",
    );
  };

  const openMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    // §4: the menu is a menu over the selection - empty selection opens it
    // for nothing, so it opens only on a selection.
    if (selection.selected.length) {
      setMenuPos({ x: e.clientX, y: e.clientY });
    }
  };

  const menuCommands: ContextMenuProps = {
    x: 0,
    y: 0,
    // Copy commands; Pin/Unpin and Highlight stay disabled until the pins
    // and highlights epics land (§4) - their handlers are not wired yet.
    onCopy: () => void copy("raw"),
    onCopyMessage: () => void copy("message"),
  };

  return (
    <div
      className="table-scroll"
      ref={scrollRef}
      onWheel={onWheel}
      // Scrolling away or clicking outside the rows closes the menu.
      onScroll={() => setMenuPos(null)}
      onMouseDown={() => setMenuPos(null)}
    >
      <div
        className="table-inner"
        style={{
          // Header row occupies one ROW_HEIGHT at the top; virtual rows slide
          // under the sticky header while scrolling.
          height: virtualizer.getTotalSize() + ROW_HEIGHT_PX,
          paddingTop: ROW_HEIGHT_PX,
        }}
        onContextMenu={rowCount > 0 ? openMenu : undefined}
      >
        <div className="table-header">
          <span className="cell cell-line">Line</span>
          <span className="cell cell-time">Time</span>
          <span className="cell cell-category">Category</span>
          <span className="cell cell-message">Message</span>
        </div>
        {virtualItems.map((vi) => {
          const row = rows.get(vi.index);
          const selected = selection.selected.includes(vi.index);
          return (
            <div
              key={vi.key}
              className={`row${selected ? " selected" : ""}${vi.index % 2 === 1 ? " zebra" : ""}${row ? ` lvl-${row.level}` : ""}`}
              style={{
                position: "absolute",
                transform: `translateY(${vi.start + ROW_HEIGHT_PX}px)`,
                height: ROW_HEIGHT_PX,
              }}
              onClick={(e) => onRowActivate(vi.index, e)}
              onContextMenu={openMenu}
            >
              <span className="cell cell-line">{row ? row.line_no : ""}</span>
              <span className="cell cell-time">{row ? row.time_display : ""}</span>
              <span className="cell cell-category">{row ? row.category : ""}</span>
              <span className="cell cell-message">{row ? row.message : ""}</span>
            </div>
          );
        })}
      </div>
      {menuPos && (
        <div
          className="context-menu-layer"
          style={{ position: "fixed", left: menuPos.x, top: menuPos.y, zIndex: 30 }}
          // The scroll's mousedown-closes rule stops here: releasing the
          // pressed button on a command row must reach the click.
          onMouseDown={(e) => e.stopPropagation()}
        >
          <ContextMenu {...menuCommands} />
        </div>
      )}
    </div>
  );
});
