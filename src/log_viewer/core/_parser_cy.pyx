# cython: boundscheck=False, wraparound=False, cdivision=True
"""Cython-accelerated plain-format log parser."""
from __future__ import annotations

from cpython.bytes cimport PyBytes_AsString
from libc.string cimport memcmp

import numpy as np
cimport numpy as cnp

cnp.import_array()


# ---------------------------------------------------------------------------
# C helpers (nogil)
# ---------------------------------------------------------------------------

cdef inline Py_ssize_t _skip_spaces(const char *buf, Py_ssize_t pos,
                                     Py_ssize_t end) nogil:
    """Advance pos past ASCII spaces. Returns new pos."""
    while pos < end and buf[pos] == 32:
        pos += 1
    return pos


cdef inline Py_ssize_t _skip_non_spaces(const char *buf, Py_ssize_t pos,
                                         Py_ssize_t end) nogil:
    """Advance pos past non-space characters. Returns new pos."""
    while pos < end and buf[pos] != 32:
        pos += 1
    return pos


cdef inline Py_ssize_t _skip_trailing_crlf(const char *buf,
                                            Py_ssize_t start,
                                            Py_ssize_t end) nogil:
    """Return adjusted end, stripping at most one \\r and one \\n from the tail."""
    if end > start and buf[end - 1] == 10:   # \n
        end -= 1
    if end > start and buf[end - 1] == 13:   # \r
        end -= 1
    return end


cdef struct _LevelEntry:
    const char *data
    int length
    unsigned char id


# Level lookup table (static, built once)
cdef _LevelEntry _LEVEL_TABLE[12]
cdef int _LEVEL_TABLE_INIT = 0


cdef void _init_level_table() noexcept nogil:
    global _LEVEL_TABLE_INIT
    if _LEVEL_TABLE_INIT:
        return

    _LEVEL_TABLE[0].data = b"crt";           _LEVEL_TABLE[0].length = 3; _LEVEL_TABLE[0].id = 0
    _LEVEL_TABLE[1].data = b"LOG_CRITICAL";   _LEVEL_TABLE[1].length = 12; _LEVEL_TABLE[1].id = 0
    _LEVEL_TABLE[2].data = b"err";           _LEVEL_TABLE[2].length = 3; _LEVEL_TABLE[2].id = 1
    _LEVEL_TABLE[3].data = b"LOG_ERROR";      _LEVEL_TABLE[3].length = 9;  _LEVEL_TABLE[3].id = 1
    _LEVEL_TABLE[4].data = b"wrn";           _LEVEL_TABLE[4].length = 3; _LEVEL_TABLE[4].id = 2
    _LEVEL_TABLE[5].data = b"LOG_WARNING";    _LEVEL_TABLE[5].length = 11; _LEVEL_TABLE[5].id = 2
    _LEVEL_TABLE[6].data = b"msg";           _LEVEL_TABLE[6].length = 3; _LEVEL_TABLE[6].id = 3
    _LEVEL_TABLE[7].data = b"LOG_INFO";       _LEVEL_TABLE[7].length = 8;  _LEVEL_TABLE[7].id = 3
    _LEVEL_TABLE[8].data = b"dbg";           _LEVEL_TABLE[8].length = 3; _LEVEL_TABLE[8].id = 4
    _LEVEL_TABLE[9].data = b"LOG_DEBUG";      _LEVEL_TABLE[9].length = 9;  _LEVEL_TABLE[9].id = 4
    _LEVEL_TABLE[10].data = b"trc";          _LEVEL_TABLE[10].length = 3; _LEVEL_TABLE[10].id = 5
    _LEVEL_TABLE[11].data = b"LOG_TRACE";     _LEVEL_TABLE[11].length = 9;  _LEVEL_TABLE[11].id = 5

    _LEVEL_TABLE_INIT = 1


cdef inline unsigned char _lookup_level(const char *data,
                                         Py_ssize_t length) nogil:
    """Look up level id from bytes. Returns 3 (INFO) as default."""
    cdef int i
    _init_level_table()
    for i in range(12):
        if length == _LEVEL_TABLE[i].length and \
           memcmp(data, _LEVEL_TABLE[i].data, length) == 0:
            return _LEVEL_TABLE[i].id
    return 3


