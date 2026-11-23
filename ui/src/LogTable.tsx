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
import { ipc } from "./ipcClient";

export const ROW_HEIGHT_PX = 23; // glyph height + 6 px (§4)

export interface LogTableHandle {
  /** Scroll so that the 1-based line number is centered in the viewport. */
  scrollToRow(lineNo: number): void;
}

interface Props {
  rowCount: number;
}

/**
 * The main table (§4): four columns, fixed 23-px rows, pixel virtualization
 * over millions of rows via chunked get_rows loads. Level colors whole-row
 * text (§3.1); line number, time and uncategorized-message neutrals come
 * from the design tokens. Selection/context menu/copy land in qt7.2.
 */
export const LogTable = forwardRef<LogTableHandle, Props>(function LogTable(
  { rowCount },
  ref,
) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const plannerRef = useRef(new ChunkPlanner());
  const [rows, setRows] = useState<Map<number, RowDto>>(new Map());
  const inFlightRef = useRef(false);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT_PX,
    overscan: 10,
  });

  // New file: throw away the cache, restart chunk planning.
  useEffect(() => {
    plannerRef.current.reset();
    setRows(new Map());
    inFlightRef.current = false;
    if (scrollRef.current && scrollRef.current.scrollTop !== 0) {
      scrollRef.current.scrollTop = 0;
    }
  }, [rowCount]);

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
  }, [virtualItems, rowCount]);

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
    }),
    [rowCount],
  );

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

  return (
    <div className="table-scroll" ref={scrollRef} onWheel={onWheel}>
      <div
        className="table-inner"
        style={{
          // Header row occupies one ROW_HEIGHT at the top; virtual rows slide
          // under the sticky header while scrolling.
          height: virtualizer.getTotalSize() + ROW_HEIGHT_PX,
          paddingTop: ROW_HEIGHT_PX,
        }}
      >
        <div className="table-header">
          <span className="cell cell-line">Line</span>
          <span className="cell cell-time">Time</span>
          <span className="cell cell-category">Category</span>
          <span className="cell cell-message">Message</span>
        </div>
        {virtualItems.map((vi) => {
          const row = rows.get(vi.index);
          return (
            <div
              key={vi.key}
              className={`row${vi.index % 2 === 1 ? " zebra" : ""}${row ? ` lvl-${row.level}` : ""}`}
              style={{
                position: "absolute",
                transform: `translateY(${vi.start + ROW_HEIGHT_PX}px)`,
                height: ROW_HEIGHT_PX,
              }}
            >
              <span className="cell cell-line">{row ? row.line_no : ""}</span>
              <span className="cell cell-time">{row ? row.time_display : ""}</span>
              <span className="cell cell-category">{row ? row.category : ""}</span>
              <span className="cell cell-message">{row ? row.message : ""}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
});
