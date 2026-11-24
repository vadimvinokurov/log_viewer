import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { SidePanel, usePanelHotkey, type SidePanelProps } from "./SidePanel.tsx";
import type { PanelState } from "./state";

afterEach(cleanup);

const panel = (): PanelState => ({
  open: true,
  tab: "categories",
  width: 220,
  search: "",
  expanded: [],
});

/** Ctrl+B lives with the app shell (the panel unmounts when closed), so the
 *  hotkey is asserted against the exported hook directly. */
function HotkeyProbe(props: { onToggle: () => void }): React.ReactElement {
  usePanelHotkey(props.onToggle);
  return createElement("div");
}

function baseProps(overrides: Partial<SidePanelProps> = {}): SidePanelProps {
  return {
    panel: panel(),
    onToggle: vi.fn(),
    onTab: vi.fn(),
    onWidth: vi.fn(),
    content: { categories: <div data-testid="categories-content" /> },
    ...overrides,
  };
}

describe("SidePanel (rhl.2, §10.1)", () => {
  it("renders the 4 tabs in the designed order with the active one marked", () => {
    const { container } = render(createElement(SidePanel, baseProps()));
    const tabs = Array.from(container.querySelectorAll(".tabs span"));
    expect(tabs.map((el) => el.textContent)).toEqual([
      "Categories", "Filters", "Highlights", "Pinned",
    ]);
    expect(tabs.map((el) => el.classList.contains("on"))).toEqual([
      true, false, false, false,
    ]);
  });

  it("clicking a tab switches; content switches with it", () => {
    const props = baseProps({
      content: {
        categories: <div data-testid="categories-content" />,
        filters: <div data-testid="filters-content" />,
      },
    });
    const { container } = render(createElement(SidePanel, props));
    const { onTab } = props;
    fireEvent.click(
      Array.from(container.querySelectorAll(".tabs span"))[1] ?? container,
    );
    expect(onTab).toHaveBeenCalledWith("filters");

    const filters = baseProps({ panel: { ...panel(), tab: "filters" }, content: { filters: <div data-testid="filters-content" /> } });
    const { container: c2 } = render(createElement(SidePanel, filters));
    expect(c2.querySelector('[data-testid="filters-content"]')).not.toBeNull();
    expect(c2.querySelector('[data-testid="categories-content"]')).toBeNull();
  });

  it("muted placeholders render for the tabs without live content yet", () => {
    const { container } = render(
      createElement(SidePanel, baseProps({ panel: { ...panel(), tab: "highlights" } })),
    );
    const placeholder = container.querySelector("[data-panel-placeholder]");
    expect(placeholder).not.toBeNull();
    expect(placeholder?.textContent).toContain("Highlights");
    const pinned = render(
      createElement(SidePanel, baseProps({ panel: { ...panel(), tab: "pinned" } })),
    );
    expect(pinned.container.querySelector("[data-panel-placeholder='pinned']")).not.toBeNull();
  });

  it("closed renders nothing", () => {
    const { container } = render(
      createElement(SidePanel, baseProps({ panel: { ...panel(), open: false } })),
    );
    expect(container.querySelector(".side")).toBeNull();
  });

  it("Ctrl+B and Cmd+B toggle the panel; a plain b does not (hotkey lives with the shell)", () => {
    const onToggle = vi.fn();
    const { unmount } = render(createElement(HotkeyProbe, { onToggle }));
    fireEvent.keyDown(document, { key: "b", ctrlKey: true });
    expect(onToggle).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(document, { key: "b", metaKey: true });
    expect(onToggle).toHaveBeenCalledTimes(2);
    fireEvent.keyDown(document, { key: "b" });
    expect(onToggle).toHaveBeenCalledTimes(2);
    fireEvent.keyDown(document, { key: "x", ctrlKey: true });
    expect(onToggle).toHaveBeenCalledTimes(2);
    unmount();
    // uninstalled: no toggle after unmount
    fireEvent.keyDown(document, { key: "b", ctrlKey: true });
    expect(onToggle).toHaveBeenCalledTimes(2);
  });

  it("the splitter drags: width = innerWidth - clientX while dragging", () => {
    const original = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { value: 1280, configurable: true });
    try {
      const spy = vi.fn();
      const props = baseProps({ onWidth: spy });
      const { container } = render(createElement(SidePanel, props));
      const splitter = container.querySelector<HTMLElement>(".side-splitter");
      expect(splitter).not.toBeNull();
      fireEvent.mouseDown(splitter ?? container, { button: 0 });
      fireEvent.mouseMove(window, { clientX: 1160 }); // 1280 - 1160
      expect(spy).toHaveBeenLastCalledWith(120);
      fireEvent.mouseMove(window, { clientX: 1060 });
      expect(spy).toHaveBeenLastCalledWith(220);
      fireEvent.mouseUp(window);
      fireEvent.mouseMove(window, { clientX: 1000 });
      // drag released: no more updates
      expect(spy).toHaveBeenCalledTimes(2);
    } finally {
      Object.defineProperty(window, "innerWidth", { value: original, configurable: true });
    }
  });

  it("applies the panel width to the aside layout", () => {
    const { container } = render(
      createElement(SidePanel, baseProps({ panel: { ...panel(), width: 330 } })),
    );
    const aside = container.querySelector<HTMLElement>(".side");
    expect(aside?.style.width).toBe("330px");
  });
});