cdef inline bint _field_is_level(const char* ptr, Py_ssize_t length) noexcept nogil:
    """Check if a byte string matches any known level prefix (exact match)."""
    cdef int j
    for j in range(12):
        if length == _LEVEL_TABLE[j].length and memcmp(ptr, _LEVEL_TABLE[j].data, length) == 0:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_plain_batch_cy(
    bytes buf,
    cnp.ndarray[cnp.uint64_t, ndim=1] line_starts,
    int n,
):
    """Parse plain-format log lines at C speed.

    Args:
        buf: Entire file as a bytes object.
        line_starts: uint64 array of length n+1.  Line i = buf[starts[i]:starts[i+1]].
        n: Number of lines.

    Returns:
        (ts_spans, cat_names, cat_name_to_id, cat_ids, levels, msg_spans)
    """
    cdef const char *cbuf = PyBytes_AsString(buf)

    # Output arrays
    cdef cnp.ndarray ts_spans = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))
    cdef cnp.ndarray cat_arr = np.empty(n, dtype=np.uint16)
    cdef cnp.ndarray lvl_arr = np.empty(n, dtype=np.uint8)
    cdef cnp.ndarray msg_spans = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))

    # Typed views
    cdef cnp.uint64_t[:] ts_off = ts_spans["offset"]
    cdef cnp.uint32_t[:] ts_len = ts_spans["length"]
    cdef cnp.uint16_t[:] cat_view = cat_arr
    cdef cnp.uint8_t[:] lvl_view = lvl_arr
    cdef cnp.uint64_t[:] msg_off = msg_spans["offset"]
    cdef cnp.uint32_t[:] msg_len = msg_spans["length"]

    # Category mappings
    cat_names = ["uncategorized"]
    cat_name_to_id = {"uncategorized": 0}
    cdef dict cat_bytes_to_id = {b"uncategorized": 0}

    # Loop variables
    cdef Py_ssize_t start, end, pos, ll
    cdef Py_ssize_t ts_start, ts_end, lvl_start, cat_start
    cdef Py_ssize_t i
    cdef int new_id
    cdef bytes cat_bytes_raw

    for i in range(n):
        start = line_starts[i]
        end = line_starts[i + 1]

        # Strip trailing \r\n
        end = _skip_trailing_crlf(cbuf, start, end)

        # Skip leading spaces
        pos = _skip_spaces(cbuf, start, end)

        if pos >= end:
            # Empty line
            ts_off[i] = 0; ts_len[i] = 0
            cat_view[i] = 0; lvl_view[i] = 3
            msg_off[i] = 0; msg_len[i] = 0
            continue

        ll = end  # adjusted line end

        # Field 1: timestamp
        ts_start = pos
        pos = _skip_non_spaces(cbuf, pos, ll)
        ts_end = pos
        ts_off[i] = ts_start
        ts_len[i] = <cnp.uint32_t>(ts_end - ts_start)

        # Skip spaces + elapsed field
        pos = _skip_spaces(cbuf, pos, ll)
        pos = _skip_non_spaces(cbuf, pos, ll)

        # Field 3: level
        pos = _skip_spaces(cbuf, pos, ll)
        lvl_start = pos
        pos = _skip_non_spaces(cbuf, pos, ll)
        lvl_view[i] = _lookup_level(cbuf + lvl_start, pos - lvl_start)

        # Field 4: category
        pos = _skip_spaces(cbuf, pos, ll)
        cat_start = pos
        pos = _skip_non_spaces(cbuf, pos, ll)

        # Category lookup (requires Python dict — release GIL concerns are
        # negligible since we need Python objects here anyway).
        cat_bytes_raw = cbuf[cat_start:pos]
        try:
            cat_view[i] = cat_bytes_to_id[cat_bytes_raw]
        except KeyError:
            cat_str = cat_bytes_raw.decode("utf-8", errors="replace")
            new_id = <int>len(cat_names)
            cat_bytes_to_id[cat_bytes_raw] = new_id
            cat_names.append(cat_str)
            cat_name_to_id[cat_str] = new_id
            cat_view[i] = new_id

        # Field 5: message (rest of line)
        pos = _skip_spaces(cbuf, pos, ll)
        if pos < ll:
            msg_off[i] = pos
            msg_len[i] = <cnp.uint32_t>(ll - pos)
        else:
            msg_off[i] = 0
            msg_len[i] = 0

    return ts_spans, cat_names, cat_name_to_id, cat_arr, lvl_arr, msg_spans


