# Typography System Implementation Plan

**Version:** 1.0
**Created:** 2026-03-15
**Status:** READY FOR IMPLEMENTATION
**Spec Reference:** [docs/specs/features/typography-system.md](../docs/specs/features/typography-system.md)

---

## Executive Summary

This plan implements a unified typography system that serves as the single source of truth for all font-related settings in the Log Viewer application. The implementation consolidates scattered font logic into a dedicated `typography.py` module.

### Problem Statement

Current implementation has font logic scattered across multiple files:
- [`get_font_family()`](../src/styles/stylesheet.py:13) in `stylesheet.py`
- [`get_monospace_font_family()`](../src/styles/stylesheet.py:27) in `stylesheet.py`
- [`get_log_font_size()`](../src/styles/stylesheet.py:41) in `stylesheet.py`
- [`TABLE_ROW_HEIGHT`](../src/constants/dimensions.py:13) in `dimensions.py` (platform-specific calculation)

This led to bugs where font size was computed but not properly applied in global stylesheet.

### Solution

Create a unified `Typography` class in `src/constants/typography.py` that:
1. Provides platform-aware font families
2. Defines a type scale with platform-specific sizes
3. Computes derived dimensions (row heights) from font sizes
4. Serves as the single source of truth for all typography

---

## Task Breakdown

### Task T-001: Create typography.py Module

**Status:** PENDING
**Priority:** HIGH (blocking other tasks)
**Estimated Effort:** 1 hour

#### 📦 TASK DELEGATION
├─ **Task ID:** T-001
├─ **Spec Reference:** §3 in [typography-system.md](../docs/specs/features/typography-system.md)
├─ **Master Constraints:** [SPEC.md](../docs/SPEC.md) §4.1 (Code Style)
├─ **Project Context:** Engine Core / Constants
├─ **Scope:** Create new file `src/constants/typography.py`
├─ **Language:** Python 3.12
├─ **Input/Output:** 
│  • Input: None (new module)
│  • Output: Module with `Platform`, `FontFamily`, `TypeScale`, `Typography` classes
├─ **Constraints:**
│  • Thread context: Main thread (constants module, no threading)
│  • Memory: Static class attributes only, no heap allocation
│  • Performance: O(1) access, computed at module load time
├─ **Tests Required:** Unit tests in `tests/test_typography.py` (Task T-005)
└─ **Dependencies:** None (first task)

#### Implementation Details

Create `src/constants/typography.py` with:

