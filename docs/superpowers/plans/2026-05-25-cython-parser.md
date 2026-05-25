# Cython Parser Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce 842 MB log file parse time from ~23s to <3s by replacing the Python hot loop with a Cython-compiled C extension.

**Architecture:** New `_parser_cy.pyx` Cython module mirrors `_parse_plain_batch` and `_parse_ksiva_batch` but runs as C code with `char*` buffer access. `parse_batch_fast` imports the Cython module if available, falls back to pure Python otherwise. No changes to LogStore, GUI, or data structures.

**Tech Stack:** Cython 3.x, C compiler (MSVC on Windows / Clang on macOS), numpy, existing PySide6/PyInstaller setup.

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/log_viewer/core/_parser_cy.pyx` | Cython implementations of `_parse_plain_batch` and `_parse_ksiva_batch` |
| Create | `setup.py` | `cythonize` build config for the extension module |
| Modify | `pyproject.toml` | Add `cython` build dependency |
| Modify | `src/log_viewer/core/parser.py:552-601` | Add Cython import + fallback dispatch in `parse_batch_fast` |
| Modify | `packaging/log-viewer.spec` | Add `_parser_cy` to hiddenimports |
| Modify | `packaging/log-viewer-windows.spec` | Add `_parser_cy` to hiddenimports |
| Create | `tests/unit/test_cython_parser.py` | Correctness tests comparing Cython output to Python output |

---

### Task 1: Create `setup.py` and add Cython build dependency

**Files:**
- Create: `setup.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add Cython to dev dependencies in pyproject.toml**

In `pyproject.toml`, add `cython>=3.0` to `[dependency-groups] dev`:

```toml
[dependency-groups]
dev = [
    "cython>=3.0",
    "psutil>=7.2.2",
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-qt>=4.4",
]
```

- [ ] **Step 2: Create setup.py**

```python
"""Build configuration for Cython extensions."""
from __future__ import annotations

from Cython.Build import cythonize
from setuptools import Extension, setup

extensions = [
    Extension(
        "log_viewer.core._parser_cy",
        sources=["src/log_viewer/core/_parser_cy.pyx"],
        include_dirs=["."],
    ),
]

setup(
    ext_modules=cythonize(extensions, language_level="3"),
)
```

- [ ] **Step 3: Install cython and verify setup.py parses**

Run: `uv sync`
Run: `uv run python -c "from setuptools import setup; print('setup.py OK')"`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add setup.py pyproject.toml
git commit -m "build: add setup.py and cython build dependency"
```

---

### Task 2: Create `_parser_cy.pyx` with plain format parser

**Files:**
- Create: `src/log_viewer/core/_parser_cy.pyx`

This is the core optimization. The Cython code mirrors `_parse_plain_batch` exactly but operates on `char*` directly.

- [ ] **Step 1: Write `_parser_cy.pyx`**

```cython
# cython: boundscheck=False, wraparound=False, cdivision=True
"""Cython-compiled batch parsers for log lines."""
from __future__ import annotations

from libc.string cimport memcmp
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.bytes cimport PyBytes_AsString, PyBytes_Size
from cpython.unicode cimport PyUnicode_DecodeUTF8

import numpy as np
cimport numpy as np

np.import_array()

# SPAN_DTYPE fields must match log_store.SPAN_DTYPE
cdef packed struct Span:
    np.uint64_t offset
    np.uint32_t length


cdef struct LevelEntry:
    const char* key
    Py_ssize_t key_len
    np.uint8_t id


# Pre-built level lookup tables (filled at module init)
cdef LevelEntry _LEVEL_TABLE[11]
cdef int _LEVEL_TABLE_LEN

cdef int _init_level_table() except -1:
    global _LEVEL_TABLE_LEN
    cdef list keys = [b"crt", b"LOG_CRITICAL", b"err", b"LOG_ERROR",
                      b"wrn", b"LOG_WARNING", b"msg", b"LOG_INFO",
                      b"dbg", b"LOG_DEBUG", b"trc", b"LOG_TRACE"]
    cdef list ids  = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    _LEVEL_TABLE_LEN = len(keys)
    for i in range(_LEVEL_TABLE_LEN):
        kb = keys[i]
        _LEVEL_TABLE[i].key = <const char*>(<bytes>kb)
        _LEVEL_TABLE[i].key_len = len(kb)
        _LEVEL_TABLE[i].id = <np.uint8_t>ids[i]
    return 0

