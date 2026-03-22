"""Unit tests for color constants.

Tests for the layered color architecture defined in:
- docs/specs/global/color-palette.md §8.1
- docs/SPEC.md §1 (Python 3.10, type safety, beartype)

Ref: docs/specs/global/color-palette.md §11
"""

from __future__ import annotations

import pytest
from beartype import beartype

from src.constants.colors import (
    BaseColors,
    PaletteColors,
    UIColors,
    LogTextColors,
    LogIconColors,
    StatsColors,
    ProcessColors,
    LogViewerColors,
    HighlightColors,
)
# Legacy constants are NOT imported at module level to test deprecation warnings
# They will be imported inside test functions


class TestBaseColors:
    """Tests for BaseColors class.
    
    Ref: docs/specs/global/color-palette.md §2.1
    """
    
    def test_white_color(self) -> None:
        """Verify WHITE has correct hex value."""
        assert BaseColors.WHITE == "#FFFFFF"
    
    def test_black_color(self) -> None:
        """Verify BLACK has correct hex value."""
        assert BaseColors.BLACK == "#000000"
    
    def test_transparent_color(self) -> None:
        """Verify TRANSPARENT has correct hex value."""
        assert BaseColors.TRANSPARENT == "#00000000"
    
    def test_gray_scale_colors(self) -> None:
        """Verify all gray scale colors have correct hex values."""
        assert BaseColors.GRAY_01 == "#A4A4A4"
        assert BaseColors.GRAY_02 == "#B6B6B6"
        assert BaseColors.GRAY_03 == "#C8C8C8"
        assert BaseColors.GRAY_04 == "#D6D6D6"
        assert BaseColors.GRAY_05 == "#E7E7E7"
    
    def test_accent_colors(self) -> None:
        """Verify all accent colors have correct hex values."""
        assert BaseColors.ACCENT_01 == "#FFA3D0FF"
        assert BaseColors.ACCENT_02 == "#0078D7"
        assert BaseColors.ACCENT_03 == "#375977"


class TestPaletteColors:
    """Tests for PaletteColors class.
    
    Ref: docs/specs/global/color-palette.md §3.1
    """
    
    def test_gray_family(self) -> None:
        """Verify gray family colors have correct hex values."""
        assert PaletteColors.GRAY_1 == "#A4A4A4"
        assert PaletteColors.GRAY_2 == "#B6B6B6"
        assert PaletteColors.GRAY_3 == "#C8C8C8"
        assert PaletteColors.GRAY_4 == "#D6D6D6"
        assert PaletteColors.GRAY_5 == "#E7E7E7"
    
    def test_red_family(self) -> None:
        """Verify red family colors have correct hex values."""
        assert PaletteColors.RED_1 == "#F97575"
        assert PaletteColors.RED_2 == "#F18989"
        assert PaletteColors.RED_3 == "#FF9A9A"
        assert PaletteColors.RED_4 == "#FFB6B6"
        assert PaletteColors.RED_5 == "#FFCACA"
    
    def test_orange_family(self) -> None:
        """Verify orange family colors have correct hex values."""
        assert PaletteColors.ORANGE_1 == "#F9A54F"
        assert PaletteColors.ORANGE_2 == "#F9BA7B"
        assert PaletteColors.ORANGE_3 == "#FCC48C"
        assert PaletteColors.ORANGE_4 == "#FCCC9C"
        assert PaletteColors.ORANGE_5 == "#FDDDBE"
    
    def test_green_family(self) -> None:
        """Verify green family colors have correct hex values."""
        assert PaletteColors.GREEN_1 == "#7CEB7C"
        assert PaletteColors.GREEN_2 == "#94F594"
        assert PaletteColors.GREEN_3 == "#9CFF9C"
        assert PaletteColors.GREEN_4 == "#B8FFB8"
        assert PaletteColors.GREEN_5 == "#D2FFD2"
    
    def test_cyan_family(self) -> None:
        """Verify cyan family colors have correct hex values."""
        assert PaletteColors.CYAN_1 == "#4AE7BF"
        assert PaletteColors.CYAN_2 == "#7CF3D4"
        assert PaletteColors.CYAN_3 == "#8FFBE0"
        assert PaletteColors.CYAN_4 == "#ABF9E6"
        assert PaletteColors.CYAN_5 == "#C3FEEF"
    
    def test_blue_family(self) -> None:
        """Verify blue family colors have correct hex values."""
        assert PaletteColors.BLUE_1 == "#70A3FF"
        assert PaletteColors.BLUE_2 == "#80B0FF"
        assert PaletteColors.BLUE_3 == "#8CBAFF"
        assert PaletteColors.BLUE_4 == "#99D0FF"
    
    def test_purple_family(self) -> None:
        """Verify purple family colors have correct hex values."""
        assert PaletteColors.PURPLE_1 == "#D86EFF"
        assert PaletteColors.PURPLE_2 == "#DF86FF"
        assert PaletteColors.PURPLE_3 == "#E09DFF"
        assert PaletteColors.PURPLE_4 == "#EBB5FF"


