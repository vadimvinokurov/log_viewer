//! cmdline tests (bead 7rf.1, §13/§13.1): the pure command registry — parse
//! (optional ':'), argument extraction, validation with the verbatim §13.1
//! error texts, and the pure in-session history helpers (the persistent part
//! is 7rf.2).

import { describe, expect, it } from "vitest";
import {
  appendHistory,
  initialCmdlineState,
  parseCommand,
  recallHistory,
  resolveCommand,
} from "./cmdline";

describe("parseCommand (§13: text from the field IS a command)", () => {
  it("strips one optional leading ':'", () => {
    expect(parseCommand(":f timeout")).toEqual({ name: "f", arg: "timeout" });
    expect(parseCommand("f timeout")).toEqual({ name: "f", arg: "timeout" });
  });

  it("splits the command word at the first whitespace; the remainder is the arg verbatim", () => {
    expect(parseCommand(":fs  (\"auth\" OR \"login\")")).toEqual({
      name: "fs",
      arg: "(\"auth\" OR \"login\")",
    });
    // Quotes and inner spacing stay in the pattern; multi-space between the
    // word and the arg is the one separator.
    expect(parseCommand(":f  msg  12 ")).toEqual({ name: "f", arg: "msg  12" });
  });

  it("ignores leading whitespace before the optional colon", () => {
    expect(parseCommand("   :fr ^retry")).toEqual({ name: "fr", arg: "^retry" });
  });

  it("no-arg commands parse with an empty arg", () => {
    expect(parseCommand("rmf")).toEqual({ name: "rmf", arg: "" });
    expect(parseCommand("rmf   ")).toEqual({ name: "rmf", arg: "" });
  });

  it("empty / whitespace-only / ':'-only submissions are no-ops (null)", () => {
    expect(parseCommand("")).toBeNull();
    expect(parseCommand("   ")).toBeNull();
    // ':' alone is the activation text (§13 boundary), not a command.
    expect(parseCommand(":")).toBeNull();
    expect(parseCommand(":   ")).toBeNull();
  });
});

describe("resolveCommand registry (§13.1)", () => {
  it("maps the filter family: f/fr/fs pattern, fn number", () => {
    expect(resolveCommand("f timeout", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "filters", mode: "plain", pattern: "timeout" },
    });
    expect(resolveCommand(":fr ^retry.*", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "filters", mode: "regex", pattern: "^retry.*" },
    });
    expect(resolveCommand("fs \"auth\"", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "filters", mode: "simple", pattern: "\"auth\"" },
    });
    expect(resolveCommand(":fn 12", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "filters", mode: "lineno", pattern: "12" },
    });
  });

  it("maps the highlight family: h/hr/hs pattern, hn number", () => {
    expect(resolveCommand(":h timeout", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "highlights", mode: "plain", pattern: "timeout" },
    });
    expect(resolveCommand(":hr ^err", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "highlights", mode: "regex", pattern: "^err" },
    });
    expect(resolveCommand("hs pool", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "highlights", mode: "simple", pattern: "pool" },
    });
    expect(resolveCommand(":hn 7", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "highlights", mode: "lineno", pattern: "7" },
    });
  });

  it("maps the pin family: p/pr/ps pattern, pn number", () => {
    expect(resolveCommand(":p cfg", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "pins", mode: "plain", pattern: "cfg" },
    });
    expect(resolveCommand("pr release", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "pins", mode: "regex", pattern: "release" },
    });
    expect(resolveCommand(":ps a b", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "pins", mode: "simple", pattern: "a b" },
    });
    expect(resolveCommand(":pn 5", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "pins", mode: "lineno", pattern: "5" },
    });
  });

  it("rmf/rmh/rmp clear their area wholesale and accept no arguments", () => {
    expect(resolveCommand(":rmf", 100)).toEqual({
      ok: true,
      command: { kind: "clear", area: "filters" },
    });
    expect(resolveCommand(":rmh", 100)).toEqual({
      ok: true,
      command: { kind: "clear", area: "highlights" },
    });
    expect(resolveCommand("rmp", 100)).toEqual({
      ok: true,
      command: { kind: "clear", area: "pins" },
    });
    expect(resolveCommand("rmf oops", 100)).toEqual({
      ok: false,
      error: "Error: rmf takes no arguments",
    });
  });

  it("a non-command (empty / bare ':') resolves to the noop marker", () => {
    expect(resolveCommand("", 100)).toEqual({ ok: false, error: null, noop: true });
    expect(resolveCommand(":", 100)).toEqual({ ok: false, error: null, noop: true });
  });

  it("an unknown command name is the verbatim §13.1 error", () => {
    expect(resolveCommand(":xyz 1", 100)).toEqual({ ok: false, error: "Unknown command" });
    expect(resolveCommand("fnx 1", 100)).toEqual({ ok: false, error: "Unknown command" });
  });

  it("a missing required pattern is an error, not a wire call", () => {
    for (const name of ["f", "fr", "fs", "h", "hr", "hs", "p", "pr", "ps"]) {
      const result = resolveCommand(name, 100);
      expect(result).toEqual({ ok: false, error: `Error: ${name} requires a pattern` });
    }
    for (const name of ["fn", "hn", "pn"]) {
      const result = resolveCommand(name, 100);
      expect(result).toEqual({ ok: false, error: `Error: ${name} requires a line number` });
    }
  });

  it("fn/hn/pn require an integer in 1..line_count with the verbatim range text", () => {
    expect(resolveCommand("fn 101", 100)).toEqual({
      ok: false,
      error: "Error: fn 101 out of range (1..100)",
    });
    expect(resolveCommand("fn 0", 100)).toEqual({
      ok: false,
      error: "Error: fn 0 out of range (1..100)",
    });
    // A non-integer arg is the ARG-FORMAT error (the number is not even a
    // line number — live round on bead 7rf.1); the range text is reserved
    // for integers outside 1..N.
    expect(resolveCommand("hn abc", 100)).toEqual({
      ok: false,
      error: "Error: hn requires a line number",
    });
    expect(resolveCommand("pn -3", 100)).toEqual({
      ok: false,
      error: "Error: pn -3 out of range (1..100)",
    });
    expect(resolveCommand("fn 12.5", 100)).toEqual({
      ok: false,
      error: "Error: fn requires a line number",
    });
    expect(resolveCommand("hn 7x", 100)).toEqual({
      ok: false,
      error: "Error: hn requires a line number",
    });
    // The boundaries are inclusive.
    expect(resolveCommand("fn 1", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "filters", mode: "lineno", pattern: "1" },
    });
    expect(resolveCommand("pn 100", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "pins", mode: "lineno", pattern: "100" },
    });
    // A number with padding whitespace is accepted.
    expect(resolveCommand("hn  7  ", 100)).toEqual({
      ok: true,
      command: { kind: "add", area: "highlights", mode: "lineno", pattern: "7" },
    });
    // N reflects the ACTUAL line count.
    expect(resolveCommand("fn 60001", 60000)).toEqual({
      ok: false,
      error: "Error: fn 60001 out of range (1..60000)",
    });
  });
});

