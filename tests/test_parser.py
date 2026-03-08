"""Tests for log parser."""
import pytest
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
        assert entry.timestamp == "10-03-2026T15:30:45.123"
        assert entry.category == "HordeMode"
        assert entry.raw_message == "LOG_ERROR Connection failed"
        assert entry.display_message == "Connection failed"
        assert entry.level == LogLevel.ERROR
        assert entry.file_offset == 0
        assert entry.raw_line == line
    
    def test_parse_valid_log_line_with_warning(self):
        """Test parsing a valid log line with WARNING level."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_WARNING Memory low"
        entry = self.parser.parse_line(line, row_index=1, file_offset=50)
        
        assert entry is not None
        assert entry.row_index == 1
        assert entry.timestamp == "10-03-2026T15:30:45.123"
        assert entry.category == "HordeMode"
        assert entry.raw_message == "LOG_WARNING Memory low"
        assert entry.display_message == "Memory low"
        assert entry.level == LogLevel.WARNING
        assert entry.file_offset == 50
    
    def test_parse_valid_log_line_with_info(self):
        """Test parsing a valid log line with MSG level (LOG_MSG)."""
        line = "10-03-2026T15:30:45.123 HordeMode LOG_MSG Starting up"
        entry = self.parser.parse_line(line, row_index=2, file_offset=100)
        
        assert entry is not None
        assert entry.row_index == 2
        assert entry.timestamp == "10-03-2026T15:30:45.123"
        assert entry.category == "HordeMode"
        assert entry.raw_message == "LOG_MSG Starting up"
        assert entry.display_message == "Starting up"
        assert entry.level == LogLevel.MSG
    
    def test_parse_log_line_without_level_marker(self):
        """Test parsing a log line without level marker (defaults to MSG)."""
        line = "10-03-2026T15:30:45.123 HordeMode Some regular message"
        entry = self.parser.parse_line(line, row_index=3, file_offset=150)
        
        assert entry is not None
        assert entry.level == LogLevel.MSG
        assert entry.display_message == "Some regular message"
        assert entry.raw_message == "Some regular message"
    
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
        assert entry.timestamp == "10-03-2026T15:30:45.123"
        assert entry.category == "HordeMode"
        assert entry.raw_message == ""
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