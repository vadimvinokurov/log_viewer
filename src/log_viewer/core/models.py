"""Core data models for Log Viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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


class SearchMode(Enum):
    PLAIN = "plain"
    REGEX = "regex"
    SIMPLE = "simple"


class SearchDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"


class InputMode(Enum):
    NORMAL = "normal"
    COMMAND = "command"
    SEARCH_FORWARD = "search_forward"
    SEARCH_BACKWARD = "search_backward"


@dataclass
class LogLine:
    line_number: int
    timestamp: str
    category: str
    level: LogLevel
    message: str
    raw: str

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
    color: str = "red"


@dataclass
class SearchState:
    pattern: str
    mode: SearchMode
    case_sensitive: bool
    direction: SearchDirection
    matches: list[int] = field(default_factory=list)
    current_index: int = 0


@dataclass
class CategoryNode:
    name: str
    full_path: str
    enabled: bool = True
    line_count: int = 0
    children: dict[str, "CategoryNode"] = field(default_factory=dict)