class TestUIColors:
    """Tests for UIColors class.
    
    Ref: docs/specs/global/color-palette.md §4.1
    """
    
    def test_background_colors(self) -> None:
        """Verify background colors have correct hex values."""
        assert UIColors.BACKGROUND_PRIMARY == "#FFFFFF"
        assert UIColors.BACKGROUND_SECONDARY == "#F5F5F5"
        assert UIColors.BACKGROUND_TERTIARY == "#F0F0F0"
        assert UIColors.BACKGROUND_HOVER == "#E8E8E8"
        assert UIColors.BACKGROUND_ACTIVE == "#D0D0D0"
        assert UIColors.BACKGROUND_SELECTED == "#DCEBF7"
        assert UIColors.BACKGROUND_DISABLED == "#F5F5F5"
    
    def test_border_colors(self) -> None:
        """Verify border colors have correct hex values."""
        assert UIColors.BORDER_DEFAULT == "#C0C0C0"
        assert UIColors.BORDER_HOVER == "#A0A0A0"
        assert UIColors.BORDER_FOCUS == "#0066CC"
        assert UIColors.BORDER_DISABLED == "#D0D0D0"
        assert UIColors.BORDER_MOUSE_OVER == "#8491A3"
        assert UIColors.BORDER_SELECTED == "#8491A3"
    
    def test_text_colors(self) -> None:
        """Verify text colors have correct hex values."""
        assert UIColors.TEXT_PRIMARY == "#333333"
        assert UIColors.TEXT_SECONDARY == "#666666"
        assert UIColors.TEXT_DISABLED == "#999999"
        assert UIColors.TEXT_SELECTED == "#382F27"
        assert UIColors.TEXT_MOUSE_OVER == "#382F27"
        assert UIColors.TEXT_INVERTED == "#FFFFFF"
    
    def test_special_colors(self) -> None:
        """Verify special colors have correct hex values."""
        assert UIColors.FIND_HIGHLIGHT == "#FFFF00"
        assert UIColors.TOOLTIP_BACKGROUND == "#333333"
        assert UIColors.TOOLTIP_TEXT == "#FFFFFF"
        assert UIColors.TOOLTIP_BORDER == "#555555"


class TestLogTextColors:
    """Tests for LogTextColors class.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    """
    
    def test_critical_color(self) -> None:
        """Verify CRITICAL has correct hex value (dark red)."""
        assert LogTextColors.CRITICAL == "#781111"
    
    def test_error_color(self) -> None:
        """Verify ERROR has correct hex value (dark red)."""
        assert LogTextColors.ERROR == "#781111"
    
    def test_warning_color(self) -> None:
        """Verify WARNING has correct hex value (amber/brown)."""
        assert LogTextColors.WARNING == "#6A5302"
    
    def test_log_text_colors_match_reference(self) -> None:
        """Verify log text colors match reference document."""
        assert LogTextColors.CRITICAL == "#781111"
        assert LogTextColors.ERROR == "#781111"
        assert LogTextColors.WARNING == "#6A5302"


