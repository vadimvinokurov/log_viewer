"""Tests for statistics calculator."""
from __future__ import annotations

from datetime import datetime

import pytest

from src.core.statistics import StatisticsCalculator, LogStatistics
from src.models.log_entry import LogEntry, LogLevel


class TestLogStatistics:
    """Tests for LogStatistics dataclass."""
    
    def test_statistics_creation(self) -> None:
        """Test creating log statistics."""
        stats = LogStatistics(
            total_lines=100,
            shown_lines=50,
            critical_count=5,
            error_count=10,
            warning_count=20,
            msg_count=40,
            debug_count=15,
            trace_count=10
        )
        
        assert stats.total_lines == 100
        assert stats.shown_lines == 50
        assert stats.critical_count == 5
        assert stats.error_count == 10
        assert stats.warning_count == 20
        assert stats.msg_count == 40
        assert stats.debug_count == 15
        assert stats.trace_count == 10
    
    def test_to_dict(self) -> None:
        """Test converting statistics to dictionary."""
        stats = LogStatistics(
            total_lines=100,
            shown_lines=50,
            critical_count=5,
            error_count=10,
            warning_count=20,
            msg_count=40,
            debug_count=15,
            trace_count=10
        )
        
        d = stats.to_dict()
        
        assert d == {
            "critical": 5,
            "error": 10,
            "warning": 20,
            "msg": 40,
            "debug": 15,
            "trace": 10,
        }