```python
"""Unified typography constants for the Log Viewer application.

This module provides a single source of truth for all font-related settings,
including font families, type scales, and derived dimensions.

Ref: docs/specs/features/typography-system.md
"""
from __future__ import annotations

import sys
from beartype import beartype


class Platform:
    """Platform detection constants.
    
    Ref: docs/specs/features/typography-system.md §3.1
    """
    IS_MACOS: bool = sys.platform == "darwin"
    IS_WINDOWS: bool = sys.platform == "win32"
    IS_LINUX: bool = sys.platform.startswith("linux")


class FontFamily:
    """Font family stacks for different contexts.
    
    Ref: docs/specs/features/ui-design-system.md §2.2.1
    Ref: docs/specs/features/typography-system.md §3.2
    """
    # Primary UI font
    MACOS_PRIMARY: str = '"SF Pro Text", "Helvetica Neue", Arial, sans-serif'
    WINDOWS_PRIMARY: str = '"Segoe UI", "Roboto", Arial, sans-serif'
    
    # Monospace font for code/logs
    MACOS_MONOSPACE: str = '"Menlo", "Monaco", "Courier New", monospace'
    WINDOWS_MONOSPACE: str = '"Consolas", "Courier New", monospace'
    
    @classmethod
    @beartype
    def get_primary(cls) -> str:
        """Get primary font family for current platform."""
        return cls.MACOS_PRIMARY if Platform.IS_MACOS else cls.WINDOWS_PRIMARY
    
    @classmethod
    @beartype
    def get_monospace(cls) -> str:
        """Get monospace font family for current platform."""
        return cls.MACOS_MONOSPACE if Platform.IS_MACOS else cls.WINDOWS_MONOSPACE


class TypeScale:
    """Type scale with platform-aware sizes.
    
    Ref: docs/specs/features/ui-design-system.md §2.2.2
    Ref: docs/specs/features/typography-system.md §3.3
    
    macOS uses +2pt for better readability on Retina displays.
    """
    # Base sizes (in points)
    BODY_BASE: int = 9      # Windows/Linux base
    HEADER_BASE: int = 11   # Windows/Linux header
    SMALL_BASE: int = 8     # Windows/Linux small
    
    # macOS offset
    MACOS_OFFSET: int = 2
    
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


class Typography:
    """Unified typography constants.
    
    Single source of truth for all font-related settings.
    Import from this class, not from FontFamily or TypeScale directly.
    
    Ref: docs/specs/features/typography-system.md §3.4
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

#### Acceptance Criteria

- [ ] File created at `src/constants/typography.py`
- [ ] All four classes implemented: `Platform`, `FontFamily`, `TypeScale`, `Typography`
- [ ] `@beartype` decorator on all public methods
- [ ] `from __future__ import annotations` at top of file
- [ ] Docstrings reference spec sections
- [ ] Platform detection matches spec §3.1
- [ ] Font families match spec §3.2 and ui-design-system.md §2.2.1
- [ ] Type scale matches spec §3.3 and ui-design-system.md §2.2.2
- [ ] Typography class matches spec §3.4

---

### Task T-002: Update dimensions.py

**Status:** PENDING
**Priority:** HIGH
**Estimated Effort:** 15 minutes
**Depends on:** T-001

#### 📦 TASK DELEGATION
├─ **Task ID:** T-002
├─ **Spec Reference:** §4.2 in [typography-system.md](../docs/specs/features/typography-system.md)
├─ **Master Constraints:** [SPEC.md](../docs/SPEC.md) §4.1 (Code Style)
├─ **Project Context:** Engine Core / Constants
├─ **Scope:** Modify `src/constants/dimensions.py`
├─ **Language:** Python 3.12
├─ **Input/Output:**
│  • Input: Current `dimensions.py` with platform-specific `TABLE_ROW_HEIGHT`
│  • Output: `dimensions.py` importing from `Typography`
├─ **Constraints:**
│  • Thread context: Main thread (constants module)
│  • Memory: No change in memory pattern
│  • Performance: No runtime impact
├─ **Tests Required:** Integration test in `tests/test_typography.py`
└─ **Dependencies:** T-001 (typography.py must exist)

#### Implementation Details

**Before (current):**
```python
import sys

if sys.platform == "darwin":
    TABLE_ROW_HEIGHT: int = 18
else:
    TABLE_ROW_HEIGHT: int = 16
```

**After (target):**
```python
from src.constants.typography import Typography

TABLE_ROW_HEIGHT: int = Typography.TABLE_ROW_HEIGHT
TABLE_HEADER_HEIGHT: int = Typography.TABLE_HEADER_HEIGHT
```

#### Changes Required

1. Remove `import sys` (no longer needed)
2. Add `from src.constants.typography import Typography`
3. Replace platform-specific `TABLE_ROW_HEIGHT` calculation with import from `Typography`
4. Add `TABLE_HEADER_HEIGHT` import from `Typography` (for consistency)
5. Update docstrings to reference typography module

#### Acceptance Criteria

- [ ] `import sys` removed
- [ ] `from src.constants.typography import Typography` added
- [ ] `TABLE_ROW_HEIGHT` uses `Typography.TABLE_ROW_HEIGHT`
- [ ] `TABLE_HEADER_HEIGHT` uses `Typography.TABLE_HEADER_HEIGHT`
- [ ] Docstrings updated to reference typography module
- [ ] No other changes to dimensions.py

---

### Task T-003: Update stylesheet.py

**Status:** PENDING
**Priority:** HIGH
**Estimated Effort:** 30 minutes
**Depends on:** T-001

#### 📦 TASK DELEGATION
├─ **Task ID:** T-003
├─ **Spec Reference:** §4.1 in [typography-system.md](../docs/specs/features/typography-system.md)
├─ **Master Constraints:** [SPEC.md](../docs/SPEC.md) §4.1 (Code Style)
├─ **Project Context:** UI Layer / Styles
├─ **Scope:** Modify `src/styles/stylesheet.py`
├─ **Language:** Python 3.12
├─ **Input/Output:**
│  • Input: Current `stylesheet.py` with `get_font_family()`, `get_monospace_font_family()`, `get_log_font_size()`
│  • Output: `stylesheet.py` using `Typography` constants
├─ **Constraints:**
│  • Thread context: Main thread (stylesheet generation)
│  • Memory: No change in memory pattern
│  • Performance: No runtime impact (constants computed at load time)
├─ **Tests Required:** Integration test in `tests/test_typography.py`, existing `tests/test_stylesheet.py`
└─ **Dependencies:** T-001 (typography.py must exist)

#### Implementation Details

**Before (current):**
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

**After (target):**
```python
from src.constants.typography import Typography

