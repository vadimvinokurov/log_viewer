# cython: boundscheck=False, wraparound=False, cdivision=True
"""Cython-accelerated filter mask computation for simple query mode."""
from __future__ import annotations

import numpy as np
cimport numpy as cnp

cnp.import_array()


def compute_simple_mask(
    cnp.ndarray[cnp.uint64_t, ndim=1] msg_offsets,
    cnp.ndarray[cnp.uint32_t, ndim=1] msg_lengths,
    int n,
    object buf,
    object ast,
):
    """Compute boolean mask for simple query matching over byte buffer.

    Args:
        msg_offsets: uint64 array of message start offsets (length n).
        msg_lengths: uint32 array of message lengths (length n).
        n: Number of lines.
        buf: bytearray — the shared byte buffer.
        ast: Compiled QueryNode from simple_query.parse_query().

    Returns:
        numpy bool mask of length n.
    """
    cdef cnp.ndarray[cnp.uint8_t, ndim=1] mask = np.zeros(n, dtype=np.uint8)
    cdef Py_ssize_t off, ln, i
    cdef bytes msg_bytes

    for i in range(n):
        off = msg_offsets[i]
        ln = msg_lengths[i]
        if ln == 0:
            continue
        msg_bytes = bytes(buf[off:off + ln])
        if ast.evaluate_bytes(msg_bytes):
            mask[i] = 1

    return mask.astype(np.bool_)
