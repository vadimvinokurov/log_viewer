# Log Viewer Benchmarks

File: `~/log.txt` — 842 MB, 6,375,495 lines, 405 categories

## 2026-05-29 — Baseline

| # | Action | best (ms) | avg (ms) |
|---|--------|-----------|----------|
| **1** | **File loading** | | |
| | load_bytes (parse + build indices) | 661 | 682 |
| **2** | **Category toggle** | | |
| | disable big category (1.3M lines) | 44 | 45 |
| | enable big category | 21 | 21 |
| | disable small category (63 lines) | 52 | 52 |
| | enable small category | 21 | 21 |
| | disable all categories | 2 | 2 |
| | enable all categories | 21 | 21 |
| **3** | **Filter apply + toggle** | | |
| | add_filter PLAIN "cfg" (563 matches) | 175 | 367 |
| | toggle filter OFF + apply | 24 | 31 |
| | toggle filter ON + apply | 3 | 3 |
| | remove_filter | 23 | 24 |
| **4** | **Pin apply + toggle** | | |
| | add_pin PLAIN "cfg" | 214 | 222 |
| | toggle pin OFF + apply | 21 | 21 |
| | toggle pin ON + apply | 45 | 45 |
| | remove_pin + re-add | 235 | 237 |
| **5** | **Highlight apply + toggle** | | |
| | add_highlight | 0 | 0 |
| | remove_highlight | 0 | 0 |
| **6** | **Category toggle with active filter** | | |
| | disable big category (filter active) | 11 | 11 |
| | enable big category (filter active) | 3 | 3 |
| | disable all (filter active) | 2 | 2 |
| | enable all (filter active) | 3 | 3 |
| **7** | **Lazy buffer init** | | |
| | first filter (creates _buf_lower 842MB) | 174 | 354 |
| | second filter (cached) | 190 | 193 |

## Bottlenecks

1. **File load — 660ms**: parsing 842MB buffer
2. **_buf_lower creation — ~170ms**: one-time cost, lower() on entire 842MB buffer
3. **add_filter / add_pin — 175-215ms**: regex scan of 842MB buffer + searchsorted
4. **apply() mask recomputation — 20-45ms**: numpy operations on 6.4M element arrays
5. **disable category (no filter) — 44-52ms**: small category paradoxically slower than big, likely _set_enabled_recursive + np.isin cost

Highlights are instant (~0ms) — they only store rules, no mask recomputation.
