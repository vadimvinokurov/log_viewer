"""Unit tests for typography module v2.0.

Ref: docs/specs/features/typography-system.md §6
"""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from src.constants.typography import SystemFonts, Typography


class TestSystemFonts:
    """Tests for SystemFonts class.
    
    Ref: docs/specs/features/typography-system.md §3.1
    """
    
    def test_get_ui_font_returns_qfont(self) -> None:
        """get_ui_font should return a QFont instance."""
        font = SystemFonts.get_ui_font()
        assert isinstance(font, QFont)
    
    def test_get_ui_font_is_system_default(self) -> None:
        """UI font should be Qt's default application font."""
        if QApplication.instance():
            app_font = QApplication.font()
            assert SystemFonts.get_ui_font().family() == app_font.family()
    
    def test_get_monospace_font_returns_qfont(self) -> None:
        """get_monospace_font should return a QFont instance."""
        font = SystemFonts.get_monospace_font()
        assert isinstance(font, QFont)
    
    def test_get_monospace_font_is_system_fixed(self) -> None:
        """Monospace font should be Qt's fixed font."""
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        assert SystemFonts.get_monospace_font().family() == fixed_font.family()


class TestTypography:
    """Tests for Typography class v2.0.
    
    Ref: docs/specs/features/typography-system.md §3.2
    """
    
    def test_ui_font_is_system_default(self, qapp: QApplication) -> None:
        """UI_FONT should be Qt's default application font."""
        app_font = QApplication.font()
        assert Typography.UI_FONT.family() == app_font.family()
        assert Typography.UI_FONT.pointSize() == app_font.pointSize()
    
    def test_log_font_is_monospace(self, qapp: QApplication) -> None:
        """LOG_FONT should be a monospace font."""
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        assert Typography.LOG_FONT.family() == fixed_font.family()
    
    def test_primary_font_family(self, qapp: QApplication) -> None:
        """PRIMARY should return font family string for QSS."""
        family = Typography.PRIMARY
        assert isinstance(family, str)
        assert family.startswith('"')
        assert family.endswith('"')
    
    def test_monospace_font_family(self, qapp: QApplication) -> None:
        """MONOSPACE should return monospace family string for QSS."""
        family = Typography.MONOSPACE
        assert isinstance(family, str)
        assert family.startswith('"')
        assert family.endswith('"')
    
    def test_font_size_matches_system(self, qapp: QApplication) -> None:
        """Font size should match system default."""
        app_font = QApplication.font()
        assert Typography.BODY_SIZE == app_font.pointSize()
    
    def test_body_alias(self, qapp: QApplication) -> None:
        """BODY should be an alias for BODY_SIZE."""
        assert Typography.BODY == Typography.BODY_SIZE
    
    def test_log_entry_alias(self, qapp: QApplication) -> None:
        """LOG_ENTRY should be an alias for BODY_SIZE."""
        assert Typography.LOG_ENTRY == Typography.BODY_SIZE
    
    def test_table_row_height_derived(self, qapp: QApplication) -> None:
        """Row height should be derived from font metrics."""
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(Typography.LOG_FONT)
        expected_height = metrics.height() + 12
        assert Typography.TABLE_ROW_HEIGHT == expected_height
    
    def test_table_header_height_fixed(self) -> None:
        """Header height should be fixed at 20."""
        assert Typography.TABLE_HEADER_HEIGHT == 20


class TestDimensionsIntegration:
    """Integration tests for dimensions.py using Typography.
    
    Ref: docs/specs/features/typography-system.md §4.3
    """
    
    def test_dimensions_uses_typography(self, qapp: QApplication) -> None:
        """Dimensions should use Typography constants."""
        from PySide6.QtGui import QFontMetrics
        from src.constants.dimensions import get_table_row_height, TABLE_HEADER_HEIGHT
        
        # get_table_row_height should be computed from QFontMetrics
        metrics = QFontMetrics(Typography.LOG_FONT)
        expected_height = metrics.height() + 12
        assert get_table_row_height() == expected_height
        assert TABLE_HEADER_HEIGHT == Typography.TABLE_HEADER_HEIGHT