class TestStatisticsCalculator:
    """Tests for StatisticsCalculator class."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.calculator = StatisticsCalculator()
    
    def _create_entry(
        self,
        category: str = "test",
        level: LogLevel = LogLevel.MSG,
        row_index: int = 0
    ) -> LogEntry:
        """Create a test log entry.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.2
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        raw_message removed - never used outside parser
        timestamp converted to Unix epoch float
        """
        level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
        return LogEntry(
            row_index=row_index,
            timestamp=datetime(2024, 1, 1, 12, 0, 0).timestamp(),
            category=category,
            display_message=f"Message {row_index}",
            level=level,
            file_offset=row_index * 100,
        )
    
    def test_process_single_entry(self) -> None:
        """Test processing single log entry."""
        entry = self._create_entry(level=LogLevel.ERROR)
        
        self.calculator.process_entry(entry)
        
        assert self.calculator.total_lines == 1
        assert self.calculator.error_count == 1
        assert self.calculator.warning_count == 0
        assert self.calculator.msg_count == 0
    
    def test_process_multiple_entries(self) -> None:
        """Test processing multiple log entries."""
        entries = [
            self._create_entry(level=LogLevel.ERROR, row_index=i)
            for i in range(5)
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 5
        assert self.calculator.error_count == 5
    
    def test_count_by_level(self) -> None:
        """Test counting by log level."""
        entries = [
            self._create_entry(level=LogLevel.CRITICAL, row_index=0),
            self._create_entry(level=LogLevel.ERROR, row_index=1),
            self._create_entry(level=LogLevel.ERROR, row_index=2),
            self._create_entry(level=LogLevel.WARNING, row_index=3),
            self._create_entry(level=LogLevel.MSG, row_index=4),
            self._create_entry(level=LogLevel.MSG, row_index=5),
            self._create_entry(level=LogLevel.DEBUG, row_index=6),
            self._create_entry(level=LogLevel.TRACE, row_index=7),
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 8
        assert self.calculator.critical_count == 1
        assert self.calculator.error_count == 2
        assert self.calculator.warning_count == 1
        assert self.calculator.msg_count == 2
        assert self.calculator.debug_count == 1
        assert self.calculator.trace_count == 1
    
    def test_reset(self) -> None:
        """Test resetting statistics."""
        entries = [
            self._create_entry(level=LogLevel.ERROR, category="app", row_index=i)
            for i in range(5)
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 5
        assert self.calculator.error_count == 5
        
        self.calculator.reset()
        
        assert self.calculator.total_lines == 0
        assert self.calculator.error_count == 0
        assert self.calculator.warning_count == 0
        assert self.calculator.msg_count == 0
        assert self.calculator.debug_count == 0
        assert self.calculator.trace_count == 0
        assert self.calculator.critical_count == 0
    
    def test_get_statistics(self) -> None:
        """Test getting statistics snapshot."""
        entries = [
            self._create_entry(level=LogLevel.ERROR, category="app", row_index=0),
            self._create_entry(level=LogLevel.WARNING, category="app", row_index=1),
            self._create_entry(level=LogLevel.MSG, category="lib", row_index=2),
        ]
        
        self.calculator.process_entries(entries)
        
        stats = self.calculator.get_statistics(shown_count=2)
        
        assert stats.total_lines == 3
        assert stats.shown_lines == 2
        assert stats.error_count == 1
        assert stats.warning_count == 1
        assert stats.msg_count == 1
    
    def test_properties(self) -> None:
        """Test property accessors."""
        entry = self._create_entry(level=LogLevel.ERROR)
        self.calculator.process_entry(entry)
        
        assert self.calculator.total_lines == 1
        assert self.calculator.error_count == 1
        assert self.calculator.warning_count == 0
        assert self.calculator.msg_count == 0
    
    def test_empty_statistics(self) -> None:
        """Test statistics with no entries."""
        stats = self.calculator.get_statistics(shown_count=0)
        
        assert stats.total_lines == 0
        assert stats.shown_lines == 0
        assert stats.critical_count == 0
        assert stats.error_count == 0
        assert stats.warning_count == 0
        assert stats.msg_count == 0
        assert stats.debug_count == 0
        assert stats.trace_count == 0
    
    def test_mixed_levels(self) -> None:
        """Test with mixed log levels."""
        entries = [
            self._create_entry(level=LogLevel.CRITICAL, row_index=0),
            self._create_entry(level=LogLevel.ERROR, row_index=1),
            self._create_entry(level=LogLevel.WARNING, row_index=2),
            self._create_entry(level=LogLevel.MSG, row_index=3),
            self._create_entry(level=LogLevel.DEBUG, row_index=4),
            self._create_entry(level=LogLevel.TRACE, row_index=5),
            self._create_entry(level=LogLevel.ERROR, row_index=6),
            self._create_entry(level=LogLevel.MSG, row_index=7),
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 8
        assert self.calculator.critical_count == 1
        assert self.calculator.error_count == 2
        assert self.calculator.warning_count == 1
        assert self.calculator.msg_count == 2
        assert self.calculator.debug_count == 1
        assert self.calculator.trace_count == 1


class TestStatisticsCalculatorPerformance:
    """Performance tests for StatisticsCalculator."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.calculator = StatisticsCalculator()
    
    def _create_entry(
        self,
        category: str = "test",
        level: LogLevel = LogLevel.MSG,
        row_index: int = 0
    ) -> LogEntry:
        """Create a test log entry.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.2
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        raw_message removed - never used outside parser
        timestamp converted to Unix epoch float
        """
        level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
        return LogEntry(
            row_index=row_index,
            timestamp=datetime(2024, 1, 1, 12, 0, 0).timestamp(),
            category=category,
            display_message=f"Message {row_index}",
            level=level,
            file_offset=row_index * 100,
        )
    
    def test_large_batch(self) -> None:
        """Test processing large batch of entries."""
        levels = [LogLevel.CRITICAL, LogLevel.ERROR, LogLevel.WARNING, LogLevel.MSG, LogLevel.DEBUG, LogLevel.TRACE]
        entries = [
            self._create_entry(
                category=f"Category{i % 20}",
                level=levels[i % 6],
                row_index=i
            )
            for i in range(10000)
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 10000
    
    def test_many_categories(self) -> None:
        """Test with many unique categories."""
        entries = [
            self._create_entry(category=f"Category{i}", row_index=i)
            for i in range(1000)
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 1000


class TestStatisticsCalculatorEdgeCases:
    """Edge case tests for StatisticsCalculator."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.calculator = StatisticsCalculator()
    
    def _create_entry(
        self,
        category: str = "test",
        level: LogLevel = LogLevel.MSG,
        row_index: int = 0
    ) -> LogEntry:
        """Create a test log entry.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.2
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        raw_message removed - never used outside parser
        timestamp converted to Unix epoch float
        """
        level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
        return LogEntry(
            row_index=row_index,
            timestamp=datetime(2024, 1, 1, 12, 0, 0).timestamp(),
            category=category,
            display_message=f"Message {row_index}",
            level=level,
            file_offset=row_index * 100,
        )
    
    def test_empty_category(self) -> None:
        """Test with empty category."""
        entry = self._create_entry(category="")
        
        self.calculator.process_entry(entry)
        
        assert self.calculator.total_lines == 1
    
    def test_special_characters_in_category(self) -> None:
        """Test with special characters in category."""
        entry = self._create_entry(category="app/controllers-v1.0")
        
        self.calculator.process_entry(entry)
        
        assert self.calculator.total_lines == 1
    
    def test_unicode_category(self) -> None:
        """Test with unicode characters in category."""
        entry = self._create_entry(category="приложение/модели")
        
        self.calculator.process_entry(entry)
        
        assert self.calculator.total_lines == 1
    
    def test_reset_after_processing(self) -> None:
        """Test reset after processing entries."""
        entries = [
            self._create_entry(level=LogLevel.ERROR, row_index=i)
            for i in range(10)
        ]
        
        self.calculator.process_entries(entries)
        self.calculator.reset()
        
        # Process new entries
        entries = [
            self._create_entry(level=LogLevel.WARNING, row_index=i)
            for i in range(5)
        ]
        
        self.calculator.process_entries(entries)
        
        assert self.calculator.total_lines == 5
        assert self.calculator.error_count == 0
        assert self.calculator.warning_count == 5
    
    def test_multiple_resets(self) -> None:
        """Test multiple resets."""
        entry = self._create_entry()
        
        self.calculator.process_entry(entry)
        self.calculator.reset()
        self.calculator.reset()  # Second reset should be safe
        
        assert self.calculator.total_lines == 0
    
    def test_get_statistics_with_different_shown_counts(self) -> None:
        """Test get_statistics with different shown counts."""
        entries = [
            self._create_entry(row_index=i)
            for i in range(10)
        ]
        
        self.calculator.process_entries(entries)
        
        stats1 = self.calculator.get_statistics(shown_count=5)
        stats2 = self.calculator.get_statistics(shown_count=10)
        
        assert stats1.shown_lines == 5
        assert stats2.shown_lines == 10
        # Other stats should be the same
        assert stats1.total_lines == stats2.total_lines
        assert stats1.msg_count == stats2.msg_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])