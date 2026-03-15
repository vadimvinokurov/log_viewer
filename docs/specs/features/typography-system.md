# Typography System Specification

**Version:** 1.0
**Last Updated:** 2026-03-15
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** v1.0 (IMPLEMENTED)

---

## §1 Overview

This specification defines a unified typography system that serves as the single source of truth for all font-related settings in the Log Viewer application. The system ensures consistent font rendering across platforms and prevents issues where font sizes are calculated but not applied.

### §1.1 Problem Statement

Previous implementation had scattered font logic:
- `get_font_family()` in `stylesheet.py`
- `get_monospace_font_family()` in `stylesheet.py`
- `get_log_font_size()` in `stylesheet.py`
- `TABLE_ROW_HEIGHT` in `dimensions.py` (depends on font size)

This led to bugs where font size was computed but not used in global stylesheet.

### §1.2 Goals

1. **Single Source of Truth**: All typography constants in one module
2. **Platform-Aware**: Automatic adjustment for macOS vs Windows/Linux
3. **Type Scale**: Named sizes for different text contexts
4. **Derived Dimensions**: Row heights computed from font size
5. **Maintainability**: Easy to modify font settings in one place

---

## §2 Architecture

### §2.1 Module Structure

```
src/constants/
├── typography.py    # NEW: Single source of truth for fonts
├── dimensions.py    # Imports TABLE_ROW_HEIGHT from typography
├── colors.py        # Unchanged
└── app_constants.py # Unchanged
```

### §2.2 Dependencies

```
typography.py
    ↓ (imported by)
├── stylesheet.py    # Uses Typography.PRIMARY, Typography.BODY
├── dimensions.py    # Uses Typography.TABLE_ROW_HEIGHT
└── log_table_view.py # Uses Typography.MONOSPACE, Typography.LOG_ENTRY
```

---

## §3 Typography Module Specification

### §3.1 Platform Detection

```python
class Platform:
    """Platform detection constants."""
    IS_MACOS: bool = sys.platform == "darwin"
    IS_WINDOWS: bool = sys.platform == "win32"
    IS_LINUX: bool = sys.platform.startswith("linux")
```

**Rules:**
- `IS_MACOS`: True on macOS (darwin)
- `IS_WINDOWS`: True on Windows (win32)
- `IS_LINUX`: True on Linux (linux, linux2)

### §3.2 Font Families

```python
class FontFamily:
    """Font family stacks for different contexts.
    
    Ref: docs/specs/features/ui-design-system.md §2.2.1
    """
    # Primary UI font
    MACOS_PRIMARY: str = '"SF Pro Text", "Helvetica Neue", Arial, sans-serif'
    WINDOWS_PRIMARY: str = '"Segoe UI", "Roboto", Arial, sans-serif'
    
    # Monospace font for code/logs
    MACOS_MONOSPACE: str = '"Menlo", "Monaco", "Courier New", monospace'
    WINDOWS_MONOSPACE: str = '"Consolas", "Courier New", monospace'
    
    @classmethod
    def get_primary(cls) -> str:
        """Get primary font family for current platform."""
        return cls.MACOS_PRIMARY if Platform.IS_MACOS else cls.WINDOWS_PRIMARY
    
    @classmethod
    def get_monospace(cls) -> str:
        """Get monospace font family for current platform."""
        return cls.MACOS_MONOSPACE if Platform.IS_MACOS else cls.WINDOWS_MONOSPACE
```

**Font Stack Rationale:**
- **macOS Primary**: SF Pro Text is the native font, fallback to Helvetica Neue
- **Windows Primary**: Segoe UI is the native font, fallback to Roboto
- **macOS Monospace**: Menlo is the native code font, fallback to Monaco
- **Windows Monospace**: Consolas is the native code font

### §3.3 Type Scale

