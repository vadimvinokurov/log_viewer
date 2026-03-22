"""Tests for highlight engine."""
from __future__ import annotations

import pytest
from PySide6.QtGui import QColor

from src.core.highlight_engine import HighlightEngine, HighlightPattern, HighlightRange


class TestHighlightPattern:
    """Tests for HighlightPattern class."""
    
    def test_pattern_creation(self) -> None:
        """Test creating a highlight pattern."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text="error", color=color)
        
        assert pattern.text == "error"
        assert pattern.color == color
        assert pattern.is_regex is False
        assert pattern.enabled is True
    
    def test_regex_pattern(self) -> None:
        """Test creating a regex pattern."""
        color = QColor(0, 255, 0)
        pattern = HighlightPattern(text=r"\d+", color=color, is_regex=True)
        
        assert pattern.text == r"\d+"
        assert pattern.is_regex is True
    
    def test_disabled_pattern(self) -> None:
        """Test creating a disabled pattern."""
        color = QColor(0, 0, 255)
        pattern = HighlightPattern(text="warning", color=color, enabled=False)
        
        assert pattern.enabled is False
    
    def test_empty_pattern_raises(self) -> None:
        """Test that empty pattern text raises ValueError."""
        with pytest.raises(ValueError, match="Pattern text cannot be empty"):
            HighlightPattern(text="", color=QColor(255, 255, 255))


class TestHighlightRange:
    """Tests for HighlightRange class."""
    
    def test_range_creation(self) -> None:
        """Test creating a highlight range."""
        color = QColor(255, 0, 0)
        range_ = HighlightRange(start=0, end=5, color=color)
        
        assert range_.start == 0
        assert range_.end == 5
        assert range_.color == color
    
    def test_range_comparison(self) -> None:
        """Test comparing highlight ranges by start position."""
        color = QColor(255, 0, 0)
        range1 = HighlightRange(start=0, end=5, color=color)
        range2 = HighlightRange(start=10, end=15, color=color)
        
        assert range1 < range2
        assert range2 > range1
    
    def test_range_sorting(self) -> None:
        """Test sorting highlight ranges."""
        color = QColor(255, 0, 0)
        ranges = [
            HighlightRange(start=20, end=25, color=color),
            HighlightRange(start=0, end=5, color=color),
            HighlightRange(start=10, end=15, color=color),
        ]
        
        sorted_ranges = sorted(ranges)
        
        assert sorted_ranges[0].start == 0
        assert sorted_ranges[1].start == 10
        assert sorted_ranges[2].start == 20


class TestHighlightEngine:
    """Tests for HighlightEngine class."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = HighlightEngine()
    
    def test_add_pattern(self) -> None:
        """Test adding highlight pattern."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text="error", color=color)
        
        self.engine.add_pattern(pattern)
        
        patterns = self.engine.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].text == "error"
    
    def test_remove_pattern(self) -> None:
        """Test removing highlight pattern."""
        color = QColor(255, 0, 0)
        pattern1 = HighlightPattern(text="error", color=color)
        pattern2 = HighlightPattern(text="warning", color=color)
        
        self.engine.add_pattern(pattern1)
        self.engine.add_pattern(pattern2)
        
        self.engine.remove_pattern(0)
        
        patterns = self.engine.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].text == "warning"
    
    def test_remove_pattern_invalid_index(self) -> None:
        """Test removing pattern with invalid index."""
        # The engine raises IndexError for invalid indices
        with pytest.raises(IndexError):
            self.engine.remove_pattern(-1)
    
    def test_remove_pattern_out_of_range(self) -> None:
        """Test removing pattern with index out of range."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text="error", color=color)
        self.engine.add_pattern(pattern)
        
        with pytest.raises(IndexError):
            self.engine.remove_pattern(10)
    
    def test_clear_patterns(self) -> None:
        """Test clearing all patterns."""
        color = QColor(255, 0, 0)
        self.engine.add_pattern(HighlightPattern(text="error", color=color))
        self.engine.add_pattern(HighlightPattern(text="warning", color=color))
        
        self.engine.clear_patterns()
        
        assert len(self.engine.get_patterns()) == 0
    
    def test_set_patterns(self) -> None:
        """Test setting patterns."""
        color1 = QColor(255, 0, 0)
        color2 = QColor(0, 255, 0)
        patterns = [
            HighlightPattern(text="error", color=color1),
            HighlightPattern(text="warning", color=color2),
        ]
        
        self.engine.set_patterns(patterns)
        
        result = self.engine.get_patterns()
        assert len(result) == 2
        assert result[0].text == "error"
        assert result[1].text == "warning"
    
    def test_plain_text_highlight(self) -> None:
        """Test plain text highlighting."""
        color = QColor(255, 255, 0)
        pattern = HighlightPattern(text="error", color=color)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("An error occurred")
        
        assert len(ranges) == 1
        assert ranges[0].start == 3
        assert ranges[0].end == 8
        assert ranges[0].color == color
    
    def test_plain_text_highlight_case_insensitive(self) -> None:
        """Test plain text highlighting is case-insensitive."""
        color = QColor(255, 255, 0)
        pattern = HighlightPattern(text="ERROR", color=color)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("An error occurred")
        
        assert len(ranges) == 1
        assert ranges[0].start == 3
    
    def test_plain_text_multiple_matches(self) -> None:
        """Test plain text with multiple matches."""
        color = QColor(255, 255, 0)
        pattern = HighlightPattern(text="a", color=color)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("banana")
        
        # Should find all 'a' occurrences
        assert len(ranges) == 3
        positions = [(r.start, r.end) for r in ranges]
        assert (1, 2) in positions
        assert (3, 4) in positions
        assert (5, 6) in positions
    
    def test_regex_highlight(self) -> None:
        """Test regex highlighting."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text=r"\d+", color=color, is_regex=True)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("Error 404: Not found")
        
        assert len(ranges) == 1
        assert ranges[0].start == 6
        assert ranges[0].end == 9
    
    def test_regex_highlight_multiple_matches(self) -> None:
        """Test regex with multiple matches."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text=r"\d+", color=color, is_regex=True)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("Values: 10, 20, 30")
        
        assert len(ranges) == 3
        # Positions: 8-10, 12-14, 16-18
        starts = [r.start for r in ranges]
        assert 8 in starts
        assert 12 in starts
        assert 16 in starts
    
    def test_regex_highlight_case_insensitive(self) -> None:
        """Test regex highlighting is case-insensitive."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text=r"ERROR", color=color, is_regex=True)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("An error occurred")
        
        assert len(ranges) == 1
    
    def test_multiple_patterns(self) -> None:
        """Test multiple highlight patterns."""
        color1 = QColor(255, 0, 0)
        color2 = QColor(0, 255, 0)
        
        self.engine.add_pattern(HighlightPattern(text="error", color=color1))
        self.engine.add_pattern(HighlightPattern(text="warning", color=color2))
        
        ranges = self.engine.highlight("error and warning")
        
        assert len(ranges) == 2
        # error at 0-5, warning at 10-17
        error_range = next((r for r in ranges if r.color == color1), None)
        warning_range = next((r for r in ranges if r.color == color2), None)
        
        assert error_range is not None
        assert error_range.start == 0
        assert error_range.end == 5
        
        assert warning_range is not None
        assert warning_range.start == 10
        assert warning_range.end == 17
    
    def test_disabled_pattern_not_highlighted(self) -> None:
        """Test that disabled patterns are not highlighted."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text="error", color=color, enabled=False)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("An error occurred")
        
        assert len(ranges) == 0
    
    def test_empty_text(self) -> None:
        """Test highlighting empty text."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text="error", color=color)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("")
        
        assert len(ranges) == 0
    
    def test_no_match(self) -> None:
        """Test highlighting with no match."""
        color = QColor(255, 0, 0)
        pattern = HighlightPattern(text="error", color=color)
        self.engine.add_pattern(pattern)
        
        ranges = self.engine.highlight("All is fine")
        
        assert len(ranges) == 0
    
    def test_overlapping_ranges_same_color(self) -> None:
        """Test overlapping ranges with same color."""
        color = QColor(255, 0, 0)
        self.engine.add_pattern(HighlightPattern(text="abc", color=color))
        self.engine.add_pattern(HighlightPattern(text="bcd", color=color))
        
        ranges = self.engine.highlight("abcd")
        
        # Both patterns match, should have overlapping ranges
        # The merge logic should handle this
        assert len(ranges) >= 1
    
    def test_overlapping_ranges_different_colors(self) -> None:
        """Test overlapping ranges with different colors."""
        color1 = QColor(255, 0, 0)
        color2 = QColor(0, 255, 0)
        
        self.engine.add_pattern(HighlightPattern(text="abc", color=color1))
        self.engine.add_pattern(HighlightPattern(text="bcd", color=color2))
        
        ranges = self.engine.highlight("abcd")
        
        # Later pattern should take precedence for overlapping parts
        assert len(ranges) >= 1
    
    def test_invalid_regex_pattern(self) -> None:
        """Test that invalid regex patterns are skipped."""
        color = QColor(255, 0, 0)
        # Invalid regex - unmatched bracket
        pattern = HighlightPattern(text=r"[invalid", color=color, is_regex=True)
        self.engine.add_pattern(pattern)
        
        # Should not raise, just skip the invalid pattern
        ranges = self.engine.highlight("test [invalid text")
        
        assert len(ranges) == 0
    
    def test_pattern_order_preserved(self) -> None:
        """Test that pattern order is preserved."""
        color1 = QColor(255, 0, 0)
        color2 = QColor(0, 255, 0)
        color3 = QColor(0, 0, 255)
        
        self.engine.add_pattern(HighlightPattern(text="first", color=color1))
        self.engine.add_pattern(HighlightPattern(text="second", color=color2))
        self.engine.add_pattern(HighlightPattern(text="third", color=color3))
        
        patterns = self.engine.get_patterns()
        
        assert patterns[0].text == "first"
        assert patterns[1].text == "second"
        assert patterns[2].text == "third"


class TestHighlightRangeMerging:
    """Tests for highlight range merging logic."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = HighlightEngine()
    
    def test_non_overlapping_ranges(self) -> None:
        """Test merging non-overlapping ranges."""
        color = QColor(255, 0, 0)
        self.engine.add_pattern(HighlightPattern(text="a", color=color))
        
        ranges = self.engine.highlight("a b a")
        
        # Two 'a' characters, non-overlapping
        assert len(ranges) == 2
    
    def test_adjacent_ranges(self) -> None:
        """Test adjacent ranges."""
        color = QColor(255, 0, 0)
        self.engine.add_pattern(HighlightPattern(text="ab", color=color))
        self.engine.add_pattern(HighlightPattern(text="bc", color=color))
        
        ranges = self.engine.highlight("abc")
        
        # 'ab' at 0-2, 'bc' at 1-3 - overlapping
        assert len(ranges) >= 1
    
    def test_nested_ranges(self) -> None:
        """Test nested ranges (one range inside another)."""
        color1 = QColor(255, 0, 0)
        color2 = QColor(0, 255, 0)
        
        # Longer pattern first
        self.engine.add_pattern(HighlightPattern(text="abcde", color=color1))
        self.engine.add_pattern(HighlightPattern(text="cd", color=color2))
        
        ranges = self.engine.highlight("abcde")
        
        # Both patterns match, later one takes precedence for overlap
        assert len(ranges) >= 1
    
    def test_complete_overlap(self) -> None:
        """Test complete overlap (same range)."""
        color1 = QColor(255, 0, 0)
        color2 = QColor(0, 255, 0)
        
        self.engine.add_pattern(HighlightPattern(text="test", color=color1))
        self.engine.add_pattern(HighlightPattern(text="test", color=color2))
        
        ranges = self.engine.highlight("test")
        
        # Both match same range, later one should win
        assert len(ranges) == 1
        assert ranges[0].color == color2


