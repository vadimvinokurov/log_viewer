//! Tests for the Filters tab (FUNCTIONAL_SPEC §10.1): canonical command
//! text per mode and the panel list behavior (checkbox, delete, dimming).
//! Component tests render via createElement (file is .ts, not .tsx).

import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

// vitest without globals does not trigger testing-library auto-cleanup.
afterEach(cleanup);
import { filterCommand, type FilterItem } from "./filtersTab";
// Explicit .tsx: on a case-insensitive filesystem "./FiltersTab" would
// resolve to filtersTab.ts (Vite tries .ts before .tsx).
import { FiltersTab } from "./FiltersTab.tsx";

function item(
  id: number,
  mode: FilterItem["mode"],
  pattern: string,
  enabled: boolean,
): FilterItem {
  return { id, mode, pattern, enabled };
}

describe("filterCommand (§10.1 canonical command text)", () => {
  it("prefixes :f for a plain pattern", () => {
    expect(filterCommand(item(1, "plain", 'timeout"', true))).toBe(':f timeout"');
  });

  it("prefixes :fr for a regex pattern", () => {
    expect(filterCommand(item(2, "regex", "^retry", true))).toBe(":fr ^retry");
  });

  it("prefixes :fs for a simple-boolean pattern", () => {
    expect(
      filterCommand(item(3, "simple", '("auth" OR "login")', false)),
    ).toBe(':fs ("auth" OR "login")');
  });

  it("prefixes :fn for a line-number pattern (pattern holds the literal)", () => {
    expect(filterCommand(item(4, "lineno", "12034", true))).toBe(":fn 12034");
  });
});

describe("FiltersTab rendering (§10.1 list tab anatomy)", () => {
  const items = [
    item(1, "plain", '"timeout"', true),
    item(2, "lineno", "12034", false),
    item(3, "regex", "^retry", true),
  ];

  function renderList(list: FilterItem[]) {
    return render(
      createElement(FiltersTab, { items: list, onToggle: () => {}, onRemove: () => {} }),
    );
  }

  it("shows one row per filter: checkbox, canonical command text, delete button", () => {
    renderList(items);
    for (const expected of [':f "timeout"', ":fn 12034", ":fr ^retry"]) {
      expect(screen.getByText(expected)).toBeTruthy();
      expect(screen.getByRole("checkbox", { name: expected })).toBeTruthy();
      expect(screen.getByRole("button", { name: `Remove ${expected}` })).toBeTruthy();
    }
  });

  it("reflects the enabled flag on the checkbox", () => {
    renderList(items);
    const on = screen.getByRole("checkbox", { name: ':f "timeout"' }) as HTMLInputElement;
    const off = screen.getByRole("checkbox", { name: ":fn 12034" }) as HTMLInputElement;
    expect(on.checked).toBe(true);
    expect(off.checked).toBe(false);
  });

  it("marks a disabled (off) entry with the dimmed class", () => {
    const { container } = renderList(items);
    const rows = container.querySelectorAll(".filters-list > .filter-row");
    expect(rows).toHaveLength(3);
    expect(rows[1].className).toContain("dimmed");
    expect(rows[0].className).not.toContain("dimmed");
  });

  it("carries the canonical command text as tooltip on a clipped span", () => {
    const long = item(4, "regex", "^connection .*refused after \\d+ retries on .*pool$", true);
    renderList([long]);
    const span = screen.getByText(":fr ^connection .*refused after \\d+ retries on .*pool$");
    expect(span.getAttribute("title")).toBe(":fr ^connection .*refused after \\d+ retries on .*pool$");
  });

  it("shows a muted (no filters) placeholder for an empty list", () => {
    renderList([]);
    expect(screen.getByText("(no filters)")).toBeTruthy();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});

describe("FiltersTab interactions (§10.1: toggle/remove emit callbacks)", () => {
  it("checkbox click reports the item id and the new target state", () => {
    const onToggle = vi.fn();
    render(
      createElement(FiltersTab, {
        items: [item(1, "plain", "timeout", true), item(2, "simple", "db", false)],
        onToggle,
        onRemove: () => {},
      }),
    );
    // A checked box, unclicked, reports on = false.
    fireEvent.click(screen.getByRole("checkbox", { name: ":f timeout" }));
    expect(onToggle).toHaveBeenCalledWith(1, false);
    // An off box, clicked, reports on = true.
    fireEvent.click(screen.getByRole("checkbox", { name: ":fs db" }));
    expect(onToggle).toHaveBeenCalledWith(2, true);
  });

  it("delete button reports the item id", () => {
    const onRemove = vi.fn();
    render(
      createElement(FiltersTab, {
        items: [item(7, "regex", "boom", true)],
        onToggle: () => {},
        onRemove,
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Remove :fr boom" }));
    expect(onRemove).toHaveBeenCalledWith(7);
  });
});
