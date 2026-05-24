"""Log file parser.

Default format: timestamp category [LOG_LEVEL] message
Split by whitespace (max 3 splits) into up to 4 parts.
If position 2 is a LOG_* prefix → use as level, position 3 = message.
Otherwise → level defaults to INFO, positions 2+ become message.
"""

from __future__ import annotations

import re
import sys

import numpy as np
from log_viewer.core.models import LogFormat, LogLevel, LogLine

UNCATEGORIZED = "uncategorized"

_SPLIT_RE = re.compile(r"\s+")
_PLAIN_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d+\s+\d+\.\d+\s+(wrn|msg|dbg|err|crt)\s+")
_PLAIN_RE_BYTES = re.compile(rb"^\d{2}:\d{2}:\d{2}\.\d+\s+\d+\.\d+\s+(wrn|msg|dbg|err|crt)\s+")



def parse_line(raw: str, line_number: int, file_offset: int = 0, line_length: int = 0) -> LogLine:
    """Parse a single raw log line into a LogLine."""
    stripped = raw.strip()

    if not stripped:
        return LogLine(
            line_number=line_number,
            timestamp="",
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message="",
            file_offset=file_offset, line_length=line_length,
        )

    parts = _SPLIT_RE.split(stripped, maxsplit=3)

    if len(parts) == 1:
        # Only timestamp — entire line is the message
        return LogLine(
            line_number=line_number,
            timestamp="",
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message=raw,
            file_offset=file_offset, line_length=line_length,
        )

    timestamp = sys.intern(parts[0])

    if len(parts) == 2:
        # Timestamp + one more field → category + message (no level)
        return LogLine(
            line_number=line_number,
            timestamp=timestamp,
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message=parts[1],
            file_offset=file_offset, line_length=line_length,
        )

    # 3 or 4 parts: [timestamp, category, level_or_message, rest?]
    category = sys.intern(parts[1])
    maybe_level = parts[2]
    level_match = LogLevel.from_log_prefix(maybe_level)

    if level_match is not None:
        message = parts[3] if len(parts) == 4 else ""
        return LogLine(
            line_number=line_number,
            timestamp=timestamp,
            category=category,
            level=level_match,
            message=message,
            file_offset=file_offset, line_length=line_length,
        )

    # No LOG_* found — merge position 2+ into message
    message = parts[2] if len(parts) == 3 else f"{parts[2]} {parts[3]}"
    return LogLine(
        line_number=line_number,
        timestamp=timestamp,
        category=category,
        level=LogLevel.INFO,
        message=message,
        file_offset=file_offset, line_length=line_length,
    )


def detect_format(raw_lines: list[str]) -> LogFormat:
    """Detect log format by sniffing the first non-empty line."""
    for line in raw_lines:
        stripped = line.strip()
        if stripped:
            if _PLAIN_RE.match(stripped):
                return LogFormat.PLAIN
            return LogFormat.KSIVA
    return LogFormat.KSIVA


def parse_plain_line(raw: str, line_number: int, file_offset: int = 0, line_length: int = 0) -> LogLine:
    """Parse a plain-format log line: time elapsed level_short category message."""
    stripped = raw.strip()

    if not stripped:
        return LogLine(
            line_number=line_number,
            timestamp="",
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message="",
            file_offset=file_offset, line_length=line_length,
        )

    # Split: time elapsed level_short category message
    parts = _SPLIT_RE.split(stripped, maxsplit=4)

    if len(parts) < 5:
        return LogLine(
            line_number=line_number,
            timestamp=sys.intern(parts[0]) if parts else "",
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message=" ".join(parts[1:]) if len(parts) > 1 else "",
            file_offset=file_offset, line_length=line_length,
        )

    timestamp = sys.intern(parts[0])
    # parts[1] = elapsed, dropped
    level = LogLevel.from_short_code(parts[2]) or LogLevel.INFO
    category = sys.intern(parts[3])
    message = parts[4]

    return LogLine(
        line_number=line_number,
        timestamp=timestamp,
        category=category,
        level=level,
        message=message,
        file_offset=file_offset, line_length=line_length,
    )


def _parse_chunk(args: tuple[list[str], int, list[tuple[int, int]]]) -> list[LogLine]:
    """Parse a chunk of lines. Worker function for parallel parsing."""
    raw_lines, start_idx, offsets = args
    return [
        parse_line(raw, start_idx + i + 1, offsets[i][0], offsets[i][1])
        for i, raw in enumerate(raw_lines)
    ]


