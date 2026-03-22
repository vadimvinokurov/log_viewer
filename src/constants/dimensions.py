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


def get_table_header_height() -> int:
    """Get table header height based on actual font metrics.

    Uses QFontMetrics to get the actual rendered height of the font
    and adds appropriate padding for comfortable reading.

    Returns:
        Header height in pixels (font metrics height + 2px padding).
    
    Ref: docs/specs/features/typography-system.md §4.3
    """
    # Use Typography.TABLE_HEADER_HEIGHT which handles QFontMetrics calculation
    return Typography.TABLE_HEADER_HEIGHT


class _LazyTableHeaderHeight:
    """Lazy descriptor for TABLE_HEADER_HEIGHT.
    
    QFontMetrics requires QApplication to be initialized.
    This descriptor computes the value on first access.
    
    Ref: docs/specs/features/typography-system.md §4.3
    """
    
    def __init__(self):
        self._value: int | None = None
    
    def __get__(self, obj, objtype=None) -> int:
        if self._value is None:
            self._value = Typography.TABLE_HEADER_HEIGHT
        return self._value


TABLE_HEADER_HEIGHT: int = _LazyTableHeaderHeight()  # type: ignore[assignment]
"""Height of the table header in pixels.
Computed dynamically from QFontMetrics.height() + 2px padding.
"""


def get_table_cell_height() -> int:
    """Get unified table cell height for both header and rows.

    Uses QFontMetrics to get the actual rendered height of the font
    and adds appropriate padding for comfortable reading.

    Returns:
        Cell height in pixels (font metrics height + 2px padding).
    
    Ref: docs/specs/features/table-unified-styles.md §3.2
    """
    return Typography.TABLE_CELL_HEIGHT


class _LazyTableCellHeight:
    """Lazy descriptor for TABLE_CELL_HEIGHT.
    
    QFontMetrics requires QApplication to be initialized.
    This descriptor computes the value on first access.
    
    Ref: docs/specs/features/table-unified-styles.md §3.2
    """
    
    def __init__(self):
        self._value: int | None = None
    
    def __get__(self, obj, objtype=None) -> int:
        if self._value is None:
            self._value = Typography.TABLE_CELL_HEIGHT
        return self._value


TABLE_CELL_HEIGHT: int = _LazyTableCellHeight()  # type: ignore[assignment]
"""Unified height for both table header and rows in pixels.
Computed dynamically from QFontMetrics.height() + 2px padding.
Ref: docs/specs/features/table-unified-styles.md §3.2
"""


def get_tree_indentation() -> int:
    """Get tree indentation based on Qt style metrics.

    Calculates indentation as checkbox size + gap for proper
    spacing between branch indicator and checkbox.

    Returns:
        Indentation in pixels (checkbox_size + 4px gap).

    Ref: docs/specs/features/category-tree-click-target-spacing.md §5.3
    """
    from PySide6.QtWidgets import QApplication, QStyle

    # Get checkbox size from Qt style
    # Note: QApplication must be initialized before calling this
    style = QApplication.style()
    if style is None:
        return 16  # Fallback: 12px checkbox + 4px gap

    checkbox_size = style.pixelMetric(QStyle.PM_IndicatorWidth)
    gap = 4  # Desktop standard minimum
    return checkbox_size + gap


class _LazyTreeIndentation:
    """Lazy descriptor for TREE_INDENTATION.

    QStyle requires QApplication to be initialized.
    This descriptor computes the value on first access.

    Ref: docs/specs/features/category-tree-click-target-spacing.md §5.3
    """

    def __init__(self):
        self._value: int | None = None

    def __get__(self, obj, objtype=None) -> int:
        if self._value is None:
            self._value = get_tree_indentation()
        return self._value


TREE_INDENTATION: int = _LazyTreeIndentation()  # type: ignore[assignment]
"""Tree indentation in pixels.
Computed dynamically from QStyle.PM_IndicatorWidth + 4px gap.
"""


# Column width constraints for auto-sizing
# Ref: docs/specs/features/table-column-auto-size.md §5.1

MIN_COLUMN_WIDTH: int = 5
"""Minimum allowed column width in pixels."""


# Column width constraints for auto-sizing
# Ref: docs/specs/features/table-column-auto-size.md §5.1

TIME_COLUMN_MIN_WIDTH: int = 60
"""Minimum width for time column in pixels."""

TIME_COLUMN_PADDING: int = 8
"""Padding for time column (4px left + 4px right)."""

TYPE_COLUMN_MIN_WIDTH: int = 30
"""Minimum width for type column in pixels."""

TYPE_COLUMN_PADDING: int = 16
"""Padding for type column (8px left + 8px right for centered icon)."""

CATEGORY_COLUMN_MIN_WIDTH: int = 50
"""Minimum width for category column in pixels."""

CATEGORY_COLUMN_MAX_WIDTH: int = 300
"""Maximum width for category column in pixels."""

CATEGORY_COLUMN_PADDING: int = 8
"""Padding for category column (4px left + 4px right)."""

CATEGORY_COLUMN_SAMPLE_SIZE: int = 100
"""Number of entries to sample for category column auto-sizing."""

MESSAGE_COLUMN_MIN_WIDTH: int = 100
"""Minimum width for message column in pixels."""


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