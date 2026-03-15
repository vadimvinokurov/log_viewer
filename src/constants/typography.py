"""Typography system for the Log Viewer application.

This module provides a unified typography system that uses Qt's system default
fonts instead of hardcoded font families and sizes. This ensures native
look-and-feel on all platforms (macOS, Windows, Linux) without manual
platform detection or maintenance.

Ref: docs/specs/features/typography-system.md §3.1, §3.2
Master: docs/SPEC.md - Python 3.12, PySide6/Qt, beartype for type checking
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


class _CachedFont:
    """Descriptor for lazy font initialization.
    
    Fonts are created on first access, not at import time.
    This ensures QApplication is initialized before font detection.
    
    Ref: docs/specs/features/typography-system.md §3.1
    """
    
    def __init__(self, font_getter):
        self.font_getter = font_getter
        self._font: QFont | None = None
    
    def __get__(self, obj, objtype=None) -> QFont:
        if self._font is None:
            self._font = self.font_getter()
        return self._font


class classproperty:
    """Descriptor for class-level properties.
    
    Allows defining properties that can be accessed on the class itself,
    not just on instances.
    
    Ref: docs/specs/features/typography-system.md §3.2
    """
    
    def __init__(self, getter):
        self.getter = getter
    
    def __get__(self, obj, objtype=None):
        return self.getter(objtype)


class SystemFonts:
    """Qt-based system font detection.
    
    Uses Qt's font system to get native fonts for each platform.
    No manual platform detection required.
    
    Ref: docs/specs/features/typography-system.md §3.1
    """
    
    @staticmethod
    def get_ui_font() -> QFont:
        """Get system default UI font.
        
        Returns:
            QFont: System default font (SF Pro Text on macOS, 
                   Segoe UI on Windows, system font on Linux).
                   Font size is determined by system settings.
        
        Ref: docs/specs/features/typography-system.md §3.1
        """
        if QApplication.instance():
            return QApplication.font()
        # Fallback for when QApplication is not initialized
        return QFont()
    
    @staticmethod
    def get_monospace_font() -> QFont:
        """Get system default monospace font.
        
        Returns:
            QFont: System monospace font (Menlo on macOS,
                   Consolas on Windows, monospace on Linux).
                   Font size matches UI font size.
        
        Ref: docs/specs/features/typography-system.md §3.1
        """
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        # Ensure monospace font matches UI font size
        ui_font = SystemFonts.get_ui_font()
        font.setPointSize(ui_font.pointSize())
        return font


class Typography:
    """Simplified typography constants.
    
    Uses Qt's system fonts instead of hardcoded values.
    All UI text uses the same font family and size.
    Log entries use monospace font.
    
    Ref: docs/specs/features/typography-system.md §3.2
    """
    
    # System fonts (QFont instances) - lazy initialization
    UI_FONT: QFont = _CachedFont(SystemFonts.get_ui_font)
    """System default UI font. Use for all UI text."""
    
    LOG_FONT: QFont = _CachedFont(SystemFonts.get_monospace_font)
    """System monospace font. Use for log entries."""
    
    # Font family strings (for QSS stylesheets)
    @classproperty
    def PRIMARY(cls) -> str:
        """Get UI font family as string for QSS.
        
        Returns:
            Font family string (e.g., '"SF Pro Text"', 'Segoe UI').
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return f'"{cls.UI_FONT.family()}"'
    
    @classproperty
    def MONOSPACE(cls) -> str:
        """Get monospace font family as string for QSS.
        
        Returns:
            Font family string (e.g., '"Menlo"', 'Consolas').
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return f'"{cls.LOG_FONT.family()}"'
    
    # Font size (from system)
    @classproperty
    def BODY_SIZE(cls) -> int:
        """Get system default font size in points.
        
        Returns:
            Font size in points (determined by system settings).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return cls.UI_FONT.pointSize()
    
    # Convenience aliases (same as BODY_SIZE)
    @classproperty
    def BODY(cls) -> int:
        """Get system default font size in points.
        
        Alias for BODY_SIZE.
        
        Returns:
            Font size in points (determined by system settings).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return cls.UI_FONT.pointSize()
    
    @classproperty
    def LOG_ENTRY(cls) -> int:
        """Get system default font size in points.
        
        Alias for BODY_SIZE, used for log entries.
        
        Returns:
            Font size in points (determined by system settings).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return cls.UI_FONT.pointSize()
    
    # Cell padding constant
    TABLE_CELL_PADDING: int = 2
    """Padding in pixels for table cells (rows and headers)."""
    
    # Derived dimensions
    @classproperty
    def TABLE_ROW_HEIGHT(cls) -> int:
        """Get table row height based on actual font metrics.
        
        Uses QFontMetrics to get the actual rendered height of the font
        and adds appropriate padding for comfortable reading.
        
        Returns:
            Row height in pixels (font metrics height + TABLE_CELL_PADDING).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(cls.LOG_FONT)
        return metrics.height() + cls.TABLE_CELL_PADDING
    
    @classproperty
    def TABLE_HEADER_HEIGHT(cls) -> int:
        """Get table header height based on actual font metrics.
        
        Uses QFontMetrics to get the actual rendered height of the font
        and adds appropriate padding for comfortable reading.
        
        Returns:
            Header height in pixels (font metrics height + TABLE_CELL_PADDING).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(cls.UI_FONT)
        return metrics.height() + cls.TABLE_CELL_PADDING