//! Pure pin logic (q1f.1, §12 + §4 menu presence): canonical command
//! strings and the context-menu availability evaluation over the
//! snapshot's pin list. Hand-computed expectations, no mocks.

import { describe, expect, it } from "vitest";
import {
  exactPinIdsCovering,
  pinCommand,
  pinMenuState,
  type PinItem,
  type SelectedRow,
} from "./pins";

const PINS: PinItem[] = [
  { id: 0, mode: "lineno", pattern: "5", enabled: true }, // exact: line 5
  { id: 1, mode: "plain", pattern: "ERROR", enabled: true }, // broad
  { id: 2, mode: "simple", pattern: "boom", enabled: true }, // never evaluated (§12 design note)
  { id: 3, mode: "lineno", pattern: "9", enabled: false }, // disabled: inert
];

const row = (line: number, raw: string): SelectedRow => ({ line, raw });

describe("pinCommand (§12 command text in the Pinned tab)", () => {
  it("maps the four pin modes to the :p/:pr/:ps/:pn prefixes", () => {
    expect(pinCommand({ id: 0, mode: "plain", pattern: "cfg", enabled: true })).toBe(":p cfg");
    expect(pinCommand({ id: 1, mode: "regex", pattern: "^retry", enabled: true })).toBe(":pr ^retry");
    expect(pinCommand({ id: 2, mode: "simple", pattern: "db", enabled: true })).toBe(":ps db");
    expect(pinCommand({ id: 3, mode: "lineno", pattern: "12", enabled: true })).toBe(":pn 12");
  });
});

describe("exactPinIdsCovering (menu Unpin targets)", () => {
  it("names the enabled exact-row pins whose line is among the selection", () => {
    expect(exactPinIdsCovering(PINS, [5])).toEqual([0]);
    expect(exactPinIdsCovering(PINS, [5, 12])).toEqual([0]);
    expect(exactPinIdsCovering(PINS, [5, 5])).toEqual([0]); // deduped
  });

  it("ignores disabled pins and broad pins and foreign lines", () => {
    expect(exactPinIdsCovering(PINS, [9])).toEqual([]); // pin 3 disabled
    expect(exactPinIdsCovering(PINS, [])).toEqual([]);
    // Broad pins never appear: the menu never removes a rule matching an
    // unknown number of rows (q1f1-design).
    expect(exactPinIdsCovering([PINS[1] as PinItem], [7])).toEqual([]);
  });
});

describe("pinMenuState (§4 presence interpretation)", () => {
  it("Pin lights for an unpinned row, Unpin for a covered one; exact targets listed", () => {
    // line 5 covered by exact pin 0, line 7 by broad pin 1, line 9 by none.
    const state = pinMenuState(PINS, [row(5, "ok"), row(7, "See ERROR here"), row(9, "plain")]);
    expect(state).toEqual({ canPin: true, canUnpin: true, exactPinIds: [0] });
  });

  it("every selected row pinned -> Pin dims, Unpin stays", () => {
    const state = pinMenuState(PINS, [row(5, "x"), row(7, "ERROR y")]);
    expect(state).toEqual({ canPin: false, canUnpin: true, exactPinIds: [0] });
  });

  it("nothing pinned -> Unpin dims, Pin stays (disabled pin is inert)", () => {
    const state = pinMenuState(PINS, [row(9, "a"), row(11, "b")]);
    expect(state).toEqual({ canPin: true, canUnpin: false, exactPinIds: [] });
  });

  it("documented limitation: a simple-mode pin never makes a row pinned for the menu", () => {
    const state = pinMenuState([{ id: 2, mode: "simple", pattern: "boom", enabled: true }], [
      row(3, "it will boom"),
    ]);
    expect(state).toEqual({ canPin: true, canUnpin: false, exactPinIds: [] });
  });

  it("broad regex pins cover raw matches; an invalid regex covers nothing", () => {
    const regexPins: PinItem[] = [
      { id: 0, mode: "regex", pattern: "^ERR", enabled: true },
      { id: 1, mode: "regex", pattern: "(unclosed", enabled: true },
    ];
    expect(pinMenuState(regexPins, [row(4, "ERROR text"), row(6, "ERROR other")])).toEqual({
      canPin: false,
      canUnpin: true,
      exactPinIds: [],
    });
    // The broken pattern does not make its row pinned for the menu.
    expect(pinMenuState(regexPins, [row(7, "broken (unclosed")])).toEqual({
      canPin: true,
      canUnpin: false,
      exactPinIds: [],
    });
  });

  it("an empty selection dims both (no selection - no menu, §4)", () => {
    expect(pinMenuState(PINS, [])).toEqual({ canPin: false, canUnpin: false, exactPinIds: [] });
  });
});
