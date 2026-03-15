"""UI dimension constants for the Log Viewer application.

This module defines all dimension-related constants including table dimensions,
column widths, and layout ratios.

Ref: docs/specs/features/typography-system.md §4.2
"""

from src.constants.typography import Typography


# Table dimensions - derived from Typography system
# Ref: docs/specs/features/typography-system.md §3.4
TABLE_ROW_HEIGHT: int = Typography.TABLE_ROW_HEIGHT
"""Height of each row in the log table in pixels (16px for Windows/Linux, 18px for macOS).
Derived from Typography.TABLE_ROW_HEIGHT.
"""

TABLE_HEADER_HEIGHT: int = Typography.TABLE_HEADER_HEIGHT
"""Height of the table header in pixels (fixed at 20px).
Derived from Typography.TABLE_HEADER_HEIGHT.
"""


# Column widths
TIME_COLUMN_WIDTH: int = 80
"""Default width of the time column in pixels."""

CATEGORY_COLUMN_WIDTH: int = 100
"""Default width of the category column in pixels."""

TYPE_COLUMN_WIDTH: int = 60
"""Default width of the type (log level) column in pixels."""

MESSAGE_COLUMN_WIDTH: int = 400
"""Default width of the message column in pixels."""

MIN_COLUMN_WIDTH: int = 5
"""Minimum allowed column width in pixels."""


# Layout ratios
SPLITTER_LEFT_RATIO: int = 75
"""Percentage of space allocated to the left panel (log table)."""

SPLITTER_RIGHT_RATIO: int = 25
"""Percentage of space allocated to the right panel (details)."""


# Statistics bar dimensions
STATISTICS_ICON_WIDTH: int = 16
"""Fixed width of the icon label in statistics counters in pixels."""


# Derived constants
TOTAL_SPLITTER_RATIO: int = SPLITTER_LEFT_RATIO + SPLITTER_RIGHT_RATIO
"""Total ratio for splitter (should equal 100)."""