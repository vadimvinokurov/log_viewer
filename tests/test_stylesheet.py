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
    get_tree_stylesheet,
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
    
    def test_table_stylesheet_no_hardcoded_font_size(self) -> None:
        """Test that table stylesheet does not contain hardcoded font-size.
        
        Ref: docs/specs/features/typography-system.md §4.1
        Ref: docs/specs/features/table-unified-styles.md §8.1
        Font is set via Qt.FontRole in LogTableModel.data(), not via QSS.
        Note: font-size: inherit is allowed for header to inherit from parent.
        """
        stylesheet = get_table_stylesheet()
        # font-size: inherit is allowed (inherits from parent)
        # but hardcoded sizes like "font-size: 12px" are not
        assert "font-size: 8px" not in stylesheet
        assert "font-size: 9px" not in stylesheet
        assert "font-size: 10px" not in stylesheet
        assert "font-size: 11px" not in stylesheet
        assert "font-size: 12px" not in stylesheet
        assert "font-size: 13px" not in stylesheet
        assert "font-size: 14px" not in stylesheet
        # Verify inherit is used for header
        assert "font-size: inherit" in stylesheet
    
    def test_table_stylesheet_no_invalid_pseudo_class(self) -> None:
        """Test that stylesheet does not contain invalid :message-column pseudo-class.
        
        Ref: docs/specs/features/ui-design-system.md §2.2.2
        Qt doesn't support custom pseudo-classes in QSS.
        """
        stylesheet = get_table_stylesheet()
        assert ':message-column' not in stylesheet
    
    def test_table_header_font_weight_normal(self) -> None:
        """Test that table header has explicit font-weight: normal.
        
        Ref: docs/specs/features/typography-system.md §4.1
        Header font should match table rows (normal weight, not bold).
        """
        stylesheet = get_table_stylesheet()
        assert 'font-weight: normal' in stylesheet
    
    def test_table_uses_row_background_constant(self) -> None:
        """Test that table uses PaletteColors.GRAY_2 constant.
        
        Ref: docs/specs/features/table-unified-styles.md §8.2
        QTableWidget and QTableWidget::item should use PaletteColors.GRAY_2.
        """
        from src.constants.colors import PaletteColors
        
        stylesheet = get_table_stylesheet()
        # PaletteColors.GRAY_2 should appear in the stylesheet
        assert PaletteColors.GRAY_2 in stylesheet
    
    def test_table_item_has_background_color(self) -> None:
        """Test that QTableWidget::item has explicit background-color.
        
        Ref: docs/specs/features/table-unified-styles.md §8.2
        Items should have explicit background-color for consistent styling.
        """
        stylesheet = get_table_stylesheet()
        # Check for QTableWidget::item with background-color
        assert 'QTableWidget::item' in stylesheet
        # Background color should be set for items
        assert 'background-color:' in stylesheet
    
    def test_table_item_hover_same_as_default(self) -> None:
        """Test that QTableWidget::item:hover has same background as default.
        
        Ref: docs/specs/features/table-unified-styles.md §8.2
        Hover state should not change visual appearance (no visual change).
        """
        from src.constants.colors import PaletteColors
        
        stylesheet = get_table_stylesheet()
        # Should have :hover pseudo-class for items
        assert 'QTableWidget::item:hover' in stylesheet
        # Hover should use same background as default
        assert PaletteColors.GRAY_2 in stylesheet
    
    def test_table_item_selected_hover_persists(self) -> None:
        """Test that QTableWidget::item:selected:hover maintains selection color.
        
        Ref: docs/specs/features/table-unified-styles.md §8.2
        Selected+hover should maintain selection background color.
        """
        from src.constants.colors import UIColors
        
        stylesheet = get_table_stylesheet()
        # Should have :selected:hover pseudo-class
        assert 'QTableWidget::item:selected:hover' in stylesheet
        # Selection highlight color should be present
        assert UIColors.BACKGROUND_SELECTED in stylesheet
    
    def test_table_header_no_hover_effect(self) -> None:
        """Test that QHeaderView::section does NOT have :hover pseudo-class.
        
        Ref: docs/specs/features/table-unified-styles.md §8.1
        The header does NOT react to mouse hover.
        """
        stylesheet = get_table_stylesheet()
        # Should NOT have :hover on header sections
        assert 'QHeaderView::section:hover' not in stylesheet
    
    def test_table_header_last_section_no_right_border(self) -> None:
        """Test that last header section has no right border.
        
        Ref: docs/specs/features/table-unified-styles.md §8.1
        Last column should have no right border.
        """
        stylesheet = get_table_stylesheet()
        # Should have :last pseudo-class for header
        assert 'QHeaderView::section:last' in stylesheet
        assert 'border-right: none' in stylesheet


class TestGetTreeStylesheet:
    """Tests for get_tree_stylesheet function.
    
    Ref: docs/specs/features/category-panel-styles.md §5.3, §6.3
    Ref: docs/specs/features/category-tree-row-unification.md §6.2
    """
    
    def test_tree_stylesheet_basic_structure(self) -> None:
        """Test that tree stylesheet contains expected selectors."""
        stylesheet = get_tree_stylesheet()
        assert 'QTreeView' in stylesheet
        assert 'QTreeView::item' in stylesheet
    
    def test_tree_item_has_zero_padding(self) -> None:
        """Test that QTreeView::item has zero padding.
        
        Ref: docs/specs/features/category-tree-row-unification.md §6.2
        Tree rows should have zero padding to match table row height.
        """
        stylesheet = get_tree_stylesheet()
        assert 'padding: 0' in stylesheet
    
    def test_no_indicator_styles(self) -> None:
        """Test that QTreeView::indicator styles are NOT present.
        
        Ref: docs/specs/features/category-tree-row-unification.md §6.2
        Checkboxes are rendered as Unicode characters by CategoryItemDelegate,
        not via QSS. Therefore, no QTreeView::indicator styles should exist.
        """
        stylesheet = get_tree_stylesheet()
        assert 'QTreeView::indicator' not in stylesheet
        assert 'QTreeView::indicator:unchecked' not in stylesheet
        assert 'QTreeView::indicator:checked' not in stylesheet
    
    def test_no_margin_left(self) -> None:
        """Test that stylesheet does NOT have margin-left.
        
        Ref: docs/specs/features/category-panel-styles.md §5.3
        Note: The gap between branch indicator and checkbox is handled by
        CategoryItemDelegate, not by QSS margin-left.
        """
        stylesheet = get_tree_stylesheet()
        # margin-left should NOT be in stylesheet - gap is handled by delegate
        assert 'margin-left' not in stylesheet