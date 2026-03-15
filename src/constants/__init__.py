"""Constants module for the Log Viewer application.

This module exports all application constants from submodules for easy
centralized access. Import from this module to access any constant.

Example:
    from src.constants import WINDOW_MIN_WIDTH, LogLevel, LogColors
"""

from __future__ import annotations

# Application-wide constants
from src.constants.app_constants import (
    APPLICATION_NAME,
    APPLICATION_VERSION,
    AUTO_SCROLL_ENABLED,
    DEFAULT_CASE_SENSITIVE,
    FILE_WATCHER_DELAY,
    MAX_RECENT_FILES,
    STATUS_MESSAGE_TIMEOUT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)

# Color definitions
from src.constants.colors import (
    BORDER_COLOR,
    DEFAULT_TEXT_COLOR,
    FIND_HIGHLIGHT_COLOR,
    HEADER_BACKGROUND,
    LogColors,
    LogIconColors,
    SECONDARY_TEXT_COLOR,
    SELECTION_HIGHLIGHT_COLOR,
    StatsColors,
)

# Dimension constants
from src.constants.dimensions import (
    CATEGORY_COLUMN_WIDTH,
    MESSAGE_COLUMN_WIDTH,
    MIN_COLUMN_WIDTH,
    SPLITTER_LEFT_RATIO,
    SPLITTER_RIGHT_RATIO,
    TABLE_HEADER_HEIGHT,
    TIME_COLUMN_WIDTH,
    TOTAL_SPLITTER_RATIO,
    TYPE_COLUMN_WIDTH,
)

# TABLE_ROW_HEIGHT is accessed via get_table_row_height() or Typography.TABLE_ROW_HEIGHT
# to ensure QFontMetrics is called only when QApplication is initialized
from src.constants.dimensions import get_table_row_height

# Log level definitions
from src.constants.log_levels import (
    LOG_LEVEL_CONFIGS,
    LogLevel,
    LogLevelConfig,
    get_all_log_levels,
    get_log_level_config,
)

__all__ = [
    # App constants
    "APPLICATION_NAME",
    "APPLICATION_VERSION",
    "AUTO_SCROLL_ENABLED",
    "DEFAULT_CASE_SENSITIVE",
    "FILE_WATCHER_DELAY",
    "MAX_RECENT_FILES",
    "STATUS_MESSAGE_TIMEOUT",
    "WINDOW_MIN_HEIGHT",
    "WINDOW_MIN_WIDTH",
    # Colors
    "BORDER_COLOR",
    "DEFAULT_TEXT_COLOR",
    "FIND_HIGHLIGHT_COLOR",
    "HEADER_BACKGROUND",
    "LogColors",
    "LogIconColors",
    "SECONDARY_TEXT_COLOR",
    "SELECTION_HIGHLIGHT_COLOR",
    "StatsColors",
    # Dimensions
    "CATEGORY_COLUMN_WIDTH",
    "MESSAGE_COLUMN_WIDTH",
    "MIN_COLUMN_WIDTH",
    "SPLITTER_LEFT_RATIO",
    "SPLITTER_RIGHT_RATIO",
    "TABLE_HEADER_HEIGHT",
    "TIME_COLUMN_WIDTH",
    "TOTAL_SPLITTER_RATIO",
    "TYPE_COLUMN_WIDTH",
    "get_table_row_height",
    # Log levels
    "LOG_LEVEL_CONFIGS",
    "LogLevel",
    "LogLevelConfig",
    "get_all_log_levels",
    "get_log_level_config",
]