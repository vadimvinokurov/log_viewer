import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { CategoriesTab, type CategoriesTabProps } from "./CategoriesTab.tsx";
import { buildTree } from "./categories";

afterEach(cleanup);

const FLAT = [
  { path: "app/main/db" },
  { path: "app/main/api" },
  { path: "unstable/pool" },
  { path: "db/pool" },
  { path: "uncategorized" },
];

/** The engine's default whitelist: every observed path and every prefix. */
function allEnabled(): string[] {
  const out = new Set<string>();
  for (const { path } of FLAT) {
    const segments = path.split("/");
    for (let i = 1; i <= segments.length; i++) {
      out.add(segments.slice(0, i).join("/"));
    }
  }
  return [...out].sort();
}

const EVERYTHING = [
  "app", "app/main", "app/main/api", "app/main/db",
  "db", "db/pool",
  "uncategorized",
  "unstable", "unstable/pool",
];

function baseProps(overrides: Partial<CategoriesTabProps> = {}): CategoriesTabProps {
  return {
    tree: buildTree(FLAT),
    flat: FLAT,
    enabled: allEnabled(),
    search: "",
    expanded: EVERYTHING,
    onToggle: vi.fn(),
    onToggleAll: vi.fn(),
    onSearch: vi.fn(),
    onExpandAll: vi.fn(),
    onToggleExpand: vi.fn(),
    ...overrides,
  };
}

