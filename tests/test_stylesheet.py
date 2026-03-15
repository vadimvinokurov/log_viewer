"""Unit tests for stylesheet functions.

Tests stylesheet generation with system fonts.
Ref: docs/specs/features/typography-system.md §4.1
Ref: docs/specs/features/ui-design-system.md §2.2.2
"""
from __future__ import annotations

import pytest

from src.constants.typography import Typography
from src.styles.stylesheet import (
    get_application_stylesheet,
    get_table_stylesheet,
)


class TestGetApplicationStylesheet:
    """Tests for get_application_stylesheet function.
    
    Ref: docs/specs/features/typography-system.md §4.1
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    """
    
    def test_stylesheet_uses_system_font_family(self) -> None:
        """Test that stylesheet uses system font family.
        
        Ref: docs/specs/features/typography-system.md §6.2
        """
        stylesheet = get_application_stylesheet()
        # Should contain font family from Typography.PRIMARY
        assert Typography.PRIMARY in stylesheet
    
    def test_stylesheet_no_hardcoded_font_size(self) -> None:
        """Test that stylesheet does not hardcode font-size.
        
        Ref: docs/specs/features/typography-system.md §4.1
        Qt uses the system default font size automatically.
        """
        stylesheet = get_application_stylesheet()
        # Font size should NOT be hardcoded
        assert "font-size:" not in stylesheet
    
    def test_stylesheet_basic_structure(self) -> None:
        """Test that stylesheet contains expected selectors."""
        stylesheet = get_application_stylesheet()
        assert 'QWidget' in stylesheet
        assert 'QMainWindow' in stylesheet
        assert 'QMenuBar' in stylesheet
        assert 'QToolTip' in stylesheet


class TestGetTableStylesheet:
    """Tests for get_table_stylesheet function.
    
    Ref: docs/specs/features/typography-system.md §4.1
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    Note: Message column font is set via Qt.FontRole in LogTableModel.data(),
    not via QSS. QSS pseudo-classes like :message-column are invalid in Qt.
    """
    
    def test_table_stylesheet_basic_structure(self) -> None:
        """Test that table stylesheet contains expected selectors."""
        stylesheet = get_table_stylesheet()
        assert 'QTableWidget' in stylesheet
        assert 'QHeaderView::section' in stylesheet
    
    def test_table_stylesheet_no_font_size(self) -> None:
        """Test that table stylesheet does not contain font-size.
        
        Ref: docs/specs/features/typography-system.md §4.1
        Font is set via Qt.FontRole in LogTableModel.data(), not via QSS.
        """
        stylesheet = get_table_stylesheet()
        assert "font-size:" not in stylesheet
    
    def test_table_stylesheet_no_invalid_pseudo_class(self) -> None:
        """Test that stylesheet does not contain invalid :message-column pseudo-class.
        
        Ref: docs/specs/features/ui-design-system.md §2.2.2
        Qt doesn't support custom pseudo-classes in QSS.
        """
        stylesheet = get_table_stylesheet()
        assert ':message-column' not in stylesheet