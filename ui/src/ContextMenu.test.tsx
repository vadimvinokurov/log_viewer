import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { ContextMenu, type ContextMenuProps } from "./ContextMenu.tsx";

afterEach(cleanup);

/** Hand-written commands plus the design anatomy in UI_DESIGN §s3 .cm. */
const baseProps = (): ContextMenuProps => ({
  x: 12,
  y: 34,
  onCopy: vi.fn(),
  onCopyMessage: vi.fn(),
  onPin: vi.fn(),
  onUnpin: vi.fn(),
  canUnpin: false,
  onHighlight: vi.fn(),
  onRemoveHighlight: vi.fn(),
  canRemoveHighlight: false,
});

const item = (root: HTMLElement, name: string): HTMLElement | null =>
  root.querySelector(`[data-menu-item="${name}"]`);

describe("ContextMenu (§4 items, UI_DESIGN study frame)", () => {
  it("renders the §4 items in the designed order", () => {
    const { container } = render(createElement(ContextMenu, baseProps()));
    const names = Array.from(
      container.querySelectorAll<HTMLElement>("[data-menu-item]"),
    ).map((el) => el.getAttribute("data-menu-item"));
    expect(names).toEqual([
      "copy",
      "copy-message",
      "unpin",
      "pin",
      "highlight",
      "remove-highlight",
    ]);
  });

  it("separates copy from pin/unpin and pin/unpin from highlight", () => {
    const { container } = render(createElement(ContextMenu, baseProps()));
    const menu = container.querySelector<HTMLElement>(".lvc-cm") as HTMLElement;
    const order = Array.from(menu.children)
      .filter((el) => el.tagName !== "STYLE")
      .map((el) => (el.hasAttribute("data-menu-item") ? "item" : "sep"));
    expect(order).toEqual([
      "item",
      "item",
      "sep",
      "item",
      "item",
      "sep",
      "item",
      "item",
    ]);
  });

  it("shows the ⌃C shortcut next to Copy", () => {
    const { container } = render(createElement(ContextMenu, baseProps()));
    const copy = item(container, "copy");
    expect(copy?.querySelector(".lvc-cm-key")?.textContent).toBe("⌃C");
  });

  it("is absolutely positioned at ({x, y})", () => {
    const { container } = render(createElement(ContextMenu, baseProps()));
    const root = container.firstElementChild as HTMLElement;
    expect(root.style.position).toBe("absolute");
    expect(root.style.left).toBe("12px");
    expect(root.style.top).toBe("34px");
  });

  it("clicks Copy and Copy Message command rows", () => {
    const props = baseProps();
    const { container } = render(createElement(ContextMenu, props));
    fireEvent.click(item(container, "copy") as HTMLElement);
    fireEvent.click(item(container, "copy-message") as HTMLElement);
    expect(props.onCopy).toHaveBeenCalledTimes(1);
    expect(props.onCopyMessage).toHaveBeenCalledTimes(1);
  });

  it("clicks the Pin, Unpin and Highlight command rows", () => {
    const props = { ...baseProps(), canUnpin: true };
    const { container } = render(createElement(ContextMenu, props));
    fireEvent.click(item(container, "pin") as HTMLElement);
    fireEvent.click(item(container, "unpin") as HTMLElement);
    fireEvent.click(item(container, "highlight") as HTMLElement);
    expect(props.onPin).toHaveBeenCalledTimes(1);
    expect(props.onUnpin).toHaveBeenCalledTimes(1);
    expect(props.onHighlight).toHaveBeenCalledTimes(1);
  });

  it("marks Unpin and Remove highlight as not applicable by default", () => {
    const { container } = render(createElement(ContextMenu, baseProps()));
    expect(item(container, "unpin")?.className).toContain("lvc-cm-dim");
    expect(item(container, "remove-highlight")?.className).toContain("lvc-cm-dim");
    expect(item(container, "pin")?.className).not.toContain("lvc-cm-dim");
    expect(item(container, "highlight")?.className).not.toContain("lvc-cm-dim");
  });

  it("does not run a not-applicable command", () => {
    const props = baseProps();
    const { container } = render(createElement(ContextMenu, props));
    fireEvent.click(item(container, "unpin") as HTMLElement);
    fireEvent.click(item(container, "remove-highlight") as HTMLElement);
    expect(props.onUnpin).not.toHaveBeenCalled();
    expect(props.onRemoveHighlight).not.toHaveBeenCalled();
  });

  it("enables Unpin when the selection contains pinned rows", () => {
    const props = { ...baseProps(), canUnpin: true };
    const { container } = render(createElement(ContextMenu, props));
    const unpin = item(container, "unpin") as HTMLElement;
    expect(unpin.className).not.toContain("lvc-cm-dim");
    fireEvent.click(unpin);
    expect(props.onUnpin).toHaveBeenCalledTimes(1);
  });

  it("enables Remove highlight when the selection contains highlighted rows", () => {
    const props = { ...baseProps(), canRemoveHighlight: true };
    const { container } = render(createElement(ContextMenu, props));
    const unhover = item(container, "remove-highlight") as HTMLElement;
    expect(unhover.className).not.toContain("lvc-cm-dim");
    fireEvent.click(unhover);
    expect(props.onRemoveHighlight).toHaveBeenCalledTimes(1);
  });

  it("dims a command whose handler is not wired yet (§4: pre-epic entries)", () => {
    // In the app shell Pin/Unpin and Highlight stay disabled until the pins
    // and highlights epics land: no handlers passed at all.
    const { container } = render(
      createElement(ContextMenu, {
        x: 0,
        y: 0,
        onCopy: vi.fn(),
        onCopyMessage: vi.fn(),
      }),
    );
    for (const name of ["unpin", "pin", "highlight", "remove-highlight"]) {
      expect(item(container, name)?.className).toContain("lvc-cm-dim");
    }
  });

  it("does nothing on a click for a command without a wired handler", () => {
    const onCopy = vi.fn();
    const { container } = render(
      createElement(ContextMenu, { x: 0, y: 0, onCopy, onCopyMessage: onCopy }),
    );
    // A not-applicable row ignores the click (no handler to run).
    fireEvent.click(item(container, "pin") as HTMLElement);
  });
});
