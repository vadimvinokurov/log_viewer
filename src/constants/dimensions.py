"""UI dimension constants for the Log Viewer application.

This module defines all dimension-related constants including table dimensions,
column widths, and layout ratios.

Ref: docs/specs/features/typography-system.md §4.2
"""

from __future__ import annotations

from src.constants.typography import Typography


# Table dimensions - derived from Typography system
# Ref: docs/specs/features/typography-system.md §4.3


def get_table_row_height() -> int:
    """Get table row height based on actual font metrics.

    Uses QFontMetrics to get the actual rendered height of the font
    and adds appropriate padding for comfortable reading.

    Returns:
        Row height in pixels (font metrics height + 2px padding).
    
    Ref: docs/specs/features/typography-system.md §4.3
    """
    # Use Typography.TABLE_ROW_HEIGHT which handles QFontMetrics calculation
    return Typography.TABLE_ROW_HEIGHT


class _LazyTableRowHeight:
    """Lazy descriptor for TABLE_ROW_HEIGHT.
    
    QFontMetrics requires QApplication to be initialized.
    This descriptor computes the value on first access.
    
    Ref: docs/specs/features/typography-system.md §4.3
    """
    
    def __init__(self):
        self._value: int | None = None
    
    def __get__(self, obj, objtype=None) -> int:
        if self._value is None:
            self._value = Typography.TABLE_ROW_HEIGHT
        return self._value


# Module-level constant computed lazily on first access
TABLE_ROW_HEIGHT: int = _LazyTableRowHeight()  # type: ignore[assignment]
"""Height of each row in the log table in pixels.
Computed dynamically from QFontMetrics.height() + 2px padding.
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