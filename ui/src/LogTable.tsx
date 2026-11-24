import {
  forwardRef,
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

export const ROW_HEIGHT_PX = 23; // glyph height + 6 px (§4)

export interface LogTableHandle {
  /** Scroll so that the 1-based line number is centered in the viewport. */
  scrollToRow(lineNo: number): void;
  /** Copy the selection (raw lines or Message column, §4); resolves to
   * the text that was put on the clipboard. */
  copy(mode: CopyMode): Promise<string>;
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
    setRows(new Map());
    inFlightRef.current = false;
    setMenuPos(null);
    if (scrollRef.current && scrollRef.current.scrollTop !== 0) {
      scrollRef.current.scrollTop = 0;
    }
  }, [fileEpoch]);

  // Visibility change (§7): get_rows indexes the visible sequence, so the
  // chunk cache and rows map refill; scrollTop stays — anchoring the
  // viewport on filter changes is qt7.3's job (§4, contract dsq.3). The
  // signal is an epoch, not rowCount: equal-count changes must still refill.
  useLayoutEffect(() => {
    plannerRef.current.reset();
    setRows(new Map());
    inFlightRef.current = false;
  }, [visibilityEpoch]);

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

  useImperativeHandle(
    ref,
    () => ({
      scrollToRow(lineNo: number) {
        const i = lineNo - 1;
        const viewport = scrollRef.current;
        if (!viewport) {
          return;
        }
        const target = i * ROW_HEIGHT_PX - Math.floor(viewport.clientHeight / 2);
        // Horizontal position is preserved by setting scrollTop only (§4).
        viewport.scrollTop = Math.max(0, Math.min(target, rowCount * ROW_HEIGHT_PX));
      },
      copy,
    }),
    [rowCount, copy],
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
  const virtualItems = virtualizer.getVirtualItems();
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
          loadNext();
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
