"""Unit tests for typography module.

Ref: docs/specs/features/typography-system.md §6
"""
from __future__ import annotations

import sys
import pytest
from src.constants.typography import Platform, FontFamily, TypeScale, Typography
from src.constants.dimensions import TABLE_ROW_HEIGHT, TABLE_HEADER_HEIGHT


class TestPlatform:
    """Tests for Platform class.
    
    Ref: docs/specs/features/typography-system.md §3.1
    """
    
    def test_platform_detection(self) -> None:
        """Platform detection should work correctly."""
        assert Platform.IS_MACOS == (sys.platform == "darwin")
        assert Platform.IS_WINDOWS == (sys.platform == "win32")
        assert Platform.IS_LINUX == sys.platform.startswith("linux")
    
    def test_platform_exclusivity(self) -> None:
        """Only one platform should be True (except Linux variants)."""
        # At most one of macOS or Windows should be True
        assert not (Platform.IS_MACOS and Platform.IS_WINDOWS)


class TestFontFamily:
    """Tests for FontFamily class.
    
    Ref: docs/specs/features/typography-system.md §3.2
    """
    
    def test_get_primary_returns_string(self) -> None:
        """get_primary should return a string."""
        result = FontFamily.get_primary()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_monospace_returns_string(self) -> None:
        """get_monospace should return a string."""
        result = FontFamily.get_monospace()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_font_family_selection(self) -> None:
        """Font family should match platform."""
        if Platform.IS_MACOS:
            assert "SF Pro Text" in Typography.PRIMARY
            assert "Menlo" in Typography.MONOSPACE
        else:
            assert "Segoe UI" in Typography.PRIMARY
            assert "Consolas" in Typography.MONOSPACE


class TestTypeScale:
    """Tests for TypeScale class.
    
    Ref: docs/specs/features/typography-system.md §3.3
    """
    
    def test_type_scale_sizes(self) -> None:
        """Type scale should be platform-appropriate."""
        if Platform.IS_MACOS:
            assert TypeScale.BODY == 11
            assert TypeScale.HEADER == 13
            assert TypeScale.SMALL == 10
        else:
            assert TypeScale.BODY == 9
            assert TypeScale.HEADER == 11
            assert TypeScale.SMALL == 8
    
    def test_type_scale_aliases(self) -> None:
        """Type scale aliases should match base sizes."""
        assert TypeScale.BODY_SIZE == TypeScale.BODY
        assert TypeScale.HEADER_SIZE == TypeScale.HEADER
        assert TypeScale.SMALL_SIZE == TypeScale.SMALL
        assert TypeScale.TABLE_HEADER_SIZE == TypeScale.BODY
        assert TypeScale.LOG_ENTRY_SIZE == TypeScale.BODY


class TestTypography:
    """Tests for Typography class.
    
    Ref: docs/specs/features/typography-system.md §3.4
    """
    
    def test_primary_font(self) -> None:
        """PRIMARY should be a valid font family string."""
        assert isinstance(Typography.PRIMARY, str)
        assert len(Typography.PRIMARY) > 0
    
    def test_monospace_font(self) -> None:
        """MONOSPACE should be a valid font family string."""
        assert isinstance(Typography.MONOSPACE, str)
        assert len(Typography.MONOSPACE) > 0
    
    def test_body_size(self) -> None:
        """BODY should match TypeScale.BODY."""
        assert Typography.BODY == TypeScale.BODY
    
    def test_header_size(self) -> None:
        """HEADER should match TypeScale.HEADER."""
        assert Typography.HEADER == TypeScale.HEADER
    
    def test_small_size(self) -> None:
        """SMALL should match TypeScale.SMALL."""
        assert Typography.SMALL == TypeScale.SMALL
    
    def test_log_entry_size(self) -> None:
        """LOG_ENTRY should match TypeScale.LOG_ENTRY_SIZE."""
        assert Typography.LOG_ENTRY == TypeScale.LOG_ENTRY_SIZE
    
    def test_table_row_height(self) -> None:
        """Row height should be derived from font size."""
        assert Typography.TABLE_ROW_HEIGHT == Typography.BODY + 7
        if Platform.IS_MACOS:
            assert Typography.TABLE_ROW_HEIGHT == 18
        else:
            assert Typography.TABLE_ROW_HEIGHT == 16
    
    def test_table_header_height(self) -> None:
        """Header height should be fixed at 20."""
        assert Typography.TABLE_HEADER_HEIGHT == 20


class TestDimensionsIntegration:
    """Integration tests for dimensions.py using Typography.
    
    Ref: docs/specs/features/typography-system.md §4.2
    """
    
    def test_dimensions_uses_typography(self) -> None:
        """Dimensions should use Typography constants."""
        assert TABLE_ROW_HEIGHT == Typography.TABLE_ROW_HEIGHT
        assert TABLE_HEADER_HEIGHT == Typography.TABLE_HEADER_HEIGHT


class TestStylesheetIntegration:
    """Integration tests for stylesheet.py using Typography.
    
    Ref: docs/specs/features/typography-system.md §4.1
    """
    
    def test_stylesheet_uses_typography(self) -> None:
        """Stylesheet should use Typography constants."""
        from src.styles.stylesheet import get_application_stylesheet
        style = get_application_stylesheet()
        
        # Check that font size is present
        if Platform.IS_MACOS:
            assert "11pt" in style
        else:
            assert "9pt" in style