# rhl.2 — categories tab + side-panel shell: design (final)

Spec: §10 (tree of checkboxes + counts, All on top, tri-state, propagation
down+up, disabling hides node rows, search shows only matching branches with
full expansion, expand/collapse-all except root nodes, expansion survives
rebuilds), §10.1 (panel tabs Categories|Filters|Highlights|Pinned, Ctrl+B
collapse, draggable splitter). The side-panel chrome is THIS task's scope
(decision recorded on dsq.3).

## Raw IPC — nothing new

- `set_category_enabled(path, on)` and snapshot `categories_enabled` exist (dsq.3).
- The flat `{path, count}` list already arrives in the load result; the UI
  rebuilds the tree from it (path segments split by `/`, deterministic sort).
  Node count = rows with exactly this path (core `categories.rs` semantics).

## Pure module `ui/src/categories.ts` (+ vitest) — Agent A deliverable

```ts
export interface UiCategoryNode { name: string; path: string; count: number; children: UiCategoryNode[] }
export function buildTree(flat: { path: string; count: number }[]): UiCategoryNode;  // synthetic root, "" path
export type CheckState = "on" | "partial" | "off";
export function nodeCheck(enabled: string[], node: UiCategoryNode): CheckState;
  // mirrors the engine's rule (exact path AND every ancestor present):
  // itself-or-ancestor missing -> any enabled descendant makes "partial", else "off";
  // present -> all-checkable subtree enabled -> "on", some -> "partial", none -> "off"
export function propagateToggle(paths: string[], node: UiCategoryNode, on: boolean): { add: string[]; remove: string[] };
  // down: node + all descendant paths; up: ancestors become partial-managed —
  // enabling a node adds every ancestor prefix too (rows stay visible);
  // disabling a node never auto-clears ancestors (parent may turn partial).
export function toggleAll(flat: { path: string }[], on: boolean): { add: string[]; remove: string[] };
  // All checkbox: on -> every path; off -> nothing stays checked.
export function visibleUnderSearch(node: UiCategoryNode, query: string): Set<string>;
  // lowercase substring: a node is visible when itself or any descendant matches;
  // empty query -> empty set (meaning «no search active»).
export function expandTargets(allPaths: string[], expand: boolean, keepRoots: boolean): string[];
  // expand-all / collapse-all-except-roots support.
```

## Reducer + console (Agent B)

- New UI state slice: `panel { open: boolean; tab: "categories" | "filters" |
  "highlights" | "pinned"; width: number; search: string; expanded: string[] }`.
  Defaults: open, width 220 (UI_DESIGN), search "", expanded = [top-level paths]
  at load (children collapsed — spec interpretation documented).
- On load-success the expanded set resets to defaults (expansion does NOT
  survive file reload, §10 action 5); it survives every other rebuild.
- Console actions: `toggleCategory(path, on)` (applies add/remove from
  propagateToggle via set_category_enabled, refetches snapshot), `setAllCategories(on)`,
  `togglePanel()`, `setPanelTab(tab)`, `setPanelWidth(px)`, `setCategorySearch(q)`,
  `expandAllCategories(expand)` (expandTargets semantics), `toggleExpansion(path)`.
- `__headless` mirrors the actions; ConsoleSnapshot gains `panel`.

## Components (Agent B)

- `SidePanel.tsx`: §10.1 tab strip (4 tabs), content switch. Categories and
  Filters render live (console state); Highlights/Pinned render a muted
  placeholder until exx.2/q1f.1 land. Ctrl+B toggles (global keydown);
  splitter drags width (mousedown+mousemove, min 180 / max 480 px clamp —
  spec interpretation); closed by default? — open (§10.1 panel is part of the
  working surface).
- `CategoriesTab.tsx`: All checkbox (tri-state), tree rows from the design
  reference (docs/UI_DESIGN.html), search input, expand/collapse-all button;
  node row = tri-state checkbox + count + name; disabled rows dim.
- Styling: copy classes/tokens verbatim from docs/UI_DESIGN.html; inline styles
  if the reference styles live there.

## e2e + gates (Agent B)

- New states: panel-open tree, propagated-uncheck state (subtree hidden),
  search-filtered state; goldens committed; numbers asserted via `__headless`.
- Full gates from ui/; design oracle from root (categories pair if the
  reference mock provides one).

## Spec interpretations to document in code

- Tri-state derives from the engine whitelist (`nodeCheck`), never stored.
- Up-propagation on ENABLE only (ancestors must be enabled for visibility);
  on DISABLE ancestors stay (they may hold enabled children or be partial).
- Default tree shows root-level nodes expanded, children collapsed.
- Panel width bounds 180–480 px; placeholder text for not-yet-implemented tabs.
