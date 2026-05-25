"""Core data models for Log Viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np


class LogLevel(Enum):
    CRITICAL = "LOG_CRITICAL"
    ERROR = "LOG_ERROR"
    WARNING = "LOG_WARNING"
    INFO = "LOG_INFO"
    DEBUG = "LOG_DEBUG"
    TRACE = "LOG_TRACE"

    @property
    def row_style(self) -> str:
        """Rich style string for coloring an entire row by level."""
        _styles = {
            "CRITICAL": "bold red",
            "ERROR": "red",
            "WARNING": "yellow",
            "INFO": "white",
            "DEBUG": "cyan",
            "TRACE": "dim",
        }
        return _styles[self.name]

    @property
    def icon_plain(self) -> str:
        """Plain text symbol for contexts that don't support Rich (e.g. status bar)."""
        _cfg = {
            "CRITICAL": "\u2716",
            "ERROR": "\u2715",
            "WARNING": "\u26a0",
            "INFO": "i",
            "DEBUG": "\u25c6",
            "TRACE": "\u00b7",
        }
        return _cfg[self.name]

    @classmethod
    def from_log_prefix(cls, prefix: str) -> Optional["LogLevel"]:
        """Convert LOG_* string to LogLevel, or None if not a valid prefix."""
        try:
            return cls(prefix)
        except ValueError:
            return None

    @classmethod
    def from_short_code(cls, code: str) -> Optional["LogLevel"]:
        """Convert short level code (wrn, msg, dbg, err, crt) to LogLevel."""
        _short = {
            "wrn": cls.WARNING,
            "msg": cls.INFO,
            "dbg": cls.DEBUG,
            "err": cls.ERROR,
            "crt": cls.CRITICAL,
        }
        return _short.get(code)


class LogFormat(Enum):
    KSIVA = "ksiva"
    PLAIN = "plain"


class SearchMode(Enum):
    PLAIN = "plain"
    REGEX = "regex"
    SIMPLE = "simple"
    LINE_NUMBER = "line_number"


class SearchDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"


class InputMode(Enum):
    NORMAL = "normal"
    COMMAND = "command"
    SEARCH_FORWARD = "search_forward"
    SEARCH_BACKWARD = "search_backward"


@dataclass(slots=True)
class LogLine:
    line_number: int
    timestamp: str
    category: str
    level: LogLevel
    message: str
    file_offset: int
    line_length: int

    @property
    def time_only(self) -> str:
        """Extract time portion (HH:MM:SS.mmm) from timestamp."""
        if not self.timestamp:
            return ""
        return self.timestamp.split("T")[-1]


@dataclass
class Filter:
    pattern: str
    mode: SearchMode
    case_sensitive: bool = False


@dataclass
class Highlight:
    pattern: str
    mode: SearchMode
    case_sensitive: bool = False
    color: str = "0"


@dataclass
class SearchState:
    pattern: str
    mode: SearchMode
    case_sensitive: bool
    direction: SearchDirection
    matches: list[int] = field(default_factory=list)
    current_index: int = 0
    in_search: bool = False


@dataclass
class CategoryNode:
    name: str
    full_path: str
    enabled: bool = True
    line_count: int = 0
    children: dict[str, "CategoryNode"] = field(default_factory=dict)


# --- SoA mapping tables ---

_LEVEL_LIST: list[LogLevel] = [
    LogLevel.CRITICAL,  # 0
    LogLevel.ERROR,     # 1
    LogLevel.WARNING,   # 2
    LogLevel.INFO,      # 3
    LogLevel.DEBUG,     # 4
    LogLevel.TRACE,     # 5
]

_LEVEL_NAMES: dict[str, int] = {
    "LOG_CRITICAL": 0,
    "crt": 0,
    "LOG_ERROR": 1,
    "err": 1,
    "LOG_WARNING": 2,
    "wrn": 2,
    "LOG_INFO": 3,
    "msg": 3,
    "LOG_DEBUG": 4,
    "dbg": 4,
    "LOG_TRACE": 5,
    "trc": 5,
}

# Numpy structured dtype for file offsets (file_offset and line_length stored contiguously)
OFFSET_DTYPE = np.dtype([("file_offset", np.uint64), ("line_length", np.uint32)])


def format_timestamp(ms: int) -> str:
    """Convert milliseconds-from-midnight to 'HH:MM:SS.mmm' string."""
    h = ms // 3_600_000 % 24
    m = ms // 60_000 % 60
    s = ms // 1_000 % 60
    mmm = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d}.{mmm:03d}"


class RowRef:
    """Lightweight read-only proxy for a single log row.

    Created on-the-fly for visible rows (~50). Not stored in bulk.
    Provides the same attribute interface as LogLine for backward-compatible
    consumer code (table model, copy, pin/unpin).
    """

    __slots__ = ("_idx", "_store")

    def __init__(self, idx: int, store: object) -> None:
        self._idx = idx
        self._store = store

    @property
    def line_number(self) -> int:
        return self._idx + 1

    @property
    def timestamp(self) -> str:
        return self._store.get_timestamp(self._idx)

    @property
    def time_only(self) -> str:
        return self.timestamp

    @property
    def category(self) -> str:
        return self._store._category_names[self._store.category_ids[self._idx]]

    @property
    def level(self) -> "LogLevel":
        from log_viewer.core.models import _LEVEL_LIST
        return _LEVEL_LIST[self._store.levels[self._idx]]

    @property
    def message(self) -> str:
        return self._store.get_message(self._idx)

    @property
    def file_offset(self) -> int:
        return int(self._store.line_starts[self._idx])

    @property
    def line_length(self) -> int:
        return int(self._store.line_starts[self._idx + 1] - self._store.line_starts[self._idx])

    def __repr__(self) -> str:
        return (
            f"RowRef(line={self.line_number}, "
            f"time={self.time_only}, "
            f"cat={self.category}, "
            f"lvl={self.level.name}, "
            f"msg={self.message[:40]!r}...)"
        )