describe("in-session history helpers (§13.2, session part)", () => {
  it("appendHistory stores entries and skips consecutive duplicates and empties", () => {
    expect(appendHistory(["f a", "f b"], "f c")).toEqual(["f a", "f b", "f c"]);
    expect(appendHistory(["f a", "f b"], "f b")).toEqual(["f a", "f b"]);
    expect(appendHistory([], "")).toEqual([]);
    expect(appendHistory(["f a"], "")).toEqual(["f a"]);
    // A non-consecutive duplicate IS stored (plain chronological order).
    expect(appendHistory(["f a", "f b"], "f a")).toEqual(["f a", "f b", "f a"]);
  });

  it("appendHistory trims the entry and treats a whitespace-only entry as empty", () => {
    expect(appendHistory([], "   ")).toEqual([]);
    expect(appendHistory(["f a"], "  f a  ")).toEqual(["f a"]);
    expect(appendHistory(["f a"], "  f b  ")).toEqual(["f a", "f b"]);
  });

  it("recallHistory walks newest-first on up, then back down to the empty draft", () => {
    const history = ["f a", "f b", "f c"];
    // index = length means "the empty draft past the newest entry".
    expect(recallHistory(history, 3, -1)).toEqual({ index: 2, text: "f c" });
    expect(recallHistory(history, 2, -1)).toEqual({ index: 1, text: "f b" });
    expect(recallHistory(history, 1, -1)).toEqual({ index: 0, text: "f a" });
    // Clamped at the oldest entry.
    expect(recallHistory(history, 0, -1)).toEqual({ index: 0, text: "f a" });
    expect(recallHistory(history, 0, 1)).toEqual({ index: 1, text: "f b" });
    expect(recallHistory(history, 2, 1)).toEqual({ index: 3, text: "" });
    expect(recallHistory(history, 3, 1)).toEqual({ index: 3, text: "" });
  });

  it("recallHistory on an empty history stays at the empty draft", () => {
    expect(recallHistory([], 0, -1)).toEqual({ index: 0, text: "" });
    expect(recallHistory([], 0, 1)).toEqual({ index: 0, text: "" });
  });

  it("initialCmdlineState: empty field, empty history, cursor past the end", () => {
    expect(initialCmdlineState()).toEqual({ value: "", history: [], historyIndex: 0, focusTick: 0 });
    expect(recallHistory(initialCmdlineState().history, initialCmdlineState().historyIndex, -1))
      .toEqual({ index: 0, text: "" });
  });
});
