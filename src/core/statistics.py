"""Log statistics calculator.

This module provides statistics calculation for log entries,
tracking counts for all log levels: critical, error, warning, msg, debug, trace.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from src.models.log_entry import LogEntry, LogLevel


@dataclass
class LogStatistics:
    """Log statistics data.
    
    Contains counts for all log levels plus total and shown lines.
    """
    total_lines: int
    shown_lines: int
    critical_count: int
    error_count: int
    warning_count: int
    msg_count: int
    debug_count: int
    trace_count: int
    
    def to_dict(self) -> dict[str, int]:
        """Convert statistics to dictionary for counter updates.
        
        Returns:
            Dictionary mapping counter types to counts.
        """
        return {
            "critical": self.critical_count,
            "error": self.error_count,
            "warning": self.warning_count,
            "msg": self.msg_count,
            "debug": self.debug_count,
            "trace": self.trace_count,
        }


class StatisticsCalculator:
    """Calculator for log statistics.
    
    Tracks counts for all log levels:
        - critical: Critical errors
        - error: Error messages
        - warning: Warning messages
        - msg: Informational messages
        - debug: Debug messages
        - trace: Trace messages
    """

    def __init__(self) -> None:
        """Initialize the statistics calculator."""
        self._total_lines: int = 0
        self._counts: dict[LogLevel, int] = {
            LogLevel.CRITICAL: 0,
            LogLevel.ERROR: 0,
            LogLevel.WARNING: 0,
            LogLevel.MSG: 0,
            LogLevel.DEBUG: 0,
            LogLevel.TRACE: 0,
        }

    def process_entry(self, entry: LogEntry) -> None:
        """Process a log entry for statistics.

        Args:
            entry: The log entry to process.
        """
        self._total_lines += 1

        # Count by level
        if entry.level in self._counts:
            self._counts[entry.level] += 1

    def process_entries(self, entries: Iterator[LogEntry] | list[LogEntry]) -> None:
        """Process multiple log entries.

        Args:
            entries: Iterator or list of log entries to process.
        """
        for entry in entries:
            self.process_entry(entry)

    def reset(self) -> None:
        """Reset all statistics."""
        self._total_lines = 0
        for level in self._counts:
            self._counts[level] = 0

    def get_statistics(self, shown_count: int) -> LogStatistics:
        """Get current statistics.

        Args:
            shown_count: Number of currently shown/filtered entries.

        Returns:
            LogStatistics with current counts.
        """
        return LogStatistics(
            total_lines=self._total_lines,
            shown_lines=shown_count,
            critical_count=self._counts[LogLevel.CRITICAL],
            error_count=self._counts[LogLevel.ERROR],
            warning_count=self._counts[LogLevel.WARNING],
            msg_count=self._counts[LogLevel.MSG],
            debug_count=self._counts[LogLevel.DEBUG],
            trace_count=self._counts[LogLevel.TRACE],
        )

    @property
    def total_lines(self) -> int:
        """Get total lines count."""
        return self._total_lines

    @property
    def critical_count(self) -> int:
        """Get critical count."""
        return self._counts[LogLevel.CRITICAL]

    @property
    def error_count(self) -> int:
        """Get error count."""
        return self._counts[LogLevel.ERROR]

    @property
    def warning_count(self) -> int:
        """Get warning count."""
        return self._counts[LogLevel.WARNING]

    @property
    def msg_count(self) -> int:
        """Get msg count."""
        return self._counts[LogLevel.MSG]

    @property
    def debug_count(self) -> int:
        """Get debug count."""
        return self._counts[LogLevel.DEBUG]

    @property
    def trace_count(self) -> int:
        """Get trace count."""
        return self._counts[LogLevel.TRACE]