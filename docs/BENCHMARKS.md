# BENCHMARKS (bead log_viewer2-7no.1, perf epic)

Criterion benches over the real `test_logs/` corpus. Harness:
`crates/logviewer-core/benches/corpus.rs`. The fixtures live in the local,
never-committed `test_logs/` folder (repo rule 1); when they are absent the
corresponding groups are skipped, so the bench binary never panics on a
machine without them.

## How to run

```bash
cargo bench -p logviewer-core   # from the workspace root
```

Per-group filtering (criterion): `cargo bench -p logviewer-core -- search_big`
etc. Compare runs: `cargo bench -- --save-baseline <name>` /
`--baseline <name>`.

## Machine / toolchain

- Model: Apple M4 (laptop, macOS power defaults)
- OS: macOS 27.0.1
- Compiler: rustc 1.99.1 (Homebrew), workspace edition 2024
- Criterion 0.5, release bench profile

## Corpus (facts only: paths, counts, formats — no contents)

Fixture paths are resolved as `<repo>/test_logs/<name>`. Short labels used in
bench group names:

| label | file | bytes | lines | format (§3) | avg line length |
|-------|------|-------|-------|-------------|-----------------|
| small | `TitleId-YBA91-Ksiva-6d865.txt` | 5,652,932 | 37,989 | A (ksiva) | ~149 B |
| big   | `log.txt` | 183,230,383 | 1,294,246 | B (plain) | ~142 B |

(The spec's rough shapes said "6.4M lines"; the measured corpus holds
1.29M lines on the big file. Categories count was not instrumented here.)

Search-pattern hit counts (the patterns are deliberately generic digit
patterns, chosen so no corpus content is ever copied into this repo — they
match timestamps of any log; treat the numbers as an upper-bound cost):

| matcher | big: matching lines of 1,294,246 visible |
|---------|------------------------------------------|
| plain `"0"` | 1,203,250 |
| regex `[0-9]+` | 1,294,246 |
| simple `"0"` | 1,203,250 |

Small file: all three match 37,989 of 37,989.

## Baselines (medians, single consistent run, warm machine)

Stages mirror the shell's real call paths (`src-tauri/src/ipc.rs`):
visibility = `visible_lines` recompute after a mutation; search = one pass
over the shell-cached visible list (`search_visible_inner`); highlight =
`highlights::row_spans` over a 10k-row window; get_rows = a 1000-row window at
50% of the cached visible list, lookup + field clones as the DTO conversion
does. Throughput is per row unless stated (GiB/s for scan).

| stage | small | big |
|-------|-------|-----|
| scan / open (mmap + offsets + format) | 519 µs (~10 GiB/s) | 24.2 ms (7.1 GiB/s) |
| scan / offsets only | 295 µs | 12.0 ms |
| scan / format detect | 28 ns | 72 ns |
| load whole file (setup, scan+parse+rollups) | 13 ms | 384 ms |
| parse 100k window, cold sweep | 9.54 ms (~4.0 Mrows/s) | 23.2 ms (~4.3 Mrows/s) |
| parse 100k window, warm | 9.59 ms | 22.1 ms |
| visibility recompute, empty whitelist (fresh default) | 2.06 ms | 59.6 ms |
| visibility recompute, all categories | 9.78 ms | 153.8 ms |
| visibility recompute, all categories + one plain filter | 9.69 ms | 222.4 ms |
| search plain over the full visible set | 4.36 ms | 135.8 ms |
| search regex over the full visible set | 2.36 ms | 77.4 ms |
| search simple over the full visible set | 3.03 ms | 98.8 ms |
| highlight spans, plain rule, 10k rows | 596 µs | 496 µs |
| highlight spans, regex rule, 10k rows | 2.35 ms | 1.13 ms |
| highlight spans, simple rule, 10k rows | 1.03 ms | 825 µs |
| get_rows, 1000 rows at 50% of visible | 17.9 µs | 15.7 µs |

Run notes: heavy groups (visibility, search on the big file) used 10 samples
per criterion's auto-adjust; the rest used the group default (20/100). The
second full run was compared to the first by criterion — the
`all_categories` whitelist grew ancestors between runs (fidelity fix), so the
relative-change lines of that run are meaningless; the absolute medians above
are from the second run only.

## Hot-spots (one line per file)

- **big (175 MB):** visibility full recompute is the slowest actionable
  stage — 154 ms per mutation (222 ms with one plain filter), and the shell
  pays a *second* full pass for the §11 level counters on every
  visibility snapshot (`level_counts_excluding_levels` right after
  `ensure_visible_cache`); search over the full visible set is next at
  77–136 ms; everything windowed (parse 23 ms/100k, highlight ≤1.2 ms/10k,
  get_rows 16 µs/1000) is already instant-class.
- **small (5.4 MB):** no hot spot — worst stage is 4.4 ms (search plain),
  everything else ≤ 10 ms; the file is instant on this stage set.

## Follow-up: the 3 cheapest wins (measurement only — not implemented here)

1. **Intern category paths into ids + an id→allowed bitmap** — where:
   `visibility.rs::category_allowed` (with a category-id table built once in
   `workspace.rs::FileModel` at load). Why: every `visible_lines` iteration
   runs 1–3 `BTreeSet<String>` lookups per row over freshly-owned strings;
   with all categories enabled that is ~1.3M hash lookups + ancestor walks on
   the big file; a bitmap hit replaces them. Expected rough factor: ~2x on the
   154 ms all-categories recompute (also trims the 60 ms empty-whitelist
   floor slightly); filter/search paths see the same benefit because the same
   category check runs in `visit_pre_level`.
2. **One shared walk for visible_lines + level_counts** — where:
   `visibility.rs` (`visit_pre_level` already centralizes the row filter) +
   `src-tauri/src/ipc.rs::visibility_snapshot_inner`. Why: today every
   visibility mutation costs two full O(N) passes on the next snapshot
   (`visible_lines` 154 ms + `level_counts_excluding_levels`, another full
   walk) although both consume exactly the same pre-filter row stream.
   Expected rough factor: ~2x on aggregate mutation latency (one 154 ms-class
   pass instead of two); trivial refactor because the sink closure already
   receives every visited row.
3. **Incremental per-mechanism sets for single-toggle mutations** — where:
   `visibility.rs`. Why: levels/categories/filters each have a fixed membership
   that can be materialized as bitsets once at load (per-level and
   per-category bitsets are filter-independent; enabling a *filter* is the
   only row-text-dependent set). A level or category toggle then becomes a
   set operation over bitsets instead of a re-visit of 1.3M rows with the
   matcher and the lossy conversion per row. Expected rough factor: ~5–20x
   for toggles (222 ms → tens of ms class); filter pattern edits and new
   filters still need one real pass, so this does not replace win 1.
