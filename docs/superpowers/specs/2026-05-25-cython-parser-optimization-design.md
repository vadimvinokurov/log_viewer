# Cython Parser Optimization — Design Spec

**Date**: 2026-05-25
**Status**: Approved
**Target**: Reduce log file parse time from ~23s to ~1-2s for 842 MB / 6.3M line files

## Problem

`_parse_plain_batch` and `_parse_ksiva_batch` in `parser.py` are pure Python loops over millions of lines. Each iteration creates temporary Python objects (byte slices, decoded strings) and writes scalars into numpy arrays. For 6.3M lines this costs ~23s — 95.8% of total load time.

## Solution

Replace the hot loops with Cython-compiled C code that accesses the byte buffer as `char*` directly, eliminating Python interpreter overhead per line.

## Architecture

### New file: `src/log_viewer/core/_parser_cy.pyx`

Two `cdef` functions mirroring the existing Python implementations:

- `parse_plain_batch_cy(buf, line_starts_ptr, line_starts_len, n, level_map_bytes, level_map_ids, level_map_len)` → fills pre-allocated numpy arrays
- `parse_ksiva_batch_cy(buf, line_starts_ptr, line_starts_len, n, level_map_bytes, level_map_ids, level_map_len)` → fills pre-allocated numpy arrays

Both functions:
1. Accept raw buffer as `const unsigned char*` (no Python object overhead)
2. Accept line_starts as raw C pointer (`uint64_t*`)
3. Accept level map as parallel C arrays (bytes + ids), not Python dict
4. Write directly into numpy array memory via typed memoryviews
5. Build category mapping using C `std::string` + linear scan or hash map
6. Return `(cat_names_list, cat_name_to_id_dict, cat_ids_array, levels_array, ts_spans_array, msg_spans_array)`

Category handling: The Cython code will use a Python dict for category mapping (since categories are strings and there are only ~400 unique values). The dict operations are cheap relative to the line scanning.

### Integration: `parse_batch_fast` fallback

In `parser.py`, `parse_batch_fast` will try to import the Cython module:

```python
try:
    from log_viewer.core._parser_cy import parse_batch_cy
    _HAS_CYTHON = True
except ImportError:
    _HAS_CYTHON = False
```

When `_HAS_CYTHON` is True, `parse_batch_fast` delegates to `parse_batch_cy`. Otherwise, falls back to the current Python `_parse_plain_batch` / `_parse_ksiva_batch`.

This ensures the app works identically on developer machines without Cython compiled, and gracefully degrades.

### Build integration

- `pyproject.toml` or `setup.py` at project root with `cythonize` extension
- Build command: `uv run python setup.py build_ext --inplace` (or via `uv sync` with build-system config)
- Cython and a C compiler become build-time dependencies only — not required at runtime on user machines (the compiled `.pyd`/`.so` ships in the PyInstaller bundle)

### PyInstaller

- Both `log-viewer.spec` and `log-viewer-windows.spec` must include the compiled extension
- Add to `datas` or `binaries`: the `.pyd` (Windows) / `.so` (macOS) file
- Test: build the app, verify Cython import succeeds in the bundled app

## What does NOT change

- `LogStore.load_bytes` — unchanged, it calls `parse_batch_fast` which handles the dispatch
- `scan_line_starts_fast` — already fast (numpy, 0.45s)
- `_build_category_tree`, `_count_levels`, `_apply_filters` — already fast
- All GUI code — completely unaffected
- Memory layout — no changes to data structures

## Success criteria

- `d:/log.txt` (842 MB, 6.3M lines) loads in < 3 seconds on the target machine
- Fallback to Python parser works when Cython extension is absent
- PyInstaller bundle on macOS and Windows includes the compiled extension and loads successfully
- All existing tests pass (unit + GUI)
- `uv run pytest` green before and after

## Out of scope

- Memory optimization (timestamp_spans removal, uint32 line_starts, mmap)
- Multiprocessing / parallel parsing
- Progressive / incremental loading
- Any changes to GUI, filtering, or search code

## Implementation order

1. Create `_parser_cy.pyx` with `parse_plain_batch_cy` (the format used by the benchmark file)
2. Create `setup.py` with `cythonize` config
3. Wire `parse_batch_fast` to use Cython with Python fallback
4. Verify with benchmark: `uv run python scripts/bench_load.py d:/log.txt`
5. Add `parse_ksiva_batch_cy`
6. Update PyInstaller specs
7. Run full test suite
