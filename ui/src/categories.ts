//! Categories tree model for the side panel (FUNCTIONAL_SPEC §10, task
//! log_viewer2-rhl.2). Pure logic, no React: the reducer/console (state.ts)
//! wires these helpers to the raw IPC shapes
//! (`categories: {path, count}[]` from the load result and the
//! `categories_enabled` whitelist from the snapshot; normalization lives in
//! ipcClient.ts). The tri-state derives from the whitelist on every render —
//! it is never stored.

/** One node of the categories tree; mirrors the engine's CategoryNode
 * (crates/logviewer-core/src/categories.rs). */
export interface UiCategoryNode {
  name: string;
  path: string;
  count: number;
  children: UiCategoryNode[];
}

/** Byte-order sort (UTF-16 code units, matching Rust byte order for the
 * BMP-heavy category names): deterministic across rebuilds. */
function byName(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** The ancestor prefixes of `path` (e.g. "app/main/db" -> "app", "app/main").
 * The engine's category_allowed requires every prefix to be enabled too. */
function prefixPath(path: string): string[] {
  const prefixes: string[] = [];
  let i = path.indexOf("/");
  while (i !== -1) {
    prefixes.push(path.slice(0, i));
    i = path.indexOf("/", i + 1);
  }
  return prefixes;
}

/** Build the tree from the flat {path, count} load result. Synthetic root
 * with an empty name/path; counts land on the node of the exact path
 * (node count = rows with exactly this path, engine categories.rs
 * semantics), zero for interior paths never logged directly. The
 * "uncategorized" path is handled like any other node here. */
export function buildTree(flat: readonly { path: string; count: number }[]): UiCategoryNode {
  type Trie = { count: number; children: Map<string, Trie> };
  const rootTrie: Trie = { count: 0, children: new Map() };
  for (const { path, count } of flat) {
    // spec interpretation: `/`-segments are kept verbatim (empty segments
    // included), mirroring categories.rs; duplicate paths sum their counts.
    let node: Trie = rootTrie;
    const segments = path.split("/");
    for (const segment of segments) {
      let child = node.children.get(segment);
      if (!child) {
        child = { count: 0, children: new Map() };
        node.children.set(segment, child);
      }
      node = child;
    }
    node.count += count;
  }

  const materialize = (trie: Trie, parentPath: string): UiCategoryNode[] => {
    const nodes: UiCategoryNode[] = [];
    for (const [name, child] of [...trie.children].sort(([a], [b]) => byName(a, b))) {
      const path = parentPath === "" ? name : `${parentPath}/${name}`;
      nodes.push({
        name,
        path,
        count: child.count,
        children: materialize(child, path),
      });
    }
    return nodes;
  };

  return { name: "", path: "", count: 0, children: materialize(rootTrie, "") };
}

export type CheckState = "on" | "partial" | "off";

/** Tri-state for one node against the enabled whitelist, mirroring the
 * engine rule (visibility = the exact path AND every ancestor prefix
 * enabled):
 * - node itself or an ancestor missing -> "partial" when any descendant
 *   path is still whitelisted (a leftover subtree), else "off";
 * - node itself fully enabled -> "on" when every node of the subtree is
 *   enabled too, "partial" when only part of it is. */
export function nodeCheck(enabled: readonly string[], node: UiCategoryNode): CheckState {
  const whitelist = new Set(enabled);
  const selfEnabled = whitelist.has(node.path) && prefixPath(node.path).every((p) => whitelist.has(p));
  const anyDescendantEnabled = (node: UiCategoryNode): boolean =>
    node.children.some((c) => whitelist.has(c.path) || anyDescendantEnabled(c));
  const allEnabled = (node: UiCategoryNode): boolean =>
    whitelist.has(node.path) && node.children.every(allEnabled);

  if (selfEnabled) {
    return node.children.every(allEnabled) ? "on" : "partial";
  }
  return anyDescendantEnabled(node) ? "partial" : "off";
}

/** Toggle propagation as a differential for raw `set_category_enabled`
 * calls: `on = true` adds the toggled paths, all their descendant paths and
 * every ancestor prefix (§10 up-propagation on ENABLE only — the prefixes
 * must be enabled or the rows stay invisible); `on = false` removes the
 * toggled paths and their descendants and never touches ancestors (a parent
 * may turn partial). A path ending up in both sets would fight itself
 * downstream, so the invariant is asserted. Returns sorted, duplicate-free
 * lists. */
export function propagateToggle(
  paths: readonly string[],
  node: UiCategoryNode,
  on: boolean,
): { add: string[]; remove: string[] } {
  const treePaths = new Set<string>();
  const collect = (n: UiCategoryNode): void => {
    treePaths.add(n.path);
    for (const child of n.children) {
      collect(child);
    }
  };
  collect(node);

  const add = new Set<string>();
  const remove = new Set<string>();
  for (const path of paths) {
    if (on) {
      add.add(path);
      // Ancestor prefixes go in unconditionally, mirroring toggleAll: the
      // engine needs every prefix enabled for the rows to be visible.
      for (const prefix of prefixPath(path)) {
        add.add(prefix);
      }
      if (treePaths.has(path)) {
        addSubtreePaths(node, path).forEach((p) => add.add(p));
      }
    } else {
      remove.add(path);
      if (treePaths.has(path)) {
        addSubtreePaths(node, path).forEach((p) => remove.add(p));
      }
    }
  }
  for (const path of remove) {
    add.delete(path);
  }
  for (const path of add) {
    remove.delete(path);
  }
  // Invariant: the differential must never fight itself.
  if (add.size > 0 && remove.size > 0) {
    for (const path of add) {
      if (remove.has(path)) {
        throw new Error(`propagateToggle conflict: ${path} in both add and remove`);
      }
    }
  }
  const sorted = (set: Set<string>): string[] => [...set].sort(byName);
  return { add: sorted(add), remove: sorted(remove) };
}

/** All tree paths at or below `path` (including `path` itself), deduped. */
function addSubtreePaths(node: UiCategoryNode, path: string): string[] {
  const found = findNode(node, path);
  if (!found) {
    return [];
  }
  const paths: string[] = [];
  const collect = (n: UiCategoryNode): void => {
    paths.push(n.path);
    for (const child of n.children) {
      collect(child);
    }
  };
  collect(found);
  return paths;
}

function findNode(node: UiCategoryNode, path: string): UiCategoryNode | null {
  const queue = [node];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) {
      continue;
    }
    if (current.path === path) {
      return current;
    }
    queue.push(...current.children);
  }
  return null;
}

