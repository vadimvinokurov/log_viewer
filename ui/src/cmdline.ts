//! Command line registry (FUNCTIONAL_SPEC §13/§13.1, bead 7rf.1). Pure
//! logic: parse + validate a submitted text against the §13.1 registry, plus
//! the pure in-session history helpers (the persistent store is 7rf.2). The
//! console wires the validated command onto the existing actions; the
//! component only renders and forwards keys.
//!
//! §13 boundary rule: the leading ':' is OPTIONAL in the field — everything
//! SUBMITTED from the field is treated as a command, including a text
//! without ':' ("text not starting with ':' is ignored" applies only at the
//! §13 ACTIVATION boundary, where pressing ':' over the table is the focus
//! hotkey, not command text). An empty (and a whitespace-only) submission is
//! a no-op; a bare ':' is the activation text, so it is a no-op too.

import type { FilterMode } from "./filtersTab";

/** §13.1 registry: the pattern commands carry the match mode (§5/§6), the
 *  number commands are lineno rules on the 1-based line number. */
export type CommandArea = "filters" | "highlights" | "pins";

/** A validated command: one wire action of the console (atomicity by
 *  construction — every §13.1 command is exactly one backend call). */
export type CliCommand =
  | { kind: "add"; area: CommandArea; mode: FilterMode; pattern: string }
  | { kind: "clear"; area: CommandArea };

export interface ParsedInput {
  /** §13.1 command name, verbatim ("f", "fn", "rmf", ...). */
  name: string;
  /** The remainder after the command word: the leading separator whitespace
   *  is skipped and the rest trimmed at the ends; inner spacing and quotes
   *  stay verbatim (patterns may contain spaces/quotes). */
  arg: string;
}

export type CommandResult =
  | { ok: true; command: CliCommand }
  | { ok: false; error: string }
  /** Not a command at all (§13: an empty/bare-':' submission) — a no-op,
   *  never a wire call and never a history entry. */
  | { ok: false; error: null; noop: true };

/** §13.1 validation texts. «Unknown command» and «Error: … out of range
 *  (1..N)» are verbatim from the spec, where the ellipsis reads as the
 *  command name and the INVALID INTEGER argument — chosen here as
 *  `<cmd> <arg>`. The spec leaves the other texts open; they follow the
 *  same register: a missing or NON-INTEGER number arg is the arg-format
 *  error, a missing pattern arg names the pattern, a Wholesale-clear
 *  command with an argument refuses it. */
export const ERROR_UNKNOWN = "Unknown command";

const rangeError = (name: string, arg: string, lineCount: number): string =>
  `Error: ${name} ${arg} out of range (1..${lineCount})`;

const patternError = (name: string): string => `Error: ${name} requires a pattern`;
const numberError = (name: string): string => `Error: ${name} requires a line number`;
const noArgsError = (name: string): string => `Error: ${name} takes no arguments`;

/** The §13.1 registry: name → action (pattern commands) and the wholesale
 *  clears (they accept no arguments — §13.1 "no other functions"). */
type PatternSpec = { area: CommandArea; mode: FilterMode };

const PATTERN_COMMANDS: ReadonlyMap<string, PatternSpec> = new Map([
  ["f", { area: "filters", mode: "plain" }],
  ["fr", { area: "filters", mode: "regex" }],
  ["fs", { area: "filters", mode: "simple" }],
  ["h", { area: "highlights", mode: "plain" }],
  ["hr", { area: "highlights", mode: "regex" }],
  ["hs", { area: "highlights", mode: "simple" }],
  ["p", { area: "pins", mode: "plain" }],
  ["pr", { area: "pins", mode: "regex" }],
  ["ps", { area: "pins", mode: "simple" }],
]);

const NUMBER_COMMANDS: ReadonlyMap<string, CommandArea> = new Map([
  ["fn", "filters"],
  ["hn", "highlights"],
  ["pn", "pins"],
]);

const CLEAR_COMMANDS: ReadonlyMap<string, CommandArea> = new Map([
  ["rmf", "filters"],
  ["rmh", "highlights"],
  ["rmp", "pins"],
]);

/** Splits a submitted text into a command word and its argument. null = the
 *  text is not a command at all: empty, whitespace-only, or the bare
 *  activation ':'. */