```python
class TypeScale:
    """Type scale with platform-aware sizes.
    
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    macOS uses +3pt for better readability on Retina displays.
    """
    # Base sizes (in points)
    BODY_BASE: int = 9      # Windows/Linux base
    HEADER_BASE: int = 11   # Windows/Linux header
    SMALL_BASE: int = 8     # Windows/Linux small
    
    # macOS offset
    MACOS_OFFSET: int = 3
    
    # Computed sizes
    BODY: int = BODY_BASE + (MACOS_OFFSET if Platform.IS_MACOS else 0)
    HEADER: int = HEADER_BASE + (MACOS_OFFSET if Platform.IS_MACOS else 0)
    SMALL: int = SMALL_BASE + (MACOS_OFFSET if Platform.IS_MACOS else 0)
    
    # Aliases for clarity
    BODY_SIZE: int = BODY
    HEADER_SIZE: int = HEADER
    SMALL_SIZE: int = SMALL
    TABLE_HEADER_SIZE: int = BODY
    LOG_ENTRY_SIZE: int = BODY
```

**Type Scale Table:**

| Name | Windows/Linux | macOS | Usage |
|------|---------------|-------|-------|
| BODY | 9pt | 12pt | Default text, labels, table content |
| HEADER | 11pt | 14pt | Dialog titles, section headers |
| SMALL | 8pt | 11pt | Tooltips, hints, secondary text |

### §3.4 Unified Typography Class

```python
class Typography:
    """Unified typography constants.
    
    Single source of truth for all font-related settings.
    Import from this class, not from FontFamily or TypeScale directly.
    """
    # Font families
    PRIMARY: str = FontFamily.get_primary()
    MONOSPACE: str = FontFamily.get_monospace()
    
    # Type scale (in points)
    BODY: int = TypeScale.BODY
    HEADER: int = TypeScale.HEADER
    SMALL: int = TypeScale.SMALL
    LOG_ENTRY: int = TypeScale.LOG_ENTRY_SIZE
    
    # Derived dimensions (in pixels)
    # Row height = font size + 7px padding
    TABLE_ROW_HEIGHT: int = TypeScale.BODY + 7  # 16px (9pt) or 18px (11pt)
    TABLE_HEADER_HEIGHT: int = 20
```

**Dimension Calculation:**
- `TABLE_ROW_HEIGHT = BODY + 7`
- 9pt font → 16px row height
- 12pt font → 19px row height

---

## §4 Integration Changes

### §4.1 stylesheet.py Changes

**Before:**
```python
def get_font_family() -> str:
    if sys.platform == "darwin":
        return '"SF Pro Text", "Helvetica Neue", Arial, sans-serif'
    else:
        return '"Segoe UI", "Roboto", Arial, sans-serif'

def get_monospace_font_family() -> str:
    if sys.platform == "darwin":
        return '"Menlo", "Monaco", "Courier New", monospace'
    else:
        return '"Consolas", "Courier New", monospace'

def get_log_font_size() -> int:
    if sys.platform == "darwin":
        return 11
    else:
        return 9
```

**After:**
```python
from src.constants.typography import Typography

# Use Typography.PRIMARY instead of get_font_family()
# Use Typography.MONOSPACE instead of get_monospace_font_family()
# Use Typography.BODY instead of get_log_font_size()
```

### §4.2 dimensions.py Changes

**Before:**
```python
import sys

if sys.platform == "darwin":
    TABLE_ROW_HEIGHT: int = 18
else:
    TABLE_ROW_HEIGHT: int = 16
```

**After:**
```python
from src.constants.typography import Typography

TABLE_ROW_HEIGHT: int = Typography.TABLE_ROW_HEIGHT
TABLE_HEADER_HEIGHT: int = Typography.TABLE_HEADER_HEIGHT
```

### §4.3 log_table_view.py Changes

**Before:**
```python
from src.styles.stylesheet import get_monospace_font_family, get_log_font_size

self._monospace_font = QFont(
    get_monospace_font_family().replace('"', ''),
    get_log_font_size()
)
```

**After:**
```python
from src.constants.typography import Typography

self._monospace_font = QFont(
    Typography.MONOSPACE.replace('"', ''),
    Typography.LOG_ENTRY
)
```

---

## §5 API Reference

### §5.1 Public API

