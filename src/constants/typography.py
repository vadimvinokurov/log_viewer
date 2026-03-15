"""Typography system for the Log Viewer application.

This module provides a unified typography system that serves as the single source
of truth for all font-related settings. It ensures consistent font rendering across
platforms (macOS, Windows, Linux).

Ref: docs/specs/features/typography-system.md
Ref: docs/specs/features/ui-design-system.md §2.2
"""

from __future__ import annotations

import sys
from beartype import beartype


class Platform:
    """Platform detection constants.
    
    Provides boolean flags for detecting the current operating system.
    Used by FontFamily and TypeScale to adjust typography for each platform.
    
    Ref: docs/specs/features/typography-system.md §3.1
    """
    
    IS_MACOS: bool = sys.platform == "darwin"
    """True if running on macOS (darwin kernel)."""
    
    IS_WINDOWS: bool = sys.platform == "win32"
    """True if running on Windows."""
    
    IS_LINUX: bool = sys.platform.startswith("linux")
    """True if running on Linux (linux or linux2)."""


class FontFamily:
    """Font family stacks for different contexts.
    
    Provides platform-appropriate font families for UI text and monospace
    (code/logs) contexts. Font stacks include fallbacks for cross-platform
    compatibility.
    
    Ref: docs/specs/features/typography-system.md §3.2
    Ref: docs/specs/features/ui-design-system.md §2.2.1
    """
    
    # Primary UI font - system native with fallbacks
    MACOS_PRIMARY: str = '"SF Pro Text", "Helvetica Neue", Arial, sans-serif'
    """Primary font family for macOS (SF Pro Text native)."""
    
    WINDOWS_PRIMARY: str = '"Segoe UI", "Roboto", Arial, sans-serif'
    """Primary font family for Windows/Linux (Segoe UI native)."""
    
    # Monospace font for code/logs
    MACOS_MONOSPACE: str = '"Menlo", "Monaco", "Courier New", monospace'
    """Monospace font family for macOS (Menlo native)."""
    
    WINDOWS_MONOSPACE: str = '"Consolas", "Courier New", monospace'
    """Monospace font family for Windows/Linux (Consolas native)."""
    
    @classmethod
    @beartype
    def get_primary(cls) -> str:
        """Get primary font family for current platform.
        
        Returns:
            str: Platform-appropriate primary font family stack.
                macOS: SF Pro Text with fallbacks
                Windows/Linux: Segoe UI with fallbacks
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return cls.MACOS_PRIMARY if Platform.IS_MACOS else cls.WINDOWS_PRIMARY
    
    @classmethod
    @beartype
    def get_monospace(cls) -> str:
        """Get monospace font family for current platform.
        
        Returns:
            str: Platform-appropriate monospace font family stack.
                macOS: Menlo with fallbacks
                Windows/Linux: Consolas with fallbacks
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return cls.MACOS_MONOSPACE if Platform.IS_MACOS else cls.WINDOWS_MONOSPACE


class TypeScale:
    """Type scale with platform-aware sizes.
    
    Provides font sizes in points for different text contexts. macOS uses
    +3pt offset for better readability on Retina displays.
    
    Ref: docs/specs/features/typography-system.md §3.3
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    """
    
    # Base sizes (in points) - Windows/Linux defaults
    BODY_BASE: int = 9
    """Base body text size for Windows/Linux (9pt)."""
    
    HEADER_BASE: int = 11
    """Base header text size for Windows/Linux (11pt)."""
    
    SMALL_BASE: int = 8
    """Base small text size for Windows/Linux (8pt)."""
    
    # macOS offset for Retina displays
    MACOS_OFFSET: int = 3
    """Font size offset for macOS Retina displays (+3pt)."""
    
    # Computed sizes (platform-aware)
    BODY: int = BODY_BASE + (MACOS_OFFSET if Platform.IS_MACOS else 0)
    """Body text size: 9pt (Windows/Linux) or 12pt (macOS)."""
    
    HEADER: int = HEADER_BASE + (MACOS_OFFSET if Platform.IS_MACOS else 0)
    """Header text size: 11pt (Windows/Linux) or 14pt (macOS)."""
    
    SMALL: int = SMALL_BASE + (MACOS_OFFSET if Platform.IS_MACOS else 0)
    """Small text size: 8pt (Windows/Linux) or 11pt (macOS)."""
    
    # Aliases for clarity
    BODY_SIZE: int = BODY
    """Alias for BODY size."""
    
    HEADER_SIZE: int = HEADER
    """Alias for HEADER size."""
    
    SMALL_SIZE: int = SMALL
    """Alias for SMALL size."""
    
    TABLE_HEADER_SIZE: int = BODY
    """Table header font size (same as BODY)."""
    
    LOG_ENTRY_SIZE: int = BODY
    """Log entry font size (same as BODY)."""


class Typography:
    """Unified typography constants.
    
    Single source of truth for all font-related settings. Import from this class,
    not from FontFamily or TypeScale directly.
    
    Ref: docs/specs/features/typography-system.md §3.4
    """
    
    # Font families
    PRIMARY: str = FontFamily.get_primary()
    """Primary UI font family for current platform."""
    
    MONOSPACE: str = FontFamily.get_monospace()
    """Monospace font family for code/logs on current platform."""
    
    # Type scale (in points)
    BODY: int = TypeScale.BODY
    """Body text size in points (9 or 12)."""
    
    HEADER: int = TypeScale.HEADER
    """Header text size in points (11 or 14)."""
    
    SMALL: int = TypeScale.SMALL
    """Small text size in points (8 or 11)."""
    
    LOG_ENTRY: int = TypeScale.LOG_ENTRY_SIZE
    """Log entry text size in points (same as BODY)."""
    
    # Derived dimensions (in pixels)
    TABLE_ROW_HEIGHT: int = TypeScale.BODY + 7
    """Table row height in pixels (16px for 9pt, 19px for 12pt font).
    
    Calculation: font size + 7px padding for comfortable row height.
    """
    
    TABLE_HEADER_HEIGHT: int = 20
    """Table header height in pixels (fixed at 20px)."""