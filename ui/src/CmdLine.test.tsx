//! CmdLine tests (bead 7rf.1, §13/§11.1; markup per docs/UI_DESIGN.html
//! "Command line" component study and the bbar mock — `.cmd`/`.dot` classes
//! copied verbatim). Presentational: state comes in as props; App wires the
//! console and the global ':' keydown.

import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { CmdLine, type CmdLineProps } from "./CmdLine.tsx";
import { initialCmdlineState, type CmdlineState } from "./cmdline";

afterEach(cleanup);

function cmdlineState(overrides: Partial<CmdlineState> = {}): CmdlineState {
  return { ...initialCmdlineState(), value: "", historyIndex: 0, ...overrides };
}

function baseProps(overrides: Partial<CmdLineProps> = {}): CmdLineProps {
  return {
    command: cmdlineState(),
    onText: vi.fn(),
    onSubmit: vi.fn(),
    onClear: vi.fn(),
    onRecall: vi.fn(),
    ...overrides,
  };
}

describe("CmdLine (bead 7rf.1, §13)", () => {
  it("renders the .cmd markup: input with the §11.1 placeholder and value from the store (no static prompt — the user types ':' themselves)", () => {
    const { container } = render(
      createElement(CmdLine, baseProps({ command: cmdlineState({ value: "" }) })),
    );
    const bar = container.querySelector(".cmd");
    expect(bar).not.toBeNull();
    // 2026-11-25 decision (owner, UI design page): no pre-filled ':' prompt —
    // the user types it themselves, an empty field is empty.
    expect(bar?.querySelector(".dot")).toBeNull();
    const input = bar?.querySelector<HTMLInputElement>("input");
    expect(input).not.toBeNull();
    expect(input?.placeholder).toBe(":type command...");
    expect(input?.value).toBe("");
    expect(input?.getAttribute("aria-label")).toBe("Command line");
  });

  it("typing dispatches onText with the typed text", () => {
    const props = baseProps();
    const { container } = render(createElement(CmdLine, props));
    const input = container.querySelector<HTMLInputElement>(".cmd input");
    if (!input) throw new Error("input missing");
    input.focus();
    fireEvent.change(input, { target: { value: ":h err" } });
    expect(props.onText).toHaveBeenCalledWith(":h err");
  });

  it("Enter submits; Esc clears; the field types ':' normally (no keydown hijack)", () => {
    const props = baseProps();
    const { container } = render(createElement(CmdLine, props));
    const input = container.querySelector<HTMLInputElement>(".cmd input");
    if (!input) throw new Error("input missing");
    input.focus();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(props.onSubmit).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(input, { key: "Escape" });
    expect(props.onClear).toHaveBeenCalledTimes(1);
    // ':' inside the field must NOT trigger the activation callbacks
    // (Enter above keeps its single call, nothing else fires).
    fireEvent.keyDown(input, { key: ":" });
    expect(props.onSubmit).toHaveBeenCalledTimes(1);
    expect(props.onClear).toHaveBeenCalledTimes(1);
    expect(props.onRecall).not.toHaveBeenCalled();
  });

  it("↑ recalls older and ↓ newer while the focus sits in the field", () => {
    const props = baseProps();
    const { container } = render(createElement(CmdLine, props));
    const input = container.querySelector<HTMLInputElement>(".cmd input");
    if (!input) throw new Error("input missing");
    input.focus();
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(props.onRecall).toHaveBeenLastCalledWith(-1);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(props.onRecall).toHaveBeenLastCalledWith(1);
  });

  it("the ':' activation (focusTick) focuses the input with the caret after the ':'", () => {
    const { container, rerender } = render(createElement(CmdLine, baseProps()));
    const input = container.querySelector<HTMLInputElement>(".cmd input");
    if (!input) throw new Error("input missing");
    expect(document.activeElement).not.toBe(input);
    rerender(
      createElement(CmdLine, baseProps({ command: cmdlineState({ value: ":", focusTick: 1 }) })),
    );
    expect(document.activeElement).toBe(input);
    expect(input.selectionStart).toBe(1);
    expect(input.selectionEnd).toBe(1);
  });
});