export function parseCommand(text: string): ParsedInput | null {
  const trimmed = text.trimStart();
  const stripped = trimmed.startsWith(":") ? trimmed.slice(1) : trimmed;
  const wordAt = stripped.search(/\S/);
  if (wordAt === -1) {
    return null; // empty / whitespace-only / a bare ':'
  }
  const rest = stripped.slice(wordAt);
  const endedAt = rest.search(/\s/);
  const name = endedAt === -1 ? rest : rest.slice(0, endedAt);
  const arg = endedAt === -1 ? "" : rest.slice(endedAt).trim();
  return { name, arg };
}

/** §13.1 validation. lineCount is the loaded file's line count (the fn/hn/pn
 *  range 1..line_count); commands are fully validated before any wire call. */
export function resolveCommand(text: string, lineCount: number): CommandResult {
  const parsed = parseCommand(text);
  if (parsed === null) {
    // Not a command (empty / whitespace-only / bare ':').
    return { ok: false, error: null, noop: true };
  }
  const { name, arg } = parsed;
  const patternSpec = PATTERN_COMMANDS.get(name);
  if (patternSpec) {
    if (arg === "") {
      return { ok: false, error: patternError(name) };
    }
    return { ok: true, command: { kind: "add", ...patternSpec, pattern: arg } };
  }
  const area = NUMBER_COMMANDS.get(name);
  if (area) {
    if (arg === "") {
      return { ok: false, error: numberError(name) };
    }
    const line = Number(arg);
    if (!Number.isInteger(line)) {
      // The arg is not even a line number (arg-format error); the verbatim
      // range text is reserved for INTEGER args outside 1..line_count.
      return { ok: false, error: numberError(name) };
    }
    if (line < 1 || line > Math.max(lineCount, 0)) {
      return { ok: false, error: rangeError(name, arg, Math.max(lineCount, 0)) };
    }
    return { ok: true, command: { kind: "add", area, mode: "lineno", pattern: arg } };
  }
  const clearArea = CLEAR_COMMANDS.get(name);
  if (clearArea) {
    if (arg !== "") {
      return { ok: false, error: noArgsError(name) };
    }
    return { ok: true, command: { kind: "clear", area: clearArea } };
  }
  return { ok: false, error: ERROR_UNKNOWN };
}

// ---- §13.2 in-session history (the persistent store is bead 7rf.2) ----

/** UI state slice of the command line: the field text, the in-session
 *  history (chronological; the last entry is the newest) and the recall
 *  cursor 0..history.length (length = the empty draft past the end). The
 *  focusTick bumps on the ':'-activation so the component can grab focus. */
export interface CmdlineState {
  value: string;
  history: string[];
  historyIndex: number;
  focusTick: number;
}

export function initialCmdlineState(): CmdlineState {
  return { value: "", history: [], historyIndex: 0, focusTick: 0 };
}

/** Appends one submitted entry to the history (§13.2 session part): empty
 *  and whitespace-only entries (not commands) are never stored, consecutive
 *  duplicates are collapsed, and the entry is stored trimmed. The copy is
 *  returned either way so callers can replace their reference. */
export function appendHistory(
  history: readonly string[],
  entry: string,
): string[] {
  const trimmed = entry.trim();
  if (trimmed === "" || history[history.length - 1] === trimmed) {
    return [...history];
  }
  return [...history, trimmed];
}

/** Unions the persistent history (the loaded store list, oldest first) with
 *  the session's own entries (§13.2, bead 7rf.2): chronological order, both
 *  sides trimmed and skipped-if-empty, consecutive duplicates collapsed
 *  across the seam. A session entry repeating an OLDER store entry is a
 *  non-consecutive duplicate and stays (plain chronology). */
export function mergeHistory(
  loaded: readonly string[],
  session: readonly string[],
): string[] {
  const merged: string[] = [];
  const append = (raw: string): void => {
    const trimmed = raw.trim();
    if (trimmed !== "" && merged[merged.length - 1] !== trimmed) {
      merged.push(trimmed);
    }
  };
  for (const entry of loaded) {
    append(entry);
  }
  for (const entry of session) {
    append(entry);
  }
  return merged;
}

/** One ↑/↓ step over the history (§13.2): up = older, down = newer; past
 *  the newest entry the field falls back to an empty string. dir −1 = up. */
export function recallHistory(
  history: readonly string[],
  index: number,
  dir: -1 | 1,
): { index: number; text: string } {
  const clamped = Math.max(0, Math.min(index, history.length));
  const next = Math.max(0, Math.min(clamped + dir, history.length));
  return { index: next, text: next === history.length ? "" : history[next] ?? "" };
}
