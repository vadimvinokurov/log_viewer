//! Tests for the categories tree model (FUNCTIONAL_SPEC §10): buildTree from
//! the flat {path, count} load result, tri-state checks mirroring the engine's
//! category_allowed rule (exact path AND every ancestor prefix enabled),
//! toggle propagation as a {add, remove} differential, the All checkbox, tree
//! search visibility and expand/collapse targets. Pure logic only.

import { describe, expect, it } from "vitest";
import {
  buildTree,
  expandTargets,
  nodeCheck,
  propagateToggle,
  toggleAll,
  type UiCategoryNode,
  visibleUnderSearch,
} from "./categories";

// ---------------------------------------------------------------- fixtures

/** Flat list shaped like the load result: observed paths only (no
 * zero-count interior nodes), sorted by path, "uncategorized" as a regular
 * path. Counts are distinctive so own-count assertions are unambiguous. */
const FLAT = [
  { path: "app", count: 1 },
  { path: "app/main", count: 2 },
  { path: "app/main/db", count: 3 },
  { path: "app/main/net", count: 4 },
  { path: "B/tree", count: 6 },
  { path: "dbx", count: 5 },
  { path: "uncategorized", count: 7 },
];

/** Node lookup by full path (throws when absent so tests fail loudly). */
function node(tree: UiCategoryNode, path: string): UiCategoryNode {
  if (path === "") {
    return tree;
  }
  const found = find(tree, path);
  if (!found) {
    throw new Error(`no node ${path} in fixture tree`);
  }
  return found;
}

function find(tree: UiCategoryNode, path: string): UiCategoryNode | null {
  for (const child of tree.children) {
    if (child.path === path) {
      return child;
    }
    const deep = find(child, path);
    if (deep) {
      return deep;
    }
  }
  return null;
}

const TREE = buildTree(FLAT);
/** What the All checkbox installs: flat paths plus the prefixes the engine
 * needs (toggleAll semantics). */
const ALL_ENABLED = [
  "B",
  "B/tree",
  "app",
  "app/main",
  "app/main/db",
  "app/main/net",
  "dbx",
  "uncategorized",
];

// ---------------------------------------------------------------- buildTree

describe("buildTree (§10 tree from the flat load result)", () => {
  it("returns a synthetic root with empty name and path", () => {
    expect(TREE.name).toBe("");
    expect(TREE.path).toBe("");
    expect(TREE.count).toBe(0);
  });

  it("orders root children in byte order, deterministically", () => {
    expect(TREE.children.map((c) => c.name)).toEqual([
      "B",
      "app",
      "dbx",
      "uncategorized",
    ]);
  });

  it("splits multi-level paths into a nested chain of full paths", () => {
    const app = node(TREE, "app");
    expect(app.count).toBe(1);
    const main = node(app, "app/main");
    expect(main.name).toBe("main");
    expect(main.count).toBe(2);
    expect(main.children.map((c) => c.path)).toEqual([
      "app/main/db",
      "app/main/net",
    ]);
    expect(node(TREE, "app/main/db").count).toBe(3);
    expect(node(TREE, "app/main/net").count).toBe(4);
  });

  it("creates zero-count interior nodes for paths never logged directly", () => {
    expect(node(TREE, "B").count).toBe(0);
    expect(node(TREE, "B/tree").count).toBe(6);
  });

  it("sums duplicate paths instead of duplicating nodes", () => {
    const merged = buildTree([
      { path: "a/b", count: 2 },
      { path: "a/b", count: 3 },
    ]);
    expect(node(merged, "a/b").count).toBe(5);
  });

  it("treats the uncategorized path like any other node", () => {
    const unc = node(TREE, "uncategorized");
    expect(unc.name).toBe("uncategorized");
    expect(unc.path).toBe("uncategorized");
    expect(unc.count).toBe(7);
  });

  it("handles an empty flat list as a childless root", () => {
    const empty = buildTree([]);
    expect(empty.children).toEqual([]);
  });

  it("is deterministic for scrambled input", () => {
    const scrambled = buildTree([...FLAT].reverse());
    expect(JSON.stringify(scrambled)).toBe(JSON.stringify(TREE));
  });

  it("keeps empty path segments verbatim, mirroring the engine", () => {
    // spec interpretation: `//` is invalid input; each segment is kept as-is.
    const weird = buildTree([{ path: "app//main", count: 1 }]);
    const app = node(weird, "app");
    const empty = app.children[0];
    expect(empty.name).toBe("");
    expect(node(weird, "app//main").count).toBe(1);
  });
});