describe("CategoriesTab (rhl.2, §10, UI_DESIGN categories frame)", () => {
  it("renders the All row on top and the tree in build order, no counts (2026-11-25 owner decision)", () => {
    const { container } = render(createElement(CategoriesTab, baseProps()));
    const rows = Array.from(container.querySelectorAll<HTMLElement>(".tree .row"));
    expect(rows.map((el) => el.getAttribute("data-path"))).toEqual([
      "", // All
      "app", "app/main", "app/main/api", "app/main/db",
      "db", "db/pool",
      "uncategorized",
      "unstable", "unstable/pool",
    ]);
    expect(container.querySelectorAll(".tree .row .ct")).toHaveLength(0);
  });

  it("full whitelist: every checkbox is on, no row is dimmed", () => {
    const { container } = render(createElement(CategoriesTab, baseProps()));
    const all = Array.from(container.querySelectorAll<HTMLElement>(".tree .row .cb"));
    expect(all.every((el) => el.classList.contains("on"))).toBe(true);
    expect(container.querySelectorAll(".row.off")).toHaveLength(0);
  });

  it("checkboxes are native inputs (mock 1d80977): checked lives on the element", () => {
    const { container } = render(createElement(CategoriesTab, baseProps()));
    const on = container.querySelector<HTMLInputElement>('[data-path="app/main/db"] .cb');
    expect(on?.tagName).toBe("INPUT");
    expect(on?.type).toBe("checkbox");
    expect(on?.checked).toBe(true);
  });

  it("the partially-whitelisted parent sets the native indeterminate state", () => {
    const { container } = render(
      createElement(CategoriesTab, baseProps({ enabled: ["app", "app/main", "app/main/db"] })),
    );
    const part = container.querySelector<HTMLInputElement>('[data-path="app"] .cb');
    expect(part?.indeterminate).toBe(true);
    const plain = container.querySelector<HTMLInputElement>('[data-path="app/main/db"] .cb');
    expect(plain?.indeterminate).toBe(false);
    const off = container.querySelector<HTMLInputElement>('[data-path="uncategorized"] .cb');
    expect(off?.checked).toBe(false);
  });

  it("tri-state: present parent with an unchecked child renders part", () => {
    const { container } = render(
      createElement(CategoriesTab, baseProps({ enabled: ["app", "app/main", "app/main/db"] })),
    );
    const check = (path: string): string[] => {
      const el = container.querySelector<HTMLElement>(`[data-path="${path}"] .cb`);
      return ["on", "part", "off"].filter((c) => el?.classList.contains(c));
    };
    expect(check("app")).toEqual(["part"]);
    expect(check("app/main")).toEqual(["part"]);
    expect(check("app/main/db")).toEqual(["on"]);
    // disabled categories dim with their whole subtree (§10); the off state
    // lives on the row (design: .row.off), the checkbox goes plain.
    const offRow = container.querySelector<HTMLElement>('[data-path="uncategorized"]');
    expect(offRow?.classList.contains("off")).toBe(true);
    expect(
      Array.from(offRow?.querySelector(".cb")?.classList ?? []).includes("on"),
    ).toBe(false);
    const dimmed = container.querySelectorAll(".row.off").length;
    expect(dimmed).toBeGreaterThan(0);
  });

  it("clicking a node checkbox toggles: on -> off, off -> on", () => {
    const props = baseProps();
    const { container } = render(createElement(CategoriesTab, props));
    fireEvent.click(container.querySelector('[data-path="db/pool"] .cb') ?? container);
    expect(props.onToggle).toHaveBeenCalledWith("db/pool", false);
    // an off node toggles back to on
    const offProps = baseProps({ enabled: ["app", "app/main", "app/main/db"] });
    const { container: offTree } = render(createElement(CategoriesTab, offProps));
    fireEvent.click(
      offTree.querySelector('[data-path="uncategorized"] .cb') ?? offTree,
    );
    expect(offProps.onToggle).toHaveBeenCalledWith("uncategorized", true);
  });

  it("the All checkbox is tri-state and toggles everything", () => {
    const on = baseProps();
    const { container: a } = render(createElement(CategoriesTab, on));
    expect(
      a.querySelector('[data-path=""] .cb')?.classList.contains("on"),
    ).toBe(true);
    fireEvent.click(a.querySelector('[data-path=""] .cb') ?? a);
    expect(on.onToggleAll).toHaveBeenCalledWith(false);

    const partial = baseProps({
      enabled: ["app", "app/main", "app/main/db"],
    });
    const { container: b } = render(createElement(CategoriesTab, partial));
    expect(
      b.querySelector('[data-path=""] .cb')?.classList.contains("part"),
    ).toBe(true);
    fireEvent.click(b.querySelector('[data-path=""] .cb') ?? b);
    expect(partial.onToggleAll).toHaveBeenCalledWith(true);
  });

  it("the twisty toggles one node's expansion; leaves render a dot", () => {
    const props = baseProps({ expanded: ["app"] });
    const { container } = render(createElement(CategoriesTab, props));
    const collapsed = container.querySelector<HTMLElement>(
      '[data-path="db"] .tw',
    );
    expect(collapsed?.textContent).toBe("▸");
    fireEvent.click(collapsed ?? container);
    expect(props.onToggleExpand).toHaveBeenCalledWith("db");
    const expanded = container.querySelector<HTMLElement>('[data-path="app"] .tw');
    expect(expanded?.textContent).toBe("▾");
    const leaf = container.querySelector<HTMLElement>(
      '[data-path="uncategorized"] .tw',
    )?.textContent;
    expect(leaf).toBe("·");
    // leaf twisty is not clickable
    fireEvent.click(container.querySelector('[data-path="uncategorized"] .tw') ?? container);
    expect(props.onToggleExpand).toHaveBeenCalledTimes(1);
  });

  it("collapsed parents hide their children; expanded show them", () => {
    const { container } = render(createElement(CategoriesTab, baseProps({ expanded: [] })));
    const rows = Array.from(container.querySelectorAll<HTMLElement>(".tree .row"));
    const top = rows.map((el) => el.getAttribute("data-path"));
    expect(top).toContain("app");
    expect(top).not.toContain("app/main");

    const { container: expandedTree } = render(
      createElement(CategoriesTab, baseProps({ expanded: ["app", "app/main", "db"] })),
    );
    const rows2 = Array.from(expandedTree.querySelectorAll<HTMLElement>(".tree .row"));
    const paths = rows2.map((el) => el.getAttribute("data-path"));
    expect(paths).toContain("app/main/api");
    expect(paths).not.toContain("unstable/pool");
  });

  it("search filters visible nodes and expands every branch while active", () => {
    const { container } = render(
      createElement(CategoriesTab, baseProps({ search: "pool", expanded: [] })),
    );
    const rows = Array.from(container.querySelectorAll<HTMLElement>(".tree .row"));
    const paths = rows.map((el) => el.getAttribute("data-path"));
    // matching branches stay linked to the root; fully expanded while the
    // search is on (§10)
    expect(paths).toEqual(["", "db", "db/pool", "unstable", "unstable/pool"]);
    expect(container.querySelector<HTMLInputElement>("input")?.value).toBe("pool");
  });

  it("search input and expand/collapse-all button wire their callbacks", () => {
    const props = baseProps({ expanded: [] });
    const { container } = render(createElement(CategoriesTab, props));
    const input = container.querySelector<HTMLInputElement>("input");
    if (input) fireEvent.change(input, { target: { value: "db" } });
    expect(props.onSearch).toHaveBeenCalledWith("db");
    const fold = container.querySelector<HTMLElement>(".fold");
    expect(fold?.getAttribute("aria-label")).toBe("Expand all");
    // native chevron glyph (2026-11-25 mock decision), not a text triangle
    expect(fold?.querySelector("svg")).not.toBeNull();
    fireEvent.click(fold ?? container);
    expect(props.onExpandAll).toHaveBeenCalledWith(true);

    const folded = baseProps({
      expanded: [
        "app", "app/main", "app/main/api", "app/main/db",
        "db", "db/pool", "uncategorized", "unstable", "unstable/pool",
      ],
    });
    const { container: c2 } = render(createElement(CategoriesTab, folded));
    const fold2 = c2.querySelector<HTMLElement>(".fold");
    expect(fold2?.getAttribute("aria-label")).toBe("Collapse all");
    fireEvent.click(fold2 ?? c2);
    expect(folded.onExpandAll).toHaveBeenCalledWith(false);
  });
});
