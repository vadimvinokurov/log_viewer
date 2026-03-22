"""Pytest configuration and fixtures."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Generator

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

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
    # Ref: docs/specs/features/log-entry-optimization.md §4.3
    # Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
    # Timestamp converted to Unix epoch float
    return [
        LogEntry(
            row_index=0,
            timestamp=datetime(2026, 2, 25, 18, 31, 0, 965000).timestamp(),
            category="Category1/Subcat1",
            display_message="Error message",
            level=LogLevel.ERROR,
            file_offset=0
        ),
        LogEntry(
            row_index=1,
            timestamp=datetime(2026, 2, 25, 18, 31, 1, 43000).timestamp(),
            category="Category2",
            display_message="Warning message",
            level=LogLevel.WARNING,
            file_offset=65
        ),
        LogEntry(
            row_index=2,
            timestamp=datetime(2026, 2, 25, 18, 31, 2, 123000).timestamp(),
            category="Category1/Subcat2",
            display_message="Info message",
            level=LogLevel.INFO,
            file_offset=130
        ),
        LogEntry(
            row_index=3,
            timestamp=datetime(2026, 2, 25, 18, 31, 3, 456000).timestamp(),
            category="Category3",
            display_message="Another info message",
            level=LogLevel.INFO,
            file_offset=195
        ),
        LogEntry(
            row_index=4,
            timestamp=datetime(2026, 2, 25, 18, 31, 4, 567000).timestamp(),
            category="Category1/Subcat1",
            display_message="Another warning",
            level=LogLevel.WARNING,
            file_offset=260
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
        
        # Ref: docs/specs/features/log-entry-optimization.md §4.3
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        # Timestamp converted to Unix epoch float
        display_message = f"Message {i}"
        
        entries.append(LogEntry(
            row_index=i,
            timestamp=datetime(2026, 2, 25, 18, 31, i % 60, (i % 1000) * 1000).timestamp(),
            category=category,
            display_message=display_message,
            level=level,
            file_offset=i * 100
        ))
    
    return entries


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Create a QApplication instance for tests that need Qt.
    
    This fixture ensures QApplication is available for font detection tests.
    Uses session scope to create only one instance per test session.
    Resets cached fonts in Typography module to ensure proper font detection.
    
    Yields:
        QApplication instance.
    
    Ref: docs/specs/features/typography-system.md §6.1
    """
    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        # Create new QApplication if none exists
        app = QApplication([])
    
    # Reset cached fonts in Typography module
    # This ensures fonts are detected correctly after QApplication is created
    from src.constants.typography import Typography, _CachedFont
    for attr_name in ('UI_FONT', 'LOG_FONT'):
        descriptor = Typography.__dict__.get(attr_name)
        if isinstance(descriptor, _CachedFont):
            descriptor._font = None
    
    yield app
    
    # Cleanup after all tests
    if QApplication.instance() is app:
        app.quit()