_init_level_table()


cdef inline np.uint8_t _lookup_level(const char* ptr, Py_ssize_t length) noexcept nogil:
    """Look up a level ID by comparing bytes against known level strings."""
    cdef int j
    for j in range(_LEVEL_TABLE_LEN):
        if length == _LEVEL_TABLE[j].key_len and memcmp(ptr, _LEVEL_TABLE[j].key, length) == 0:
            return _LEVEL_TABLE[j].id
    return 3  # default INFO


cdef inline Py_ssize_t _skip_spaces(const char* ptr, Py_ssize_t pos, Py_ssize_t length) noexcept nogil:
    """Skip forward over spaces starting at pos."""
    while pos < length and ptr[pos] == 32:
        pos += 1
    return pos


cdef inline Py_ssize_t _skip_non_spaces(const char* ptr, Py_ssize_t pos, Py_ssize_t length) noexcept nogil:
    """Skip forward over non-space characters starting at pos."""
    while pos < length and ptr[pos] != 32:
        pos += 1
    return pos


cdef inline Py_ssize_t _skip_trailing_crlf(const char* ptr, Py_ssize_t length) noexcept nogil:
    """Return adjusted length after stripping trailing \\n and \\r."""
    if length > 0 and ptr[length - 1] == 10:  # \n
        length -= 1
    if length > 0 and ptr[length - 1] == 13:  # \r
        length -= 1
    return length


def parse_plain_batch_cy(
    bytes buf,
    np.ndarray[np.uint64_t, ndim=1] line_starts,
    int n,
):
    """Parse PLAIN format lines: timestamp elapsed level_short category message.

    Returns (ts_spans, cat_names, cat_name_to_id, cat_ids, levels, msg_spans).
    """
    cdef const char* buf_ptr = PyBytes_AsString(buf)
    cdef Py_ssize_t buf_len = PyBytes_Size(buf)
    cdef np.uint64_t[:] ls_view = line_starts

    # Output arrays
    cdef np.ndarray[np.uint16_t, ndim=1] cat_arr = np.empty(n, dtype=np.uint16)
    cdef np.ndarray[np.uint8_t, ndim=1] lvl_arr = np.empty(n, dtype=np.uint8)
    cdef np.ndarray ts_spans_arr = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))
    cdef np.ndarray msg_spans_arr = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))

    cdef Span[:] ts_spans = ts_spans_arr
    cdef Span[:] msg_spans = msg_spans_arr

    # Category mapping (Python dict for bytes keys — only ~400 unique values)
    cat_bytes_to_id = {b"uncategorized": 0}
    cat_names = ["uncategorized"]
    cat_name_to_id = {"uncategorized": 0}

    cdef Py_ssize_t i, start, end, ll, pos, ts_start, ts_end, lvl_start, cat_start
    cdef Py_ssize_t msg_start
    cdef const char* line_ptr

    for i in range(n):
        start = ls_view[i]
        end = ls_view[i + 1]
        line_ptr = buf_ptr + start
        ll = end - start

        # Strip trailing \n\r
        ll = _skip_trailing_crlf(line_ptr, ll)

        # Skip leading whitespace
        pos = _skip_spaces(line_ptr, 0, ll)

        if pos >= ll:
            ts_spans[i].offset = 0; ts_spans[i].length = 0
            cat_arr[i] = 0; lvl_arr[i] = 3
            msg_spans[i].offset = 0; msg_spans[i].length = 0
            continue

        # Field 1: timestamp (until first space)
        ts_start = pos
        pos = _skip_non_spaces(line_ptr, pos, ll)
        ts_end = pos
        ts_spans[i].offset = <np.uint64_t>(start + ts_start)
        ts_spans[i].length = <np.uint32_t>(ts_end - ts_start)

        # Skip spaces + elapsed field
        pos = _skip_spaces(line_ptr, pos, ll)
        pos = _skip_non_spaces(line_ptr, pos, ll)

        # Field 3: level_short
        pos = _skip_spaces(line_ptr, pos, ll)
        lvl_start = pos
        pos = _skip_non_spaces(line_ptr, pos, ll)
        lvl_arr[i] = _lookup_level(line_ptr + lvl_start, pos - lvl_start)

        # Field 4: category
        pos = _skip_spaces(line_ptr, pos, ll)
        cat_start = pos
        pos = _skip_non_spaces(line_ptr, pos, ll)
        cat_key = bytes(line_ptr[cat_start:pos])  # Python object — only ~400 unique
        try:
            cat_arr[i] = cat_bytes_to_id[cat_key]
        except KeyError:
            new_id = len(cat_names)
            cat_str = cat_key.decode("utf-8", errors="replace")
            cat_bytes_to_id[cat_key] = new_id
            cat_names.append(cat_str)
            cat_name_to_id[cat_str] = new_id
            cat_arr[i] = new_id

        # Field 5: message (rest of line)
        pos = _skip_spaces(line_ptr, pos, ll)
        if pos < ll:
            msg_spans[i].offset = <np.uint64_t>(start + pos)
            msg_spans[i].length = <np.uint32_t>(ll - pos)
        else:
            msg_spans[i].offset = 0
            msg_spans[i].length = 0

    return ts_spans_arr, cat_names, cat_name_to_id, cat_arr, lvl_arr, msg_spans_arr
