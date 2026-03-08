"""Filter controller."""
from __future__ import annotations

from typing import Callable

from beartype import beartype
from PySide6.QtCore import QObject, Signal

from src.models.filter_state import FilterMode, FilterState
from src.core.filter_engine import FilterEngine
from src.core.category_tree import CategoryTree
from src.models.log_entry import LogEntry
from src.utils.settings_manager import CustomCategory


class FilterController(QObject):
    """Controller for filter operations."""
    
    # Signals
    filter_applied = Signal()  # Emitted when filter is applied
    filter_error = Signal(str)  # Emitted when filter has an error
    categories_changed = Signal()  # Emitted when categories are updated
    
    @beartype
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._state = FilterState()
        self._engine = FilterEngine()
        self._category_tree = CategoryTree()
        self._compiled_filter: Callable[[LogEntry], bool] | None = None
        self._all_categories_enabled = True
        self._custom_categories: list[CustomCategory] = []
    
    @beartype
    def set_filter_text(self, text: str) -> None:
        """
        Set filter text (does not apply yet).
        
        Args:
            text: Filter text
        """
        self._state.filter_text = text
    
    @beartype
    def set_filter_mode(self, mode: FilterMode) -> None:
        """
        Set filter mode.
        
        Args:
            mode: Filter mode (Plain, Regex, Simple)
        """
        self._state.filter_mode = mode
    
    @beartype
    def get_filter_mode(self) -> FilterMode:
        """Get current filter mode."""
        return self._state.filter_mode
    
    @beartype
    def get_filter_text(self) -> str:
        """Get current filter text."""
        return self._state.filter_text
    
    @beartype
    def validate_current_filter(self) -> tuple[bool, str]:
        """
        Validate the current filter text with current mode.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self._engine.validate_filter(
            self._state.filter_text,
            self._state.filter_mode
        )
    
    @beartype
    def apply_filter(self) -> bool:
        """
        Compile and apply current filter.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §6.3
        // Passes category_tree to FilterEngine for visibility-based filtering
        
        Returns:
            True if filter was applied successfully, False if there was an error
        """
        # Validate first
        is_valid, error_msg = self.validate_current_filter()
        
        if not is_valid:
            self.filter_error.emit(error_msg)
            return False
        
        try:
            # Update enabled categories from tree
            self._state.enabled_categories = self._category_tree.get_enabled_categories()
            
            # Update all known categories
            all_cats = self._category_tree.get_all_categories()
            self._state.all_categories = all_cats
            
            # Check if all categories are enabled
            self._all_categories_enabled = (
                len(self._state.enabled_categories) == len(all_cats)
            )
            
            # Compile the filter with category tree for visibility-based filtering
            # Ref: docs/specs/features/category-checkbox-behavior.md §6.3
            self._compiled_filter = self._engine.compile_filter(
                self._state,
                category_tree=self._category_tree
            )
            
            # Emit success signal
            self.filter_applied.emit()
            return True
            
        except Exception as e:
            self.filter_error.emit(str(e))
            return False
    
    @beartype
    def get_filter(self) -> Callable[[LogEntry], bool] | None:
        """
        Get compiled filter.
        
        Returns:
            Compiled filter callable or None if no filter
        """
        return self._compiled_filter
    
    @beartype
    def set_categories(self, categories: set[str]) -> None:
        """
        Set available categories.
        
        Args:
            categories: Set of category paths
        """
        self._category_tree.clear()
        for cat in categories:
            self._category_tree.add_category(cat)
        
        # All categories enabled by default
        self._state.enabled_categories = self._category_tree.get_enabled_categories()
        self._all_categories_enabled = True
        
        self.categories_changed.emit()
    
    @beartype
    def toggle_category(self, path: str, enabled: bool) -> None:
        """
        Toggle a category (cascades to children).
        
        Args:
            path: Category path
            enabled: New enabled state
        """
        self._category_tree.toggle(path, enabled)
        self._state.enabled_categories = self._category_tree.get_enabled_categories()
        
        # Update all categories flag
        all_cats = self._category_tree.get_all_categories()
        self._all_categories_enabled = (
            len(self._state.enabled_categories) == len(all_cats)
        )
    
    @beartype
    def set_category_enabled(self, path: str, enabled: bool) -> None:
        """
        Set category enabled state WITHOUT cascading to children.
        
        Use this when syncing exact checkbox states from UI.
        
        Args:
            path: Category path
            enabled: New enabled state
        """
        self._category_tree.set_enabled(path, enabled)
    
    @beartype
    def toggle_all_categories(self, enabled: bool) -> None:
        """
        Toggle all categories.
        
        Args:
            enabled: New enabled state for all categories
        """
        if enabled:
            self._category_tree.enable_all()
        else:
            self._category_tree.disable_all()
        
        self._state.enabled_categories = self._category_tree.get_enabled_categories()
        self._all_categories_enabled = enabled
    
    @beartype
    def is_category_enabled(self, path: str) -> bool:
        """
        Check if a category is enabled.
        
        Args:
            path: Category path
            
        Returns:
            True if enabled
        """
        return self._category_tree.is_enabled(path)
    
    @beartype
    def get_enabled_categories(self) -> set[str]:
        """
        Get all enabled categories.
        
        Returns:
            Set of enabled category paths
        """
        return self._state.enabled_categories.copy()
    
    @beartype
    def get_all_categories(self) -> set[str]:
        """
        Get all categories.
        
        Returns:
            Set of all category paths
        """
        return self._category_tree.get_all_categories()
    
    @beartype
    def get_category_tree(self) -> CategoryTree:
        """
        Get the category tree.
        
        Returns:
            CategoryTree instance
        """
        return self._category_tree
    
    @beartype
    def matches(self, entry: LogEntry) -> bool:
        """
        Check if entry matches current filter.
        
        Args:
            entry: Log entry to check
            
        Returns:
            True if entry matches filter (or no filter is set)
        """
        if self._compiled_filter is None:
            return True
        return self._compiled_filter(entry)
    
    @beartype
    def has_active_filter(self) -> bool:
        """
        Check if there's an active text filter.
        
        Returns:
            True if filter text is set
        """
        return bool(self._state.filter_text and self._state.filter_text.strip())
    
    @beartype
    def has_category_filter(self) -> bool:
        """
        Check if category filtering is active.
        
        Returns:
            True if some categories are disabled
        """
        return not self._all_categories_enabled
    
    @beartype
    def clear_filter(self) -> None:
        """Clear the text filter."""
        self._state.filter_text = ""
        self._compiled_filter = None
    
    @beartype
    def reset(self) -> None:
        """Reset all filters to default state."""
        self._state = FilterState()
        self._category_tree.enable_all()
        self._compiled_filter = None
        self._all_categories_enabled = True
        # Reset level filter to all enabled (using LogLevel.value strings)
        self._state.enabled_levels = {
            "LOG_CRITICAL", "LOG_ERROR", "LOG_WARNING", "LOG_MSG", "LOG_DEBUG", "LOG_TRACE"
        }
    
    @beartype
    def get_state(self) -> FilterState:
        """
        Get current filter state.
        
        Returns:
            Current FilterState
        """
        return self._state
    
    @beartype
    def set_state(self, state: FilterState) -> None:
        """
        Set filter state.
        
        Args:
            state: New filter state
        """
        self._state = state
        self._compiled_filter = None  # Will be recompiled on apply
    
    @beartype
    def set_custom_categories(self, categories: list[CustomCategory]) -> None:
        """
        Set custom categories.
        
        Args:
            categories: List of custom categories
        """
        self._custom_categories = categories.copy()
        self._state.custom_categories = self._custom_categories
    
    @beartype
    def get_custom_categories(self) -> list[CustomCategory]:
        """
        Get custom categories.
        
        Returns:
            List of custom categories
        """
        return self._custom_categories.copy()
    
    @beartype
    def set_custom_category_enabled(self, name: str, enabled: bool) -> None:
        """
        Set custom category enabled state.
        
        Args:
            name: Custom category name
            enabled: New enabled state
        """
        for custom in self._custom_categories:
            if custom.name == name:
                custom.enabled = enabled
                break
        self._state.custom_categories = self._custom_categories
    
    @beartype
    def is_custom_category_active(self, name: str) -> bool:
        """
        Check if a custom category is active (enabled and parent is enabled).
        
        Args:
            name: Custom category name
            
        Returns:
            True if custom category is active
        """
        for custom in self._custom_categories:
            if custom.name == name:
                if not custom.enabled:
                    return False
                # Check parent inheritance
                if custom.parent is not None:
                    if not self._category_tree.is_enabled(custom.parent):
                        return False
                return True
        return False
    
    @beartype
    def toggle_level(self, level: str, enabled: bool) -> None:
        """
        Toggle a log level filter.
        
        Args:
            level: Level name (LogLevel value string like "LOG_ERROR", "LOG_WARNING", etc.)
            enabled: New enabled state
        """
        if enabled:
            self._state.enabled_levels.add(level)
        else:
            self._state.enabled_levels.discard(level)
    
    @beartype
    def is_level_enabled(self, level: str) -> bool:
        """
        Check if a log level is enabled.
        
        Args:
            level: Level name (LogLevel value string like "LOG_ERROR", "LOG_WARNING", etc.)
            
        Returns:
            True if level is enabled
        """
        return level in self._state.enabled_levels
    
    @beartype
    def get_enabled_levels(self) -> set[str]:
        """
        Get all enabled log levels.
        
        Returns:
            Set of enabled level names
        """
        return self._state.enabled_levels.copy()
    
    @beartype
    def set_enabled_levels(self, levels: set[str]) -> None:
        """
        Set enabled log levels.
        
        Args:
            levels: Set of level names to enable
        """
        self._state.enabled_levels = levels.copy()