// ---------------------------------------------------------------- nodeCheck

describe("nodeCheck (§10 tri-state mirroring category_allowed)", () => {
  it("reports on for every node when everything is enabled", () => {
    for (const path of ["app", "app/main", "app/main/db", "dbx", "B"]) {
      expect(nodeCheck(ALL_ENABLED, node(TREE, path))).toBe("on");
    }
  });

  it("reports partial when a parent is on but some children are off", () => {
    const enabled = ["app", "app/main", "app/main/db"];
    expect(nodeCheck(enabled, node(TREE, "app/main"))).toBe("partial");
    expect(nodeCheck(enabled, node(TREE, "app"))).toBe("partial");
  });

  it("reports on for a leaf whose full chain is enabled", () => {
    expect(
      nodeCheck(["app", "app/main", "app/main/db"], node(TREE, "app/main/db")),
    ).toBe("on");
  });

  it("reports partial for an off node that still has enabled descendants", () => {
    // Ancestor-prefix rule: nothing under app/main is visible (its own path
    // is missing), but a leftover enabled descendant keeps the checkbox not
    // fully off.
    const enabled = ["app", "app/main/net"];
    expect(nodeCheck(enabled, node(TREE, "app/main"))).toBe("partial");
    expect(nodeCheck([], node(TREE, "app/main"))).toBe("off");
  });

  it("reports off for nodes with neither self nor descendants enabled", () => {
    expect(nodeCheck([], node(TREE, "app"))).toBe("off");
    expect(nodeCheck([], node(TREE, "app/main/db"))).toBe("off");
  });

  it("reports partial for a disabled ancestor above enabled leaves", () => {
    const enabled = ["app/main", "app/main/db"];
    expect(nodeCheck(enabled, node(TREE, "app"))).toBe("partial");
  });

  it("reports off when an ancestor is missing even for a whitelisted leaf", () => {
    // The leaf's own path is in the whitelist but a prefix is not, so no row
    // of it is visible and it has no enabled descendants: off.
    const enabled = ["app/main/db"];
    expect(nodeCheck(enabled, node(TREE, "app/main/db"))).toBe("off");
  });

  it("ignores whitelist entries outside the node's subtree", () => {
    const enabled = ["app", "app/main", "app/main/db", "app/main/net"];
    expect(nodeCheck(enabled, node(TREE, "dbx"))).toBe("off");
  });
});

// ------------------------------------------------------------ propagateToggle

describe("propagateToggle (§10 differential for set_category_enabled)", () => {
  it("enabling a deep leaf adds the leaf and every ancestor prefix", () => {
    expect(propagateToggle(["app/main/db"], TREE, true)).toEqual({
      add: ["app", "app/main", "app/main/db"],
      remove: [],
    });
  });

  it("enabling a mid node adds it, its ancestors and all descendants", () => {
    expect(propagateToggle(["app/main"], TREE, true)).toEqual({
      add: ["app", "app/main", "app/main/db", "app/main/net"],
      remove: [],
    });
  });

  it("disabling a mid node removes it and its descendants, never ancestors", () => {
    expect(propagateToggle(["app/main"], TREE, false)).toEqual({
      add: [],
      remove: ["app/main", "app/main/db", "app/main/net"],
    });
  });

  it("disabling a deep leaf removes only the leaf", () => {
    expect(propagateToggle(["app/main/db"], TREE, false)).toEqual({
      add: [],
      remove: ["app/main/db"],
    });
  });

  it("merges overlapping batch toggles without duplicates, sorted", () => {
    expect(propagateToggle(["app/main/net", "dbx", "app/main/db"], TREE, true)).toEqual({
      add: ["app", "app/main", "app/main/db", "app/main/net", "dbx"],
      remove: [],
    });
  });

  it("collapses a disable batch of ancestor and descendant paths", () => {
    expect(propagateToggle(["app", "app/main/db"], TREE, false)).toEqual({
      add: [],
      remove: ["app", "app/main", "app/main/db", "app/main/net"],
    });
  });

  it("keeps add and remove disjoint in both directions", () => {
    // A path in both sets would fight itself downstream; single direction
    // calls must never produce one.
    for (const on of [true, false]) {
      const diff = propagateToggle(["app", "app/main/db", "dbx"], TREE, on);
      expect(diff.add.filter((p) => diff.remove.includes(p))).toEqual([]);
      expect(on ? diff.remove : diff.add).toEqual([]);
    }
  });

  it("propagates through the uncategorized node like any other", () => {
    expect(propagateToggle(["uncategorized"], TREE, true)).toEqual({
      add: ["uncategorized"],
      remove: [],
    });
  });

  it("toggles stale paths absent from the tree by prefix expansion", () => {
    expect(propagateToggle(["ghost/x"], TREE, true)).toEqual({
      add: ["ghost", "ghost/x"],
      remove: [],
    });
    expect(propagateToggle(["ghost/x"], TREE, false)).toEqual({
      add: [],
      remove: ["ghost/x"],
    });
  });
});