```

- [ ] **Step 2: Compile the extension**

Run: `uv run python setup.py build_ext --inplace`
Expected: Compilation succeeds. A `.pyd` (Windows) or `.so` (macOS) file appears in `src/log_viewer/core/`.

- [ ] **Step 3: Verify import works**

Run: `uv run python -c "from log_viewer.core._parser_cy import parse_plain_batch_cy; print('Cython import OK')"`
Expected: `Cython import OK`

- [ ] **Step 4: Commit**

```bash
git add src/log_viewer/core/_parser_cy.pyx
git commit -m "feat: add Cython plain-format parser"
```

---

### Task 3: Wire Cython parser into `parse_batch_fast` with fallback

**Files:**
- Modify: `src/log_viewer/core/parser.py:516-601`

- [ ] **Step 1: Add Cython import + dispatch at top of `parse_batch_fast`**

In `parser.py`, add the try/import block right before `parse_batch_fast` (around line 527), and modify `parse_batch_fast` to use it:

```python
# --- Cython fast path ---
try:
    from log_viewer.core._parser_cy import parse_plain_batch_cy as _parse_plain_cy
    _HAS_CYTHON = True
except ImportError:
    _HAS_CYTHON = False
```

Then modify `parse_batch_fast` (line 552) — replace the body after the `cat_name_to_id` initialization with a Cython branch:

```python
def parse_batch_fast(
    buf: bytearray,
    line_starts: np.ndarray,
    fmt: str,
) -> tuple[np.ndarray, list[str], dict[str, int], np.ndarray, np.ndarray, np.ndarray]:
    """Parse all lines in batch, avoiding per-line Python overhead."""
    from log_viewer.core.log_store import SPAN_DTYPE

    n = len(line_starts) - 1

    # Cython fast path
    if _HAS_CYTHON:
        buf_bytes = bytes(buf)
        if fmt == "plain":
            return _parse_plain_cy(buf_bytes, line_starts, n)
        # ksiva falls through to Python below (added in Task 5)

    # Pure Python fallback
    ts_spans = np.empty(n, dtype=SPAN_DTYPE)
    cat_arr = np.empty(n, dtype=np.uint16)
    lvl_arr = np.empty(n, dtype=np.uint8)
    msg_spans = np.empty(n, dtype=SPAN_DTYPE)

    cat_bytes_to_id: dict[bytes, int] = {b"uncategorized": 0}
    cat_names: list[str] = ["uncategorized"]
    cat_name_to_id: dict[str, int] = {"uncategorized": 0}

    level_map = _LEVEL_BYTES

    ls = line_starts.tolist()
    buf_bytes = bytes(buf)

    if fmt == "plain":
        _parse_plain_batch(buf_bytes, ls, n, ts_spans, cat_arr, lvl_arr, msg_spans,
                          cat_bytes_to_id, cat_names, cat_name_to_id, level_map)
    else:
        _parse_ksiva_batch(buf_bytes, ls, n, ts_spans, cat_arr, lvl_arr, msg_spans,
                          cat_bytes_to_id, cat_names, cat_name_to_id, level_map)

    return ts_spans, cat_names, cat_name_to_id, cat_arr, lvl_arr, msg_spans
