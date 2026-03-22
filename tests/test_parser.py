"""Tests for log parser."""
import pytest
from datetime import datetime
from src.core.parser import LogParser
from src.models.log_entry import LogLevel


class TestLogParser:
    """Test cases for LogParser."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = LogParser()
    
    def test_parse_valid_log_line_with_error(self):
        """Test parsing a valid log line with ERROR level."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR Connection failed"
        entry = self.parser.parse_line(line, row_index=0, file_offset=0)
        
        assert entry is not None
        assert entry.row_index == 0
        # Ref: docs/specs/features/timestamp-unix-epoch.md §7.1
        # timestamp is now Unix Epoch float
        expected_dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
        assert isinstance(entry.timestamp, float)
        assert abs(entry.timestamp - expected_dt.timestamp()) < 0.001
        assert entry.category == "HordeMode"
        # Ref: docs/specs/features/log-entry-optimization.md §4.3
        # raw_line removed - lazy loaded via LogDocument.get_raw_line()
        assert entry.display_message == "Connection failed"
        assert entry.level == LogLevel.ERROR
        assert entry.file_offset == 0
    
    def test_parse_valid_log_line_with_warning(self):
        """Test parsing a valid log line with WARNING level."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_WARNING Memory low"
        entry = self.parser.parse_line(line, row_index=1, file_offset=50)
        
        assert entry is not None
        assert entry.row_index == 1
        # Ref: docs/specs/features/timestamp-unix-epoch.md §7.1
        expected_dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
        assert isinstance(entry.timestamp, float)
        assert abs(entry.timestamp - expected_dt.timestamp()) < 0.001
        assert entry.category == "HordeMode"
        assert entry.display_message == "Memory low"
        assert entry.level == LogLevel.WARNING
        assert entry.file_offset == 50
    
    def test_parse_valid_log_line_with_info(self):
        """Test parsing a valid log line with MSG level (LOG_MSG)."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_MSG Starting up"
        entry = self.parser.parse_line(line, row_index=2, file_offset=100)
        
        assert entry is not None
        assert entry.row_index == 2
        # Ref: docs/specs/features/timestamp-unix-epoch.md §7.1
        expected_dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
        assert isinstance(entry.timestamp, float)
        assert abs(entry.timestamp - expected_dt.timestamp()) < 0.001
        assert entry.category == "HordeMode"
        assert entry.display_message == "Starting up"
        assert entry.level == LogLevel.MSG
    
    def test_parse_log_line_without_level_marker(self):
        """Test parsing a log line without level marker (defaults to MSG)."""
        line = "10-03-2026T15:30:45.123 HordeMode Some regular message"
        entry = self.parser.parse_line(line, row_index=3, file_offset=150)
        
        assert entry is not None
        assert entry.level == LogLevel.MSG
        assert entry.display_message == "Some regular message"
    
    def test_parse_log_line_with_category_hierarchy(self):
        """Test parsing a log line with hierarchical category."""
        line = "10-03-2026T15:30:45.123 HordeMode/scripts/app LOG_ERROR Init failed"
        entry = self.parser.parse_line(line, row_index=4, file_offset=200)
        
        assert entry is not None
        assert entry.category == "HordeMode/scripts/app"
        assert entry.level == LogLevel.ERROR
        assert entry.display_message == "Init failed"
    
    def test_parse_empty_line(self):
        """Test parsing an empty line returns None."""
        line = ""
        entry = self.parser.parse_line(line, row_index=5, file_offset=250)
        
        assert entry is None
    
    def test_parse_whitespace_only_line(self):
        """Test parsing a whitespace-only line returns None."""
        line = "   \t  "
        entry = self.parser.parse_line(line, row_index=6, file_offset=300)
        
        assert entry is None
    
    def test_parse_line_with_only_timestamp(self):
        """Test parsing a line with only timestamp returns None."""
        line = "10-03-2026T15:30:45.123"
        entry = self.parser.parse_line(line, row_index=7, file_offset=350)
        
        assert entry is None
    
    def test_parse_line_with_timestamp_and_category_only(self):
        """Test parsing a line with timestamp and category but no message."""
        line = "10-03-2026T15:30:45.123 HordeMode"
        entry = self.parser.parse_line(line, row_index=8, file_offset=400)
        
        assert entry is not None
        # Ref: docs/specs/features/timestamp-unix-epoch.md §7.1
        expected_dt = datetime(2026, 3, 10, 15, 30, 45, 123000)
        assert isinstance(entry.timestamp, float)
        assert abs(entry.timestamp - expected_dt.timestamp()) < 0.001
        assert entry.category == "HordeMode"
        assert entry.display_message == ""
        assert entry.level == LogLevel.MSG
    
    def test_parse_line_with_trailing_whitespace(self):
        """Test parsing a line with trailing whitespace."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR Test  \n"
        entry = self.parser.parse_line(line, row_index=9, file_offset=450)
        
        assert entry is not None
        assert entry.category == "HordeMode"
        assert entry.level == LogLevel.ERROR
    
    def test_extract_category_simple(self):
        """Test extracting simple category."""
        full_path, components = self.parser.extract_category("HordeMode")
        
        assert full_path == "HordeMode"
        assert components == ["HordeMode"]
    
    def test_extract_category_hierarchical(self):
        """Test extracting hierarchical category."""
        full_path, components = self.parser.extract_category("HordeMode/scripts/app")
        
        assert full_path == "HordeMode/scripts/app"
        assert components == ["HordeMode", "scripts", "app"]
    
    def test_extract_category_empty(self):
        """Test extracting empty category."""
        full_path, components = self.parser.extract_category("")
        
        assert full_path == ""
        assert components == []
    
    def test_level_marker_without_space(self):
        """Test that level marker without trailing space is not matched."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR"
        entry = self.parser.parse_line(line, row_index=10, file_offset=500)
        
        assert entry is not None
        # LOG_ERROR without space should not be detected as level marker
        assert entry.level == LogLevel.MSG
        assert entry.display_message == "LOG_ERROR"
    
    def test_multiple_spaces_in_message(self):
        """Test parsing line with multiple spaces in message."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR Multiple   spaces   here"
        entry = self.parser.parse_line(line, row_index=11, file_offset=550)
        
        assert entry is not None
        assert entry.display_message == "Multiple   spaces   here"
    
    def test_category_is_interned(self):
        """Test that category strings are interned for memory efficiency.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.1
        """
        import sys
        
        # Parse multiple entries with same category
        line1 = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR Test 1"
        line2 = "10-03-2026T15:30:45.124 HordeMode LOG_ERROR Test 2"
        line3 = "10-03-2026T15:30:45.125 OtherCategory LOG_ERROR Test 3"
        
        entry1 = self.parser.parse_line(line1, row_index=0, file_offset=0)
        entry2 = self.parser.parse_line(line2, row_index=1, file_offset=50)
        entry3 = self.parser.parse_line(line3, row_index=2, file_offset=100)
        
        assert entry1 is not None
        assert entry2 is not None
        assert entry3 is not None
        
        # Verify category is interned (same identity for same string)
        assert entry1.category is entry2.category  # Same category should have same identity
        assert entry1.category is not entry3.category  # Different category should have different identity
        
        # Verify it's actually interned using sys.intern
        assert entry1.category is sys.intern("HordeMode")
        assert entry3.category is sys.intern("OtherCategory")
    
    def test_hierarchical_category_is_interned(self):
        """Test that hierarchical category strings are interned.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.1
        """
        import sys
        
        # Parse entries with hierarchical categories
        line1 = "10-03-2026T15:30:45.123 HordeMode/scripts/app LOG_ERROR Test 1"
        line2 = "10-03-2026T15:30:45.124 HordeMode/scripts/app LOG_ERROR Test 2"
        
        entry1 = self.parser.parse_line(line1, row_index=0, file_offset=0)
        entry2 = self.parser.parse_line(line2, row_index=1, file_offset=50)
        
        assert entry1 is not None
        assert entry2 is not None
        
        # Same hierarchical category should have same identity
        assert entry1.category is entry2.category
        assert entry1.category is sys.intern("HordeMode/scripts/app")
    
    # Ref: docs/specs/features/timestamp-unix-epoch.md §7.1
    # New tests for Unix Epoch timestamp format
    
    def test_parse_timestamp_as_epoch(self):
        """Test that timestamp is parsed to Unix Epoch.
        
        Ref: docs/specs/features/timestamp-unix-epoch.md §7.1
        """
        line = "10-03-2026T15:30:45.123 HordeMode LOG_ERROR Test"
        entry = self.parser.parse_line(line, row_index=0, file_offset=0)
        
        # Verify timestamp is a float
        assert isinstance(entry.timestamp, float)
        
        # Verify correct conversion
        expected = datetime(2026, 3, 10, 15, 30, 45, 123000).timestamp()
        assert abs(entry.timestamp - expected) < 0.001
    
    def test_parse_timestamp_format_dd_mm_yyyy(self):
        """Test DD-MM-YYYYTHH:MM:SS.MS format.
        
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.2
        """
        line = "10-03-2026T15:30:45.123 HordeMode LOG_MSG Test"
        entry = self.parser.parse_line(line, row_index=0, file_offset=0)
        
        expected = datetime(2026, 3, 10, 15, 30, 45, 123000).timestamp()
        assert abs(entry.timestamp - expected) < 0.001
    
    def test_parse_timestamp_format_yyyy_mm_dd(self):
        """Test YYYY-MM-DD HH:MM:SS format.
        
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.2
        """
        line = "2024-01-01 12:00:00 HordeMode LOG_MSG Test"
        entry = self.parser.parse_line(line, row_index=0, file_offset=0)
        
        expected = datetime(2024, 1, 1, 12, 0, 0).timestamp()
        assert abs(entry.timestamp - expected) < 0.001
    
    def test_parse_timestamp_format_hh_mm_ss(self):
        """Test HH:MM:SS format (uses current date).
        
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.2
        """
        line = "00:00:00 HordeMode LOG_MSG Test"
        entry = self.parser.parse_line(line, row_index=0, file_offset=0)
        
        # Just verify it's a float and doesn't raise
        assert isinstance(entry.timestamp, float)