# Use Typography.PRIMARY instead of get_font_family()
# Use Typography.MONOSPACE instead of get_monospace_font_family()
# Use Typography.BODY instead of get_log_font_size()
```

#### Changes Required

1. Add `from src.constants.typography import Typography` import
2. In `get_application_stylesheet()`:
   - Replace `font_family = get_font_family()` with `font_family = Typography.PRIMARY`
   - Replace `font_size = get_log_font_size()` with `font_size = Typography.BODY`
3. In `get_table_stylesheet()`:
   - Replace `monospace_font = get_monospace_font_family()` with `monospace_font = Typography.MONOSPACE`
   - Replace `font_size = get_log_font_size()` with `font_size = Typography.LOG_ENTRY`
4. **Keep** the deprecated functions for backward compatibility during transition (mark with deprecation warning)
5. Update docstrings to reference typography module

#### Deprecation Strategy

Mark old functions as deprecated but keep them for backward compatibility:

```python
import warnings

def get_font_family() -> str:
    """Get the appropriate font family for the current platform.
    
    .. deprecated:: 1.1
        Use Typography.PRIMARY instead.
    """
    warnings.warn(
        "get_font_family() is deprecated. Use Typography.PRIMARY instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return Typography.PRIMARY
```

#### Acceptance Criteria

- [ ] `from src.constants.typography import Typography` added
- [ ] `get_application_stylesheet()` uses `Typography.PRIMARY` and `Typography.BODY`
- [ ] `get_table_stylesheet()` uses `Typography.MONOSPACE` and `Typography.LOG_ENTRY`
- [ ] Deprecated functions marked with `DeprecationWarning`
- [ ] Docstrings updated to reference typography module
- [ ] Existing tests in `tests/test_stylesheet.py` still pass

---

### Task T-004: Update log_table_view.py

**Status:** PENDING
**Priority:** HIGH
**Estimated Effort:** 15 minutes
**Depends on:** T-001

#### 📦 TASK DELEGATION
├─ **Task ID:** T-004
├─ **Spec Reference:** §4.3 in [typography-system.md](../docs/specs/features/typography-system.md)
├─ **Master Constraints:** [SPEC.md](../docs/SPEC.md) §4.1 (Code Style)
├─ **Project Context:** UI Layer / Views
├─ **Scope:** Modify `src/views/log_table_view.py`
├─ **Language:** Python 3.12
├─ **Input/Output:**
│  • Input: Current `log_table_view.py` importing from `stylesheet.py`
│  • Output: `log_table_view.py` using `Typography` constants
├─ **Constraints:**
│  • Thread context: Main thread (Qt UI)
│  • Memory: QFont created once in model constructor
│  • Performance: No runtime impact
├─ **Tests Required:** Existing tests should pass
└─ **Dependencies:** T-001 (typography.py must exist)

#### Implementation Details

**Before (current):**
```python
from src.styles.stylesheet import get_table_stylesheet, get_monospace_font_family, get_log_font_size

# In LogTableModel.__init__:
self._monospace_font = QFont(
    get_monospace_font_family().replace('"', ''),
    get_log_font_size()
)
```

**After (target):**
```python
from src.constants.typography import Typography

# In LogTableModel.__init__:
self._monospace_font = QFont(
    Typography.MONOSPACE.replace('"', ''),
    Typography.LOG_ENTRY
)
```

#### Changes Required

1. Add `from src.constants.typography import Typography` import
2. Remove `get_monospace_font_family, get_log_font_size` from `stylesheet` import
3. In `LogTableModel.__init__()`:
   - Replace `get_monospace_font_family().replace('"', '')` with `Typography.MONOSPACE.replace('"', '')`
   - Replace `get_log_font_size()` with `Typography.LOG_ENTRY`
4. Update docstrings to reference typography module

#### Acceptance Criteria

- [ ] `from src.constants.typography import Typography` added
- [ ] `get_monospace_font_family, get_log_font_size` removed from stylesheet import
- [ ] `LogTableModel._monospace_font` uses `Typography.MONOSPACE` and `Typography.LOG_ENTRY`
- [ ] Docstrings updated to reference typography module
- [ ] No other changes to log_table_view.py

---

### Task T-005: Create Typography Unit Tests

**Status:** PENDING
**Priority:** HIGH
**Estimated Effort:** 45 minutes
**Depends on:** T-001, T-002, T-003, T-004

#### 📦 TASK DELEGATION
├─ **Task ID:** T-005
├─ **Spec Reference:** §6 in [typography-system.md](../docs/specs/features/typography-system.md)
├─ **Master Constraints:** [SPEC.md](../docs/SPEC.md) §8 (Testing Requirements)
├─ **Project Context:** Tests
├─ **Scope:** Create `tests/test_typography.py`
├─ **Language:** Python 3.12
├─ **Input/Output:**
│  • Input: Typography module implementation
│  • Output: Unit tests for typography module
├─ **Constraints:**
│  • Thread context: Main thread (tests)
│  • Memory: Standard test fixtures
│  • Performance: Tests should run in < 1 second
├─ **Tests Required:** N/A (this IS the test task)
└─ **Dependencies:** T-001, T-002, T-003, T-004 (all implementation tasks)

#### Test Cases Required

Per spec §6.1 and §6.2:

```python
"""Unit tests for typography module.

Ref: docs/specs/features/typography-system.md §6
"""
from __future__ import annotations

import sys
import pytest
from src.constants.typography import Platform, FontFamily, TypeScale, Typography
from src.constants.dimensions import TABLE_ROW_HEIGHT, TABLE_HEADER_HEIGHT


class TestPlatform:
    """Tests for Platform class."""
    
    def test_platform_detection(self):
        """Platform detection should work correctly."""
        assert Platform.IS_MACOS == (sys.platform == "darwin")
        assert Platform.IS_WINDOWS == (sys.platform == "win32")
        assert Platform.IS_LINUX == sys.platform.startswith("linux")
    
    def test_platform_exclusivity(self):
        """Only one platform should be True (except Linux variants)."""
        # At most one of macOS or Windows should be True
        assert not (Platform.IS_MACOS and Platform.IS_WINDOWS)


class TestFontFamily:
    """Tests for FontFamily class."""
    
    def test_get_primary_returns_string(self):
        """get_primary should return a string."""
        result = FontFamily.get_primary()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_monospace_returns_string(self):
        """get_monospace should return a string."""
        result = FontFamily.get_monospace()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_font_family_selection(self):
        """Font family should match platform."""
        if Platform.IS_MACOS:
            assert "SF Pro Text" in Typography.PRIMARY
            assert "Menlo" in Typography.MONOSPACE
        else:
            assert "Segoe UI" in Typography.PRIMARY
            assert "Consolas" in Typography.MONOSPACE


class TestTypeScale:
    """Tests for TypeScale class."""
    
    def test_type_scale_sizes(self):
        """Type scale should be platform-appropriate."""
        if Platform.IS_MACOS:
            assert TypeScale.BODY == 11
            assert TypeScale.HEADER == 13
            assert TypeScale.SMALL == 10
        else:
            assert TypeScale.BODY == 9
            assert TypeScale.HEADER == 11
            assert TypeScale.SMALL == 8
    
    def test_type_scale_aliases(self):
        """Type scale aliases should match base sizes."""
        assert TypeScale.BODY_SIZE == TypeScale.BODY
        assert TypeScale.HEADER_SIZE == TypeScale.HEADER
        assert TypeScale.SMALL_SIZE == TypeScale.SMALL
        assert TypeScale.TABLE_HEADER_SIZE == TypeScale.BODY
        assert TypeScale.LOG_ENTRY_SIZE == TypeScale.BODY


class TestTypography:
    """Tests for Typography class."""
    
    def test_primary_font(self):
        """PRIMARY should be a valid font family string."""
        assert isinstance(Typography.PRIMARY, str)
        assert len(Typography.PRIMARY) > 0
    
    def test_monospace_font(self):
        """MONOSPACE should be a valid font family string."""
        assert isinstance(Typography.MONOSPACE, str)
        assert len(Typography.MONOSPACE) > 0
    
    def test_body_size(self):
        """BODY should match TypeScale.BODY."""
        assert Typography.BODY == TypeScale.BODY
    
    def test_header_size(self):
        """HEADER should match TypeScale.HEADER."""
        assert Typography.HEADER == TypeScale.HEADER
    
    def test_small_size(self):
        """SMALL should match TypeScale.SMALL."""
        assert Typography.SMALL == TypeScale.SMALL
    
    def test_log_entry_size(self):
        """LOG_ENTRY should match TypeScale.LOG_ENTRY_SIZE."""
        assert Typography.LOG_ENTRY == TypeScale.LOG_ENTRY_SIZE
    
    def test_table_row_height(self):
        """Row height should be derived from font size."""
        assert Typography.TABLE_ROW_HEIGHT == Typography.BODY + 7
        if Platform.IS_MACOS:
            assert Typography.TABLE_ROW_HEIGHT == 18
        else:
            assert Typography.TABLE_ROW_HEIGHT == 16
    
    def test_table_header_height(self):
        """Header height should be fixed at 20."""
        assert Typography.TABLE_HEADER_HEIGHT == 20


class TestDimensionsIntegration:
    """Integration tests for dimensions.py using Typography."""
    
    def test_dimensions_uses_typography(self):
        """Dimensions should use Typography constants."""
        assert TABLE_ROW_HEIGHT == Typography.TABLE_ROW_HEIGHT
        assert TABLE_HEADER_HEIGHT == Typography.TABLE_HEADER_HEIGHT


class TestStylesheetIntegration:
    """Integration tests for stylesheet.py using Typography."""
    
    def test_stylesheet_uses_typography(self):
        """Stylesheet should use Typography constants."""
        from src.styles.stylesheet import get_application_stylesheet
        style = get_application_stylesheet()
        
        # Check that font size is present
        if Platform.IS_MACOS:
            assert "11pt" in style
        else:
            assert "9pt" in style
```

#### Acceptance Criteria

- [ ] File created at `tests/test_typography.py`
- [ ] All test classes implemented: `TestPlatform`, `TestFontFamily`, `TestTypeScale`, `TestTypography`, `TestDimensionsIntegration`, `TestStylesheetIntegration`
- [ ] All tests pass with `pytest tests/test_typography.py`
- [ ] Test coverage matches spec §6.1 and §6.2
- [ ] Tests use `@beartype` where appropriate

---

## Dependency Graph

```
T-001 (typography.py)
    ├── T-002 (dimensions.py) ──┐
    ├── T-003 (stylesheet.py) ──┼── T-005 (tests)
    └── T-004 (log_table_view.py) ──┘
```

**Execution Order:**
1. T-001 (Create typography.py) - MUST complete first
2. T-002, T-003, T-004 can run in parallel after T-001
3. T-005 (Tests) runs after all implementation tasks

---

## Migration Checklist (from spec §7)

- [ ] Create `src/constants/typography.py` (T-001)
- [ ] Update `src/constants/dimensions.py` to import from typography (T-002)
- [ ] Update `src/styles/stylesheet.py` to use Typography constants (T-003)
- [ ] Update `src/views/log_table_view.py` to use Typography constants (T-004)
- [ ] Create `tests/test_typography.py` (T-005)
- [ ] Update `docs/specs/features/ui-design-system.md` to reference typography module (post-implementation)
- [ ] Remove deprecated font functions from stylesheet.py (post-implementation, after audit)

---

## Cross-Spec Validation Checklist

When reviewing code, check compliance with:

- [ ] **Feature spec:** [typography-system.md](../docs/specs/features/typography-system.md) ✓
- [ ] **UI Design System:** [ui-design-system.md](../docs/specs/features/ui-design-system.md) §2.2 ✓
- [ ] **Global rules:** [memory-model.md](../docs/specs/global/memory-model.md) (static constants, no memory management needed) ✓
- [ ] **Global rules:** [threading.md](../docs/specs/global/threading.md) (main thread only) ✓
- [ ] **Master constraints:** [SPEC.md](../docs/SPEC.md) §4.1 (Code Style) ✓
- [ ] **Project conventions:** `src/constants/` patterns ✓

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Platform detection fails | Low | High | Fallback to Windows defaults |
| Font not available on system | Low | Low | Font stacks have fallbacks |
| Breaking existing code | Medium | Medium | Deprecation warnings, keep old functions |
| Test coverage gaps | Low | Medium | Comprehensive test plan in T-005 |

---

## Post-Implementation Tasks

1. **Documentation Update:** Update `docs/specs/features/ui-design-system.md` to reference the new typography module
2. **Deprecation Cleanup:** Remove deprecated functions from `stylesheet.py` after one release cycle
3. **Audit:** Trigger spec-auditor to verify implementation matches specification

---

## Sign-Off

**Plan Created By:** spec-orchestrator
**Plan Date:** 2026-03-15
**Ready For:** spec-coder implementation