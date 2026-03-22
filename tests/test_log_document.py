"""Unit tests for LogDocument."""
from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from beartype import beartype

from src.models.log_document import LogDocument
from src.models.log_entry import LogEntry, LogLevel


# Ref: docs/specs/features/file-management.md §3.1-§3.4
# Ref: docs/specs/global/memory-model.md §3.2
# Log format: timestamp category message (timestamp is first space-delimited token)
@pytest.fixture
def temp_log_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary log file for testing."""
    log_file = tmp_path / "test.log"
    # Format matches conftest.py: timestamp category [level] message
    log_file.write_text(
        "2024-01-01T10:00:00 Category1 LOG_MSG Message 1\n"
        "2024-01-01T10:00:01 Category2 LOG_ERROR Error message\n"
        "2024-01-01T10:00:02 Category1/SubCat LOG_DEBUG Debug message\n"
        "2024-01-01T10:00:03 Category3 LOG_WARNING Warning message\n"
        "2024-01-01T10:00:04 Category2 LOG_CRITICAL Critical message\n"
    )
    yield log_file


@pytest.fixture
def temp_empty_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create an empty temporary file."""
    empty_file = tmp_path / "empty.log"
    empty_file.write_text("")
    yield empty_file


@pytest.fixture
def temp_unicode_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a file with unicode content and invalid UTF-8 sequences."""
    unicode_file = tmp_path / "unicode.log"
    # Write valid UTF-8 content
    content = (
        "2024-01-01T10:00:00 Category1 LOG_MSG Valid message\n"
        "2024-01-01T10:00:01 Category2 LOG_MSG Another valid\n"
    )
    unicode_file.write_bytes(content.encode('utf-8'))
    yield unicode_file


class TestLogDocumentLoad:
    """Tests for LogDocument.load() method."""
    
    def test_load_basic(self, temp_log_file: Path) -> None:
        """Test basic file loading."""
        # Ref: docs/specs/features/file-management.md §3.3
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        # Verify all entries loaded
        entries = doc.get_all_entries()
        assert len(entries) == 5
        
        # Verify entries are LogEntry objects
        for entry in entries:
            assert isinstance(entry, LogEntry)
    
    def test_load_with_progress_callback(self, temp_log_file: Path) -> None:
        """Test loading with progress callback."""
        # Ref: docs/specs/features/file-management.md §3.2
        progress_calls: list[tuple[int, int]] = []
        
        def progress_callback(bytes_read: int, total_bytes: int) -> None:
            progress_calls.append((bytes_read, total_bytes))
        
        doc = LogDocument(str(temp_log_file))
        doc.load(progress_callback)
        
        # Verify progress was reported
        assert len(progress_calls) > 0
        
        # Verify final progress shows completion
        final_bytes, total_bytes = progress_calls[-1]
        assert final_bytes == total_bytes
    
    def test_load_empty_file(self, temp_empty_file: Path) -> None:
        """Test loading an empty file."""
        doc = LogDocument(str(temp_empty_file))
        doc.load()
        
        entries = doc.get_all_entries()
        assert len(entries) == 0
    
    def test_load_extracts_categories(self, temp_log_file: Path) -> None:
        """Test that categories are extracted during load."""
        # Ref: docs/specs/global/memory-model.md §3.2
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        categories = doc.get_categories()
        
        # Verify all categories extracted
        # Categories are: Category1, Category2, Category1/SubCat, Category3
        assert "Category1" in categories
        assert "Category2" in categories
        assert "Category1/SubCat" in categories
        assert "Category3" in categories
    
    def test_load_preserves_entry_order(self, temp_log_file: Path) -> None:
        """Test that entries are loaded in order."""
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        entries = doc.get_all_entries()
        
        # Verify order preserved
        assert entries[0].row_index == 0
        assert entries[1].row_index == 1
        assert entries[2].row_index == 2
    
    def test_load_parses_entry_fields(self, temp_log_file: Path) -> None:
        """Test that entry fields are correctly parsed."""
        from datetime import datetime
        
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        entries = doc.get_all_entries()
        
        # Check first entry
        first = entries[0]
        # Timestamp is Unix Epoch float (converted from "2024-01-01T10:00:00")
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.2
        expected_dt = datetime(2024, 1, 1, 10, 0, 0)
        assert isinstance(first.timestamp, float)
        assert abs(first.timestamp - expected_dt.timestamp()) < 0.001
        # Category is second token: "Category1"
        assert first.category == "Category1"
        assert first.level == LogLevel.MSG
        assert "Message 1" in first.display_message
        
        # Check second entry (ERROR level)
        second = entries[1]
        assert second.category == "Category2"
        assert second.level == LogLevel.ERROR
    
    def test_file_handle_closed_after_load(self, temp_log_file: Path) -> None:
        """Test that file handle is closed after loading."""
        # Ref: docs/specs/global/memory-model.md §3.2
        # Ref: docs/specs/features/file-management.md §3.4
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        # File should be deletable after load (handle closed)
        # On Windows, this would fail if file was still open
        temp_log_file.unlink()


class TestLogDocumentGetAllEntries:
    """Tests for LogDocument.get_all_entries() method."""
    
    def test_get_all_entries_returns_list(self, temp_log_file: Path) -> None:
        """Test that get_all_entries returns a list."""
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        entries = doc.get_all_entries()
        
        assert isinstance(entries, list)
    
    def test_get_all_entries_returns_correct_count(self, temp_log_file: Path) -> None:
        """Test that all entries are returned."""
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        entries = doc.get_all_entries()
        
        assert len(entries) == 5
    
    def test_get_all_entries_before_load(self, temp_log_file: Path) -> None:
        """Test that get_all_entries returns empty list before load."""
        doc = LogDocument(str(temp_log_file))
        
        # Should return empty list before load
        entries = doc.get_all_entries()
        assert entries == []


class TestLogDocumentGetLineCount:
    """Tests for LogDocument.get_line_count() method."""
    
    def test_get_line_count_after_load(self, temp_log_file: Path) -> None:
        """Test line count after loading."""
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        assert doc.get_line_count() == 5
    
    def test_get_line_count_before_load(self, temp_log_file: Path) -> None:
        """Test line count before loading."""
        doc = LogDocument(str(temp_log_file))
        
        assert doc.get_line_count() == 0
    
    def test_get_line_count_empty_file(self, temp_empty_file: Path) -> None:
        """Test line count for empty file."""
        doc = LogDocument(str(temp_empty_file))
        doc.load()
        
        assert doc.get_line_count() == 0


class TestLogDocumentGetCategories:
    """Tests for LogDocument.get_categories() method."""
    
    def test_get_categories_returns_set(self, temp_log_file: Path) -> None:
        """Test that get_categories returns a set."""
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        categories = doc.get_categories()
        
        assert isinstance(categories, set)
    
    def test_get_categories_returns_copy(self, temp_log_file: Path) -> None:
        """Test that get_categories returns a copy."""
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        categories1 = doc.get_categories()
        categories2 = doc.get_categories()
        
        # Should be different objects
        assert categories1 is not categories2
    
    def test_get_categories_before_load(self, temp_log_file: Path) -> None:
        """Test categories before loading."""
        doc = LogDocument(str(temp_log_file))
        
        categories = doc.get_categories()
        assert categories == set()


class TestLogDocumentUnicodeHandling:
    """Tests for Unicode handling during load."""
    
    def test_unicode_decode_error_skipped(self, tmp_path: Path) -> None:
        """Test that lines with UnicodeDecodeError are skipped."""
        # Create file with invalid UTF-8 sequence
        log_file = tmp_path / "invalid.log"
        # Valid lines + invalid UTF-8 byte sequence
        # Use proper timestamp format: YYYY-MM-DDTHH:MM:SS
        content = b"2024-01-01T10:00:00 Cat1 LOG_MSG Valid\n\xff\xfe Invalid line\n2024-01-01T10:00:01 Cat2 LOG_MSG Also valid\n"
        log_file.write_bytes(content)
        
        doc = LogDocument(str(log_file))
        doc.load()
        
        # Should have loaded 2 valid lines, skipped the invalid one
        entries = doc.get_all_entries()
        assert len(entries) == 2


class TestLogDocumentMemoryModel:
    """Tests for memory model compliance."""
    
    def test_entries_stored_in_memory(self, temp_log_file: Path) -> None:
        """Test that all entries are stored in memory."""
        # Ref: docs/specs/global/memory-model.md §3.2
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        # All entries should be accessible after file is deleted
        entries_before = doc.get_all_entries()
        temp_log_file.unlink()
        entries_after = doc.get_all_entries()
        
        # Same entries should still be available
        assert len(entries_before) == len(entries_after)
        assert entries_before == entries_after
    
    def test_no_file_handle_retained(self, temp_log_file: Path) -> None:
        """Test that no file handle is retained after load."""
        # Ref: docs/specs/features/file-management.md §3.4
        doc = LogDocument(str(temp_log_file))
        doc.load()
        
        # File should be deletable (no open handle)
        temp_log_file.unlink()
        
        # Entries should still be accessible
        entries = doc.get_all_entries()
        assert len(entries) == 5