"""Log file parser.

Default format: timestamp category [LOG_LEVEL] message
Split by whitespace (max 3 splits) into up to 4 parts.
If position 2 is a LOG_* prefix → use as level, position 3 = message.
Otherwise → level defaults to INFO, positions 2+ become message.
"""

from __future__ import annotations

import re

from log_viewer.core.models import LogLevel, LogLine

UNCATEGORIZED = "uncategorized"

_SPLIT_RE = re.compile(r"\s+")


def parse_line(raw: str, line_number: int) -> LogLine:
    """Parse a single raw log line into a LogLine."""
    stripped = raw.strip()

    if not stripped:
        return LogLine(
            line_number=line_number,
            timestamp="",
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message="",
            raw=raw,
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
            raw=raw,
        )

    timestamp = parts[0]

    if len(parts) == 2:
        # Timestamp + one more field → category + message (no level)
        return LogLine(
            line_number=line_number,
            timestamp=timestamp,
            category=UNCATEGORIZED,
            level=LogLevel.INFO,
            message=parts[1],
            raw=raw,
        )

    # 3 or 4 parts: [timestamp, category, level_or_message, rest?]
    category = parts[1]
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
            raw=raw,
        )

    # No LOG_* found — merge position 2+ into message
    message = parts[2] if len(parts) == 3 else f"{parts[2]} {parts[3]}"
    return LogLine(
        line_number=line_number,
        timestamp=timestamp,
        category=category,
        level=LogLevel.INFO,
        message=message,
        raw=raw,
    )