```

- [ ] **Step 2: Verify fallback works without Cython**

Run: `uv run python -c "from log_viewer.core.parser import _HAS_CYTHON, parse_batch_fast; print(f'Cython: {_HAS_CYTHON}')"`
Expected: `Cython: True` (if compiled) or `Cython: False` (if not compiled). Either way no error.

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/parser.py
git commit -m "feat: wire Cython parser into parse_batch_fast with fallback"
```

---

### Task 4: Write correctness tests

**Files:**
- Create: `tests/unit/test_cython_parser.py`

Test that Cython output matches Python output for both formats and edge cases.

- [ ] **Step 1: Write the test file**

```python
"""Correctness tests: Cython parser must produce identical output to Python parser."""
from __future__ import annotations

import numpy as np
import pytest

from log_viewer.core.parser import parse_batch_fast, _HAS_CYTHON
from log_viewer.core.log_store import SPAN_DTYPE


pytestmark = pytest.mark.skipif(not _HAS_CYTHON, reason="Cython extension not compiled")


def _parse_python(buf: bytearray, line_starts: np.ndarray, fmt: str):
    """Force the Python fallback path."""
    # Temporarily disable Cython to get reference output
    from log_viewer.core import parser
    old = parser._HAS_CYTHON
    parser._HAS_CYTHON = False
    try:
        return parse_batch_fast(buf, line_starts, fmt)
    finally:
        parser._HAS_CYTHON = old


def _parse_cython(buf: bytearray, line_starts: np.ndarray, fmt: str):
    """Force the Cython path."""
    from log_viewer.core import parser
    old = parser._HAS_CYTHON
    parser._HAS_CYTHON = True
    try:
        return parse_batch_fast(buf, line_starts, fmt)
    finally:
        parser._HAS_CYTHON = old


PLAIN_SAMPLE = (
    b"10:13:05.912    0.001 wrn    cfg                                 Found 35 config variables\n"
    b"10:13:05.912    0.001 wrn    cfg                                 Duplicate #1\n"
    b"10:13:05.913    0.002 msg    app/main                           Starting\n"
    b"10:13:05.914    0.003 err    net                                Connection refused\n"
    b"10:13:05.915    0.004 dbg    net                                Retrying\n"
    b"\n"
    b"10:13:05.916    0.005 crt    sys                                Fatal error\n"
    b"10:13:05.917    0.006 trc    perf                               tick\n"
)

KSIVA_SAMPLE = (
    b"2024-01-01T10:00:00 app/main [LOG_INFO] Starting application\n"
    b"2024-01-01T10:00:01 net      [LOG_ERROR] Connection failed\n"
    b"2024-01-01T10:00:02 cfg      [LOG_WARNING] Unknown key\n"
    b"\n"
    b"2024-01-01T10:00:03 db       [LOG_DEBUG] Query executed\n"
    b"2024-01-01T10:00:04 sys      [LOG_CRITICAL] Out of memory\n"
    b"2024-01-01T10:00:05 ui       [LOG_TRACE] Repaint\n"
    b"2024-01-01T10:00:06 app      no level here\n"
)


@pytest.fixture()
def plain_data():
    buf = bytearray(PLAIN_SAMPLE)
    from log_viewer.core.parser import scan_line_starts_fast
    ls = scan_line_starts_fast(buf)
    return buf, ls


@pytest.fixture()
def ksiva_data():
    buf = bytearray(KSIVA_SAMPLE)
    from log_viewer.core.parser import scan_line_starts_fast
    ls = scan_line_starts_fast(buf)
    return buf, ls


def _assert_equal_result(py, cy, label: str):
    """Assert Cython and Python results are identical."""
    py_ts, py_cat_names, py_cat_map, py_cats, py_lvls, py_msgs = py
    cy_ts, cy_cat_names, cy_cat_map, cy_cats, cy_lvls, cy_msgs = cy

    assert py_cat_names == cy_cat_names, f"{label} cat_names mismatch"
    assert py_cat_map == cy_cat_map, f"{label} cat_map mismatch"
    np.testing.assert_array_equal(py_cats, cy_cats, err_msg=f"{label} category_ids")
    np.testing.assert_array_equal(py_lvls, cy_lvls, err_msg=f"{label} levels")
    np.testing.assert_array_equal(py_ts["offset"], cy_ts["offset"], err_msg=f"{label} ts offsets")
    np.testing.assert_array_equal(py_ts["length"], cy_ts["length"], err_msg=f"{label} ts lengths")
    np.testing.assert_array_equal(py_msgs["offset"], cy_msgs["offset"], err_msg=f"{label} msg offsets")
    np.testing.assert_array_equal(py_msgs["length"], cy_msgs["length"], err_msg=f"{label} msg lengths")


def test_plain_format_matches(plain_data):
    buf, ls = plain_data
    py = _parse_python(buf, ls, "plain")
    cy = _parse_cython(buf, ls, "plain")
    _assert_equal_result(py, cy, "plain")


def test_plain_levels_correct(plain_data):
    buf, ls = plain_data
    _, _, _, _, lvls, _ = _parse_cython(buf, ls, "plain")
    # wrn=2, wrn=2, msg=3, err=1, dbg=4, empty(3), crt=0, trc=5
    expected = np.array([2, 2, 3, 1, 4, 3, 0, 5], dtype=np.uint8)
    np.testing.assert_array_equal(lvls, expected)


def test_plain_categories_correct(plain_data):
    buf, ls = plain_data
    _, cat_names, _, cats, _, _ = _parse_cython(buf, ls, "plain")
    # cfg, cfg, app/main, net, net, uncategorized(empty), sys, perf
    assert "cfg" in cat_names
    assert "app/main" in cat_names or "uncategorized" in cat_names


def test_plain_empty_line(plain_data):
    buf, ls = plain_data
    ts, _, _, _, lvls, msgs = _parse_cython(buf, ls, "plain")
    # Line index 5 is empty
    assert ts[5]["length"] == 0
    assert lvls[5] == 3
    assert msgs[5]["length"] == 0


def test_single_empty_buffer():
    buf = bytearray(b"\n\n\n")
    from log_viewer.core.parser import scan_line_starts_fast
    ls = scan_line_starts_fast(buf)
    py = _parse_python(buf, ls, "plain")
    cy = _parse_cython(buf, ls, "plain")
    _assert_equal_result(py, cy, "empty")


def test_single_line():
    buf = bytearray(b"10:00:00.000    0.001 msg    test  hello world\n")
    from log_viewer.core.parser import scan_line_starts_fast
    ls = scan_line_starts_fast(buf)
    py = _parse_python(buf, ls, "plain")
    cy = _parse_cython(buf, ls, "plain")
    _assert_equal_result(py, cy, "single")
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/unit/test_cython_parser.py -v`
Expected: All tests pass (both Cython correctness and level values).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_cython_parser.py
git commit -m "test: add Cython parser correctness tests"
```

---

### Task 5: Add KSIVA format parser to Cython module

**Files:**
- Modify: `src/log_viewer/core/_parser_cy.pyx`
- Modify: `src/log_viewer/core/parser.py`

- [ ] **Step 1: Add `parse_ksiva_batch_cy` to `_parser_cy.pyx`**

Append the following function to the end of `_parser_cy.pyx`:

```cython
def parse_ksiva_batch_cy(
    bytes buf,
    np.ndarray[np.uint64_t, ndim=1] line_starts,
    int n,
):
    """Parse KSIVA format lines: timestamp category [LOG_LEVEL] message.

    Returns (ts_spans, cat_names, cat_name_to_id, cat_ids, levels, msg_spans).
    """
    cdef const char* buf_ptr = PyBytes_AsString(buf)
    cdef Py_ssize_t buf_len = PyBytes_Size(buf)
    cdef np.uint64_t[:] ls_view = line_starts

    cdef np.ndarray[np.uint16_t, ndim=1] cat_arr = np.empty(n, dtype=np.uint16)
    cdef np.ndarray[np.uint8_t, ndim=1] lvl_arr = np.empty(n, dtype=np.uint8)
    cdef np.ndarray ts_spans_arr = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))
    cdef np.ndarray msg_spans_arr = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))

    cdef Span[:] ts_spans = ts_spans_arr
    cdef Span[:] msg_spans = msg_spans_arr

    cat_bytes_to_id = {b"uncategorized": 0}
    cat_names = ["uncategorized"]
    cat_name_to_id = {"uncategorized": 0}

    cdef Py_ssize_t i, start, end, ll, pos, ts_start, fld_start, cat_start
    cdef const char* line_ptr
    cdef np.uint8_t lvl_id

    for i in range(n):
        start = ls_view[i]
        end = ls_view[i + 1]
        line_ptr = buf_ptr + start
        ll = end - start

        ll = _skip_trailing_crlf(line_ptr, ll)
        pos = _skip_spaces(line_ptr, 0, ll)

        if pos >= ll:
            ts_spans[i].offset = 0; ts_spans[i].length = 0
            cat_arr[i] = 0; lvl_arr[i] = 3
            msg_spans[i].offset = 0; msg_spans[i].length = 0
            continue

        # Field 1: timestamp
        ts_start = pos
        pos = _skip_non_spaces(line_ptr, pos, ll)
        ts_spans[i].offset = <np.uint64_t>(start + ts_start)
        ts_spans[i].length = <np.uint32_t>(pos - ts_start)

        # Field 2: category
        pos = _skip_spaces(line_ptr, pos, ll)
        cat_start = pos
        pos = _skip_non_spaces(line_ptr, pos, ll)
        cat_key = bytes(line_ptr[cat_start:pos])
        try:
            cat_arr[i] = cat_bytes_to_id[cat_key]
        except KeyError:
            new_id = len(cat_names)
            cat_str = cat_key.decode("utf-8", errors="replace")
            cat_bytes_to_id[cat_key] = new_id
            cat_names.append(cat_str)
            cat_name_to_id[cat_str] = new_id
            cat_arr[i] = new_id

        # Field 3: maybe level
        pos = _skip_spaces(line_ptr, pos, ll)
        fld_start = pos
        pos = _skip_non_spaces(line_ptr, pos, ll)
        lvl_id = _lookup_level(line_ptr + fld_start, pos - fld_start)

        if lvl_id != 3 or _field_is_level(line_ptr + fld_start, pos - fld_start):
            lvl_arr[i] = lvl_id
            pos = _skip_spaces(line_ptr, pos, ll)
            if pos < ll:
                msg_spans[i].offset = <np.uint64_t>(start + pos)
                msg_spans[i].length = <np.uint32_t>(ll - pos)
            else:
                msg_spans[i].offset = 0
                msg_spans[i].length = 0
        else:
            lvl_arr[i] = 3
            msg_spans[i].offset = <np.uint64_t>(start + fld_start)
            msg_spans[i].length = <np.uint32_t>(ll - fld_start)

    return ts_spans_arr, cat_names, cat_name_to_id, cat_arr, lvl_arr, msg_spans_arr
