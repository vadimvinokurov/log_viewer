"""Unit tests for stylesheet functions.

Tests platform-specific font size and font family functions.
Ref: docs/specs/features/ui-design-system.md §2.2.2
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from src.styles.stylesheet import get_log_font_size, get_font_family, get_monospace_font_family


class TestGetLogFontSize:
    """Tests for get_log_font_size function.
    
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    macOS should return 11pt, Windows/Linux should return 9pt.
    """
    
    def test_macos_returns_11pt(self) -> None:
        """Test that macOS (darwin) returns 11pt font size."""
        with patch.object(sys, 'platform', 'darwin'):
            # Re-import to get the patched value
            from src.styles.stylesheet import get_log_font_size
            assert get_log_font_size() == 11
    
    def test_windows_returns_9pt(self) -> None:
        """Test that Windows (win32) returns 9pt font size."""
        with patch.object(sys, 'platform', 'win32'):
            from src.styles.stylesheet import get_log_font_size
            assert get_log_font_size() == 9
    
    def test_linux_returns_9pt(self) -> None:
        """Test that Linux returns 9pt font size."""
        with patch.object(sys, 'platform', 'linux'):
            from src.styles.stylesheet import get_log_font_size
            assert get_log_font_size() == 9
    
    def test_unknown_platform_returns_9pt(self) -> None:
        """Test that unknown platforms default to 9pt font size."""
        with patch.object(sys, 'platform', 'unknown'):
            from src.styles.stylesheet import get_log_font_size
            assert get_log_font_size() == 9


class TestGetFontFamily:
    """Tests for get_font_family function."""
    
    def test_macos_font_family(self) -> None:
        """Test that macOS returns SF Pro Text font family."""
        with patch.object(sys, 'platform', 'darwin'):
            from src.styles.stylesheet import get_font_family
            result = get_font_family()
            assert 'SF Pro Text' in result
            assert 'Helvetica Neue' in result
    
    def test_windows_font_family(self) -> None:
        """Test that Windows returns Segoe UI font family."""
        with patch.object(sys, 'platform', 'win32'):
            from src.styles.stylesheet import get_font_family
            result = get_font_family()
            assert 'Segoe UI' in result
            assert 'Roboto' in result


class TestGetMonospaceFontFamily:
    """Tests for get_monospace_font_family function."""
    
    def test_macos_monospace_font(self) -> None:
        """Test that macOS returns Menlo/Monaco font family."""
        with patch.object(sys, 'platform', 'darwin'):
            from src.styles.stylesheet import get_monospace_font_family
            result = get_monospace_font_family()
            assert 'Menlo' in result
            assert 'Monaco' in result
    
    def test_windows_monospace_font(self) -> None:
        """Test that Windows returns Consolas font family."""
        with patch.object(sys, 'platform', 'win32'):
            from src.styles.stylesheet import get_monospace_font_family
            result = get_monospace_font_family()
            assert 'Consolas' in result


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