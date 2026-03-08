"""Service for managing log statistics.

This service wraps the StatisticsCalculator with a clean API for use
by views and controllers, providing caching for performance.
"""
from __future__ import annotations

from typing import Optional

from src.core.statistics import StatisticsCalculator, LogStatistics
from src.models.log_entry import LogEntry


class StatisticsService:
    """Service for managing log statistics.
    
    This service handles:
    - Calculating statistics from log entries
    - Caching statistics for performance
    - Providing clean API for views
    
    The service is decoupled from the UI and can be tested independently.
    """
    
    def __init__(self) -> None:
        """Initialize the statistics service."""
        self._calculator: StatisticsCalculator = StatisticsCalculator()
        self._cached_stats: Optional[LogStatistics] = None
        self._entries_hash: Optional[int] = None
        self._last_shown_count: int = 0
    
    def calculate(
        self, entries: list[LogEntry], shown_count: int = 0
    ) -> LogStatistics:
        """Calculate statistics for log entries.
        
        Args:
            entries: List of log entries to calculate statistics for.
            shown_count: Number of currently shown/filtered entries.
            
        Returns:
            LogStatistics with calculated values.
        """
        # Check if we can use cached stats
        entries_hash = hash(tuple(id(e) for e in entries))
        if (
            self._entries_hash == entries_hash
            and self._cached_stats is not None
            and self._last_shown_count == shown_count
        ):
            return self._cached_stats
        
        # Reset calculator and process entries
        self._calculator.reset()
        self._calculator.process_entries(entries)
        
        # Get statistics
        stats = self._calculator.get_statistics(shown_count)
        
        # Cache results
        self._cached_stats = stats
        self._entries_hash = entries_hash
        self._last_shown_count = shown_count
        
        return stats
    
    def get_level_counts(self, entries: list[LogEntry]) -> dict[str, int]:
        """Get counts by log level.
        
        Args:
            entries: List of log entries.
            
        Returns:
            Dictionary with level counts (critical, error, warning, msg, debug, trace).
        """
        stats = self.calculate(entries)
        return stats.to_dict()
    
    def get_time_range(
        self, entries: list[LogEntry]
    ) -> tuple[Optional[float], Optional[float]]:
        """Get time range of entries.
        
        Note: This is a placeholder for future implementation when
        timestamp tracking is added to StatisticsCalculator.
        
        Args:
            entries: List of log entries.
            
        Returns:
            Tuple of (first_timestamp, last_timestamp) or (None, None).
        """
        # TODO: Implement when timestamp tracking is added
        # For now, return None values
        return (None, None)
    
    def clear_cache(self) -> None:
        """Clear cached statistics."""
        self._cached_stats = None
        self._entries_hash = None
        self._last_shown_count = 0
        self._calculator.reset()
    
    def get_cached_stats(self) -> Optional[LogStatistics]:
        """Get cached statistics without recalculating.
        
        Returns:
            Cached LogStatistics or None if not calculated.
        """
        return self._cached_stats
    
    def update_shown_count(self, shown_count: int) -> Optional[LogStatistics]:
        """Update the shown count in cached statistics.
        
        This is a fast update that doesn't require recalculating
        all statistics, only updating the shown_lines field.
        
        Args:
            shown_count: New shown count value.
            
        Returns:
            Updated LogStatistics or None if no cached stats.
        """
        if self._cached_stats is None:
            return None
        
        self._last_shown_count = shown_count
        # Create new stats with updated shown_count
        self._cached_stats = self._calculator.get_statistics(shown_count)
        return self._cached_stats