class TestLogIconColors:
    """Tests for LogIconColors class.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    """
    
    def test_critical_icon(self) -> None:
        """Verify CRITICAL icon color (dark red)."""
        assert LogIconColors.CRITICAL == "#781111"
    
    def test_error_icon(self) -> None:
        """Verify ERROR icon color (dark red)."""
        assert LogIconColors.ERROR == "#781111"
    
    def test_warning_icon(self) -> None:
        """Verify WARNING icon color (amber/brown)."""
        assert LogIconColors.WARNING == "#6A5302"
    
    def test_msg_icon(self) -> None:
        """Verify MSG icon color (light gray)."""
        assert LogIconColors.MSG == "#BDBDBD"
    
    def test_debug_icon(self) -> None:
        """Verify DEBUG icon color (light gray)."""
        assert LogIconColors.DEBUG == "#BDBDBD"
    
    def test_trace_icon(self) -> None:
        """Verify TRACE icon color (light gray)."""
        assert LogIconColors.TRACE == "#BDBDBD"
    
    def test_log_icon_colors_match_reference(self) -> None:
        """Verify log icon colors match reference document."""
        assert LogIconColors.CRITICAL == "#781111"
        assert LogIconColors.ERROR == "#781111"
        assert LogIconColors.WARNING == "#6A5302"
        assert LogIconColors.MSG == "#BDBDBD"
        assert LogIconColors.DEBUG == "#BDBDBD"
        assert LogIconColors.TRACE == "#BDBDBD"


class TestStatsColors:
    """Tests for StatsColors class.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    """
    
    def test_critical_colors(self) -> None:
        """Verify CRITICAL counter colors."""
        assert StatsColors.CRITICAL_BG == "#FFE4E4"
        assert StatsColors.CRITICAL_TEXT == "#781111"
        assert StatsColors.CRITICAL_BORDER == "#781111"
    
    def test_error_colors(self) -> None:
        """Verify ERROR counter colors."""
        assert StatsColors.ERROR_BG == "#FFE4E4"
        assert StatsColors.ERROR_TEXT == "#781111"
        assert StatsColors.ERROR_BORDER == "#781111"
    
    def test_warning_colors(self) -> None:
        """Verify WARNING counter colors."""
        assert StatsColors.WARNING_BG == "#FFF4E0"
        assert StatsColors.WARNING_TEXT == "#6A5302"
        assert StatsColors.WARNING_BORDER == "#6A5302"
    
    def test_msg_colors(self) -> None:
        """Verify MSG counter colors."""
        assert StatsColors.MSG_BG == "#E0F0FF"
        assert StatsColors.MSG_TEXT == "#0066CC"
        assert StatsColors.MSG_BORDER == "#0066CC"
    
    def test_debug_colors(self) -> None:
        """Verify DEBUG counter colors."""
        assert StatsColors.DEBUG_BG == "#F0E8F4"
        assert StatsColors.DEBUG_TEXT == "#8844AA"
        assert StatsColors.DEBUG_BORDER == "#8844AA"
    
    def test_trace_colors(self) -> None:
        """Verify TRACE counter colors."""
        assert StatsColors.TRACE_BG == "#E4FFE4"
        assert StatsColors.TRACE_TEXT == "#00AA00"
        assert StatsColors.TRACE_BORDER == "#00AA00"
    
    def test_stats_colors_match_reference(self) -> None:
        """Verify stats colors match reference document."""
        assert StatsColors.CRITICAL_TEXT == "#781111"
        assert StatsColors.CRITICAL_BORDER == "#781111"
        assert StatsColors.ERROR_TEXT == "#781111"
        assert StatsColors.ERROR_BORDER == "#781111"
        assert StatsColors.WARNING_TEXT == "#6A5302"
        assert StatsColors.WARNING_BORDER == "#6A5302"