class TestHighlightEnginePerformance:
    """Performance tests for HighlightEngine."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = HighlightEngine()
    
    def test_large_text_highlighting(self) -> None:
        """Test highlighting large text."""
        color = QColor(255, 0, 0)
        self.engine.add_pattern(HighlightPattern(text="error", color=color))
        
        # Create large text with multiple occurrences
        text = "This is an error message. " * 1000
        
        ranges = self.engine.highlight(text)
        
        # Should find 1000 occurrences
        assert len(ranges) == 1000
    
    def test_many_patterns(self) -> None:
        """Test highlighting with many patterns."""
        color = QColor(255, 0, 0)
        
        # Add many patterns
        for i in range(50):
            self.engine.add_pattern(HighlightPattern(text=f"word{i}", color=color))
        
        text = "word0 word1 word2 word3 word4"
        ranges = self.engine.highlight(text)
        
        # Should find matches
        assert len(ranges) >= 5
    
    def test_complex_regex(self) -> None:
        """Test complex regex pattern."""
        color = QColor(255, 0, 0)
        # Match email-like patterns
        pattern = HighlightPattern(
            text=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            color=color,
            is_regex=True
        )
        self.engine.add_pattern(pattern)
        
        text = "Contact us at test@example.com or support@example.org"
        ranges = self.engine.highlight(text)
        
        assert len(ranges) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])