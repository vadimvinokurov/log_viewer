"""Typography system for the Log Viewer application.

Uses Qt's system default fonts instead of hardcoded font families and sizes.
Ensures native look-and-feel on all platforms (macOS, Windows, Linux).
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


class _CachedFont:
    """Descriptor for lazy font initialization.

    Fonts are created on first access, not at import time.
    This ensures QApplication is initialized before font detection.
    """

    def __init__(self, font_getter):
        self.font_getter = font_getter
        self._font: QFont | None = None

    def __get__(self, obj, objtype=None) -> QFont:
        if self._font is None:
            self._font = self.font_getter()
        return self._font


class classproperty:
    """Descriptor for class-level properties."""

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, obj, objtype=None):
        return self.getter(objtype)


class SystemFonts:
    """Qt-based system font detection."""

    @staticmethod
    def get_ui_font() -> QFont:
        """Get system default UI font."""
        if QApplication.instance():
            return QApplication.font()
        return QFont()

    @staticmethod
    def get_monospace_font() -> QFont:
        """Get system default monospace font with UI font size."""
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        ui_font = SystemFonts.get_ui_font()
        font.setPointSize(max(ui_font.pointSize() - 1, 9))
        return font


class Typography:
    """Typography constants using Qt system fonts."""

    # System fonts (QFont instances) - lazy initialization
    UI_FONT: QFont = _CachedFont(SystemFonts.get_ui_font)
    """System default UI font. Use for all UI text."""

    LOG_FONT: QFont = _CachedFont(SystemFonts.get_monospace_font)
    """System monospace font. Use for log entries."""

    # Font family strings (for QSS stylesheets)
    @classproperty
    def PRIMARY(cls) -> str:
        """Get UI font family as string for QSS."""
        return f'"{cls.UI_FONT.family()}"'

    @classproperty
    def MONOSPACE(cls) -> str:
        """Get monospace font family as string for QSS."""
        return f'"{cls.LOG_FONT.family()}"'

    # Font size (from system)
    @classproperty
    def BODY_SIZE(cls) -> int:
        """Get system default font size in points."""
        return cls.UI_FONT.pointSize()

    # Cell padding constant
    TABLE_CELL_PADDING: int = 0
    """Padding in pixels for table cells."""

    @classproperty
    def TABLE_ROW_HEIGHT(cls) -> int:
        """Compact row height — tighter than font metrics."""
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(cls.LOG_FONT)
        return metrics.tightBoundingRect("Ag").height() + 3

    @classproperty
    def TABLE_HEADER_HEIGHT(cls) -> int:
        """Header height based on font metrics + padding."""
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(cls.UI_FONT)
        return metrics.height() + cls.TABLE_CELL_PADDING
