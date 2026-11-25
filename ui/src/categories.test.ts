//! Tests for the categories tree model (FUNCTIONAL_SPEC §10): buildTree from
//! the flat {path} load result, tri-state checks mirroring the engine's
//! category_allowed rule (exact path AND every ancestor prefix enabled),
//! toggle propagation as a {add, remove} differential, the All checkbox, tree
//! search visibility and expand/collapse targets. Pure logic only.

import { describe, expect, it } from "vitest";
import {
  buildTree,
  nodeCheck,
  propagateToggle,
  toggleAll,
  type UiCategoryNode,
  visibleUnderSearch,
} from "./categories";

// ---------------------------------------------------------------- fixtures

/** Flat list shaped like the load result: observed paths only (no interior
 * nodes), sorted by path, "uncategorized" as a regular path. */
const FLAT = [
  { path: "app" },
  { path: "app/main" },
  { path: "app/main/db" },
  { path: "app/main/net" },
  { path: "B/tree" },
  { path: "dbx" },
  { path: "uncategorized" },
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
    expect(app.name).toBe("app");
    const main = node(app, "app/main");
    expect(main.name).toBe("main");
    expect(main.children.map((c) => c.path)).toEqual([
      "app/main/db",
      "app/main/net",
    ]);
    expect(node(TREE, "app/main/db").path).toBe("app/main/db");
    expect(node(TREE, "app/main/net").path).toBe("app/main/net");
  });

  it("creates interior nodes for paths never logged directly", () => {
    const b = node(TREE, "B");
    expect(b.children.map((c) => c.path)).toEqual(["B/tree"]);
  });

  it("deduplicates duplicate paths instead of duplicating nodes", () => {
    const merged = buildTree([
      { path: "a/b" },
      { path: "a/b" },
    ]);
    expect(node(merged, "a/b").children).toEqual([]);
    expect(merged.children.filter((c) => c.name === "a")).toHaveLength(1);
  });

  it("treats the uncategorized path like any other node", () => {
    const unc = node(TREE, "uncategorized");
    expect(unc.name).toBe("uncategorized");
    expect(unc.path).toBe("uncategorized");
    expect(unc.children).toEqual([]);
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
    const weird = buildTree([{ path: "app//main" }]);
    const app = node(weird, "app");
    const empty = app.children[0];
    expect(empty.name).toBe("");
    expect(node(weird, "app//main").path).toBe("app//main");
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
