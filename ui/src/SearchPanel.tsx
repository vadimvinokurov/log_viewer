//! §8 find bar (bead 2wu.1): Chrome-style panel floating at the top-right of
//! the table — input, mutually exclusive Regex | Simple tumblers (both off =
//! plain substring), counter «k / N» / «0 / 0», prev/next, close. Markup,
//! classes and tokens are copied verbatim from docs/UI_DESIGN.html ("Find
//! bar — Ctrl+F, floats top-right"). Presentational: state comes in as
//! props; App wires the console and the global keydown rules.

import { useEffect, useRef, type ReactElement } from "react";
import type { SearchState } from "./state";

export interface SearchPanelProps {
  search: SearchState;
  /** The input changed; the console debounces the recompute (250 ms). */
  onQuery(query: string): void;
  /** A tumbler was clicked: a mode value switches to it, null returns to
   *  plain («both off», bead 2wu.1 spec interpretation). */
  onTumbler(mode: "regex" | "simple" | null): void;
  /** ↓ next match (cyclic). */
  onNext(): void;
  /** ↑ previous match (cyclic). */
  onPrev(): void;
  /** ✕ closes (Esc does the same through the global keydown rules). */
  onClose(): void;
}

/** Counter text: «k / N», k 1-based; none matches «0 / 0». */
export function searchCounter(search: SearchState): string {
  const total = search.positions.length;
  if (search.current === null || search.current < 0 || search.current >= total) {
    return "0 / 0";
  }
  return `${search.current + 1} / ${total}`;
}

export function SearchPanel(props: SearchPanelProps): ReactElement {
  const { search } = props;
  const inputRef = useRef<HTMLInputElement | null>(null);

  // §8: Ctrl+F opens with the focus in the input (also on a reopen).
  useEffect(() => {
    if (search.open) {
      inputRef.current?.focus();
    }
  }, [search.open]);

  return (
    <div className="findbar" role="search">
      <input
        ref={inputRef}
        className="field"
        value={search.query}
        placeholder="Find"
        onChange={(e) => props.onQuery(e.target.value)}
      />
      <span className="cnt">{searchCounter(search)}</span>
      <span
        className={"tg" + (search.mode === "regex" ? " on" : "")}
        role="button"
        tabIndex={0}
        onClick={() => props.onTumbler(search.mode === "regex" ? null : "regex")}
      >
        Regex
      </span>
      <span
        className={"tg" + (search.mode === "simple" ? " on" : "")}
        role="button"
        tabIndex={0}
        onClick={() => props.onTumbler(search.mode === "simple" ? null : "simple")}
      >
        Simple
      </span>
      <span className="ar" role="button" tabIndex={0} onClick={props.onNext} title="Next match (Down)">
        ↓
      </span>
      <span className="ar" role="button" tabIndex={0} onClick={props.onPrev} title="Previous match (Up)">
        ↑
      </span>
      <span className="x" role="button" tabIndex={0} onClick={props.onClose} title="Close (Esc)">
        ✕
      </span>
    </div>
  );
}