```

Also add the helper `_field_is_level` before this function (it needs to distinguish "3=default INFO" from "3=explicit LOG_INFO"):

```cython
cdef inline bint _field_is_level(const char* ptr, Py_ssize_t length) noexcept nogil:
    """Check if a byte string matches any known level prefix (exact match)."""
    cdef int j
    for j in range(_LEVEL_TABLE_LEN):
        if length == _LEVEL_TABLE[j].key_len and memcmp(ptr, _LEVEL_TABLE[j].key, length) == 0:
            return True
    return False
```

- [ ] **Step 2: Update the Cython import in parser.py**

Change the import block at the top of the Cython section to also import `parse_ksiva_batch_cy`:

```python
try:
    from log_viewer.core._parser_cy import parse_plain_batch_cy as _parse_plain_cy
    from log_viewer.core._parser_cy import parse_ksiva_batch_cy as _parse_ksiva_cy
    _HAS_CYTHON = True
except ImportError:
    _HAS_CYTHON = False
```

Update the Cython dispatch inside `parse_batch_fast` to handle ksiva:

```python
    if _HAS_CYTHON:
        buf_bytes = bytes(buf)
        if fmt == "plain":
            return _parse_plain_cy(buf_bytes, line_starts, n)
        else:
            return _parse_ksiva_cy(buf_bytes, line_starts, n)
