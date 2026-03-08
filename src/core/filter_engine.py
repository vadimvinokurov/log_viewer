"""Filter engine for log entries."""
from __future__ import annotations

import re
from typing import Callable

from beartype import beartype

from src.models.log_entry import LogEntry, LogLevel
from src.models.filter_state import FilterMode, FilterState
from src.core.simple_query_parser import SimpleQueryParser
from src.core.category_tree import CategoryTree
from src.utils.settings_manager import CustomCategory


class FilterEngine:
    """Engine for filtering log entries."""
    
    @beartype
    def __init__(self):
        self._regex_cache: dict[str, re.Pattern] = {}
        self._simple_parser = SimpleQueryParser()
    
    @beartype
    def compile_filter(
        self,
        state: FilterState,
        category_tree: CategoryTree | None = None
    ) -> Callable[[LogEntry], bool]:
        """
        Compile a filter from state.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §6.3
        // Uses is_category_visible() when category_tree is provided
        
        Args:
            state: Filter state with enabled categories, filter text, mode, and enabled levels
            category_tree: Optional CategoryTree for visibility-based filtering.
                          When provided, uses is_category_visible() for correct ancestor checking.
            
        Returns:
            Callable that returns True if entry matches filter
        """
        # Build category filter
        category_filter = self._compile_category_filter(
            state.enabled_categories,
            state.all_categories,
            category_tree
        )
        
        # Build custom category filter (filters by message content)
        custom_filter = self._compile_custom_category_filter(
            state.custom_categories,
            state.enabled_categories
        )
        
        # Build text filter based on mode
        text_filter = self._compile_text_filter(state.filter_text, state.filter_mode)
        
        # Build level filter
        level_filter = self._compile_level_filter(state.enabled_levels)
        
        # Combine filters:
        # - category_filter: filters by log category path
        # - custom_filter: filters by message content (OR with category)
        # - text_filter: additional text filter (AND with category/custom)
        # - level_filter: filters by log level (AND with others)
        
        # Combine category and custom filters with OR logic
        # Special case: if enabled_categories is empty but custom categories exist,
        # we need to use custom filter only
        if category_filter is None and custom_filter is None:
            # No category filtering and no custom categories - match all
            category_or_custom: Callable[[LogEntry], bool] | None = None
        elif category_filter is None:
            # No category filter (all enabled or all disabled)
            # Check if we have any enabled categories at all
            if not state.enabled_categories and state.all_categories:
                # No categories enabled - only custom categories can match
                category_or_custom = custom_filter
            else:
                # All categories enabled - custom categories add more matches (OR)
                # But since all categories pass, we don't need to filter
                category_or_custom = None
        elif custom_filter is None:
            # Only category filter, no custom categories
            category_or_custom = category_filter
        else:
            # Both filters - OR logic: entry passes if category OR custom matches
            def combined_category(entry: LogEntry) -> bool:
                return category_filter(entry) or custom_filter(entry)
            category_or_custom = combined_category
        
        # Combine all filters using AND logic
        filters: list[Callable[[LogEntry], bool]] = []
        
        if category_or_custom is not None:
            filters.append(category_or_custom)
        
        if text_filter is not None:
            filters.append(text_filter)
        
        if level_filter is not None:
            filters.append(level_filter)
        
        if not filters:
            # No filters - match everything
            return lambda entry: True
        
        if len(filters) == 1:
            return filters[0]
        
        # Combine all filters with AND logic
        def combined_filter(entry: LogEntry) -> bool:
            return all(f(entry) for f in filters)
        
        return combined_filter
    
    @beartype
    def _compile_category_filter(
        self,
        enabled_categories: set[str],
        all_categories: set[str],
        category_tree: CategoryTree | None = None
    ) -> Callable[[LogEntry], bool] | None:
        """
        Compile category filter.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §4.1
        // Visibility Rule: log_visible(category) = category.checked OR any_ancestor.checked
        // When category_tree is provided, uses is_category_visible() for correct logic
        
        Args:
            enabled_categories: Set of enabled category paths
            all_categories: Set of all known category paths
            category_tree: Optional CategoryTree for visibility-based filtering
            
        Returns:
            Callable that returns True if entry's category is enabled,
            or None if all categories are enabled (no filtering needed)
        """
        # If all categories are enabled, no filtering needed
        if enabled_categories == all_categories:
            return None
        
        # Use CategoryTree-based filtering if available (spec §6.3)
        if category_tree is not None:
            # Use is_category_visible() for correct ancestor-based visibility
            # Ref: docs/specs/features/category-checkbox-behavior.md §4.1
            def tree_category_filter(entry: LogEntry) -> bool:
                return category_tree.is_category_visible(entry.category)
            
            return tree_category_filter
        
        # Fallback: set-based filtering (backward compatibility)
        # If no categories are enabled, return a filter that rejects all
        # (unless custom categories are active)
        if not enabled_categories:
            # Return None here - the caller will handle combining with custom categories
            # If there are no custom categories, nothing will pass
            # If there are custom categories, they will provide the filter
            return None
        
        # Make copies to avoid mutation issues
        enabled = frozenset(enabled_categories)
        all_known = frozenset(all_categories)
        
        def category_filter(entry: LogEntry) -> bool:
            # Check if the entry's category is enabled
            # A category is enabled if:
            # 1. The exact category is in the enabled set, OR
            # 2. Any parent of the category is in the enabled set
            #
            # A category is disabled if:
            # 1. It's in all_known but not in enabled (explicitly disabled), OR
            # 2. Any parent is in all_known but not in enabled
            
            if entry.category in enabled:
                return True
            
            # Check if the category is explicitly disabled
            if entry.category in all_known:
                # Category exists but is not enabled
                return False
            
            # Category is not in all_known (virtual/unknown category)
            # Check if any parent path is enabled
            parts = entry.category.split('/')
            for i in range(1, len(parts)):
                parent_path = '/'.join(parts[:i])
                if parent_path in enabled:
                    return True
                # If parent is known but not enabled, this category is disabled
                if parent_path in all_known and parent_path not in enabled:
                    return False
            
            # No parent found in enabled set
            return False
        
        return category_filter
    
    @beartype
    def _compile_custom_category_filter(
        self,
        custom_categories: list[CustomCategory],
        enabled_categories: set[str]
    ) -> Callable[[LogEntry], bool] | None:
        """
        Compile custom category filter.
        
        Custom categories filter by message content (substring match),
        not by log category path. They can be attached to a parent
        category for hierarchical filtering.
        
        Args:
            custom_categories: List of custom categories
            enabled_categories: Set of enabled category paths (for parent check)
            
        Returns:
            Callable that returns True if entry's message matches any enabled
            custom category pattern, or None if no custom categories are active
        """
        # Filter to only enabled custom categories
        active_customs = []
        for custom in custom_categories:
            if not custom.enabled:
                continue
            
            # Check parent inheritance
            if custom.parent is not None:
                # Parent must be enabled for custom category to be active
                if custom.parent not in enabled_categories:
                    continue
            
            active_customs.append(custom)
        
        if not active_customs:
            return None
        
        # Pre-compile patterns to lowercase for case-insensitive matching
        patterns = [(custom.name, custom.pattern.lower()) for custom in active_customs]
        
        def custom_filter(entry: LogEntry) -> bool:
            # Check if message contains any custom pattern (case-insensitive)
            message_lower = entry.raw_line.lower()
            for name, pattern in patterns:
                if pattern in message_lower:
                    return True
            return False
        
        return custom_filter
    
    @beartype
    def _compile_text_filter(
        self,
        text: str,
        mode: FilterMode
    ) -> Callable[[LogEntry], bool] | None:
        """
        Compile text filter based on mode.
        
        Args:
            text: Filter text
            mode: Filter mode (Plain, Regex, Simple)
            
        Returns:
            Callable that returns True if entry matches,
            or None if no text filter needed
        """
        if not text or not text.strip():
            # Empty filter - match all
            return None
        
        if mode == FilterMode.PLAIN:
            return self._compile_plain_filter(text)
        elif mode == FilterMode.REGEX:
            return self._compile_regex_filter(text)
        elif mode == FilterMode.SIMPLE:
            return self._compile_simple_filter(text)
        else:
            raise ValueError(f"Unknown filter mode: {mode}")
    
    @beartype
    def _compile_level_filter(
        self,
        enabled_levels: set[str]
    ) -> Callable[[LogEntry], bool] | None:
        """
        Compile level filter.
        
        Args:
            enabled_levels: Set of enabled level names (LogLevel value strings)
            
        Returns:
            Callable that returns True if entry's level is enabled,
            or None if all levels are enabled (no filtering needed)
        """
        # All levels enabled - no filtering needed
        # Default levels are all log levels
        all_levels = {
            LogLevel.CRITICAL.value,
            LogLevel.ERROR.value,
            LogLevel.WARNING.value,
            LogLevel.MSG.value,
            LogLevel.DEBUG.value,
            LogLevel.TRACE.value,
        }
        if enabled_levels == all_levels:
            return None
        
        # No levels enabled - reject all
        if not enabled_levels:
            return lambda entry: False
        
        # Build level mapping from string to LogLevel enum
        level_map = {
            LogLevel.CRITICAL.value: LogLevel.CRITICAL,
            LogLevel.ERROR.value: LogLevel.ERROR,
            LogLevel.WARNING.value: LogLevel.WARNING,
            LogLevel.MSG.value: LogLevel.MSG,
            LogLevel.DEBUG.value: LogLevel.DEBUG,
            LogLevel.TRACE.value: LogLevel.TRACE,
        }
        
        # Get enabled LogLevel enums
        enabled_level_enums = frozenset(
            level_map[level] for level in enabled_levels if level in level_map
        )
        
        def level_filter(entry: LogEntry) -> bool:
            return entry.level in enabled_level_enums
        
        return level_filter
    
    @beartype
    def _compile_plain_filter(self, text: str) -> Callable[[LogEntry], bool]:
        """
        Compile plain text filter (case-insensitive substring).
        
        Args:
            text: Text to search for
            
        Returns:
            Callable that returns True if entry contains text
        """
        # Case-insensitive search
        search_text = text.lower()
        
        def plain_filter(entry: LogEntry) -> bool:
            return search_text in entry.raw_line.lower()
        
        return plain_filter
    
    @beartype
    def _compile_regex_filter(self, pattern: str) -> Callable[[LogEntry], bool]:
        """
        Compile regex filter with caching.
        
        Args:
            pattern: Regex pattern string
            
        Returns:
            Callable that returns True if entry matches pattern
            
        Raises:
            re.error: If pattern is invalid
        """
        # Check cache
        if pattern in self._regex_cache:
            compiled = self._regex_cache[pattern]
        else:
            # Compile and cache
            compiled = re.compile(pattern)
            self._regex_cache[pattern] = compiled
        
        def regex_filter(entry: LogEntry) -> bool:
            return compiled.search(entry.raw_line) is not None
        
        return regex_filter
    
    @beartype
    def _compile_simple_filter(self, query: str) -> Callable[[LogEntry], bool]:
        """
        Compile simple query language filter.
        
        Args:
            query: Query string like "`error` and not `warning`"
            
        Returns:
            Callable that returns True if entry matches query
            
        Raises:
            ValueError: If query is malformed
        """
        return self._simple_parser.compile(query)
    
    def clear_cache(self) -> None:
        """Clear regex cache."""
        self._regex_cache.clear()
    
    @beartype
    def validate_filter(self, text: str, mode: FilterMode) -> tuple[bool, str]:
        """
        Validate a filter without compiling it.
        
        Args:
            text: Filter text
            mode: Filter mode
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or not text.strip():
            return True, ""
        
        if mode == FilterMode.REGEX:
            try:
                re.compile(text)
                return True, ""
            except re.error as e:
                return False, f"Invalid regex: {e}"
        
        if mode == FilterMode.SIMPLE:
            try:
                self._simple_parser.parse(text)
                return True, ""
            except ValueError as e:
                return False, f"Invalid query: {e}"
        
        # Plain mode is always valid
        return True, ""
    
    @beartype
    def get_cache_size(self) -> int:
        """Get number of cached regex patterns."""
        return len(self._regex_cache)