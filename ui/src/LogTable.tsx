import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ChunkPlanner, type RowDto } from "./table";
import { missingRanges, messageCopyText, rawCopyText } from "./selection";
import type { SelectionState } from "./selection";
import type { PinItem } from "./pins";
import { pinMenuState } from "./pins";
import type { ContextMenuProps } from "./ContextMenu";
import { ContextMenu } from "./ContextMenu";
import { ipc } from "./ipcClient";
import { console_ } from "./uiConsole";
import type { CopyMode } from "./uiConsole";
import { overlaySegments, type HighlightSpan } from "./highlights";
import {
  ROW_HEIGHT_PX,
  anchorForChange,
  anchorScrollTop,
  resolveLineIndex,
  type Anchor,
  type ViewportInfo,
} from "./viewportAnchoring";
import {
  columnGridTemplate,
  columnTotal,
  effectiveWidths,
  type ColumnKey,
  type ColumnWidths,
} from "./columnWidths.ts";
// The row height lives in the pure anchoring module now (§4); re-exported
// for the existing import sites.
export { ROW_HEIGHT_PX };

export interface LogTableHandle {
  /** Scroll so that the 1-based line number is centered in the viewport. */
  scrollToRow(lineNo: number): void;
  /** Copy the selection (raw lines or Message column, §4); resolves to
   * the text that was put on the clipboard. */
  copy(mode: CopyMode): Promise<string>;
  /** Viewport scroll state incl. the live anchor (§4, qt7.3): identity and
   * offset of the next anchor row — the first visible row, or the on-screen
   * selection pivot (2026-11-25). Assertions use this text RPC, never the
   * DOM. Null without a mounted viewport. */
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
  /** §12 snapshot pin list: drives the context menu's §4 Pin/Unpin
   *  presence (evaluation lives in the pins.ts pure module). */
  pins: PinItem[];
  /** USER column widths (design 2026-11-25-column-resize); the effective
   *  Message width is computed here from the measured viewport. */
  columnWidths: ColumnWidths;
  /** Drag on a header border: set one column's user width (live resize). */
  onColumnSet(key: ColumnKey, px: number): void;
  /** Drag end: persist the widths fire-and-forget. */
  onColumnCommit(): void;
  /** Double-click on a header border: reset to the §4 default. */
  onColumnReset(key: ColumnKey): void;
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
  { rowCount, fileEpoch, visibilityEpoch, selection, pins, columnWidths, onColumnSet, onColumnCommit, onColumnReset, onRowClick },
  ref,
) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const plannerRef = useRef(new ChunkPlanner());
  const [rows, setRows] = useState<Map<number, RowDto>>(new Map());
  /** §9 (exx.2): the message spans per visible index, kept beside the row
   *  cache (the rows DTO is the table.ts shape, which is outside this
   *  task's file list — the spans travel through this parallel map and are
   *  reset with the rows at every epoch, exactly like the row cache). */
  const [spans, setSpans] = useState<Map<number, HighlightSpan[]>>(new Map());
  const inFlightRef = useRef(false);
  // Live mirror of the rows cache for callbacks that must not re-create
  // across renders (the line probes below, §4 qt7.3).
  const rowsRef = useRef<Map<number, RowDto>>(rows);
  useLayoutEffect(() => {
    rowsRef.current = rows;
  }, [rows]);
  // Live anchor: identity and captured offset of the anchor row for the next
  // visibility change — the first visible row, or the selection pivot while
  // it is on screen (§4/§7, 2026-11-25 revision: the selected row must not
  // shift when filters/categories change).
  interface LiveAnchor {
    index: number;
    anchor: Anchor;
  }
  const anchorRef = useRef<LiveAnchor | null>(null);
  // The pivot's 1-based line at selection time (§7 remap input): file line
  // numbers survive every visibility change, so this stays valid even while
  // the rows cache is cleared and refilled mid-mutation — the capture reads
  // the pivot line from here instead of a possibly-stale pivot INDEX.
  const pivotLineRef = useRef<number | null>(null);
  useLayoutEffect(() => {
    const pivot = selection.anchor;
    pivotLineRef.current =
      pivot === null ? null : rowsRef.current.get(pivot)?.line_no ?? null;
  }, [selection]);
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

  // Viewport width for the effective column widths (design
  // 2026-11-25-column-resize): a ResizeObserver keeps it live — window
  // resizes and the side panel both change the table's viewport width.
  const [vw, setVw] = useState(0);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) {
      return;
    }
    setVw(el.clientWidth);
    const ro = new ResizeObserver(() => setVw(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const effective = effectiveWidths(columnWidths, vw);

  /** Drag one header border (design 2026-11-25-column-resize): listeners
   *  live on the WINDOW so a mouseup outside the webview still ends the
   *  drag; mouseup commits the widths (fire-and-forget persist). The drag
   *  anchors on the VISIBLE (effective) width — review finding 2: for
   *  Message, anchoring on the hidden user width builds a dead zone the
   *  handle must grow out of before it visibly moves again. */
  const startResize = (key: ColumnKey, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const start = effective[key];
    const move = (ev: MouseEvent) =>
      onColumnSet(key, start + (ev.clientX - startX));
    const up = () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
      onColumnCommit();
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

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
    setSpans(new Map());
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
    setSpans(new Map());
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
        // The probe's spans travel with it (exx.2; already JS indexes from
        // the ipc adapter's normalization).
        setSpans((prev) => new Map(prev).set(index, raw.spans ?? []));
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

  // §4/§7: the live anchor ref updates on every layout pass, after the
  // restore step above ran (so a same-commit visibility bump first sees the
  // pre-refilter anchor). With a selection pivot on screen the anchor row is
  // the pivot (2026-11-25 revision); the cache-consistency check
  // (cached line at the pivot index must equal the pivot line captured at
  // selection time) makes a stale mid-refetch pivot index fall back to the
  // top row rather than anchor a different row by accident.
  useLayoutEffect(() => {
    const viewport = scrollRef.current;
    const first = virtualItems[0];
    if (!viewport || !first) {
      anchorRef.current = null;
      return;
    }
    const pivot =
      pivotLineRef.current !== null &&
      selection.anchor !== null &&
      rowsRef.current.get(selection.anchor)?.line_no === pivotLineRef.current
        ? { index: selection.anchor, line: pivotLineRef.current }
        : null;
    anchorRef.current = anchorForChange(
      {
        index: first.index,
        line: rowsRef.current.get(first.index)?.line_no ?? null,
      },
      pivot,
      viewport.scrollTop,
      viewport.clientHeight,
    );
  }, [virtualItems, rows, selection]);

  /** §4 copy: raw lines (Ctrl+C / Copy) or the Message column. Rows missing
   * from the visible cache are fetched first. Resolves to the copy text. */
  const copy = async (mode: CopyMode): Promise<string> => {
    const indexes = [...selection.selected].sort((a, b) => a - b);
    if (!indexes.length) {
      return "";
    }
    const merged = await resolveRows(indexes);
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

  /** Visible rows by index for a set of indexes: the cache plus the missing
   *  ranges fetched in one get_rows call each (shared by copy and the §4
   *  menu's pin evaluation). */
  const resolveRows = useCallback(
    async (indexes: number[]): Promise<Map<number, RowDto>> => {
      const merged = new Map(rows);
      for (const range of missingRanges(indexes, rowCount, new Set(rows.keys()))) {
        const chunk = await ipc().getRows(range.start, range.end - range.start);
        ChunkPlanner.fromChunk(chunk, range.start).forEach((row, idx) =>
          merged.set(idx, row),
        );
      }
      return merged;
    },
    [rows, rowCount],
  );

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
            // The chunk's spans land beside the rows (exx.2): the adapter
            // already converted the byte offsets to JS string indexes.
            setSpans((prev) => {
              const next = new Map(prev);
              chunk.forEach((row, offset) =>
                next.set(range.start + offset, row.spans ?? []),
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
    // for nothing, so it opens only on a selection. The pin evaluation is
    // reset with the menu: a stale state from a previous open would paint
    // wrong presence for one frame before the probes resolve.
    if (selection.selected.length) {
      setMenuPin({ canPin: false, canUnpin: false, lines: [] });
      setMenuPos({ x: e.clientX, y: e.clientY });
    }
  };

  // §4 q1f.1: menu Pin/Unpin presence + targets, evaluated from the rows
  // cache (missing selected rows load via one get_rows call each, like
  // copy) against the snapshot's pin list — the pure decision lives in
  // pins.ts. The evaluation is async (probes), so the menu opens with the
  // not-yet-evaluated default (Pin light on an unvisited selection, Unpin
  // dim) and updates when the probes resolve. Menu interactions close it
  // and selection is fixed while it stands, so [menuPos] is the full input.
  const [menuPin, setMenuPin] = useState({ canPin: false, canUnpin: false, lines: [] as number[] });
  useEffect(() => {
    if (!menuPos || selection.selected.length === 0) {
      return;
    }
    let cancelled = false;
    void (async () => {
      const indexes = [...selection.selected].sort((a, b) => a - b);
      const merged = await resolveRows(indexes);
      if (cancelled) {
        return;
      }
      const selectedRows = indexes
        .map((i) => merged.get(i))
        .filter((row): row is RowDto => row !== undefined)
        .map((row) => ({ line: row.line_no, raw: row.raw }));
      setMenuPin({
        ...pinMenuState(pins, selectedRows),
        lines: selectedRows.map((r) => r.line),
      });
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [menuPos]);

  /** §9 Message cell content (exx.2): with spans, the text is cut at the
   *  segment boundaries (overlaySegments composes the stacked translucent
   *  layers) and every matched range renders its rectangle BEHIND the text;
   *  the level tint stays underneath on the row (the marks carry no text
   *  color, color inherit). The plain path avoids per-cell work for the
   *  overwhelmingly common span-less case. */
  const renderMessage = (index: number, row: RowDto | undefined): ReactNode => {
    if (!row) {
      return "";
    }
    const rowSpans = spans.get(index);
    if (!rowSpans || rowSpans.length === 0) {
      return row.message;
    }
    const segments = overlaySegments(row.message.length, rowSpans);
    if (segments.length === 0) {
      return row.message;
    }
    const parts: ReactNode[] = [];
    let cursor = 0;
    segments.forEach((segment, i) => {
      if (segment.start > cursor) {
        parts.push(row.message.slice(cursor, segment.start));
      }
      parts.push(
        <span
          key={i}
          data-message-mark={i}
          style={{
            background: segment.background,
            color: "inherit",
            borderRadius: 2,
          }}
        >
          {row.message.slice(segment.start, segment.start + segment.len)}
        </span>,
      );
      cursor = segment.start + segment.len;
    });
    parts.push(row.message.slice(cursor));
    return parts;
  };

  const menuCommands: ContextMenuProps = {    x: 0,
    y: 0,
    // Copy commands. §4 Pin/Unpin are live since q1f.1: the presence comes
    // from the snapshot pin list, the handlers route to the console (one
    // mutating critical section per command). Highlight stays dim until the
    // highlights epic lands (§4).
    onCopy: () => void copy("raw"),
    onCopyMessage: () => void copy("message"),
    canPin: menuPin.canPin,
    canUnpin: menuPin.canUnpin,
    onPin: menuPin.canPin
      ? () => {
          setMenuPos(null);
          void console_.pinSelected();
        }
      : undefined,
    onUnpin: menuPin.canUnpin
      ? () => {
          setMenuPos(null);
          void console_.unpinSelected(menuPin.lines);
        }
      : undefined,
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
          // The extra ROW at the end is the under-header slack: virtual rows
          // render at +ROW_HEIGHT (they slide under the sticky header) and
          // must fill the viewport down to the last band. The padding that
          // used to "reserve" the header row above sat in flow BEFORE the
          // sticky header and pushed it one row down: at scrollTop=0 the
          // header showed a row-height gap above and covered row 0 (abspos
          // rows are unaffected by the padding — 2026-11-25 top-gap bug).
          height: virtualizer.getTotalSize() + ROW_HEIGHT_PX,
          // Resizable columns (design 2026-11-25-column-resize): the inner
          // layer carries the scroll width; when the effective widths fit
          // the viewport, min-width below the width leaves the block at
          // 100% (no horizontal overflow).
          minWidth: columnTotal(effective),
        }}
        onContextMenu={rowCount > 0 ? openMenu : undefined}
      >
        <div
          className="table-header"
          style={{
            gridTemplateColumns: columnGridTemplate(effective),
            width: columnTotal(effective),
          }}
        >
          {([["line", "Line"], ["time", "Time"], ["category", "Category"], ["message", "Message"]] as const).map(
            ([key, label]) => (
              <span key={key} className={`cell cell-${key}`}>
                {label}
                <span
                  data-col-resizer={key}
                  className="cell-resizer"
                  onMouseDown={(e) => startResize(key, e)}
                  onDoubleClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onColumnReset(key);
                  }}
                />
              </span>
            ),
          )}
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
                // Same template as the header (design 2026-11-25-column-resize).
                gridTemplateColumns: columnGridTemplate(effective),
                width: columnTotal(effective),
              }}
              onClick={(e) => onRowActivate(vi.index, e)}
              onContextMenu={openMenu}
            >
              <span className="cell cell-line">{row ? row.line_no : ""}</span>
              <span className="cell cell-time">{row ? row.time_display : ""}</span>
              <span className="cell cell-category">{row ? row.category : ""}</span>
              <span className="cell cell-message">{renderMessage(vi.index, row)}</span>
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
