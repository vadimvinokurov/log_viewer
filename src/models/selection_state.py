"""Selection state for preserving row selection across filter changes.

Ref: docs/specs/features/selection-preservation.md §4.2
Master: docs/SPEC.md §1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.log_entry import LogEntry
    from src.views.log_table_view import LogEntryDisplay


@dataclass(frozen=True)
class SelectionState:
    """Immutable snapshot of selection state.
    
    Stored before filter operation, used after to restore selection.
    Uses file_offset for identification (works with lazy loading).
    
    Ref: docs/specs/features/selection-preservation.md §4.2
    Master: docs/SPEC.md §1
    """
    offsets: frozenset[int]  # Set of file_offset values
    current_offset: int | None = None  # Current row for keyboard navigation
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_entries(
        cls, 
        entries: list[LogEntry] | list[LogEntryDisplay],
        current_entry: LogEntry | LogEntryDisplay | None = None
    ) -> SelectionState:
        """Create selection state from selected entries.
        
        Extracts file_offset from each entry for stable identification.
        
        Args:
            entries: List of LogEntry or LogEntryDisplay objects.
            current_entry: Currently focused entry (for keyboard navigation).
            
        Returns:
            SelectionState with file_offset values.
        """
        offsets = frozenset(e.file_offset for e in entries)
        current_offset = current_entry.file_offset if current_entry else None
        return cls(offsets=offsets, current_offset=current_offset)
    
    def restore_indices(
        self, 
        new_entries: list[LogEntryDisplay]
    ) -> list[int]:
        """Get row indices for entries that remain visible.
        
        Args:
            new_entries: List of entries in the filtered view.
            
        Returns:
            List of row indices (in new_entries) that should be selected.
        
        Performance: O(m) where m = number of new visible entries.
        """
        indices = []
        for idx, entry in enumerate(new_entries):
            if entry.file_offset in self.offsets:
                indices.append(idx)
        return indices
    
    def is_empty(self) -> bool:
        """Check if selection state is empty.
        
        Returns:
            True if no rows were selected.
        """
        return len(self.offsets) == 0


@dataclass(frozen=True)
class ViewportState:
    """Snapshot of viewport position for preservation.
    
    Captures the visual position of the selected row relative to the viewport
    to enable precise restoration after filter changes.
    
    Attributes:
        selected_offset: file_offset of the selected row (or current index row)
        viewport_offset: Y position of selected row relative to viewport top.
            Positive value = pixels from viewport top.
            Used to restore the exact visual position after filter change.
        row_height: Height of the selected row in pixels (for variable-height rows).
            If None, uses default row height from table view.
    
    Ref: docs/specs/features/selection-preservation.md §7.3
    Master: docs/SPEC.md §1
    """
    selected_offset: int
    viewport_offset: int
    row_height: int | None = None