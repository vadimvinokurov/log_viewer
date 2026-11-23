//! Showcase entries for the Filters tab (?show=filters): the visual harness
//! variants of FUNCTIONAL_SPEC §10.1 (empty, mixed on/off, all off) fed with
//! fixed demo filters; callbacks are no-ops (wiring lands with dsq.3).

import { FiltersTab, type FilterItem, type FilterMode } from "../FiltersTab.tsx";

function item(id: number, mode: FilterMode, pattern: string, enabled: boolean): FilterItem {
  return { id, mode, pattern, enabled };
}

function list(items: FilterItem[]) {
  return <FiltersTab items={items} onToggle={() => {}} onRemove={() => {}} />;
}

export const filtersShowcase: Record<string, React.ReactNode> = {
  empty: list([]),
  "mixed 2 on 1 off": list([
    item(1, "plain", '"timeout"', true),
    item(2, "simple", '("auth" + "login") + ~"db"', true),
    item(3, "regex", "^connection .*refused after \\d+ retries on .*pool$", false),
  ]),
  "all-off": list([
    item(4, "plain", '"timeout"', false),
    item(5, "lineno", "12034", false),
    item(6, "simple", '("auth" + "login") + ~"db"', false),
    item(7, "regex", "^retry", false),
  ]),
};