class TestProcessColors:
    """Tests for ProcessColors class.
    
    Ref: docs/specs/global/color-palette.md §6.1
    """
    
    def test_process_colors_exist(self) -> None:
        """Verify all process colors have correct hex values."""
        assert ProcessColors.BLUE == "#96CBF8"
        assert ProcessColors.RED == "#CC7474"
        assert ProcessColors.ORANGE == "#F5B76E"
        assert ProcessColors.PINK == "#D786CA"
        assert ProcessColors.GREEN == "#9BBF7C"
        assert ProcessColors.CREAM == "#FAE744"
    
    def test_get_color_index_0(self) -> None:
        """Verify get_color(0) returns BLUE."""
        assert ProcessColors.get_color(0) == "#96CBF8"
    
    def test_get_color_index_1(self) -> None:
        """Verify get_color(1) returns RED."""
        assert ProcessColors.get_color(1) == "#CC7474"
    
    def test_get_color_index_2(self) -> None:
        """Verify get_color(2) returns ORANGE."""
        assert ProcessColors.get_color(2) == "#F5B76E"
    
    def test_get_color_index_3(self) -> None:
        """Verify get_color(3) returns PINK."""
        assert ProcessColors.get_color(3) == "#D786CA"
    
    def test_get_color_index_4(self) -> None:
        """Verify get_color(4) returns GREEN."""
        assert ProcessColors.get_color(4) == "#9BBF7C"
    
    def test_get_color_index_5(self) -> None:
        """Verify get_color(5) returns CREAM."""
        assert ProcessColors.get_color(5) == "#FAE744"
    
    def test_get_color_cyclic_assignment(self) -> None:
        """Verify get_color cycles back to BLUE after index 5."""
        # Index 6 should cycle back to BLUE (index 0)
        assert ProcessColors.get_color(6) == "#96CBF8"
        # Index 7 should be RED (index 1)
        assert ProcessColors.get_color(7) == "#CC7474"
        # Index 10 should be GREEN (10 % 6 = 4)
        assert ProcessColors.get_color(10) == "#9BBF7C"
    
    def test_get_color_negative_index(self) -> None:
        """Verify get_color handles negative indices correctly."""
        # Python's modulo handles negative indices
        # -1 % 6 = 5, so should return CREAM
        assert ProcessColors.get_color(-1) == "#FAE744"
        # -2 % 6 = 4, so should return GREEN
        assert ProcessColors.get_color(-2) == "#9BBF7C"
    
    def test_get_color_large_index(self) -> None:
        """Verify get_color handles large indices correctly."""
        # 100 % 6 = 4, so should return GREEN
        assert ProcessColors.get_color(100) == "#9BBF7C"
        # 1000 % 6 = 4, so should return GREEN
        assert ProcessColors.get_color(1000) == "#9BBF7C"


class TestLogViewerColors:
    """Tests for LogViewerColors class.
    
    Ref: docs/specs/global/color-palette.md §7
    """
    
    def test_log_item_selected(self) -> None:
        """Verify LOG_ITEM_SELECTED has correct hex value."""
        assert LogViewerColors.LOG_ITEM_SELECTED == "#B7CFD5"
    
    def test_log_item_border_mouse_over(self) -> None:
        """Verify LOG_ITEM_BORDER_MOUSE_OVER has correct hex value."""
        assert LogViewerColors.LOG_ITEM_BORDER_MOUSE_OVER == "#B7CFD5"
    
    def test_log_item_text_mouse_over(self) -> None:
        """Verify LOG_ITEM_TEXT_MOUSE_OVER has correct hex value."""
        assert LogViewerColors.LOG_ITEM_TEXT_MOUSE_OVER == "#382F27"
    
    def test_log_border(self) -> None:
        """Verify LOG_BORDER has correct hex value."""
        assert LogViewerColors.LOG_BORDER == "#00000080"
    
    def test_auto_scroll_selected(self) -> None:
        """Verify AUTO_SCROLL_SELECTED has correct hex value."""
        assert LogViewerColors.AUTO_SCROLL_SELECTED == "#483D8B"
    
    def test_auto_scroll_mouse_over(self) -> None:
        """Verify AUTO_SCROLL_MOUSE_OVER has correct hex value."""
        assert LogViewerColors.AUTO_SCROLL_MOUSE_OVER == "#2587CF"
    
    def test_container_panel_highlighted(self) -> None:
        """Verify CONTAINER_PANEL_HIGHLIGHTED has correct hex value."""
        assert LogViewerColors.CONTAINER_PANEL_HIGHLIGHTED == "#0078D7"


