"""Table configuration constants.

This module defines centralized configuration for table columns,
including alignment, widths, and other display properties.

Ref: docs/specs/features/table-column-alignment.md
"""
from __future__ import annotations

from PySide6.QtCore import Qt


# Column alignment constants
# Per docs/specs/features/table-column-alignment.md §2.1

# Alignment for Time, Category, Message columns
ALIGN_LEFT_VCENTER = Qt.AlignLeft | Qt.AlignVCenter

# Alignment for Type column (log level icons)
ALIGN_CENTER = Qt.AlignCenter


# Column alignment mapping by column index
# Used by LogTableModel.data() for Qt.TextAlignmentRole
COLUMN_ALIGNMENTS: dict[int, Qt.AlignmentFlag] = {
    0: ALIGN_LEFT_VCENTER,   # COL_TIME
    1: ALIGN_LEFT_VCENTER,   # COL_CATEGORY
    2: ALIGN_CENTER,         # COL_TYPE
    3: ALIGN_LEFT_VCENTER,   # COL_MESSAGE
}


def get_column_alignment(column: int) -> Qt.AlignmentFlag:
    """Get alignment for a column index.
    
    Args:
        column: Column index (0-3)
        
    Returns:
        Alignment flags, defaults to ALIGN_LEFT_VCENTER if column not found.
        
    Ref: docs/specs/features/table-column-alignment.md §2.1
    """
    return COLUMN_ALIGNMENTS.get(column, ALIGN_LEFT_VCENTER)