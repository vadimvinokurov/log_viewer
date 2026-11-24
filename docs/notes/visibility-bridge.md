# dsq.3 visibility bridge — IPC contract (RAW shapes)

Status: contract fixed 2026-11-24; conclusions recorded in the bead (`bd update
log_viewer2-dsq.3 --design`). RAW = exactly what Tauri returns; normalization
to UI shapes happens only in `ui/src/ipcClient.ts` (=PIPELINE conventions).

## Commands to add (snake_case names, specta schemas)

- `add_filter(mode, pattern)` / `add_pin(mode, pattern)` — `mode` ∈
  `plain | regex | simple | lineno` (same strings as `filtersTab.ts` FilterMode).
  Invalid pattern (bad regex, non-numeric lineno) matches nothing — `never()`.
- `set_filter_enabled(id, on)` / `set_pin_enabled(id, on)` — `id` = index in the
  filters/pins list of the LATEST snapshot. Out of range → `Err("no such filter")`
  style message, never a panic (core panics by design on Vec::remove).
- `remove_filter(id)` / `remove_pin(id)`
- `set_level_enabled(level, on)` — level = lowercase long name
  (`critical..trace`, mirrors `level_name`).
- `set_category_enabled(path, on)` — full path string.
- `visibility_snapshot() -> VisibilitySnapshot` — the single read command.
- `get_rows(offset, limit)` — RESHAPED: `offset` indexes the VISIBLE sequence
  (rows passing §7), not raw line numbers. Shell caches the visible-line list,
  invalidated on every visibility mutation and on file load.

## VisibilitySnapshot (RAW, snake_case)

```ts
{
  visible_count: number;
  levels: { level: string; enabled: boolean; count: number }[]; // fixed order critical..trace; count = §11 semantics (level toggles ignored)
  filters:  { id: number; mode: string; pattern: string; enabled: boolean }[];
  pins:     { id: number; mode: string; pattern: string; enabled: boolean }[];
  categories_enabled: string[];
}
```

No file loaded: `visible_count` 0, level counts 0, toggles/filters/pins as
stored; `get_rows` returns `[]` (current behavior).

## Shell state and policy decisions (final)

1. Source command strings stay UI-derived: `filtersTab.filterCommand(mode,
   pattern)` is the single canonicalizer — the backend does not store text.
2. Pins get `set_pin_enabled` now for the future Pinned tab (§10.1); UI wiring
   lands with q1f.1.
3. Shell keeps a `disabled_categories` set; on load the core whitelist is
   repopulated as `model.categories() − disabled` (§2.1/§10: disabled categories
   survive reload by name; new categories start enabled). Rows with no category
   carry the parser path `uncategorized` — covered by `model.categories()`.
   Levels, filters, pins simply persist in the Visibility object across reloads.
4. `LevelBar` goes into the real app footer (§11 right side of the bottom bar).
   `FiltersTab` consumes snapshot data in the dev showcase until the side-panel
   shell exists (rhl.2 owns the panel); add/toggle/remove flow through console
   actions + headless RPC either way.
5. Filter changes move selection by line number and the viewport anchor issue
   to qt7.3 (same §4 bullet); dsq.3 only resets the chunk cache on a visibility
   change (new `visibilityEpoch` prop, NOT rowCount — equal-count changes still
   reload chunks) and keeps scrollTop for qt7.3 to anchor.