/** All-checkbox differential: on adds every flat path plus the ancestor
 * prefixes (the flat list holds observed paths only — without the prefixes
 * the engine's category_allowed would keep nested rows invisible), off
 * removes the same set. */
export function toggleAll(
  flat: readonly { path: string }[],
  on: boolean,
): { add: string[]; remove: string[] } {
  const paths = new Set<string>();
  for (const { path } of flat) {
    paths.add(path);
    for (const prefix of prefixPath(path)) {
      paths.add(prefix);
    }
  }
  const sorted = [...paths].sort(byName);
  return on ? { add: sorted, remove: [] } : { add: [], remove: sorted };
}

/** Tree search (§10): a node is visible when its name matches the
 * lowercased query, or any descendant matches (the matching branches stay
 * linked to the root through their ancestor chain). An empty query returns
 * an empty set, meaning "no search active" — the UI shows everything. */
export function visibleUnderSearch(node: UiCategoryNode, query: string): Set<string> {
  const visible = new Set<string>();
  if (query === "") {
    return visible;
  }
  const needle = query.toLowerCase();
  const mark = (n: UiCategoryNode): boolean => {
    // Must not short-circuit: every branch is examined even when one child
    // already matched.
    let descendantMatched = false;
    for (const child of n.children) {
      if (mark(child)) {
        descendantMatched = true;
      }
    }
    if (n.name.toLowerCase().includes(needle) || descendantMatched) {
      visible.add(n.path);
      return true;
    }
    return false;
  };
  // The synthetic root is the container, not a row: never included.
  for (const child of node.children) {
    mark(child);
  }
  return visible;
}

// expandTargets (§10 expanded set for the collapse/expand-all button) was
// removed 2026-11-25: the shell installs collapse/expand targets through
// expandedForToggleAll in state.ts (collapse closes everything), this copy
// carried the superseded keepRoots semantics.
