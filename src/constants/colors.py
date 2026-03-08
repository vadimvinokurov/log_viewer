"""Color definitions for the Log Viewer application.

This module defines all color constants used throughout the application,
including log level colors, UI element colors, and semantic color names.
"""

from __future__ import annotations


class LogColors:
    """Namespace for log level background colors.
    
    These colors are used as backgrounds for log entries in the table view
    to visually distinguish different log levels.
    """
    
    CRITICAL: str = "#FF6B6B"
    """Background color for CRITICAL level log entries."""
    
    ERROR: str = "#FF8C8C"
    """Background color for ERROR level log entries."""
    
    WARNING: str = "#FFD93D"
    """Background color for WARNING level log entries."""
    
    MSG: str = "#FFFFFF"
    """Background color for MSG (message) level log entries."""
    
    DEBUG: str = "#E8E8E8"
    """Background color for DEBUG level log entries."""
    
    TRACE: str = "#F5F5F5"
    """Background color for TRACE level log entries."""


class LogIconColors:
    """Namespace for log level icon colors.
    
    These colors are used for the icons displayed alongside log entries.
    """
    
    CRITICAL: str = "#CC0000"
    """Icon color for CRITICAL level."""
    
    ERROR: str = "#CC0000"
    """Icon color for ERROR level."""
    
    WARNING: str = "#B8860B"
    """Icon color for WARNING level."""
    
    MSG: str = "#CCCCCC"
    """Icon color for MSG level."""
    
    DEBUG: str = "#999999"
    """Icon color for DEBUG level."""
    
    TRACE: str = "#AAAAAA"
    """Icon color for TRACE level."""


class StatsColors:
    """Namespace for statistics counter colors.
    
    These colors are used for the statistics bar counters that display
    counts for each log level. Each level has background, text, and border colors.
    
    Design: Light background with colored text/border for readability.
    """
    
    # Critical level colors
    CRITICAL_BG: str = "#FFE4E4"
    """Background color for CRITICAL level counter."""
    CRITICAL_TEXT: str = "#FF4444"
    """Text/icon color for CRITICAL level counter."""
    CRITICAL_BORDER: str = "#FF4444"
    """Border color for CRITICAL level counter."""
    
    # Error level colors
    ERROR_BG: str = "#FFE4E4"
    """Background color for ERROR level counter."""
    ERROR_TEXT: str = "#CC0000"
    """Text/icon color for ERROR level counter."""
    ERROR_BORDER: str = "#CC0000"
    """Border color for ERROR level counter."""
    
    # Warning level colors
    WARNING_BG: str = "#FFF4E0"
    """Background color for WARNING level counter."""
    WARNING_TEXT: str = "#FFAA00"
    """Text/icon color for WARNING level counter."""
    WARNING_BORDER: str = "#FFAA00"
    """Border color for WARNING level counter."""
    
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


# UI element colors
SELECTION_HIGHLIGHT_COLOR: str = "#dcebf7"
"""Background color for selected items in lists and tables."""

FIND_HIGHLIGHT_COLOR: str = "#FFFF00"
"""Background color for highlighting search results (yellow)."""

DEFAULT_TEXT_COLOR: str = "#000000"
"""Default text color for normal content."""

SECONDARY_TEXT_COLOR: str = "#666666"
"""Secondary text color for less prominent content."""

BORDER_COLOR: str = "#CCCCCC"
"""Default border color for UI elements."""

HEADER_BACKGROUND: str = "#F0F0F0"
"""Background color for table headers and similar elements."""