# Core Engine Redesign — Lazy Parsing + Raw Buffer Search

**Date:** 2026-05-29
**Scope:** `core/` only. GUI adapts to new API.

## Problem

Benchmarks on 842 MB / 6.4M line file:

| Operation | Time | Verdict |
|---|---|---|
| File loading | 966 ms | OK |
| Plain filter | 195 ms | Acceptable |
| Regex filter | **11.88 s** | Catastrophic |
| Simple query | 452 ms | Slow |
| Toggle filter | 5-6 ms | Good |

Root causes:
1. LogStore is a god-class (~760 lines) doing storage, filtering, search, categories, pins.
2. Regex uses bytes+IGNORECASE — Python has no lookup tables for this, checks every byte.
3. Simple query re-scans entire buffer for each term, no cross-query caching.
4. Eager parsing: message_spans and timestamp_spans computed for all 6.4M lines at load time, used only for filtering/search. Display needs ~50 rows.

## Design

### 1. Lazy parsing — parse only category + level at load time

**Two-pass loading:**

Pass 1 — count lines, pre-allocate numpy arrays:
```
line_starts = scan_line_starts_fast(buf)   # numpy SIMD, uint64[n+1]
n = len(line_starts) - 1
category_ids = np.empty(n, dtype=uint16)
levels       = np.empty(n, dtype=uint8)
```

Pass 2 — minimal parse per line:
```
for i in range(n):
    raw = buf[line_starts[i]:line_starts[i+1]]
    category_ids[i], levels[i] = parse_minimal(raw)
```

Cython version does the same without Python overhead.

**LogStore after loading:**
```
_buf             : bytearray        # entire file, single chunk
_buf_lower       : bytes            # cached lowered buffer (created in load_bytes)
_buf_str         : str | None       # cached decoded string (lazy, for regex)
line_starts      : ndarray[uint64]  # n+1, line boundaries
category_ids     : ndarray[uint16]  # n, category ID per line
levels           : ndarray[uint8]   # n, level ID per line
_category_names  : list[str]        # ID → name mapping
```

**Removed:**
- message_spans (SPAN_DTYPE × n) — search on full buffer instead
- timestamp_spans (SPAN_DTYPE × n) — lazy parse at render time
- timestamps (uint64 × n) — legacy, unused

Memory savings: ~200 MB for 6.4M lines (two SPAN_DTYPE arrays removed).

### 2. Search/filter/pin — on entire raw buffer

All text matching operates on the full file buffer. When a match is found at byte position P, binary search (`np.searchsorted`) maps it to a line index.

```python
def _compute_mask(self, store, filt):
    positions = regex.finditer(store._buf_lower)  # all match positions
    line_indices = np.searchsorted(store.line_starts, positions, side="right") - 1
    mask = np.zeros(store.n, dtype=bool)
    mask[line_indices] = True
    return mask
```

No `in_msg` boundary check. A match anywhere in the line (timestamp, category, level, message) counts as a hit. This is simpler and matches what the user sees.

### 3. Lazy column parsing — only for visible rows

Rendering (~50 visible rows) calls:
```python
def get_columns(self, index: int) -> tuple[str, str, str, str]:
    """Return (timestamp, category, level, message) for one line."""
    raw = self._buf[line_starts[index]:line_starts[index+1]]
    return parse_columns(raw)   # split by whitespace, ~microsecond
```

Called from `LogTableModel.data()` — only for viewport cells.

Highlighting (`HighlightDelegate`): `find_spans()` also operates on the full line string. Highlights can color any part of the line.

### 4. Regex fix — string regex instead of bytes regex

Current (12s):
```python
combined = re.compile(pattern.encode("utf-8"), re.IGNORECASE)  # bytes regex = slow
search_buf = self._buf
```

