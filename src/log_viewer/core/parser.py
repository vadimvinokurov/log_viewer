"""Log file parser.

Default format: timestamp category [LOG_LEVEL] message
Split by whitespace (max 3 splits) into up to 4 parts.
If position 2 is a LOG_* prefix → use as level, position 3 = message.
Otherwise → level defaults to INFO, positions 2+ become message.
"""

from __future__ import annotations

import re
import sys

from log_viewer.core.models import LogFormat, LogLevel, LogLine

UNCATEGORIZED = "uncategorized"

_SPLIT_RE = re.compile(r"\s+")
_PLAIN_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d+\s+\d+\.\d+\s+(wrn|msg|dbg|err|crt)\s+")


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
            timestamp=sys.intern(timestamp),
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
