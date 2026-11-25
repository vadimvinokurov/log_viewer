//! Categories tab of the side panel (FUNCTIONAL_SPEC §10, bead rhl.2):
//! All tri-state checkbox on top, tree of checkboxes with counts, search
//! input (matching branches fully expanded while active) and the
//! expand/collapse-all fold button. Presentational: the decisions live in
//! ui/src/categories.ts — the tri-state derives from the engine whitelist
//! on every render, it is never stored.

import type { ReactElement, ReactNode } from "react";
import { nodeCheck, visibleUnderSearch, type CheckState, type UiCategoryNode } from "./categories";

export interface CategoriesTabProps {
  /** The loaded file's tree (buildTree over the flat load result). */
  tree: UiCategoryNode;
  /** The loaded file's flat {path, count} list (All row count + check). */
  flat: readonly { path: string; count: number }[];
  /** The snapshot's categories_enabled whitelist (raw order kept). */
  enabled: readonly string[];
  /** §10 tree search; "" = no search active. */
  search: string;
  /** Expanded node paths (panel slice). */
  expanded: readonly string[];
  /** Node checkbox flipped; `on` is the checkbox's new state. */
  onToggle(path: string, on: boolean): void;
  /** All checkbox flipped. */
  onToggleAll(on: boolean): void;
  /** Search input changed. */
  onSearch(query: string): void;
  /** Fold button: expand-all / collapse-all-except-roots (§10 action 5). */
  onExpandAll(expand: boolean): void;
  /** A node's twisty flipped. */
  onToggleExpand(path: string): void;
}

function treePaths(node: UiCategoryNode): string[] {
  const paths: string[] = [];
  const collect = (n: UiCategoryNode): void => {
    paths.push(n.path);
    for (const child of n.children) {
      collect(child);
    }
  };
  for (const child of node.children) {
    collect(child);
  }
  return paths;
}

/** "on" when every observed path is whitelisted, "off" when none is,
 *  "partial" otherwise — the All checkbox derives like any other node. */
function allCheck(flat: readonly { path: string }[], enabled: readonly string[]): CheckState {
  const whitelist = new Set(enabled);
  let any = false;
  let all = flat.length > 0;
  for (const { path } of flat) {
    if (whitelist.has(path)) {
      any = true;
    } else {
      all = false;
    }
  }
  return !any ? "off" : all ? "on" : "partial";
}

function checkbox(check: CheckState, onClick: () => void): ReactElement {
  const cls = check === "off" ? "cb" : check === "partial" ? "cb part" : "cb on";
  return (
    <input
      type="checkbox"
      className={cls}
      title={check}
      checked={check === "on"}
      /* readOnly: the checkbox is state-derived, never internally mutable —
         clicks flow through onToggle (mock 1d80977: native checkboxes). */
      readOnly
      /* native indeterminate mark for the partially-enabled parents; the
         className keeps "part" so tests keep the class-based API. */
      ref={(el) => {
        if (el) {
          el.indeterminate = check === "partial";
        }
      }}
      onClick={onClick}
    />
  );
}

/** The matched substring renders bold-accent like the UI_DESIGN search
 *  frame (<b>db</b>/pool); a name matched via a descendant renders plain. */
function nameLabel(name: string, search: string): ReactNode {
  if (search === "") {
    return name;
  }
  const index = name.toLowerCase().indexOf(search.toLowerCase());
  if (index === -1) {
    return name;
  }
  return (
    <>
      {name.slice(0, index)}
      <b>{name.slice(index, index + search.length)}</b>
      {name.slice(index + search.length)}
    </>
  );
}

export function CategoriesTab(props: CategoriesTabProps): ReactElement {
  const {
    tree,
    flat,
    enabled,
    search,
    expanded,
    onToggle,
    onToggleAll,
    onSearch,
    onExpandAll,
    onToggleExpand,
  } = props;

  // §10: a node is visible when it matches or has a matching descendant;
  // empty query = no search active (everything shows).
  const visible = search === "" ? null : visibleUnderSearch(tree, search);
  const expandedSet = new Set(expanded);
  // §10: while the search is active, the tree expands fully.
  const isOpen = (path: string): boolean => (search === "" ? expandedSet.has(path) : true);

  const paths = treePaths(tree);
  const everythingExpanded = paths.length > 0 && paths.every((p) => isOpen(p));
  const total = flat.reduce((sum, { count }) => sum + count, 0);
  const allState = allCheck(flat, enabled);

  const renderNodes = (nodes: readonly UiCategoryNode[], depth: number): ReactElement[] =>
    nodes.flatMap((node) => {
      if (visible !== null && !visible.has(node.path)) {
        return [];
      }
      const check = nodeCheck(enabled, node);
      const hasChildren = node.children.length > 0;
      const expandedHere = hasChildren && isOpen(node.path);
      const row = (
        <div
          key={node.path}
          className={`row${check === "off" ? " off" : ""}`}
          data-path={node.path}
          style={{ paddingLeft: 12 + depth * 14 }}
        >
          <span
            className="tw"
            style={{ cursor: hasChildren ? "pointer" : "default" }}
            onClick={hasChildren ? () => onToggleExpand(node.path) : undefined}
          >
            {hasChildren ? (expandedHere ? "▾" : "▸") : "·"}
          </span>
          {checkbox(check, () => onToggle(node.path, check !== "on"))}
          <span className="nm">{nameLabel(node.name, search)}</span>
          <span className="ct">{node.count.toLocaleString("en-US")}</span>
        </div>
      );
      return expandedHere ? [row, ...renderNodes(node.children, depth + 1)] : [row];
    });

  return (
    <>
      <div className="tree-search">
        <input
          type="text"
          placeholder="Filter tree"
          aria-label="Filter tree"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
        />
        <span
          className="fold"
          role="button"
          tabIndex={0}
          aria-label={everythingExpanded ? "Collapse all" : "Expand all"}
          onClick={() => onExpandAll(!everythingExpanded)}
        >
          {/* native chevron glyph (2026-11-25 mock decision), not a text
              triangle: the mono "▾" read as a cramped box inside the 24px
              chrome button */}
          <svg width={13} height={8} viewBox="0 0 9 6" aria-hidden="true">
            <path
              d="M1 1l3.5 3.5L8 1"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </div>
      <div className="tree" role="tree" aria-label="Categories">
        <div className="row" data-path="">
          <span className="tw">▾</span>
          {checkbox(allState, () => onToggleAll(allState !== "on"))}
          <span className="nm">All</span>
          <span className="ct">{total.toLocaleString("en-US")}</span>
        </div>
        {renderNodes(tree.children, 0)}
      </div>
    </>
  );
}
