import { afterEach, describe, expect, it, vi } from "vitest";
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
// The explicit extension is load-bearing: a case-insensitive filesystem plus
// Vite's `.ts`-before-`.tsx` resolution order makes "./LevelBar" resolve to
// the logic module "levelBar.ts", losing the component export.
import { LevelBar, type LevelBarProps } from "./LevelBar.tsx";
import { LEVEL_LABELS, LEVEL_ORDER, formatCount } from "./levelBar";

afterEach(cleanup);

describe("formatCount (§11 count formatting, as in the UI_DESIGN mock)", () => {
  it("formats 0 as empty - the button shows no count", () => {
    expect(formatCount(0)).toBe("");
  });

  it("ignores negative and non-finite input as junk input", () => {
    for (const bad of [-1, -2041, Number.NaN, Infinity, -Infinity]) {
      expect(formatCount(bad)).toBe("");
    }
    // The visibility engine only delivers integer counts, so a fractional
    // input has no defined meaning and is not pinned by a test here.
  });

  it("keeps plain numbers under 1000 ungrouped", () => {
    expect(formatCount(3)).toBe("3");
    expect(formatCount(172)).toBe("172");
    expect(formatCount(999)).toBe("999");
  });

  it("groups thousands with a thin space up to 9 999", () => {
    expect(formatCount(1000)).toBe("1" + " " + "000");
    expect(formatCount(2041)).toBe("2" + " " + "041");
    expect(formatCount(9999)).toBe("9" + " " + "999");
  });

  it("switches to whole k at exactly 10 000", () => {
    expect(formatCount(10_000)).toBe("10k");
    expect(formatCount(10_001)).toBe("10k");
    expect(formatCount(14_000)).toBe("14k");
  });

  it("matches the mock k values", () => {
    expect(formatCount(96_000)).toBe("96k");
    expect(formatCount(405_000)).toBe("405k");
    expect(formatCount(611_000)).toBe("611k");
    expect(formatCount(681_000)).toBe("681k");
    expect(formatCount(999_000)).toBe("999k");
    // 999 500..999 999 would round to "1000k" - it must promote to M.
    expect(formatCount(999_999)).toBe("1.0M");
  });

  it("switches to one-decimal M from 1M upward", () => {
    expect(formatCount(1_000_000)).toBe("1.0M");
    expect(formatCount(1_049_000)).toBe("1.0M");
    expect(formatCount(1_050_000)).toBe("1.1M");
    expect(formatCount(4_200_000)).toBe("4.2M");
    expect(formatCount(6_400_000)).toBe("6.4M");
    expect(formatCount(9_999_999)).toBe("10.0M");
  });
});

describe("LEVEL_ORDER (§11 fixed button order)", () => {
  it("is critical, error, warning, msg, debug, trace", () => {
    expect([...LEVEL_ORDER]).toEqual([
      "critical",
      "error",
      "warning",
      "msg",
      "debug",
      "trace",
    ]);
  });

  it("has a caption for every level", () => {
    for (const level of LEVEL_ORDER) {
      expect(LEVEL_LABELS[level]).toBe(level.toUpperCase());
    }
    expect(LEVEL_LABELS.msg).toBe("MSG");
  });
});

describe("LevelBar component (§11)", () => {
  const baseProps = (): LevelBarProps => ({
    counts: {
      critical: 3,
      error: 172,
      warning: 2041,
      msg: 4_200_000,
      debug: 681_000,
      trace: 96_000,
    },
    enabled: {
      critical: true,
      error: true,
      warning: false,
      msg: true,
      debug: true,
      trace: true,
    },
    onToggle: vi.fn(),
  });

  const buttons = (container: HTMLElement): HTMLButtonElement[] =>
    Array.from(container.querySelectorAll("button"));

  it("renders six buttons in the fixed §11 order with formatted counts", () => {
    const { container } = render(createElement(LevelBar, baseProps()));
    const captions = buttons(container).map(
      (b) => b.getAttribute("aria-label") ?? "",
    );
    expect(captions).toEqual([
      "CRITICAL",
      "ERROR",
      "WARNING",
      "MSG",
      "DEBUG",
      "TRACE",
    ]);
    expect(buttons(container)[2].textContent).toContain("2" + " " + "041");
    expect(buttons(container)[3].textContent).toContain("4.2M");
  });

  it("mirrors the enabled map into aria-pressed", () => {
    const { container } = render(createElement(LevelBar, baseProps()));
    expect(buttons(container).map((b) => b.getAttribute("aria-pressed"))).toEqual([
      "true",
      "true",
      "false",
      "true",
      "true",
      "true",
    ]);
  });

  it("clicking a button toggles exactly that level", () => {
    const onToggle = vi.fn();
    const props = { ...baseProps(), onToggle };
    const { container } = render(createElement(LevelBar, props));
    buttons(container)[2].click();
    buttons(container)[4].click();
    expect(onToggle.mock.calls).toEqual([["warning"], ["debug"]]);
  });

  it("hides the count when the count is 0", () => {
    const props = baseProps();
    props.counts = { critical: 0, error: 0, warning: 0, msg: 0, debug: 0, trace: 0 };
    const { container } = render(createElement(LevelBar, props));
    for (const button of buttons(container)) {
      expect(button.querySelector("[data-level-count]")).toBeNull();
      // Only dot and caption remain - no digit anywhere in the label.
      expect(/\d/.test(button.textContent ?? "")).toBe(false);
    }
  });

  it("dims a disabled level and strikes its count", () => {
    const { container } = render(createElement(LevelBar, baseProps()));
    const warning = buttons(container)[2];
    const msg = buttons(container)[3];
    expect(warning.getAttribute("aria-pressed")).toBe("false");
    expect(warning.style.opacity).toBe("0.45");
    const warningCount = warning.querySelector("[data-level-count]") as HTMLElement | null;
    expect(warningCount?.style.textDecorationLine).toBe("line-through");
    // Enabled level: no dimming, no strikethrough.
    expect(msg.getAttribute("aria-pressed")).toBe("true");
    expect(msg.style.opacity).not.toBe("0.45");
    const msgCount = msg.querySelector("[data-level-count]") as HTMLElement | null;
    expect(msgCount?.style.textDecorationLine).not.toBe("line-through");
  });

  it("uses button elements so keyboard toggling works", () => {
    const onToggle = vi.fn();
    const props = { ...baseProps(), onToggle };
    const { container } = render(createElement(LevelBar, props));
    const trace = buttons(container)[5];
    expect(trace.tagName).toBe("BUTTON");
    fireEvent.keyDown(trace, { key: "Enter" });
    fireEvent.click(trace);
    expect(onToggle).toHaveBeenCalledWith("trace");
  });
});