def _parse_plain_chunk(args: tuple[list[str], int, list[tuple[int, int]]]) -> list[LogLine]:
    """Parse a chunk of plain-format lines. Worker function for parallel parsing."""
    raw_lines, start_idx, offsets = args
    return [
        parse_plain_line(raw, start_idx + i + 1, offsets[i][0], offsets[i][1])
        for i, raw in enumerate(raw_lines)
    ]


def parse_lines_batch(
    raw_lines: list[str],
    offsets: list[tuple[int, int]],
    plain: bool = False,
    chunk_size: int = 500_000,
) -> list[LogLine]:
    """Parse all lines using multiple processes.

    Args:
        raw_lines: Raw text lines to parse.
        offsets: Pre-computed (file_offset, line_length) tuples.
        plain: Use plain format parser if True, KSIVA format if False.
        chunk_size: Lines per chunk.

    Returns:
        Flat list of LogLine objects in original order.
    """
    import concurrent.futures
    import os

    worker = _parse_plain_chunk if plain else _parse_chunk
    n = len(raw_lines)
    num_workers = min(os.cpu_count() or 4, max(1, n // chunk_size))

    if num_workers <= 1 or n < chunk_size:
        if plain:
            return [
                parse_plain_line(raw, i + 1, offsets[i][0], offsets[i][1])
                for i, raw in enumerate(raw_lines)
            ]
        return [
            parse_line(raw, i + 1, offsets[i][0], offsets[i][1])
            for i, raw in enumerate(raw_lines)
        ]

    chunks: list[tuple[list[str], int, list[tuple[int, int]]]] = []
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        chunks.append((raw_lines[start:end], start, offsets[start:end]))

    results: list[LogLine] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        for chunk_result in executor.map(worker, chunks):
            results.extend(chunk_result)

    return results


# --- SoA parsing functions ---


def _parse_time_to_ms(ts: str) -> int:
    """Convert a time string to milliseconds from midnight.

    Accepts 'HH:MM:SS.mmm' or ISO 'YYYY-MM-DDTHH:MM:SS.mmm'.
    Returns milliseconds from midnight (0 .. 86_399_999).
    """
    # Extract time portion after 'T' if present
    time_part = ts.split("T")[-1] if "T" in ts else ts
    parts = time_part.split(":")
    if len(parts) < 3:
        return 0
    try:
        h = int(parts[0])
        m = int(parts[1])
        sec_parts = parts[2].split(".")
        s = int(sec_parts[0])
        ms = int(sec_parts[1]) if len(sec_parts) > 1 else 0
        # Pad/truncate ms to 3 digits
        if len(sec_parts) > 1:
            ms_str = sec_parts[1]
            if len(ms_str) < 3:
                ms = int(ms_str.ljust(3, "0"))
            else:
                ms = int(ms_str[:3])
        return h * 3_600_000 + m * 60_000 + s * 1_000 + ms
    except (ValueError, IndexError):
        return 0


def parse_line_soa(
    raw: str,
    cat_name_to_id: dict[str, int],
    cat_names: list[str],
) -> tuple[int, int, int, str]:
    """Parse a KSIVA-format log line into SoA tuple.

    Returns (timestamp_ms, category_id, level_id, message).
    """
    from log_viewer.core.models import _LEVEL_NAMES

    stripped = raw.strip()

    if not stripped:
        return (0, 0, 3, "")  # level 3 = INFO

    parts = _SPLIT_RE.split(stripped, maxsplit=3)

    if len(parts) == 1:
        return (0, 0, 3, raw)

    ts_ms = _parse_time_to_ms(parts[0])

    if len(parts) == 2:
        return (ts_ms, 0, 3, parts[1])

    # Category
    cat_str = parts[1]
    if cat_str not in cat_name_to_id:
        cat_name_to_id[cat_str] = len(cat_names)
        cat_names.append(cat_str)
    cat_id = cat_name_to_id[cat_str]

    # Level
    maybe_level = parts[2]
    level_id = _LEVEL_NAMES.get(maybe_level, 3)  # default INFO=3

    if level_id != 3 or maybe_level in _LEVEL_NAMES:
        # Level found at position 2
        message = parts[3] if len(parts) == 4 else ""
        return (ts_ms, cat_id, level_id, message)

    # No LOG_* found — merge position 2+ into message
    message = parts[2] if len(parts) == 3 else f"{parts[2]} {parts[3]}"
    return (ts_ms, cat_id, 3, message)


def parse_plain_line_soa(
    raw: str,
    cat_name_to_id: dict[str, int],
    cat_names: list[str],
) -> tuple[int, int, int, str]:
    """Parse a plain-format log line into SoA tuple.

    Plain format: time elapsed level_short category message
    Returns (timestamp_ms, category_id, level_id, message).
    """
    from log_viewer.core.models import _LEVEL_NAMES

    stripped = raw.strip()

    if not stripped:
        return (0, 0, 3, "")

    parts = _SPLIT_RE.split(stripped, maxsplit=4)

    if len(parts) < 5:
        ts_ms = _parse_time_to_ms(parts[0]) if parts else 0
        cat_id = 0
        msg = " ".join(parts[1:]) if len(parts) > 1 else ""
        return (ts_ms, cat_id, 3, msg)

    ts_ms = _parse_time_to_ms(parts[0])
    # parts[1] = elapsed, dropped
    level_id = _LEVEL_NAMES.get(parts[2], 3)

    cat_str = parts[3]
    if cat_str not in cat_name_to_id:
        cat_name_to_id[cat_str] = len(cat_names)
        cat_names.append(cat_str)
    cat_id = cat_name_to_id[cat_str]

    message = parts[4]
    return (ts_ms, cat_id, level_id, message)


# --- Byte-buffer parsing functions ---


def _parse_time_bytes_to_ms(ts: bytes) -> int:
    """Convert a byte timestamp to milliseconds from midnight."""
    t_pos = ts.find(b"T")
    time_part = ts[t_pos + 1:] if t_pos != -1 else ts

    c1 = time_part.find(b":")
    if c1 == -1:
        return 0
    c2 = time_part.find(b":", c1 + 1)
    if c2 == -1:
        return 0

    try:
        h = int(time_part[:c1])
        m = int(time_part[c1 + 1:c2])

        rest = time_part[c2 + 1:]
        d_pos = rest.find(b".")
        if d_pos == -1:
            s = int(rest)
            ms = 0
        else:
            s = int(rest[:d_pos])
            frac = rest[d_pos + 1:]
            if len(frac) < 3:
                ms = int(frac.ljust(3, b"0"))
            else:
                ms = int(frac[:3])

        return h * 3_600_000 + m * 60_000 + s * 1_000 + ms
    except (ValueError, IndexError):
        return 0


def scan_line_starts(buf: bytes) -> list[int]:
    """Scan a byte buffer and return line start positions.

    Returns list of length (n_lines + 1), where each entry is the byte offset
    where a line begins. The last entry equals len(buf) for easy slicing:
    line i = buf[starts[i]:starts[i+1]].
    """
    starts = [0]
    pos = 0
    while True:
        pos = buf.find(b"\n", pos)
        if pos == -1:
            break
        starts.append(pos + 1)
        pos += 1
    if starts[-1] != len(buf):
        starts.append(len(buf))
    return starts


def detect_format_bytes(buf: bytes) -> str:
    """Detect log format by sniffing the first non-empty line in a byte buffer.

    Returns "ksiva" or "plain".
    """
    pos = 0
    while pos < len(buf):
        end = buf.find(b"\n", pos)
        if end == -1:
            end = len(buf)
        line = buf[pos:end].strip()
        if line:
            if _PLAIN_RE_BYTES.match(line):
                return "plain"
            return "ksiva"
        pos = end + 1
    return "ksiva"


def parse_line_soa_bytes(
    raw: bytes,
    line_offset: int,
    cat_name_to_id: dict[str, int],
    cat_names: list[str],
) -> tuple[int, int, int, int, int]:
    """Parse a KSIVA-format byte slice into SoA tuple with message span.

    Args:
        raw: Byte slice of a single line (no trailing newline).
        line_offset: Byte offset of this line's start in the parent buffer.
        cat_name_to_id: Mutable category name → ID mapping.
        cat_names: Mutable list of category names.

    Returns:
        (timestamp_ms, category_id, level_id, msg_buf_offset, msg_length)
        msg_buf_offset is relative to the parent buffer (line_offset + offset within raw).
    """
    from log_viewer.core.models import _LEVEL_NAMES

    stripped = raw.strip()

    if not stripped:
        return (0, 0, 3, line_offset, 0)

    parts = stripped.split(None, 3)

    if len(parts) == 1:
        off = line_offset + (len(raw) - len(raw.lstrip()))
        return (0, 0, 3, off, len(stripped))

    ts_ms = _parse_time_bytes_to_ms(parts[0])

    if len(parts) == 2:
        # Find where parts[1] starts in raw
        msg_start_in_raw = raw.find(parts[1])
        off = line_offset + msg_start_in_raw
        return (ts_ms, 0, 3, off, len(parts[1]))

    # Category
    cat_str = parts[1].decode("utf-8", errors="replace")
    if cat_str not in cat_name_to_id:
        cat_name_to_id[cat_str] = len(cat_names)
        cat_names.append(cat_str)
    cat_id = cat_name_to_id[cat_str]

    # Level
    maybe_level = parts[2].decode("utf-8", errors="replace")
    level_id = _LEVEL_NAMES.get(maybe_level, 3)

    if level_id != 3 or maybe_level in _LEVEL_NAMES:
        message = parts[3] if len(parts) == 4 else b""
        msg_start_in_raw = raw.find(message) if message else line_offset
        off = line_offset + msg_start_in_raw if message else line_offset
        return (ts_ms, cat_id, level_id, off, len(message))

    # No LOG_* found — merge position 2+ into message
    if len(parts) == 3:
        message = parts[2]
    else:
        # Find where parts[2] starts and goes to end
        message = raw[raw.find(parts[2]):]
    msg_start_in_raw = raw.find(parts[2])
    off = line_offset + msg_start_in_raw
    return (ts_ms, cat_id, 3, off, len(message))


def parse_plain_line_soa_bytes(
    raw: bytes,
    line_offset: int,
    cat_name_to_id: dict[str, int],
    cat_names: list[str],
) -> tuple[int, int, int, int, int]:
    """Parse a plain-format byte slice into SoA tuple with message span.

    Plain format: time elapsed level_short category message
    Returns (timestamp_ms, category_id, level_id, msg_buf_offset, msg_length).
    """
    from log_viewer.core.models import _LEVEL_NAMES

    stripped = raw.strip()

    if not stripped:
        return (0, 0, 3, line_offset, 0)

    parts = stripped.split(None, 4)

    if len(parts) < 5:
        ts_ms = _parse_time_bytes_to_ms(parts[0]) if parts else 0
        msg = stripped
        off = line_offset + (len(raw) - len(raw.lstrip()))
        return (ts_ms, 0, 3, off, len(msg))

    ts_ms = _parse_time_bytes_to_ms(parts[0])
    # parts[1] = elapsed, dropped
    level_id = _LEVEL_NAMES.get(parts[2].decode("utf-8", errors="replace"), 3)

    cat_str = parts[3].decode("utf-8", errors="replace")
    if cat_str not in cat_name_to_id:
        cat_name_to_id[cat_str] = len(cat_names)
        cat_names.append(cat_str)
    cat_id = cat_name_to_id[cat_str]

    message = parts[4]
    msg_start_in_raw = raw.find(message)
    off = line_offset + msg_start_in_raw
    return (ts_ms, cat_id, level_id, off, len(message))


# --- Fast batch parsing ---

_LEVEL_BYTES: dict[bytes, int] = {
    b"crt": 0, b"LOG_CRITICAL": 0,
    b"err": 1, b"LOG_ERROR": 1,
    b"wrn": 2, b"LOG_WARNING": 2,
    b"msg": 3, b"LOG_INFO": 3,
    b"dbg": 4, b"LOG_DEBUG": 4,
    b"trc": 5, b"LOG_TRACE": 5,
}


def scan_line_starts_fast(buf: bytes | bytearray) -> np.ndarray:
    """Scan line starts using numpy for SIMD-level newline detection.

    Returns uint64 array of length (n_lines + 1) where line i = buf[starts[i]:starts[i+1]].
    """
    if len(buf) == 0:
        return np.array([0], dtype=np.uint64)

    arr = np.frombuffer(buf, dtype=np.uint8)
    nl = np.where(arr == np.uint8(10))[0].astype(np.uint64)

    # Build starts: 0, then position after each newline
    starts = np.empty(len(nl) + 2, dtype=np.uint64)
    starts[0] = 0
    starts[1:-1] = nl + 1
    starts[-1] = len(buf)

    # Remove trailing empty line if file ends with newline
    if len(buf) > 0 and buf[-1] == 10:
        starts = starts[:-1]

    return starts


def parse_batch_fast(
    buf: bytearray,
    line_starts: np.ndarray,
    fmt: str,
) -> tuple[np.ndarray, list[str], dict[str, int], np.ndarray, np.ndarray, np.ndarray]:
    """Parse all lines in batch, avoiding per-line Python overhead.

    Args:
        buf: Raw byte buffer (entire file).
        line_starts: Line start positions from scan_line_starts_fast (length n+1).
        fmt: "plain" or "ksiva"

    Returns:
        (timestamp_spans, cat_names, cat_name_to_id, cat_ids, levels, message_spans)
        - timestamp_spans: ndarray SPAN_DTYPE (offset, length) -- raw bytes, lazy decode
        - cat_names: list of category name strings
        - cat_name_to_id: dict mapping category name to id
        - cat_ids: ndarray uint16
        - levels: ndarray uint8
        - message_spans: ndarray SPAN_DTYPE (offset, length)
    """
    from log_viewer.core.log_store import SPAN_DTYPE

    n = len(line_starts) - 1

    # Pre-allocate output arrays
    ts_spans = np.empty(n, dtype=SPAN_DTYPE)
    cat_arr = np.empty(n, dtype=np.uint16)
    lvl_arr = np.empty(n, dtype=np.uint8)
    msg_spans = np.empty(n, dtype=SPAN_DTYPE)

    # Category mapping (bytes-based to avoid decode)
    cat_bytes_to_id: dict[bytes, int] = {b"uncategorized": 0}
    cat_names: list[str] = ["uncategorized"]
    cat_name_to_id: dict[str, int] = {"uncategorized": 0}

    level_map = _LEVEL_BYTES

    # Convert line_starts to a Python list for fast indexing
    ls = line_starts.tolist()
    buf_bytes = bytes(buf)  # immutable view for safety

    if fmt == "plain":
        _parse_plain_batch(buf_bytes, ls, n, ts_spans, cat_arr, lvl_arr, msg_spans,
                          cat_bytes_to_id, cat_names, cat_name_to_id, level_map)
    else:
        _parse_ksiva_batch(buf_bytes, ls, n, ts_spans, cat_arr, lvl_arr, msg_spans,
                          cat_bytes_to_id, cat_names, cat_name_to_id, level_map)

    return ts_spans, cat_names, cat_name_to_id, cat_arr, lvl_arr, msg_spans


def _parse_plain_batch(
    buf: bytes,
    ls: list[int],
    n: int,
    ts_spans: np.ndarray,
    cat_arr: np.ndarray,
    lvl_arr: np.ndarray,
    msg_spans: np.ndarray,
    cat_bytes_to_id: dict[bytes, int],
    cat_names: list[str],
    cat_name_to_id: dict[str, int],
    level_map: dict[bytes, int],
) -> None:
    """Parse PLAIN format lines: timestamp elapsed level_short category message"""
    _ts_off = ts_spans["offset"]
    _ts_len = ts_spans["length"]
    _cat = cat_arr
    _lvl = lvl_arr
    _msg_off = msg_spans["offset"]
    _msg_len = msg_spans["length"]

    for i in range(n):
        start = ls[i]
        end = ls[i + 1]
        line = buf[start:end]

        # Strip trailing \n\r
        if line and line[-1] == 10:  # \n
            line = line[:-1]
        if line and line[-1] == 13:  # \r
            line = line[:-1]

        # Skip leading whitespace
        ll = len(line)
        pos = 0
        while pos < ll and line[pos] == 32:  # space
            pos += 1

        if pos >= ll:
            # Empty line
            _ts_off[i] = 0; _ts_len[i] = 0
            _cat[i] = 0; _lvl[i] = 3
            _msg_off[i] = 0; _msg_len[i] = 0
            continue

        # Field 1: timestamp (until first space)
        ts_start = pos
        while pos < ll and line[pos] != 32:
            pos += 1
        ts_end = pos
        _ts_off[i] = start + ts_start
        _ts_len[i] = ts_end - ts_start

        # Skip spaces to field 2 (elapsed -- we skip this)
        while pos < ll and line[pos] == 32:
            pos += 1
        # Skip elapsed field
        while pos < ll and line[pos] != 32:
            pos += 1

        # Skip spaces to field 3 (level_short)
        while pos < ll and line[pos] == 32:
            pos += 1
        lvl_start = pos
        while pos < ll and line[pos] != 32:
            pos += 1
        lvl_bytes = line[lvl_start:pos]
        _lvl[i] = level_map.get(lvl_bytes, 3)

        # Skip spaces to field 4 (category)
        while pos < ll and line[pos] == 32:
            pos += 1
        cat_start = pos
        while pos < ll and line[pos] != 32:
            pos += 1
        cat_bytes = line[cat_start:pos]

        if cat_bytes not in cat_bytes_to_id:
            cat_str = cat_bytes.decode("utf-8", errors="replace")
            new_id = len(cat_names)
            cat_bytes_to_id[cat_bytes] = new_id
            cat_names.append(cat_str)
            cat_name_to_id[cat_str] = new_id
        _cat[i] = cat_bytes_to_id[cat_bytes]

        # Skip spaces to field 5 (message -- rest of line)
        while pos < ll and line[pos] == 32:
            pos += 1
        if pos < ll:
            _msg_off[i] = start + pos
            _msg_len[i] = ll - pos
        else:
            _msg_off[i] = 0
            _msg_len[i] = 0


def _parse_ksiva_batch(
    buf: bytes,
    ls: list[int],
    n: int,
    ts_spans: np.ndarray,
    cat_arr: np.ndarray,
    lvl_arr: np.ndarray,
    msg_spans: np.ndarray,
    cat_bytes_to_id: dict[bytes, int],
    cat_names: list[str],
    cat_name_to_id: dict[str, int],
    level_map: dict[bytes, int],
) -> None:
    """Parse KSIVA format lines: timestamp category [LOG_LEVEL] message"""
    _ts_off = ts_spans["offset"]
    _ts_len = ts_spans["length"]
    _cat = cat_arr
    _lvl = lvl_arr
    _msg_off = msg_spans["offset"]
    _msg_len = msg_spans["length"]

    for i in range(n):
        start = ls[i]
        end = ls[i + 1]
        line = buf[start:end]

        # Strip trailing \n\r
        if line and line[-1] == 10:
            line = line[:-1]
        if line and line[-1] == 13:
            line = line[:-1]

        ll = len(line)
        pos = 0
        while pos < ll and line[pos] == 32:
            pos += 1

        if pos >= ll:
            _ts_off[i] = 0; _ts_len[i] = 0
            _cat[i] = 0; _lvl[i] = 3
            _msg_off[i] = 0; _msg_len[i] = 0
            continue

        # Field 1: timestamp
        ts_start = pos
        while pos < ll and line[pos] != 32:
            pos += 1
        _ts_off[i] = start + ts_start
        _ts_len[i] = pos - ts_start

        # Skip spaces to field 2 (category)
        while pos < ll and line[pos] == 32:
            pos += 1
        cat_start = pos
        while pos < ll and line[pos] != 32:
            pos += 1
        cat_bytes = line[cat_start:pos]

        if cat_bytes not in cat_bytes_to_id:
            cat_str = cat_bytes.decode("utf-8", errors="replace")
            new_id = len(cat_names)
            cat_bytes_to_id[cat_bytes] = new_id
            cat_names.append(cat_str)
            cat_name_to_id[cat_str] = new_id
        _cat[i] = cat_bytes_to_id[cat_bytes]

        # Skip spaces to field 3 (maybe level)
        while pos < ll and line[pos] == 32:
            pos += 1
        fld_start = pos
        while pos < ll and line[pos] != 32:
            pos += 1
        fld_bytes = line[fld_start:pos]

        lvl_id = level_map.get(fld_bytes)
        if lvl_id is not None:
            # It's a level -- message starts after spaces
            _lvl[i] = lvl_id
            while pos < ll and line[pos] == 32:
                pos += 1
            if pos < ll:
                _msg_off[i] = start + pos
                _msg_len[i] = ll - pos
            else:
                _msg_off[i] = 0
                _msg_len[i] = 0
        else:
            # Not a level -- field 3+ is the message
            _lvl[i] = 3
            _msg_off[i] = start + fld_start
            _msg_len[i] = ll - fld_start