def parse_ksiva_batch_cy(
    bytes buf,
    cnp.ndarray[cnp.uint64_t, ndim=1] line_starts,
    int n,
):
    """Parse KSIVA format lines: timestamp category [LOG_LEVEL] message.

    Args:
        buf: Entire file as a bytes object.
        line_starts: uint64 array of length n+1.  Line i = buf[starts[i]:starts[i+1]].
        n: Number of lines.

    Returns:
        (ts_spans, cat_names, cat_name_to_id, cat_ids, levels, msg_spans)
    """
    cdef const char *cbuf = PyBytes_AsString(buf)

    # Output arrays
    cdef cnp.ndarray ts_spans = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))
    cdef cnp.ndarray cat_arr = np.empty(n, dtype=np.uint16)
    cdef cnp.ndarray lvl_arr = np.empty(n, dtype=np.uint8)
    cdef cnp.ndarray msg_spans = np.empty(n, dtype=np.dtype([("offset", np.uint64), ("length", np.uint32)]))

    # Typed views
    cdef cnp.uint64_t[:] ts_off = ts_spans["offset"]
    cdef cnp.uint32_t[:] ts_len = ts_spans["length"]
    cdef cnp.uint16_t[:] cat_view = cat_arr
    cdef cnp.uint8_t[:] lvl_view = lvl_arr
    cdef cnp.uint64_t[:] msg_off = msg_spans["offset"]
    cdef cnp.uint32_t[:] msg_len = msg_spans["length"]

    # Category mappings
    cat_names = ["uncategorized"]
    cat_name_to_id = {"uncategorized": 0}
    cdef dict cat_bytes_to_id = {b"uncategorized": 0}

    # Loop variables
    cdef Py_ssize_t start, end, pos, ll
    cdef Py_ssize_t ts_start, fld_start, cat_start
    cdef Py_ssize_t lvl_ptr_start, lvl_ptr_len
    cdef Py_ssize_t i
    cdef int new_id
    cdef bytes cat_bytes_raw

    for i in range(n):
        start = line_starts[i]
        end = line_starts[i + 1]

        # Strip trailing \r\n
        end = _skip_trailing_crlf(cbuf, start, end)

        # Skip leading spaces
        pos = _skip_spaces(cbuf, start, end)

        if pos >= end:
            # Empty line
            ts_off[i] = 0; ts_len[i] = 0
            cat_view[i] = 0; lvl_view[i] = 3
            msg_off[i] = 0; msg_len[i] = 0
            continue

        ll = end  # adjusted line end

        # Field 1: timestamp
        ts_start = pos
        pos = _skip_non_spaces(cbuf, pos, ll)
        ts_off[i] = ts_start
        ts_len[i] = <cnp.uint32_t>(pos - ts_start)

        # Field 2: category
        pos = _skip_spaces(cbuf, pos, ll)
        cat_start = pos
        pos = _skip_non_spaces(cbuf, pos, ll)
        cat_bytes_raw = cbuf[cat_start:pos]

        try:
            cat_view[i] = cat_bytes_to_id[cat_bytes_raw]
        except KeyError:
            cat_str = cat_bytes_raw.decode("utf-8", errors="replace")
            new_id = <int>len(cat_names)
            cat_bytes_to_id[cat_bytes_raw] = new_id
            cat_names.append(cat_str)
            cat_name_to_id[cat_str] = new_id
            cat_view[i] = new_id

        # Field 3: maybe level
        pos = _skip_spaces(cbuf, pos, ll)
        fld_start = pos
        pos = _skip_non_spaces(cbuf, pos, ll)

        # Strip surrounding brackets: [LOG_INFO] -> LOG_INFO
        lvl_ptr_start = fld_start
        lvl_ptr_len = pos - fld_start
        if lvl_ptr_len >= 2 and cbuf[fld_start] == 91 and cbuf[pos - 1] == 93:
            lvl_ptr_start = fld_start + 1
            lvl_ptr_len = lvl_ptr_len - 2

        if _field_is_level(cbuf + lvl_ptr_start, lvl_ptr_len):
            lvl_view[i] = _lookup_level(cbuf + lvl_ptr_start, lvl_ptr_len)
            pos = _skip_spaces(cbuf, pos, ll)
            if pos < ll:
                msg_off[i] = pos
                msg_len[i] = <cnp.uint32_t>(ll - pos)
            else:
                msg_off[i] = 0
                msg_len[i] = 0
        else:
            # Not a level -- field 3+ is the message
            lvl_view[i] = 3
            msg_off[i] = fld_start
            msg_len[i] = <cnp.uint32_t>(ll - fld_start)

    return ts_spans, cat_names, cat_name_to_id, cat_arr, lvl_arr, msg_spans
