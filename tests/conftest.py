"""Pytest configuration and fixtures."""
from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest

from src.models.log_entry import LogEntry, LogLevel


@pytest.fixture
def temp_log_file() -> Generator[str, None, None]:
    """Create a temporary log file for testing.
    
    Yields:
        Path to the temporary log file.
    """
    content = """25-02-2026T18:31:00.965 Category1/Subcat1 LOG_ERROR Error message
25-02-2026T18:31:01.043 Category2 LOG_WARNING Warning message
25-02-2026T18:31:02.123 Category1/Subcat2 LOG_MSG Info message
25-02-2026T18:31:03.456 Category3 Another info message
25-02-2026T18:31:04.567 Category1/Subcat1 LOG_WARNING Another warning
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    try:
        os.unlink(filepath)
    except OSError:
        pass


@pytest.fixture
def sample_log_entries() -> list[LogEntry]:
    """Create sample log entries for testing.
    
    Returns:
        List of sample LogEntry objects.
    """
    return [
        LogEntry(
            row_index=0,
            timestamp="25-02-2026T18:31:00.965",
            category="Category1/Subcat1",
            raw_message="LOG_ERROR Error message",
            display_message="Error message",
            level=LogLevel.ERROR,
            file_offset=0,
            raw_line="25-02-2026T18:31:00.965 Category1/Subcat1 LOG_ERROR Error message"
        ),
        LogEntry(
            row_index=1,
            timestamp="25-02-2026T18:31:01.043",
            category="Category2",
            raw_message="LOG_WARNING Warning message",
            display_message="Warning message",
            level=LogLevel.WARNING,
            file_offset=65,
            raw_line="25-02-2026T18:31:01.043 Category2 LOG_WARNING Warning message"
        ),
        LogEntry(
            row_index=2,
            timestamp="25-02-2026T18:31:02.123",
            category="Category1/Subcat2",
            raw_message="LOG_MSG Info message",
            display_message="Info message",
            level=LogLevel.INFO,
            file_offset=130,
            raw_line="25-02-2026T18:31:02.123 Category1/Subcat2 LOG_MSG Info message"
        ),
        LogEntry(
            row_index=3,
            timestamp="25-02-2026T18:31:03.456",
            category="Category3",
            raw_message="Another info message",
            display_message="Another info message",
            level=LogLevel.INFO,
            file_offset=195,
            raw_line="25-02-2026T18:31:03.456 Category3 Another info message"
        ),
        LogEntry(
            row_index=4,
            timestamp="25-02-2026T18:31:04.567",
            category="Category1/Subcat1",
            raw_message="LOG_WARNING Another warning",
            display_message="Another warning",
            level=LogLevel.WARNING,
            file_offset=260,
            raw_line="25-02-2026T18:31:04.567 Category1/Subcat1 LOG_WARNING Another warning"
        ),
    ]


@pytest.fixture
def temp_settings_file() -> Generator[str, None, None]:
    """Create a temporary settings file path for testing.
    
    Yields:
        Path to the temporary settings file.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    try:
        os.unlink(filepath)
    except OSError:
        pass


@pytest.fixture
def large_log_entries() -> list[LogEntry]:
    """Create a larger set of log entries for performance testing.
    
    Returns:
        List of 1000 sample LogEntry objects.
    """
    entries = []
    for i in range(1000):
        level = LogLevel.INFO
        if i % 10 == 0:
            level = LogLevel.ERROR
        elif i % 5 == 0:
            level = LogLevel.WARNING
        
        category = f"Category{i % 20}"
        if i % 3 == 0:
            category = f"Category{i % 20}/Subcat{i % 5}"
        
        level_prefix = f"{level.value} " if level != LogLevel.INFO else ""
        raw_message = f"{level_prefix}Message {i}"
        display_message = f"Message {i}" if level == LogLevel.INFO else raw_message.split(' ', 1)[1]
        
        entries.append(LogEntry(
            row_index=i,
            timestamp=f"25-02-2026T18:31:{i % 60:02d}.{i % 1000:03d}",
            category=category,
            raw_message=raw_message,
            display_message=display_message,
            level=level,
            file_offset=i * 100,
            raw_line=f"25-02-2026T18:31:{i % 60:02d}.{i % 1000:03d} {category} {raw_message}"
        ))
    
    return entries