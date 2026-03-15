# Typography System Specification

**Version:** 2.1
**Last Updated:** 2026-03-15
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** v2.1 (APPROVED)

---

## §1 Overview

This specification defines a simplified typography system that uses Qt's system default fonts instead of hardcoded font families and sizes. This approach ensures native look-and-feel on all platforms without manual font selection.

### §1.1 Problem Statement

Previous implementation (v1.x) had:
- Hardcoded font families (SF Pro Text, Segoe UI)
- Hardcoded font sizes with platform-specific offsets
- Multiple type scales (BODY, HEADER, SMALL)
- Manual maintenance required for each platform

This created inconsistency and maintenance overhead.

### §1.2 Goals

1. **System Native**: Use Qt's system default fonts for native look-and-feel
2. **Automatic Sizing**: Let the OS determine appropriate font size
3. **Simplified API**: Single font size for all UI text
4. **Monospace for Logs**: Preserve monospace font for log entries
5. **Zero Maintenance**: No platform-specific code required

### §1.3 Non-Goals

- Custom font sizes for headers or tooltips (use system default)
- Font weight variations (use system default weight)
- Manual font family selection (delegate to Qt)

---

## §2 Architecture

### §2.1 Module Structure

```
src/constants/
├── typography.py    # System fonts + monospace
├── dimensions.py    # Imports TABLE_ROW_HEIGHT from typography
├── colors.py        # Unchanged
└── app_constants.py # Unchanged
```

### §2.2 Dependencies

```
typography.py
    ↓ (imported by)
├── stylesheet.py    # Uses Typography.PRIMARY, Typography.MONOSPACE
├── dimensions.py    # Uses Typography.TABLE_ROW_HEIGHT
└── log_table_view.py # Uses Typography.LOG_FONT
```

---

## §3 Typography Module Specification

### §3.1 System Font Detection

```python
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

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
```

**Font Selection Table:**

| Platform | UI Font | Monospace Font | Size Source |
|----------|---------|----------------|--------------|
| macOS | SF Pro Text | Menlo | System Preferences |
| Windows | Segoe UI | Consolas | Display Settings |
| Linux | Sans Serif | Monospace | Desktop Environment |

### §3.2 Typography Constants

```python
class Typography:
    """Simplified typography constants.
    
    Uses Qt's system fonts instead of hardcoded values.
    All UI text uses the same font family and size.
    Log entries use monospace font.
    
    Ref: docs/specs/features/typography-system.md §3.2
    """
    
    # System fonts (QFont instances)
    UI_FONT: QFont = SystemFonts.get_ui_font()
    """System default UI font. Use for all UI text."""
    
    LOG_FONT: QFont = SystemFonts.get_monospace_font()
    """System monospace font. Use for log entries."""
    
    # Font family strings (for QSS stylesheets)
    @classmethod
    @property
    def PRIMARY(cls) -> str:
        """Get UI font family as string for QSS.
        
        Returns:
            Font family string (e.g., '"SF Pro Text"', 'Segoe UI').
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return f'"{cls.UI_FONT.family()}"'
    
    @classmethod
    @property
    def MONOSPACE(cls) -> str:
        """Get monospace font family as string for QSS.
        
        Returns:
            Font family string (e.g., '"Menlo"', 'Consolas').
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return f'"{cls.LOG_FONT.family()}"'
    
    # Font size (from system)
    @classmethod
    @property
    def BODY_SIZE(cls) -> int:
        """Get system default font size in points.
        
        Returns:
            Font size in points (determined by system settings).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        return cls.UI_FONT.pointSize()
    
    # Convenience aliases
    BODY: int = BODY_SIZE  # Same as BODY_SIZE
    LOG_ENTRY: int = BODY_SIZE  # Same as BODY_SIZE
    
    # Derived dimensions
    @classmethod
    @property
    def TABLE_ROW_HEIGHT(cls) -> int:
        """Get table row height based on actual font metrics.
        
        Uses QFontMetrics to get the actual rendered height of the font
        and adds appropriate padding for comfortable reading.
        
        Returns:
            Row height in pixels (font metrics height + 12px padding).
        
        Ref: docs/specs/features/typography-system.md §3.2
        """
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(cls.LOG_FONT)
        return metrics.height() + 12
    
    TABLE_HEADER_HEIGHT: int = 20
    """Table header height (fixed at 20px)."""
```

**Key Differences from v1.x:**

| Aspect | v1.x | v2.0 |
|--------|------|------|
| Font Family | Hardcoded per platform | Qt system font |
| Font Size | Hardcoded (9/12pt) | System default |
| Type Scales | BODY/HEADER/SMALL | Single size |
| Platform Code | Manual detection | Qt handles it |
| Maintenance | Update for each OS | Zero maintenance |

---

## §4 Integration Changes

### §4.1 stylesheet.py Changes

**Before (v1.x):**
```python
from src.constants.typography import Typography

font_family = Typography.PRIMARY
font_size = Typography.BODY

return f"""
    QWidget {{
        font-family: {font_family};
        font-size: {font_size}pt;
        color: #333333;
    }}
"""
```

**After (v2.0):**
```python
from src.constants.typography import Typography

# Use system font - no need to specify size
# Qt will use the application font automatically

return f"""
    QWidget {{
        font-family: {Typography.PRIMARY};
        color: #333333;
    }}
"""
```

**Note:** Font size is no longer specified in QSS. Qt uses the system default size automatically.

### §4.2 log_table_view.py Changes

**Before (v1.x):**
```python
from src.constants.typography import Typography

self._monospace_font = QFont(
    Typography.MONOSPACE.replace('"', ''),
    Typography.LOG_ENTRY
)
```