Fixed (~200ms):
```python
if store._buf_str is None:
    store._buf_str = store._buf.decode("utf-8", errors="replace")
combined = re.compile(pattern, re.IGNORECASE)  # string regex = fast
search_buf = store._buf_str
```

`_buf_str` is lazily created on first regex request, invalidated on `load_bytes()`.
Memory cost: ~800 MB for 842 MB file, only when user uses regex filters.

### 5. Simple query optimization — term mask cache

```python
class FilterPipeline:
    _term_cache: dict[str, ndarray]  # term → bool mask (length n)
```

On `_compute_mask(SIMPLE)`:
1. Parse AST, `collect_terms()` → unique terms
2. Check `_term_cache` — skip scan if already cached
3. New terms: scan `_buf_lower`, store mask in cache
4. `ast.eval_masks(term_masks, n)` — unchanged

Cache invalidated on `load_bytes()`. Typical session: 20-30 unique terms × ~6 MB/mask = 120-180 MB.

### 6. Class separation

```
LogStore (storage + access)
  - buf, buf_lower, buf_str, line_starts, category_ids, levels
  - category tree and mapping
  - level counting
  - load_bytes(), get_columns(), get_raw()
  - Public field: filtered_indices (set by pipeline)

FilterPipeline (filtering)
  - filters, highlights, pins + masks + enabled flags
  - disabled_levels, disabled_categories
  - _compute_mask(), apply()
  - add/remove/toggle filters, highlights, pins, levels, categories
  - _term_cache for simple query

SearchEngine (search)
  - search(store, pattern, mode, direction, start_line)
  - next_match(), prev_match(), clear_search()
  - search_state
```

```
core/
  log_store.py        # LogStore — data storage
  filter_pipeline.py  # FilterPipeline — filtering
  search_engine.py    # SearchEngine — search navigation
  filter_engine.py    # Low-level matching (match, find_spans) — unchanged
  simple_query.py     # AST parser — unchanged
  parser.py           # Line parsing — minimal changes
  models.py           # Data classes — add _compiled to Filter
```

### 7. Data flow

```
MainWindow
  │
  ├─ store.load_bytes(buf)
  │    ├─ scan_line_starts_fast()         # pass 1: count + allocate
  │    ├─ parse_minimal_batch()           # pass 2: category + level only
  │    ├─ _buf_lower = bytes(buf).lower() # eager, for plain search
  │    └─ pipeline.apply(store)           # compute filtered_indices
  │
  ├─ pipeline.add_filter(filt)
  │    ├─ _compute_mask(store, filt)
  │    └─ pipeline.apply(store)
  │
  ├─ search_engine.search(store, pattern, mode)
  │    ├─ pipeline._compute_mask(store, Filter(pattern, mode))
  │    └─ SearchState(matches, current_index)
  │
  └─ pipeline.toggle_level(level)
       └─ pipeline.apply(store)
```

### 8. Pre-compiled regex

Store compiled pattern on Filter to avoid re-compilation:
```python
@dataclass
class Filter:
    pattern: str
    mode: SearchMode
    _compiled: re.Pattern | None = None   # lazy, cached
```

### 9. What does NOT change

- parser.py — minimal changes (add parse_minimal, keep parse_line for backward compat)
- simple_query.py — no changes
- filter_engine.py — no changes (used by highlight delegate for find_spans on visible rows)
- models.py — add _compiled field to Filter
- GUI — point adaptation (store.add_filter → pipeline.add_filter, etc.)

### 10. Expected performance

| Operation | Before | After (estimated) |
|---|---|---|
| File loading | 966 ms | ~800 ms (less parsing) |
| Regex filter | 11.88 s | ~200 ms (string regex) |
| Simple query | 452 ms | ~200 ms (term cache) |
| Plain filter | 195 ms | ~195 ms (already fast) |
| Toggle filter | 5-6 ms | 5-6 ms (no change) |
| Memory (842 MB file) | ~1.7 GB | ~1.5 GB (no message/timestamp spans) |
