"""Saved filter model and store.

// Ref: docs/specs/features/saved-filters.md §2.1, §2.2
// Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
// Thread: Main thread only (per docs/specs/global/threading.md §8.1)
// Memory: Stack-allocated dataclass, dict for O(1) lookup
// Perf: O(1) add/remove/lookup, O(n) for get_all_filters
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beartype import beartype

if TYPE_CHECKING:
    from src.models.filter_state import FilterMode


@dataclass
class SavedFilter:
    """Saved filter configuration.
    
    // Ref: docs/specs/features/saved-filters.md §2.1
    """
    id: str
    name: str
    filter_text: str
    filter_mode: FilterMode
    created_at: float
    enabled: bool = True


class SavedFilterStore:
    """Manages saved filters collection.
    
    // Ref: docs/specs/features/saved-filters.md §2.2
    // Persists to QSettings via SettingsManager
    // Thread: Main thread only (per docs/specs/global/threading.md §8.1)
    """
    
    @beartype
    def __init__(self) -> None:
        """Initialize the store."""
        self._filters: dict[str, SavedFilter] = {}
    
    @beartype
    def add_filter(self, filter: SavedFilter) -> str:
        """Add new filter, return ID.
        
        Args:
            filter: The filter to add.
            
        Returns:
            The filter ID.
        """
        self._filters[filter.id] = filter
        return filter.id
    
    @beartype
    def remove_filter(self, id: str) -> bool:
        """Remove filter by ID, return success.
        
        Args:
            id: The filter ID to remove.
            
        Returns:
            True if filter was removed, False if not found.
        """
        if id in self._filters:
            del self._filters[id]
            return True
        return False
    
    @beartype
    def rename_filter(self, id: str, new_name: str) -> bool:
        """Rename filter, return success.
        
        Args:
            id: The filter ID to rename.
            new_name: The new name for the filter.
            
        Returns:
            True if filter was renamed, False if not found.
        """
        if id in self._filters:
            self._filters[id].name = new_name
            return True
        return False
    
    @beartype
    def set_enabled(self, id: str, enabled: bool) -> bool:
        """Toggle filter enabled state.
        
        Args:
            id: The filter ID to update.
            enabled: The new enabled state.
            
        Returns:
            True if filter was updated, False if not found.
        """
        if id in self._filters:
            self._filters[id].enabled = enabled
            return True
        return False
    
    @beartype
    def get_enabled_filters(self) -> list[SavedFilter]:
        """Get all enabled filters.
        
        Returns:
            List of enabled filters.
        """
        return [f for f in self._filters.values() if f.enabled]
    
    @beartype
    def get_all_filters(self) -> list[SavedFilter]:
        """Get all filters (enabled and disabled).
        
        Returns:
            List of all filters.
        """
        return list(self._filters.values())