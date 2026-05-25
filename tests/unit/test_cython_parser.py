"""Correctness tests: Cython parser must produce identical output to Python parser."""
from __future__ import annotations

import numpy as np
import pytest

from log_viewer.core.parser import parse_batch_fast, _HAS_CYTHON
from log_viewer.core.log_store import SPAN_DTYPE


pytestmark = pytest.mark.skipif(not _HAS_CYTHON, reason="Cython extension not compiled")


def _parse_python(buf: bytearray, line_starts: np.ndarray, fmt: str):
    """Force the Python fallback path."""
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


def test_plain_empty_line(plain_data):
    buf, ls = plain_data
    ts, _, _, _, lvls, msgs = _parse_cython(buf, ls, "plain")
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
