"""Constants module for the Log Viewer application.

This module exports all application constants from submodules for easy
centralized access. Import from this module to access any constant.

Example:
    from src.constants import APPLICATION_NAME, LogLevel, LogTextColors
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
)

# Color definitions
# Ref: docs/specs/global/color-palette.md §8.1
from src.constants.colors import (
    # New layered architecture
    BaseColors,
    PaletteColors,
    UIColors,
    ProcessColors,
    LogViewerColors,
    HighlightColors,
    
    # Existing classes
    LogTextColors,
    LogIconColors,
    StatsColors,
)

# Dimension constants
# Ref: docs/specs/features/table-column-auto-size.md §5.1
from src.constants.dimensions import (
    # Column width constraints
    TIME_COLUMN_MIN_WIDTH,
    TIME_COLUMN_PADDING,
    TYPE_COLUMN_MIN_WIDTH,
    TYPE_COLUMN_PADDING,
    CATEGORY_COLUMN_MIN_WIDTH,
    CATEGORY_COLUMN_MAX_WIDTH,
    CATEGORY_COLUMN_PADDING,
    CATEGORY_COLUMN_SAMPLE_SIZE,
    MESSAGE_COLUMN_MIN_WIDTH,
    MIN_COLUMN_WIDTH,
    # Layout ratios
    SPLITTER_LEFT_RATIO,
    SPLITTER_RIGHT_RATIO,
    TOTAL_SPLITTER_RATIO,
)

# TABLE_ROW_HEIGHT, TABLE_HEADER_HEIGHT, and TABLE_CELL_HEIGHT are accessed via 
# get_table_row_height(), get_table_header_height(), get_table_cell_height() or 
# Typography constants to ensure QFontMetrics is called only when QApplication is initialized
from src.constants.dimensions import get_table_row_height, get_table_header_height, get_table_cell_height

# Log level definitions
from src.constants.log_levels import (
    LOG_LEVEL_CONFIGS,
    LogLevel,
    LogLevelConfig,
    get_all_log_levels,
    get_log_level_config,
)

# Table configuration
from src.constants.table_config import (
    ALIGN_CENTER,
    ALIGN_LEFT_VCENTER,
    COLUMN_ALIGNMENTS,
    get_column_alignment,
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
    # Colors - New layered architecture
    "BaseColors",
    "PaletteColors",
    "UIColors",
    "ProcessColors",
    "LogViewerColors",
    "HighlightColors",
    # Colors - Existing classes
    "LogTextColors",
    "LogIconColors",
    "StatsColors",
    # Dimensions - Column width constraints
    "TIME_COLUMN_MIN_WIDTH",
    "TIME_COLUMN_PADDING",
    "TYPE_COLUMN_MIN_WIDTH",
    "TYPE_COLUMN_PADDING",
    "CATEGORY_COLUMN_MIN_WIDTH",
    "CATEGORY_COLUMN_MAX_WIDTH",
    "CATEGORY_COLUMN_PADDING",
    "CATEGORY_COLUMN_SAMPLE_SIZE",
    "MESSAGE_COLUMN_MIN_WIDTH",
    "MIN_COLUMN_WIDTH",
    # Dimensions - Layout ratios
    "SPLITTER_LEFT_RATIO",
    "SPLITTER_RIGHT_RATIO",
    "TOTAL_SPLITTER_RATIO",
    "get_table_row_height",
    "get_table_header_height",
    "get_table_cell_height",
    # Log levels
    "LOG_LEVEL_CONFIGS",
    "LogLevel",
    "LogLevelConfig",
    "get_all_log_levels",
    "get_log_level_config",
    # Table configuration
    "ALIGN_CENTER",
    "ALIGN_LEFT_VCENTER",
    "COLUMN_ALIGNMENTS",
    "get_column_alignment",
]