class TestNewClassesImportable:
    """Tests to verify new classes are importable.
    
    Ref: docs/specs/global/color-palette.md §8.1
    """
    
    def test_base_colors_importable(self) -> None:
        """Verify BaseColors is importable."""
        from src.constants.colors import BaseColors
        assert hasattr(BaseColors, 'WHITE')
        assert hasattr(BaseColors, 'BLACK')
        assert hasattr(BaseColors, 'TRANSPARENT')
    
    def test_palette_colors_importable(self) -> None:
        """Verify PaletteColors is importable."""
        from src.constants.colors import PaletteColors
        assert hasattr(PaletteColors, 'GRAY_1')
        assert hasattr(PaletteColors, 'RED_1')
        assert hasattr(PaletteColors, 'BLUE_1')
    
    def test_ui_colors_importable(self) -> None:
        """Verify UIColors is importable."""
        from src.constants.colors import UIColors
        assert hasattr(UIColors, 'BACKGROUND_PRIMARY')
        assert hasattr(UIColors, 'BORDER_DEFAULT')
        assert hasattr(UIColors, 'TEXT_PRIMARY')
    
    def test_process_colors_importable(self) -> None:
        """Verify ProcessColors is importable."""
        from src.constants.colors import ProcessColors
        assert hasattr(ProcessColors, 'BLUE')
        assert hasattr(ProcessColors, 'get_color')
    
    def test_log_viewer_colors_importable(self) -> None:
        """Verify LogViewerColors is importable."""
        from src.constants.colors import LogViewerColors
        assert hasattr(LogViewerColors, 'LOG_ITEM_SELECTED')
        assert hasattr(LogViewerColors, 'LOG_BORDER')


class TestExistingClassesUnchanged:
    """Tests to verify background colors remain unchanged.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    Note: Only TEXT and BORDER colors were updated. BG colors remain unchanged.
    """
    
    def test_stats_background_colors_unchanged(self) -> None:
        """Verify StatsColors background colors are unchanged."""
        from src.constants.colors import StatsColors
        assert StatsColors.CRITICAL_BG == "#FFE4E4"
        assert StatsColors.ERROR_BG == "#FFE4E4"
        assert StatsColors.WARNING_BG == "#FFF4E0"
        assert StatsColors.MSG_BG == "#E0F0FF"
        assert StatsColors.DEBUG_BG == "#F0E8F4"
        assert StatsColors.TRACE_BG == "#E4FFE4"


class TestHighlightColors:
    """Tests for HighlightColors class.
    
    Ref: docs/audit/HARDCODED_COLORS_AUDIT.md §3
    """
    
    def test_yellow_color(self) -> None:
        """Test YELLOW color value."""
        assert HighlightColors.YELLOW == "#FFFF00"
    
    def test_green_color(self) -> None:
        """Test GREEN color value."""
        assert HighlightColors.GREEN == "#00FF00"
    
    def test_cyan_color(self) -> None:
        """Test CYAN color value."""
        assert HighlightColors.CYAN == "#00FFFF"
    
    def test_magenta_color(self) -> None:
        """Test MAGENTA color value."""
        assert HighlightColors.MAGENTA == "#FF00FF"
    
    def test_orange_color(self) -> None:
        """Test ORANGE color value."""
        assert HighlightColors.ORANGE == "#FFA500"
    
    def test_pink_color(self) -> None:
        """Test PINK color value."""
        assert HighlightColors.PINK == "#FF69B4"
    
    def test_get_all_colors(self) -> None:
        """Test get_all_colors returns all 6 colors."""
        colors = HighlightColors.get_all_colors()
        assert len(colors) == 6
        assert HighlightColors.YELLOW in colors
        assert HighlightColors.GREEN in colors
        assert HighlightColors.CYAN in colors
        assert HighlightColors.MAGENTA in colors
        assert HighlightColors.ORANGE in colors
        assert HighlightColors.PINK in colors
    
    def test_highlight_colors_importable(self) -> None:
        """Test HighlightColors can be imported."""
        from src.constants.colors import HighlightColors
        assert HighlightColors is not None