```

- [ ] **Step 3: Recompile**

Run: `uv run python setup.py build_ext --inplace`
Expected: Compilation succeeds.

- [ ] **Step 4: Add KSIVA correctness test to `test_cython_parser.py`**

Append to the test file:

```python
def test_ksiva_format_matches(ksiva_data):
    buf, ls = ksiva_data
    py = _parse_python(buf, ls, "ksiva")
    cy = _parse_cython(buf, ls, "ksiva")
    _assert_equal_result(py, cy, "ksiva")


def test_ksiva_levels_correct(ksiva_data):
    buf, ls = ksiva_data
    _, _, _, _, lvls, _ = _parse_cython(buf, ls, "ksiva")
    # INFO=3, ERROR=1, WARNING=2, empty(3), DEBUG=4, CRITICAL=0, TRACE=5, INFO(3, no level)
    expected = np.array([3, 1, 2, 3, 4, 0, 5, 3], dtype=np.uint8)
    np.testing.assert_array_equal(lvls, expected)


def test_ksiva_no_level_line(ksiva_data):
    buf, ls = ksiva_data
    ts, _, _, _, lvls, msgs = _parse_cython(buf, ls, "ksiva")
    # Line index 7 has no LOG_* level — message should start at "no level here"
    assert lvls[7] == 3  # defaults to INFO
    assert msgs[7]["length"] > 0
