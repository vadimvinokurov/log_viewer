"""Unit tests for stylesheet functions.

Tests deprecated font functions and stylesheet generation.
Ref: docs/specs/features/typography-system.md §4.1
Ref: docs/specs/features/ui-design-system.md §2.2.2
"""
from __future__ import annotations

import warnings

import pytest

from src.constants.typography import Typography
from src.styles.stylesheet import (
    get_log_font_size,
    get_font_family,
    get_monospace_font_family,
    get_application_stylesheet,
    get_table_stylesheet,
)


class TestDeprecatedFunctions:
    """Tests for deprecated font functions.
    
    These functions delegate to Typography constants and emit DeprecationWarning.
    Platform-specific behavior is tested in test_typography.py.
    """
    
    def test_get_log_font_size_returns_typography_body(self) -> None:
        """Test that get_log_font_size() returns Typography.BODY value."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = get_log_font_size()
            
            # Should return Typography.BODY value
            assert result == Typography.BODY
            
            # Should emit DeprecationWarning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "get_log_font_size() is deprecated" in str(w[0].message)
    
    def test_get_font_family_returns_typography_primary(self) -> None:
        """Test that get_font_family() returns Typography.PRIMARY value."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = get_font_family()
            
            # Should return Typography.PRIMARY value
            assert result == Typography.PRIMARY
            
            # Should emit DeprecationWarning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "get_font_family() is deprecated" in str(w[0].message)
    
    def test_get_monospace_font_family_returns_typography_monospace(self) -> None:
        """Test that get_monospace_font_family() returns Typography.MONOSPACE value."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = get_monospace_font_family()
            
            # Should return Typography.MONOSPACE value
            assert result == Typography.MONOSPACE
            
            # Should emit DeprecationWarning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "get_monospace_font_family() is deprecated" in str(w[0].message)


class TestGetTableStylesheet:
    """Tests for get_table_stylesheet function.
    
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    Note: Message column font is set via Qt.FontRole in LogTableModel.data(),
    not via QSS. QSS pseudo-classes like :message-column are invalid in Qt.
    """
    
    def test_table_stylesheet_basic_structure(self) -> None:
        """Test that table stylesheet contains expected selectors."""
        from src.styles.stylesheet import get_table_stylesheet
        stylesheet = get_table_stylesheet()
        assert 'QTableWidget' in stylesheet
        assert 'QHeaderView::section' in stylesheet
    
    def test_table_stylesheet_no_invalid_pseudo_class(self) -> None:
        """Test that stylesheet does not contain invalid :message-column pseudo-class.
        
        Ref: docs/specs/features/ui-design-system.md §2.2.2
        Qt doesn't support custom pseudo-classes in QSS.
        """
        from src.styles.stylesheet import get_table_stylesheet
        stylesheet = get_table_stylesheet()
        assert ':message-column' not in stylesheet