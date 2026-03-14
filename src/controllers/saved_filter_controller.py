"""Controller for saved filter operations.

# Ref: docs/specs/features/saved-filters.md §5.1
# Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
# Thread: Main thread only (per docs/specs/global/threading.md §8.1)
# Memory: Owned by MainController (Qt parent-child)
# Perf: Filter compilation on-demand, cached until filter list changes
"""
from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Callable

from beartype import beartype
from PySide6.QtCore import QObject, Signal

from src.models.saved_filter import SavedFilter, SavedFilterStore
from src.models.filter_state import FilterMode
from src.utils.settings_manager import SettingsManager

if TYPE_CHECKING:
    from src.core.filter_engine import FilterEngine
    from src.models.filter_state import FilterState
    from src.models.log_entry import LogEntry


class SavedFilterController(QObject):
    """Controller for saved filter operations.
    
    // Ref: docs/specs/features/saved-filters.md §5.1
    Manages saved filters: save, delete, rename, enable/disable.
    Combines multiple enabled filters with OR logic.
    """
    
    # Signals
    filters_changed = Signal()  # Filter list changed
    filter_applied = Signal()   # Combined filter applied
    
    @beartype
    def __init__(
        self, 
        settings_manager: SettingsManager, 
        parent: QObject | None = None
    ) -> None:
        """Initialize controller with settings manager.
        
        Args:
            settings_manager: Settings manager for persistence
            parent: Parent QObject for Qt parent-child ownership
        """
        super().__init__(parent)
        self._store = SavedFilterStore()
        self._settings_manager = settings_manager
        self._load_from_settings()
    
    @beartype
    def save_filter(
        self, 
        text: str, 
        mode: FilterMode, 
        name: str | None = None
    ) -> str:
        """Save a new filter.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        
        Args:
            text: Filter text content
            mode: Filter mode (Plain, Regex, Simple)
            name: Optional name (auto-generated if None)
            
        Returns:
            Filter ID
        """
        filter_id = str(uuid.uuid4())
        if name is None:
            name = self._generate_name(text)
        
        saved_filter = SavedFilter(
            id=filter_id,
            name=name,
            filter_text=text,
            filter_mode=mode,
            created_at=time.time(),
            enabled=True
        )
        
        self._store.add_filter(saved_filter)
        self._save_to_settings()
        self.filters_changed.emit()
        return filter_id
    
    @beartype
    def delete_filter(self, filter_id: str) -> bool:
        """Delete a saved filter.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        
        Args:
            filter_id: ID of filter to delete
            
        Returns:
            True if filter was deleted, False if not found
        """
        success = self._store.remove_filter(filter_id)
        if success:
            self._save_to_settings()
            self.filters_changed.emit()
        return success
    
    @beartype
    def rename_filter(self, filter_id: str, new_name: str) -> bool:
        """Rename a saved filter.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        
        Args:
            filter_id: ID of filter to rename
            new_name: New name for the filter
            
        Returns:
            True if filter was renamed, False if not found
        """
        success = self._store.rename_filter(filter_id, new_name)
        if success:
            self._save_to_settings()
            self.filters_changed.emit()
        return success
    
    @beartype
    def set_filter_enabled(self, filter_id: str, enabled: bool) -> None:
        """Enable/disable a saved filter.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        
        Args:
            filter_id: ID of filter to update
            enabled: New enabled state
        """
        self._store.set_enabled(filter_id, enabled)
        self._save_to_settings()
        self.filter_applied.emit()
    
    def get_combined_filter(self) -> Callable[[LogEntry], bool] | None:
        """Get combined filter for all enabled saved filters.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        // Ref: docs/specs/features/saved-filters.md §3.1 (OR logic)
        
        Returns:
            Callable that returns True if entry matches ANY enabled filter,
            or None if no filters are enabled.
        """
        enabled_filters = self._store.get_enabled_filters()
        if not enabled_filters:
            return None
        
        # Import here to avoid circular dependency
        from src.core.filter_engine import FilterEngine
        from src.models.filter_state import FilterState
        
        # Compile each filter
        filter_engine = FilterEngine()
        compiled_filters: list[Callable[[LogEntry], bool]] = []
        
        for f in enabled_filters:
            state = FilterState(
                filter_text=f.filter_text,
                filter_mode=f.filter_mode
            )
            compiled = filter_engine.compile_filter(state)
            compiled_filters.append(compiled)
        
        # Combine with OR logic
        # Ref: docs/specs/features/saved-filters.md §3.1
        def combined_filter(entry: LogEntry) -> bool:
            return any(f(entry) for f in compiled_filters)
        
        return combined_filter
    
    @beartype
    def get_all_filters(self) -> list[SavedFilter]:
        """Get all saved filters.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        
        Returns:
            List of all saved filters (enabled and disabled)
        """
        return self._store.get_all_filters()
    
    def _generate_name(self, text: str) -> str:
        """Generate filter name from text.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        // Uses first 30 chars of text as name
        
        Args:
            text: Filter text
            
        Returns:
            Generated name
        """
        # Use first 30 chars of text as name
        return text[:30] + ("..." if len(text) > 30 else "")
    
    def _save_to_settings(self) -> None:
        """Persist filters to settings.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        // Ref: docs/specs/features/saved-filters.md §6.1
        """
        filters_data = [
            {
                "id": f.id,
                "name": f.name,
                "filter_text": f.filter_text,
                "filter_mode": f.filter_mode.value,
                "created_at": f.created_at,
                "enabled": f.enabled
            }
            for f in self._store.get_all_filters()
        ]
        self._settings_manager.save_saved_filters(filters_data)
    
    def _load_from_settings(self) -> None:
        """Load filters from settings.
        
        // Ref: docs/specs/features/saved-filters.md §5.1
        // Ref: docs/specs/features/saved-filters.md §6.1
        """
        from src.models.filter_state import FilterMode
        
        filters_data = self._settings_manager.load_saved_filters()
        for data in filters_data:
            try:
                saved_filter = SavedFilter(
                    id=data["id"],
                    name=data["name"],
                    filter_text=data["filter_text"],
                    filter_mode=FilterMode(data["filter_mode"]),
                    created_at=data["created_at"],
                    enabled=data.get("enabled", True)
                )
                self._store.add_filter(saved_filter)
            except (KeyError, ValueError) as e:
                # Ref: docs/specs/features/saved-filters.md §7.1
                # Invalid filter mode - skip this filter
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load saved filter: {e}")