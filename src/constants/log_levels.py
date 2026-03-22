"""Log level definitions and configurations for the Log Viewer application.

This module defines the LogLevel enum and associated configuration data
including colors, icons, and visual styling for each log level.

Ref: docs/specs/global/color-palette.md §5.1
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.constants.colors import (
    BaseColors,
    UIColors,
    StatsColors,
    LogIconColors,
)


class LogLevel(Enum):
    """Enumeration of all supported log levels in the application.
    
    Log levels are ordered from most severe (CRITICAL) to least severe (TRACE).
    """
    
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    MSG = "MSG"
    DEBUG = "DEBUG"
    TRACE = "TRACE"


@dataclass(frozen=True)
class LogLevelConfig:
    """Configuration data for a log level.
    
    Contains all visual and metadata properties for a single log level.
    
    Attributes:
        level: The LogLevel enum value this config represents.
        icon: Unicode icon string displayed for this log level.
        background_color: Hex color string for the background.
        text_color: Hex color string for the text.
        border_color: Hex color string for the border.
        tooltip: Tooltip text for this log level.
    """
    
    level: LogLevel
    icon: str
    background_color: str
    text_color: str
    border_color: str
    tooltip: str = ""


# Mapping of LogLevel to its configuration
# Ref: docs/specs/global/color-palette.md §5.1 (StatsColors)
LOG_LEVEL_CONFIGS: dict[LogLevel, LogLevelConfig] = {
    LogLevel.CRITICAL: LogLevelConfig(
        level=LogLevel.CRITICAL,
        icon="⛔",
        background_color=StatsColors.CRITICAL_BG,
        text_color=BaseColors.WHITE,
        border_color=StatsColors.CRITICAL_BORDER,
        tooltip="Critical errors",
    ),
    LogLevel.ERROR: LogLevelConfig(
        level=LogLevel.ERROR,
        icon="🛑",
        background_color=StatsColors.ERROR_BG,
        text_color=BaseColors.WHITE,
        border_color=StatsColors.ERROR_BORDER,
        tooltip="Errors",
    ),
    LogLevel.WARNING: LogLevelConfig(
        level=LogLevel.WARNING,
        icon="⚠️",
        background_color=StatsColors.WARNING_BG,
        text_color=BaseColors.BLACK,
        border_color=StatsColors.WARNING_BORDER,
        tooltip="Warnings",
    ),
    LogLevel.MSG: LogLevelConfig(
        level=LogLevel.MSG,
        icon="ℹ️",
        background_color=BaseColors.WHITE,
        text_color=BaseColors.BLACK,
        border_color=StatsColors.MSG_BORDER,
        tooltip="Messages",
    ),
    LogLevel.DEBUG: LogLevelConfig(
        level=LogLevel.DEBUG,
        icon="🟪",
        background_color=StatsColors.DEBUG_BG,
        text_color=UIColors.TEXT_PRIMARY,
        border_color=UIColors.TEXT_DISABLED,
        tooltip="Debug",
    ),
    LogLevel.TRACE: LogLevelConfig(
        level=LogLevel.TRACE,
        icon="🟩",
        background_color=UIColors.BACKGROUND_SECONDARY,
        text_color=UIColors.TEXT_SECONDARY,
        border_color=LogIconColors.TRACE,
        tooltip="Trace",
    ),
}


def get_log_level_config(level: LogLevel) -> LogLevelConfig:
    """Get the configuration for a specific log level.
    
    Args:
        level: The LogLevel to get configuration for.
        
    Returns:
        The LogLevelConfig for the specified level.
        
    Raises:
        KeyError: If the level is not found in LOG_LEVEL_CONFIGS.
    """
    return LOG_LEVEL_CONFIGS[level]


def get_all_log_levels() -> list[LogLevel]:
    """Get all log levels in order from most to least severe.
    
    Returns:
        List of all LogLevel values in severity order.
    """
    return list(LogLevel)