```python
from src.constants.typography import Typography

# Font families
Typography.PRIMARY      # Primary UI font family (str)
Typography.MONOSPACE   # Monospace font family (str)

# Type scale (font sizes in points)
Typography.BODY        # Body text size (9 or 11)
Typography.HEADER      # Header text size (11 or 13)
Typography.SMALL       # Small text size (8 or 10)
Typography.LOG_ENTRY   # Log entry size (same as BODY)

# Derived dimensions (in pixels)
Typography.TABLE_ROW_HEIGHT    # Row height (16 or 18)
Typography.TABLE_HEADER_HEIGHT # Header height (20)
```

### §5.2 Internal API

```python
from src.constants.typography import Platform, FontFamily, TypeScale

# Platform detection
Platform.IS_MACOS   # bool
Platform.IS_WINDOWS # bool
Platform.IS_LINUX   # bool

# Font families
FontFamily.MACOS_PRIMARY    # str
FontFamily.WINDOWS_PRIMARY  # str
FontFamily.MACOS_MONOSPACE  # str
FontFamily.WINDOWS_MONOSPACE # str
FontFamily.get_primary()    # str
FontFamily.get_monospace()  # str

# Type scale
TypeScale.BODY      # int
TypeScale.HEADER    # int
TypeScale.SMALL     # int
```

---

## §6 Testing Requirements

### §6.1 Unit Tests

```python
# tests/test_typography.py

def test_platform_detection():
    """Platform detection should work correctly."""
    import sys
    assert Platform.IS_MACOS == (sys.platform == "darwin")
    assert Platform.IS_WINDOWS == (sys.platform == "win32")

def test_font_family_selection():
    """Font family should match platform."""
    if Platform.IS_MACOS:
        assert "SF Pro Text" in Typography.PRIMARY
        assert "Menlo" in Typography.MONOSPACE
    else:
        assert "Segoe UI" in Typography.PRIMARY
        assert "Consolas" in Typography.MONOSPACE

def test_type_scale_sizes():
    """Type scale should be platform-appropriate."""
    if Platform.IS_MACOS:
        assert Typography.BODY == 12
        assert Typography.HEADER == 14
        assert Typography.SMALL == 11
    else:
        assert Typography.BODY == 9
        assert Typography.HEADER == 11
        assert Typography.SMALL == 8

def test_table_row_height():
    """Row height should be derived from font size."""
    assert Typography.TABLE_ROW_HEIGHT == Typography.BODY + 7
    if Platform.IS_MACOS:
        assert Typography.TABLE_ROW_HEIGHT == 19
    else:
        assert Typography.TABLE_ROW_HEIGHT == 16
```

### §6.2 Integration Tests

```python
def test_stylesheet_uses_typography():
    """Stylesheet should use Typography constants."""
    from src.styles.stylesheet import get_application_stylesheet
    style = get_application_stylesheet()
    
    if Platform.IS_MACOS:
        assert "12pt" in style
    else:
        assert "9pt" in style

def test_dimensions_uses_typography():
    """Dimensions should use Typography constants."""
    from src.constants.dimensions import TABLE_ROW_HEIGHT
    assert TABLE_ROW_HEIGHT == Typography.TABLE_ROW_HEIGHT
```

---

## §7 Migration Checklist

- [x] Create `src/constants/typography.py`
- [x] Update `src/constants/dimensions.py` to import from typography
- [x] Update `src/styles/stylesheet.py` to use Typography constants
- [x] Update `src/views/log_table_view.py` to use Typography constants
- [x] Create `tests/test_typography.py`
- [ ] Update `docs/specs/features/ui-design-system.md` to reference typography module (optional)
- [x] Deprecate font functions in stylesheet.py (kept with DeprecationWarning)

---

## §8 Cross-References

- **UI Design System:** [ui-design-system.md](ui-design-system.md) §2.2 Typography
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)
- **Stylesheet:** [src/styles/stylesheet.py](../../src/styles/stylesheet.py)

---

## §9 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-15 | Changed macOS offset from +2pt to +3pt (BODY: 9→12pt, HEADER: 11→14pt, SMALL: 8→11pt) |
| 1.0 | 2026-03-15 | Initial specification for unified typography system |