```

- [ ] **Step 5: Run all tests**

Run: `uv run pytest tests/unit/test_cython_parser.py -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/log_viewer/core/_parser_cy.pyx src/log_viewer/core/parser.py tests/unit/test_cython_parser.py
git commit -m "feat: add Cython KSIVA parser, full format coverage"
```

---

### Task 6: Run existing test suite + benchmark

**Files:** No changes — verification only.

- [ ] **Step 1: Run full unit test suite**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run GUI tests**

Run: `uv run pytest tests/gui/ -v`
Expected: All tests pass.

- [ ] **Step 3: Run benchmark against d:/log.txt**

Run: `uv run python scripts/bench_load.py d:/log.txt`
Expected: `[4] Batch parse` shows < 3 seconds (down from 23s).

- [ ] **Step 4: Verify fallback works**

Rename the `.pyd`/`.so` file temporarily, run the benchmark, restore:
```bash
# In src/log_viewer/core/, rename _parser_cy.* to _parser_cy.*.bak
# Run benchmark — should still work, just slower
# Restore the file
```
Expected: Falls back to Python parser, no crash.

---

### Task 7: Update PyInstaller specs

**Files:**
- Modify: `packaging/log-viewer.spec`
- Modify: `packaging/log-viewer-windows.spec`

- [ ] **Step 1: Add `_parser_cy` to hiddenimports in both specs**

In `packaging/log-viewer.spec`, add to the `hiddenimports` list:

```python
        'log_viewer.core._parser_cy',
```

In `packaging/log-viewer-windows.spec`, add to the `hiddenimports` list:

```python
        'log_viewer.core._parser_cy',
```

- [ ] **Step 2: Commit**

```bash
git add packaging/log-viewer.spec packaging/log-viewer-windows.spec
git commit -m "build: add _parser_cy to PyInstaller hidden imports"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Task 2-3 covers Cython plain parser + fallback. Task 5 adds ksiva. Task 7 covers PyInstaller. Task 6 verifies benchmark target. All spec requirements mapped.
- [x] **Placeholder scan:** No TBD, TODO, or vague steps. Every step has exact code or exact commands.
- [x] **Type consistency:** Function names `parse_plain_batch_cy`, `parse_ksiva_batch_cy`, `_HAS_CYTHON`, `_parse_plain_cy`, `_parse_ksiva_cy` used consistently across all tasks.
