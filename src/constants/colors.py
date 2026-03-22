"""Color definitions for the Log Viewer application.

This module defines all color constants used throughout the application,
including log level colors, UI element colors, and semantic color names.

Ref: docs/specs/global/color-palette.md §8.1
Master: docs/SPEC.md §1 (Python 3.10, type safety, beartype)
"""

from __future__ import annotations

from beartype import beartype


# Base Colors (Light Theme)
class BaseColors:
    """Base color palette for light theme.
    
    These are the foundational colors from which all semantic colors are derived.
    Use these only as fallback or for derived calculations.
    
    Ref: docs/specs/global/color-palette.md §2.1
    """
    
    WHITE: str = "#FFFFFF"
    """Primary background color."""
    
    BLACK: str = "#000000"
    """Primary text color."""
    
    TRANSPARENT: str = "#00000000"
    """Transparent overlay color."""
    
    # Gray Scale
    GRAY_01: str = "#A4A4A4"
    """Dark gray - borders, disabled text."""
    
    GRAY_02: str = "#B6B6B6"
    """Medium-dark gray - table row background."""
    
    GRAY_03: str = "#C8C8C8"
    """Medium gray - borders."""
    
    GRAY_04: str = "#D6D6D6"
    """Medium-light gray - hover states."""
    
    GRAY_05: str = "#E7E7E7"
    """Light gray - panel backgrounds."""
    
    # Accent Colors
    ACCENT_01: str = "#FFA3D0FF"
    """Primary accent (light blue) - transparent."""
    
    ACCENT_02: str = "#0078D7"
    """Container panel highlighted."""
    
    ACCENT_03: str = "#375977"
    """Log item entry (selected)."""


# Palette Colors (Color Families)
class PaletteColors:
    """Color families with multiple shades.
    
    Each color family provides a range of shades from dark to light.
    Use for custom components that need color variations.
    
    Ref: docs/specs/global/color-palette.md §3.1
    """
    
    # Gray Family
    GRAY_1: str = "#A4A4A4"
    """Dark borders, disabled states."""
    
    GRAY_2: str = "#B6B6B6"
    """Table row background, medium borders."""
    
    GRAY_3: str = "#C8C8C8"
    """Default borders, inactive elements."""
    
    GRAY_4: str = "#D6D6D6"
    """Hover backgrounds."""
    
    GRAY_5: str = "#E7E7E7"
    """Panel backgrounds, light areas."""
    
    # Red Family
    RED_1: str = "#F97575"
    """Dark red - error icons."""
    
    RED_2: str = "#F18989"
    """Medium-dark red."""
    
    RED_3: str = "#FF9A9A"
    """Medium red."""
    
    RED_4: str = "#FFB6B6"
    """Medium-light red."""
    
    RED_5: str = "#FFCACA"
    """Light red - error backgrounds."""
    
    # Orange Family
    ORANGE_1: str = "#F9A54F"
    """Dark orange."""
    
    ORANGE_2: str = "#F9BA7B"
    """Medium-dark orange."""
    
    ORANGE_3: str = "#FCC48C"
    """Medium orange."""
    
    ORANGE_4: str = "#FCCC9C"
    """Medium-light orange."""
    
    ORANGE_5: str = "#FDDDBE"
    """Light orange."""
    
    # Green Family
    GREEN_1: str = "#7CEB7C"
    """Dark green - success icons."""
    
    GREEN_2: str = "#94F594"
    """Medium-dark green."""
    
    GREEN_3: str = "#9CFF9C"
    """Medium green."""
    
    GREEN_4: str = "#B8FFB8"
    """Medium-light green."""
    
    GREEN_5: str = "#D2FFD2"
    """Light green - success backgrounds."""
    
    # Cyan Family
    CYAN_1: str = "#4AE7BF"
    """Dark cyan."""
    
    CYAN_2: str = "#7CF3D4"
    """Medium-dark cyan."""
    
    CYAN_3: str = "#8FFBE0"
    """Medium cyan."""
    
    CYAN_4: str = "#ABF9E6"
    """Medium-light cyan."""
    
    CYAN_5: str = "#C3FEEF"
    """Light cyan."""
    
    # Blue Family
    BLUE_1: str = "#70A3FF"
    """Dark blue - primary actions."""
    
    BLUE_2: str = "#80B0FF"
    """Medium-dark blue."""
    
    BLUE_3: str = "#8CBAFF"
    """Medium blue."""
    
    BLUE_4: str = "#99D0FF"
    """Medium-light blue."""
    
    # Purple Family
    PURPLE_1: str = "#D86EFF"
    """Dark purple - debug level."""
    
    PURPLE_2: str = "#DF86FF"
    """Medium-dark purple."""
    
    PURPLE_3: str = "#E09DFF"
    """Medium purple."""
    
    PURPLE_4: str = "#EBB5FF"
    """Medium-light purple."""


