//! PinnedTab anatomy (q1f.1, §10.1): mirrors the Filters tab — checkbox, the
//! canonical pin command text with a tooltip, right-aligned delete; off
//! entries render dimmed; the empty tab explains itself without chrome.

import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { PinnedTab, type PinnedTabProps } from "./PinnedTab.tsx";

afterEach(cleanup);

const ITEMS = [
  { id: 0, mode: "lineno" as const, pattern: "31", enabled: true },
  { id: 1, mode: "plain" as const, pattern: "cfg", enabled: false },
];

function baseProps(overrides: Partial<PinnedTabProps> = {}): PinnedTabProps {
  return { items: ITEMS, onToggle: vi.fn(), onRemove: vi.fn(), ...overrides };
}

describe("PinnedTab (q1f.1, §10.1 Pinned tab)", () => {
  it("renders the canonical pin command text with the :p/:pr/:ps/:pn prefixes", () => {
    const { container } = render(createElement(PinnedTab, baseProps()));
    const commands = Array.from(container.querySelectorAll<HTMLElement>(".command"));
    expect(commands.map((el) => el.textContent)).toEqual([":pn 31", ":p cfg"]);
  });

  it("dims an off pin and keeps an enabled one at full opacity", () => {
    const { container } = render(createElement(PinnedTab, baseProps()));
    const rows = Array.from(container.querySelectorAll<HTMLElement>(".filter-row"));
    expect(rows).toHaveLength(2);
    expect(rows[1]?.className).toContain("dimmed");
    expect(rows[0]?.className).not.toContain("dimmed");
  });

  it("checkbox flips a pin through onToggle", () => {
    const props = baseProps();
    const { container } = render(createElement(PinnedTab, props));
    fireEvent.click(container.querySelector('input[type="checkbox"]') as HTMLInputElement);
    expect(props.onToggle).toHaveBeenCalledWith(0, false);
  });

  it("the delete button removes exactly that pin", () => {
    const props = baseProps();
    const { container } = render(createElement(PinnedTab, props));
    const buttons = Array.from(container.querySelectorAll<HTMLElement>("button"));
    fireEvent.click(buttons[1] as HTMLElement);
    expect(props.onRemove).toHaveBeenCalledTimes(1);
    expect(props.onRemove).toHaveBeenCalledWith(1);
  });

  it("the empty tab renders a muted placeholder", () => {
    const { container } = render(createElement(PinnedTab, baseProps({ items: [] })));
    expect(container.textContent).toContain("(no pins)");
  });
});
