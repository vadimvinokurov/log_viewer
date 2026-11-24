//! SearchPanel tests (bead 2wu.1, §8; markup per docs/UI_DESIGN.html
//! "Find bar" component study — classes copied verbatim).

import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { SearchPanel, type SearchPanelProps } from "./SearchPanel.tsx";
import type { SearchState } from "./state";

afterEach(cleanup);

function searchState(overrides: Partial<SearchState> = {}): SearchState {
  return {
    open: true,
    mode: null,
    query: "",
    positions: [],
    current: null,
    ...overrides,
  };
}

function baseProps(overrides: Partial<SearchPanelProps> = {}): SearchPanelProps {
  return {
    search: searchState(),
    onQuery: vi.fn(),
    onTumbler: vi.fn(),
    onNext: vi.fn(),
    onPrev: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  };
}

describe("SearchPanel (bead 2wu.1, §8)", () => {
  it("renders the findbar markup with field, counter, tumblers, arrows, close", () => {
    const { container } = render(createElement(SearchPanel, baseProps()));
    const bar = container.querySelector(".findbar");
    expect(bar).not.toBeNull();
    expect(bar?.querySelector<HTMLInputElement>(".field")).not.toBeNull();
    expect(bar?.querySelector(".cnt")?.textContent).toBe("0 / 0");
    const tumblers = bar?.querySelectorAll(".tg");
    expect(tumblers?.[0]?.textContent).toBe("Regex");
    expect(tumblers?.[1]?.textContent).toBe("Simple");
    expect(bar?.querySelectorAll(".ar")).toHaveLength(2);
    expect(bar?.querySelector(".x")?.textContent).toBe("✕");
  });

  it("the counter is «k / N», 1-based; no matches renders «0 / 0»", () => {
    const { container: a } = render(
      createElement(
        SearchPanel,
        baseProps({ search: searchState({ query: "q", positions: [1, 4, 9], current: 1 }) }),
      ),
    );
    expect(a.querySelector(".cnt")?.textContent).toBe("2 / 3");
    const { container: b } = render(
      createElement(SearchPanel, baseProps({ search: searchState({ query: "q" }) })),
    );
    expect(b.querySelector(".cnt")?.textContent).toBe("0 / 0");
  });

  it("typing dispatches the query; the input focuses on open", () => {
    const onQuery = vi.fn();
    const { container } = render(
      createElement(SearchPanel, baseProps({ onQuery })),
    );
    const field = container.querySelector<HTMLInputElement>(".field");
    fireEvent.change(field!, { target: { value: "timeout" } });
    expect(onQuery).toHaveBeenCalledWith("timeout");
    expect(document.activeElement).toBe(field);
  });

  it("the tumblers are exclusive: clicking an active one returns to plain", () => {
    const onTumbler = vi.fn();
    const { container, rerender } = render(
      createElement(SearchPanel, baseProps({ onTumbler })),
    );

    const onClick = (root: HTMLElement, tumbler: number) => {
      const [regex, simple] = Array.from(root.querySelectorAll<HTMLElement>(".tg"));
      fireEvent.click(tumbler === 0 ? regex! : simple!);
    };

    // Regex on.
    onClick(container, 0);
    expect(onTumbler).toHaveBeenNthCalledWith(1, "regex");
    // Simple: switching to the other tumbler keeps it exclusive.
    rerender(createElement(SearchPanel, baseProps({
      onTumbler,
      search: searchState({ mode: "regex" }),
    })));
    onClick(container, 1);
    expect(onTumbler).toHaveBeenNthCalledWith(2, "simple");
    // Clicking the active tumbler turns it off («plain», both off).
    rerender(createElement(SearchPanel, baseProps({
      onTumbler,
      search: searchState({ mode: "simple" }),
    })));
    onClick(container, 1);
    expect(onTumbler).toHaveBeenNthCalledWith(3, null);
  });

  it("the active tumbler carries the .on class", () => {
    const { container } = render(
      createElement(SearchPanel, baseProps({ search: searchState({ mode: "regex" }) })),
    );
    const [regex, simple] = Array.from(container.querySelectorAll<HTMLElement>(".tg"));
    expect(regex!.classList.contains("on")).toBe(true);
    expect(simple!.classList.contains("on")).toBe(false);
  });

  it("the arrows and close dispatch their actions", () => {
    const onNext = vi.fn();
    const onPrev = vi.fn();
    const onClose = vi.fn();
    const { container } = render(
      createElement(SearchPanel, baseProps({ onNext, onPrev, onClose })),
    );
    const [down, up] = Array.from(container.querySelectorAll<HTMLElement>(".ar"));
    fireEvent.click(down!);
    expect(onNext).toHaveBeenCalledTimes(1);
    fireEvent.click(up!);
    expect(onPrev).toHaveBeenCalledTimes(1);
    fireEvent.click(container.querySelector<HTMLElement>(".x")!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