# Semantic Colors (UI Elements)
class UIColors:
    """Semantic colors for UI elements.
    
    Use for standard UI elements (buttons, inputs, etc.).
    
    Ref: docs/specs/global/color-palette.md §4.1
    """
    
    # Background Colors
    BACKGROUND_PRIMARY: str = "#FFFFFF"
    """Main content background."""
    
    BACKGROUND_SECONDARY: str = "#F5F5F5"
    """Panel backgrounds, toolbar."""
    
    BACKGROUND_TERTIARY: str = "#F0F0F0"
    """Main window background."""
    
    BACKGROUND_HOVER: str = "#E8E8E8"
    """Hover states."""
    
    BACKGROUND_ACTIVE: str = "#D0D0D0"
    """Active/pressed states."""
    
    BACKGROUND_SELECTED: str = "#DCEBF7"
    """Selection highlight."""
    
    BACKGROUND_DISABLED: str = "#F5F5F5"
    """Disabled element backgrounds."""
    
    # Border Colors
    BORDER_DEFAULT: str = "#C0C0C0"
    """Default borders."""
    
    BORDER_HOVER: str = "#A0A0A0"
    """Hover borders."""
    
    BORDER_FOCUS: str = "#0066CC"
    """Focus indicator."""
    
    BORDER_DISABLED: str = "#D0D0D0"
    """Disabled borders."""
    
    BORDER_MOUSE_OVER: str = "#8491A3"
    """Mouse over border (LogViewer)."""
    
    BORDER_SELECTED: str = "#8491A3"
    """Selected border (LogViewer)."""
    
    # Text Colors
    TEXT_PRIMARY: str = "#333333"
    """Primary text."""
    
    TEXT_SECONDARY: str = "#666666"
    """Secondary text, placeholders."""
    
    TEXT_DISABLED: str = "#999999"
    """Disabled text."""
    
    TEXT_SELECTED: str = "#382F27"
    """Selected text (LogViewer)."""
    
    TEXT_MOUSE_OVER: str = "#382F27"
    """Mouse over text (LogViewer)."""
    
    TEXT_INVERTED: str = "#FFFFFF"
    """Text on dark backgrounds."""
    
    # Special Colors
    FIND_HIGHLIGHT: str = "#FFFF00"
    """Search result highlighting."""
    
    TOOLTIP_BACKGROUND: str = "#333333"
    """Tooltip background."""
    
    TOOLTIP_TEXT: str = "#FFFFFF"
    """Tooltip text."""
    
    TOOLTIP_BORDER: str = "#555555"
    """Tooltip border."""


# Log Level Colors
class LogTextColors:
    """Namespace for log level text colors.
    
    These colors are used for the text foreground in log entries
    to visually distinguish different log levels.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    
    Note: MSG, DEBUG, and TRACE levels use default text color (no special color).
    """
    
    CRITICAL: str = "#781111"
    """Text color for CRITICAL level (dark red)."""
    
    ERROR: str = "#781111"
    """Text color for ERROR level (dark red)."""
    
    WARNING: str = "#6A5302"
    """Text color for WARNING level (amber/brown)."""


class LogIconColors:
    """Namespace for log level icon colors.
    
    These colors are used for the icons displayed alongside log entries.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    """
    
    CRITICAL: str = "#781111"
    """Icon color for CRITICAL level (dark red)."""
    
    ERROR: str = "#781111"
    """Icon color for ERROR level (dark red)."""
    
    WARNING: str = "#6A5302"
    """Icon color for WARNING level (amber/brown)."""
    
    MSG: str = "#BDBDBD"
    """Icon color for MSG level (light gray)."""
    
    DEBUG: str = "#BDBDBD"
    """Icon color for DEBUG level (light gray)."""
    
    TRACE: str = "#BDBDBD"
    """Icon color for TRACE level (light gray)."""