// ---------------------------------------------------------------- toggleAll

describe("toggleAll (§10 All checkbox)", () => {
  it("on adds every path plus the ancestor prefixes the engine needs", () => {
    // The flat list holds observed paths only; a nested path stays invisible
    // unless its prefixes are enabled too (category_allowed), so the All
    // checkbox adds them as well.
    expect(toggleAll(FLAT, true)).toEqual({
      add: ["B", "B/tree", "app", "app/main", "app/main/db", "app/main/net", "dbx", "uncategorized"],
      remove: [],
    });
  });

  it("off removes every path including the prefixes on added", () => {
    expect(toggleAll(FLAT, false)).toEqual({
      add: [],
      remove: ["B", "B/tree", "app", "app/main", "app/main/db", "app/main/net", "dbx", "uncategorized"],
    });
  });

  it("does nothing for an empty flat list", () => {
    expect(toggleAll([], true)).toEqual({ add: [], remove: [] });
    expect(toggleAll([], false)).toEqual({ add: [], remove: [] });
  });
});

// -------------------------------------------------------- visibleUnderSearch

describe("visibleUnderSearch (§10 tree search)", () => {
  it("returns an empty set for an empty query (no search active)", () => {
    expect(visibleUnderSearch(TREE, "")).toEqual(new Set());
  });

  it("returns an empty set when nothing matches", () => {
    expect(visibleUnderSearch(TREE, "nosuchbranch")).toEqual(new Set());
  });

  it("shows a matching leaf and its ancestor chain only", () => {
    expect(visibleUnderSearch(TREE, "net")).toEqual(
      new Set(["app", "app/main", "app/main/net"]),
    );
  });

  it("matches case-insensitively on the node name", () => {
    expect(visibleUnderSearch(TREE, "MAIN")).toEqual(
      new Set(["app", "app/main"]),
    );
    expect(visibleUnderSearch(TREE, "TREE")).toEqual(new Set(["B", "B/tree"]));
  });

  it("hides branches whose names do not match", () => {
    const visible = visibleUnderSearch(TREE, "net");
    expect(visible.has("dbx")).toBe(false);
    expect(visible.has("uncategorized")).toBe(false);
  });

  it("collects matches from several branches", () => {
    expect(visibleUnderSearch(TREE, "e")).toEqual(
      new Set([
        "B",
        "B/tree",
        "app",
        "app/main",
        "app/main/net",
        "uncategorized",
      ]),
    );
  });
});

// ------------------------------------------------------------- expandTargets

describe("expandTargets (§10 expand/collapse-all button)", () => {
  const paths = ["app", "app/main", "app/main/db", "B", "B/tree"];

  it("expand returns every path sorted", () => {
    expect(expandTargets(["app", "app/main", "B"], true, false)).toEqual([
      "B",
      "app",
      "app/main",
    ]);
  });

  it("collapse with keepRoots leaves only root-level paths expanded", () => {
    // Spec interpretation: keepRoots matters only when collapsing; the result
    // is the expanded set to install (top-level paths stay expanded).
    expect(expandTargets(paths, false, true)).toEqual(["B", "app"]);
  });

  it("collapse without keepRoots clears the set", () => {
    expect(expandTargets(paths, false, false)).toEqual([]);
  });

  it("expand ignores keepRoots and covers the whole tree, sorted", () => {
    expect(expandTargets(paths, true, true)).toEqual([
      "B",
      "B/tree",
      "app",
      "app/main",
      "app/main/db",
    ]);
  });

  it("returns empty targets for an empty path list", () => {
    expect(expandTargets([], true, false)).toEqual([]);
    expect(expandTargets([], false, true)).toEqual([]);
  });
});
