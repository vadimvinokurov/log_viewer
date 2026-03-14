"""Filter state model."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Set


class FilterMode(Enum):
    """Filter mode enumeration."""
    PLAIN = "plain"
    REGEX = "regex"
    SIMPLE = "simple"


@dataclass
class FilterState:
    """Mutable filter state."""
    enabled_categories: Set[str] = field(default_factory=set)
    filter_text: str = ""
    filter_mode: FilterMode = FilterMode.PLAIN
    all_categories: Set[str] = field(default_factory=set)  # All known categories
    # Default: all log levels enabled (using LogLevel.value strings)
    enabled_levels: Set[str] = field(default_factory=lambda: {
        "LOG_CRITICAL", "LOG_ERROR", "LOG_WARNING", "LOG_MSG", "LOG_DEBUG", "LOG_TRACE"
    })