class StatsColors:
    """Namespace for statistics counter colors.
    
    These colors are used for the statistics bar counters that display
    counts for each log level. Each level has background, text, and border colors.
    
    Design: Light background with colored text/border for readability.
    
    Ref: docs/style_example §2.1.2 (lines 43-50, 567-577)
    """
    
    # Critical level colors
    CRITICAL_BG: str = "#FFE4E4"
    """Background color for CRITICAL level counter."""
    
    CRITICAL_TEXT: str = "#781111"
    """Text/icon color for CRITICAL level counter (dark red)."""
    
    CRITICAL_BORDER: str = "#781111"
    """Border color for CRITICAL level counter (dark red)."""
    
    # Error level colors
    ERROR_BG: str = "#FFE4E4"
    """Background color for ERROR level counter."""
    
    ERROR_TEXT: str = "#781111"
    """Text/icon color for ERROR level counter (dark red)."""
    
    ERROR_BORDER: str = "#781111"
    """Border color for ERROR level counter (dark red)."""
    
    # Warning level colors
    WARNING_BG: str = "#FFF4E0"
    """Background color for WARNING level counter."""
    
    WARNING_TEXT: str = "#6A5302"
    """Text/icon color for WARNING level counter (amber/brown)."""
    
    WARNING_BORDER: str = "#6A5302"
    """Border color for WARNING level counter (amber/brown)."""
    
    # Message level colors
    MSG_BG: str = "#E0F0FF"
    """Background color for MSG level counter."""
    
    MSG_TEXT: str = "#0066CC"
    """Text/icon color for MSG level counter."""
    
    MSG_BORDER: str = "#0066CC"
    """Border color for MSG level counter."""
    
    # Debug level colors
    DEBUG_BG: str = "#F0E8F4"
    """Background color for DEBUG level counter."""
    
    DEBUG_TEXT: str = "#8844AA"
    """Text/icon color for DEBUG level counter."""
    
    DEBUG_BORDER: str = "#8844AA"
    """Border color for DEBUG level counter."""
    
    # Trace level colors
    TRACE_BG: str = "#E4FFE4"
    """Background color for TRACE level counter."""
    
    TRACE_TEXT: str = "#00AA00"
    """Text/icon color for TRACE level counter."""
    
    TRACE_BORDER: str = "#00AA00"
    """Border color for TRACE level counter."""


# Process Identification Colors
class ProcessColors:
    """Colors for process identification.
    
    Colors for identifying different processes in the log view.
    Assigned cyclically when new processes are detected.
    
    Ref: docs/specs/global/color-palette.md §6.1
    """
    
    BLUE: str = "#96CBF8"
    """Process identifier 1."""
    
    RED: str = "#CC7474"
    """Process identifier 2."""
    
    ORANGE: str = "#F5B76E"
    """Process identifier 3."""
    
    PINK: str = "#D786CA"
    """Process identifier 4."""
    
    GREEN: str = "#9BBF7C"
    """Process identifier 5."""
    
    CREAM: str = "#FAE744"
    """Process identifier 6."""
    
    @classmethod
    @beartype
    def get_color(cls, index: int) -> str:
        """Get process color by index (cyclic).
        
        Process colors are assigned in order (Blue → Red → Orange → 
        Pink → Green → Cream) and cycle back to Blue when all colors
        are used.
        
        Args:
            index: Process index (0-based).
            
        Returns:
            Color hex value for the process.
            
        Ref: docs/specs/global/color-palette.md §6.1
        """
        colors = [cls.BLUE, cls.RED, cls.ORANGE, 
                  cls.PINK, cls.GREEN, cls.CREAM]
        return colors[index % len(colors)]


# LogViewer-Specific Colors
class LogViewerColors:
    """Colors specific to LogViewer plugin.
    
    Colors for log item rendering in the LogViewer plugin.
    
    Ref: docs/specs/global/color-palette.md §7
    """
    
    LOG_ITEM_SELECTED: str = "#B7CFD5"
    """Background for selected log items."""
    
    LOG_ITEM_BORDER_MOUSE_OVER: str = "#B7CFD5"
    """Log item border on hover."""
    
    LOG_ITEM_TEXT_MOUSE_OVER: str = "#382F27"
    """Text color on mouse hover."""
    
    LOG_BORDER: str = "#00000080"
    """Semi-transparent black for log borders."""
    
    AUTO_SCROLL_SELECTED: str = "#483D8B"
    """Auto-scroll button selected state."""
    
    AUTO_SCROLL_MOUSE_OVER: str = "#2587CF"
    """Auto-scroll button hover state."""
    
    CONTAINER_PANEL_HIGHLIGHTED: str = "#0078D7"
    """Highlighted container panel background."""


# Highlight Colors
class HighlightColors:
    """Colors for highlight patterns in log messages.
    
    These colors are used for highlighting search results and 
    user-defined highlight patterns in the log viewer.
    
    Ref: docs/audit/HARDCODED_COLORS_AUDIT.md §3
    """
    
    YELLOW: str = "#FFFF00"
    """Yellow highlight (same as UIColors.FIND_HIGHLIGHT)."""
    
    GREEN: str = "#00FF00"
    """Green highlight color."""
    
    CYAN: str = "#00FFFF"
    """Cyan highlight color."""
    
    MAGENTA: str = "#FF00FF"
    """Magenta highlight color."""
    
    ORANGE: str = "#FFA500"
    """Orange highlight color."""
    
    PINK: str = "#FF69B4"
    """Pink highlight color."""
    
    @classmethod
    @beartype
    def get_all_colors(cls) -> list[str]:
        """Get all highlight colors as a list.
        
        Returns:
            List of all highlight color hex values.
            
        Ref: docs/audit/HARDCODED_COLORS_AUDIT.md §3
        """
        return [
            cls.YELLOW,
            cls.GREEN,
            cls.CYAN,
            cls.MAGENTA,
            cls.ORANGE,
            cls.PINK,
        ]