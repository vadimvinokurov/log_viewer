//! Pure logic for the Filters side-panel tab (FUNCTIONAL_SPEC §10.1).
//! No React here: the component (FiltersTab.tsx) renders, this module
//! defines the data shape and the canonical command strings.

/** Filter kinds accepted by the :f / :fr / :fs / :fn commands. */
export type FilterMode = "plain" | "regex" | "simple" | "lineno";

export interface FilterItem {
  id: number;
  mode: FilterMode;
  /** Pattern text; for lineno this is the line-number literal. */
  pattern: string;
  enabled: boolean;
}

/** Command prefix per filter mode (§13 command line, §10.1 panel display). */
const PREFIX: Record<FilterMode, string> = {
  plain: ":f ",
  regex: ":fr ",
  simple: ":fs ",
  lineno: ":fn ",
};

/** Canonical command string that created the filter, e.g. `:fr ^retry`. */
export function filterCommand(item: FilterItem): string {
  return PREFIX[item.mode] + item.pattern;
}
