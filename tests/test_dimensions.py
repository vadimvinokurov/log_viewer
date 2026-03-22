"""Unit tests for dimensions module constants.

Ref: docs/specs/features/table-column-auto-size.md §5.1
"""
from __future__ import annotations

import pytest

from src.constants.dimensions import (
    TIME_COLUMN_MIN_WIDTH,
    TIME_COLUMN_PADDING,
    TYPE_COLUMN_MIN_WIDTH,
    TYPE_COLUMN_PADDING,
    CATEGORY_COLUMN_MIN_WIDTH,
    CATEGORY_COLUMN_MAX_WIDTH,
    CATEGORY_COLUMN_PADDING,
    CATEGORY_COLUMN_SAMPLE_SIZE,
    MESSAGE_COLUMN_MIN_WIDTH,
)


class TestColumnWidthConstraints:
    """Tests for column width constraint constants.
    
    Ref: docs/specs/features/table-column-auto-size.md §5.1
    """
    
    def test_time_column_min_width(self) -> None:
        """TIME_COLUMN_MIN_WIDTH should be 60 pixels."""
        assert TIME_COLUMN_MIN_WIDTH == 60
        assert isinstance(TIME_COLUMN_MIN_WIDTH, int)
    
    def test_time_column_padding(self) -> None:
        """TIME_COLUMN_PADDING should be 8 pixels (4px left + 4px right)."""
        assert TIME_COLUMN_PADDING == 8
        assert isinstance(TIME_COLUMN_PADDING, int)
    
    def test_type_column_min_width(self) -> None:
        """TYPE_COLUMN_MIN_WIDTH should be 30 pixels."""
        assert TYPE_COLUMN_MIN_WIDTH == 30
        assert isinstance(TYPE_COLUMN_MIN_WIDTH, int)
    
    def test_type_column_padding(self) -> None:
        """TYPE_COLUMN_PADDING should be 16 pixels (8px left + 8px right for centered icon)."""
        assert TYPE_COLUMN_PADDING == 16
        assert isinstance(TYPE_COLUMN_PADDING, int)
    
    def test_category_column_min_width(self) -> None:
        """CATEGORY_COLUMN_MIN_WIDTH should be 50 pixels."""
        assert CATEGORY_COLUMN_MIN_WIDTH == 50
        assert isinstance(CATEGORY_COLUMN_MIN_WIDTH, int)
    
    def test_category_column_max_width(self) -> None:
        """CATEGORY_COLUMN_MAX_WIDTH should be 300 pixels."""
        assert CATEGORY_COLUMN_MAX_WIDTH == 300
        assert isinstance(CATEGORY_COLUMN_MAX_WIDTH, int)
    
    def test_category_column_padding(self) -> None:
        """CATEGORY_COLUMN_PADDING should be 8 pixels (4px left + 4px right)."""
        assert CATEGORY_COLUMN_PADDING == 8
        assert isinstance(CATEGORY_COLUMN_PADDING, int)
    
    def test_category_column_sample_size(self) -> None:
        """CATEGORY_COLUMN_SAMPLE_SIZE should be 100 entries."""
        assert CATEGORY_COLUMN_SAMPLE_SIZE == 100
        assert isinstance(CATEGORY_COLUMN_SAMPLE_SIZE, int)
    
    def test_message_column_min_width(self) -> None:
        """MESSAGE_COLUMN_MIN_WIDTH should be 100 pixels."""
        assert MESSAGE_COLUMN_MIN_WIDTH == 100
        assert isinstance(MESSAGE_COLUMN_MIN_WIDTH, int)
    
    def test_category_min_less_than_max(self) -> None:
        """CATEGORY_COLUMN_MIN_WIDTH should be less than CATEGORY_COLUMN_MAX_WIDTH."""
        assert CATEGORY_COLUMN_MIN_WIDTH < CATEGORY_COLUMN_MAX_WIDTH
    
    def test_all_widths_positive(self) -> None:
        """All width constants should be positive values."""
        assert TIME_COLUMN_MIN_WIDTH > 0
        assert TYPE_COLUMN_MIN_WIDTH > 0
        assert CATEGORY_COLUMN_MIN_WIDTH > 0
        assert CATEGORY_COLUMN_MAX_WIDTH > 0
        assert MESSAGE_COLUMN_MIN_WIDTH > 0
    
    def test_all_padding_positive(self) -> None:
        """All padding constants should be positive values."""
        assert TIME_COLUMN_PADDING > 0
        assert TYPE_COLUMN_PADDING > 0
        assert CATEGORY_COLUMN_PADDING > 0
    
    def test_sample_size_positive(self) -> None:
        """CATEGORY_COLUMN_SAMPLE_SIZE should be positive."""
        assert CATEGORY_COLUMN_SAMPLE_SIZE > 0