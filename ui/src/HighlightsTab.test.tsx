// Tests for the §9 Highlights tab (bead exx.2): like the Filters/Pinned rows
// — checkbox, canonical command text with ellipsis+tooltip, delete — plus
// the color dot (click opens the webview's color picker; the picked color
// goes back through onColor). Off entries render dimmed.

import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { HighlightsTab, type HighlightsTabProps } from "./HighlightsTab";

afterEach(cleanup);

const ITEMS = [
  { id: 0, mode: "plain" as const, pattern: "timeout", enabled: true, colorIndex: 0, overrideColor: null },
  { id: 1, mode: "lineno" as const, pattern: "42", enabled: false, colorIndex: 4, overrideColor: "#00aabb" },
];

function baseProps(overrides: Partial<HighlightsTabProps> = {}): HighlightsTabProps {
  return { items: ITEMS, onToggle: vi.fn(), onColor: vi.fn(), onRemove: vi.fn(), ...overrides };
}

describe("HighlightsTab (exx.2, §10.1 highlight row)", () => {
  it("renders the canonical command text with the :h/:hr/:hs/:hn prefixes", () => {
    const { container } = render(createElement(HighlightsTab, baseProps()));
    const commands = Array.from(container.querySelectorAll<HTMLElement>(".command"));
    expect(commands.map((el) => el.textContent)).toEqual([":h timeout", ":hn 42"]);
  });

  it("dims an off rule and keeps an enabled one at full opacity", () => {
    const { container } = render(createElement(HighlightsTab, baseProps()));
    const rows = Array.from(container.querySelectorAll<HTMLElement>(".filter-row"));
    expect(rows).toHaveLength(2);
    expect(rows[1]?.className).toContain("dimmed");
    expect(rows[0]?.className).not.toContain("dimmed");
  });

  it("the checkbox flips a rule through onToggle", () => {
    const props = baseProps();
    const { container } = render(createElement(HighlightsTab, props));
    fireEvent.click(container.querySelector('input[type="checkbox"]') as HTMLInputElement);
    expect(props.onToggle).toHaveBeenCalledWith(0, false);
  });

  it("the delete button removes exactly that rule", () => {
    const props = baseProps();
    const { container } = render(createElement(HighlightsTab, props));
    const buttons = Array.from(container.querySelectorAll<HTMLElement>("button[type=button]"));
    fireEvent.click(buttons[1] as HTMLElement);
    expect(props.onRemove).toHaveBeenCalledTimes(1);
    expect(props.onRemove).toHaveBeenCalledWith(1);
  });

  it("the empty tab renders a muted placeholder", () => {
    const { container } = render(createElement(HighlightsTab, baseProps({ items: [] })));
    expect(container.textContent).toContain("(no highlights)");
  });

  it("the color dot shows the rule's resolved color (override first)", () => {
    const { container } = render(createElement(HighlightsTab, baseProps()));
    const dots = Array.from(container.querySelectorAll<HTMLElement>(".color-dot"));
    expect(dots[0]?.style.background).toBe("rgb(232, 195, 74)"); // palette slot 0
    expect(dots[1]?.style.background).toBe("rgb(0, 170, 187)"); // the override
  });

  it("clicking a dot opens its hidden color input; the picked hex goes through onColor", () => {
    const props = baseProps();
    const { container } = render(createElement(HighlightsTab, props));
    const input = container.querySelector('input[type="color"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    // The system picker opens from the dot's click (label wraps the input);
    // the change event of that input carries the picked color onward.
    fireEvent.click(container.querySelector(".color-dot") as HTMLElement);
    fireEvent.input(input, { target: { value: "#123456" } });
    fireEvent.change(input, { target: { value: "#123456" } });
    expect(props.onColor).toHaveBeenCalledWith(0, "#123456");
  });
});
