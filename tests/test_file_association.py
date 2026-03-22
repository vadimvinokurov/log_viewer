"""Tests for file association functionality.

// Ref: docs/specs/features/file-association.md §6
"""
from __future__ import annotations
from pathlib import Path
import pytest
from src.main import parse_arguments


class TestParseArguments:
    """Tests for parse_arguments function."""
    
    def test_no_arguments(self) -> None:
        """Test with no arguments.
        
        Per docs/specs/features/file-association.md §6.1:
        parse_arguments([]) returns []
        """
        result = parse_arguments([])
        assert result == []
    
    def test_single_valid_file(self, tmp_path: Path) -> None:
        """Test with single valid file.
        
        Per docs/specs/features/file-association.md §6.1:
        parse_arguments(["/valid/file.log"]) returns [Path("/valid/file.log")]
        """
        test_file = tmp_path / "test.log"
        test_file.write_text("test content")
        
        result = parse_arguments([str(test_file)])
        assert len(result) == 1
        assert result[0] == test_file
    
    def test_multiple_valid_files(self, tmp_path: Path) -> None:
        """Test with multiple valid files.
        
        Per docs/specs/features/file-association.md §6.1:
        Multiple files should all be returned.
        """
        files = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.log"
            test_file.write_text(f"content {i}")
            files.append(str(test_file))
        
        result = parse_arguments(files)
        assert len(result) == 3
    
    def test_nonexistent_file(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test with nonexistent file.
        
        Per docs/specs/features/file-association.md §6.1:
        parse_arguments(["/nonexistent.log"]) returns [] and logs warning.
        """
        result = parse_arguments(["/nonexistent/file.log"])
        assert result == []
        assert "File not found" in caplog.text
    
    def test_directory_argument(self, tmp_path: Path) -> None:
        """Test with directory instead of file.
        
        Per docs/specs/features/file-association.md §6.1:
        Directories should be skipped (only files accepted).
        """
        result = parse_arguments([str(tmp_path)])
        assert result == []
    
    def test_mixed_valid_invalid(self, tmp_path: Path) -> None:
        """Test with mix of valid and invalid paths.
        
        Per docs/specs/features/file-association.md §6.1:
        Returns only valid paths.
        """
        valid_file = tmp_path / "valid.log"
        valid_file.write_text("content")
        
        result = parse_arguments([str(valid_file), "/nonexistent.log"])
        assert len(result) == 1
        assert result[0] == valid_file
    
    def test_skip_flags(self, tmp_path: Path) -> None:
        """Test that flags are skipped.
        
        Per docs/specs/features/file-association.md §4.1:
        Arguments starting with '-' are skipped (flags).
        """
        test_file = tmp_path / "test.log"
        test_file.write_text("content")
        
        result = parse_arguments(["--flag", str(test_file), "-v"])
        assert len(result) == 1
        assert result[0] == test_file
    
    def test_path_with_spaces(self, tmp_path: Path) -> None:
        """Test with path containing spaces.
        
        Per docs/specs/features/file-association.md §4.1:
        Paths with spaces should be handled correctly.
        """
        # Create directory with space
        space_dir = tmp_path / "My Documents"
        space_dir.mkdir()
        test_file = space_dir / "test file.log"
        test_file.write_text("content")
        
        result = parse_arguments([str(test_file)])
        assert len(result) == 1
        assert result[0] == test_file
    
    def test_path_with_special_characters(self, tmp_path: Path) -> None:
        """Test with path containing special characters.
        
        Per docs/specs/features/file-association.md §4.1:
        Paths with special characters (parentheses, etc.) should be handled.
        """
        # Create file with special characters
        test_file = tmp_path / "test (1).log"
        test_file.write_text("content")
        
        result = parse_arguments([str(test_file)])
        assert len(result) == 1
        assert result[0] == test_file
    
    def test_path_with_unicode(self, tmp_path: Path) -> None:
        """Test with path containing unicode characters.
        
        Per docs/specs/features/file-association.md §4.1:
        Paths with unicode characters should be handled.
        """
        # Create file with unicode characters
        test_file = tmp_path / "тест_日志.log"
        test_file.write_text("content")
        
        result = parse_arguments([str(test_file)])
        assert len(result) == 1
        assert result[0] == test_file