**After (v2.0):**
```python
from src.constants.typography import Typography

self._monospace_font = Typography.LOG_FONT
```

### §4.3 dimensions.py Changes

**Before (v1.x):**
```python
from src.constants.typography import Typography

TABLE_ROW_HEIGHT: int = Typography.TABLE_ROW_HEIGHT
```

**After (v2.0):**
```python
from src.constants.typography import Typography

# TABLE_ROW_HEIGHT is now dynamic (computed at runtime)
def get_table_row_height() -> int:
    """Get table row height based on actual font metrics.
    
    Returns:
        Row height in pixels (font metrics height + 12px padding).
    """
    from PySide6.QtGui import QFontMetrics
    metrics = QFontMetrics(Typography.LOG_FONT)
    return metrics.height() + 12

# Module-level constant computed at import time
TABLE_ROW_HEIGHT: int = get_table_row_height()
```

---

## §5 API Reference

### §5.1 Public API

```python
from src.constants.typography import Typography

# System fonts (QFont instances)
Typography.UI_FONT      # System default UI font (QFont)
Typography.LOG_FONT    # System monospace font (QFont)

# Font family strings (for QSS)
Typography.PRIMARY     # UI font family string
Typography.MONOSPACE   # Monospace font family string

# Font size (from system)
Typography.BODY_SIZE   # System default font size (int)
Typography.BODY        # Alias for BODY_SIZE
Typography.LOG_ENTRY   # Alias for BODY_SIZE

# Derived dimensions
Typography.TABLE_ROW_HEIGHT    # Row height (font metrics height + 12)
Typography.TABLE_HEADER_HEIGHT # Header height (20px)
```

### §5.2 Internal API

```python
from src.constants.typography import SystemFonts

# System font detection
SystemFonts.get_ui_font()         # Returns QFont
SystemFonts.get_monospace_font()  # Returns QFont
```

---

## §6 Testing Requirements

### §6.1 Unit Tests

```python
# tests/test_typography.py

def test_ui_font_is_system_default():
    """UI font should be Qt's default application font."""
    from PySide6.QtWidgets import QApplication
    from src.constants.typography import Typography
    
    app_font = QApplication.font()
    assert Typography.UI_FONT.family() == app_font.family()
    assert Typography.UI_FONT.pointSize() == app_font.pointSize()

def test_monospace_font_is_system_fixed():
    """Monospace font should be Qt's fixed font."""
    from PySide6.QtGui import QFontDatabase
    from src.constants.typography import Typography
    
    fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    assert Typography.LOG_FONT.family() == fixed_font.family()

def test_font_size_matches_system():
    """Font size should match system default."""
    from PySide6.QtWidgets import QApplication
    from src.constants.typography import Typography
    
    app_font = QApplication.font()
    assert Typography.BODY_SIZE == app_font.pointSize()

def test_table_row_height_derived():
    """Row height should be derived from font metrics."""
    from PySide6.QtGui import QFontMetrics
    from src.constants.typography import Typography
    
    metrics = QFontMetrics(Typography.LOG_FONT)
    expected_height = metrics.height() + 12
    assert Typography.TABLE_ROW_HEIGHT == expected_height

def test_primary_font_family():
    """PRIMARY should return font family string."""
    from src.constants.typography import Typography
    
    family = Typography.PRIMARY
    assert isinstance(family, str)
    assert family.startswith('"')
    assert family.endswith('"')

def test_monospace_font_family():
    """MONOSPACE should return monospace family string."""
    from src.constants.typography import Typography
    
    family = Typography.MONOSPACE
    assert isinstance(family, str)
    assert family.startswith('"')
    assert family.endswith('"')
```

### §6.2 Integration Tests

```python
def test_stylesheet_uses_system_font():
    """Stylesheet should use system font family."""
    from src.styles.stylesheet import get_application_stylesheet
    from src.constants.typography import Typography
    
    style = get_application_stylesheet()
    # Should contain font family
    assert Typography.PRIMARY in style
    # Font size should NOT be hardcoded
    assert "font-size:" not in style

def test_log_table_uses_monospace():
    """Log table should use monospace font."""
    from src.styles.stylesheet import get_table_stylesheet
    from src.constants.typography import Typography
    
    style = get_table_stylesheet()
    # Should contain monospace font family
    assert Typography.MONOSPACE in style
```

---

## §7 Migration Checklist

- [ ] Update `src/constants/typography.py` to use Qt system fonts
- [ ] Update `src/constants/dimensions.py` to use dynamic row height
- [ ] Update `src/styles/stylesheet.py` to remove font-size from QSS
- [ ] Update `src/views/log_table_view.py` to use `Typography.LOG_FONT`
- [ ] Update `tests/test_typography.py` for new API
- [ ] Update `tests/test_stylesheet.py` for new behavior
- [ ] Update `docs/specs/features/ui-design-system.md` to reference v2.0
- [ ] Remove all deprecated FontFamily and TypeScale classes

---

## §8 Cross-References

- **UI Design System:** [ui-design-system.md](ui-design-system.md) §2.2 Typography
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)
- **Stylesheet:** [src/styles/stylesheet.py](../../src/styles/stylesheet.py)
- **Qt Documentation:** https://doc.qt.io/qt-6/qfont.html

---

## §9 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 2.1 | 2026-03-15 | Use QFontMetrics.height() for accurate row height calculation |
| 2.0.1 | 2026-03-15 | Fixed row height padding from 7px to 18px for proper text display |
| 2.0 | 2026-03-15 | Simplified to use Qt system fonts, removed platform-specific code |