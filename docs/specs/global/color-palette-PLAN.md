# Color Palette Refactoring Implementation Plan

**Version:** 1.0
**Last Updated:** 2026-03-19
**Status:** READY FOR IMPLEMENTATION
**Spec Reference:** [color-palette.md](color-palette.md)

---

## Overview

This plan breaks down the refactoring of the color system from the current implementation to the new layered architecture defined in [color-palette.md](color-palette.md).

### Current State

- [`src/constants/colors.py`](../../src/constants/colors.py) contains:
  - `LogTextColors` class (3 constants)
  - `LogIconColors` class (6 constants)
  - `StatsColors` class (18 constants)
  - Module-level legacy constants (9 constants)

### Target State

- Layered color architecture:
  - `BaseColors` class (base colors)
  - `PaletteColors` class (color families)
  - `UIColors` class (semantic colors)
  - `LogTextColors` class (log level text colors)
  - `LogIconColors` class (log level icon colors)
  - `StatsColors` class (statistics counter colors)
  - `ProcessColors` class (process identification colors)
  - `LogViewerColors` class (LogViewer-specific colors)
  - Legacy constants (backward compatibility)

---

## Task Breakdown

### Task 1: Refactor colors.py Core Structure

**Task ID:** T-001
**Spec Reference:** §8.1 File Organization
**Project Context:** src/constants/
**Language:** Python 3.10
**Scope:** [`src/constants/colors.py`](../../src/constants/colors.py)

**Input/Output:**
- Input: Current colors.py with legacy constants
- Output: New colors.py with layered architecture

**Constraints:**
- Maintain backward compatibility
- All existing imports must continue to work
- No breaking changes to existing code

**Implementation Steps:**

1. Add `BaseColors` class with:
   - `WHITE`, `BLACK`, `TRANSPARENT`
   - `GRAY_01` through `GRAY_05`
   - `ACCENT_01`, `ACCENT_02`, `ACCENT_03`

2. Add `PaletteColors` class with:
   - Gray family (5 levels)
   - Red family (5 levels)
   - Orange family (5 levels)
   - Green family (5 levels)
   - Cyan family (5 levels)
   - Blue family (4 levels)
   - Purple family (4 levels)

3. Add `UIColors` class with:
   - Background colors (7 constants)
   - Border colors (6 constants)
   - Text colors (6 constants)
   - Special colors (4 constants)

4. Keep existing classes:
   - `LogTextColors` (no changes)
   - `LogIconColors` (no changes)
   - `StatsColors` (no changes)

5. Add `ProcessColors` class with:
   - 6 process colors (BLUE, RED, ORANGE, PINK, GREEN, CREAM)
   - `get_color(index)` class method for cyclic assignment

6. Add `LogViewerColors` class with:
   - `LOG_ITEM_SELECTED`
   - `LOG_ITEM_BORDER_MOUSE_OVER`
   - `LOG_ITEM_TEXT_MOUSE_OVER`
   - `LOG_BORDER`
   - `AUTO_SCROLL_SELECTED`
   - `AUTO_SCROLL_MOUSE_OVER`
   - `CONTAINER_PANEL_HIGHLIGHTED`

7. Keep legacy constants at module level:
   - `TABLE_ROW_BACKGROUND`
   - `SELECTION_HIGHLIGHT_COLOR`
   - `FIND_HIGHLIGHT_COLOR`
   - `DEFAULT_TEXT_COLOR`
   - `SECONDARY_TEXT_COLOR`
   - `BORDER_COLOR`
   - `HEADER_BACKGROUND`
   - `PRIMARY_BLUE`
   - `BACKGROUND_HOVER`

**Tests Required:**
- Unit test: Verify all color constants have correct hex values
- Unit test: Verify `ProcessColors.get_color()` cyclic assignment
- Unit test: Verify legacy constants still accessible
- Unit test: Verify new classes are importable

**Dependencies:** None

---

### Task 2: Update stylesheet.py to Use New Constants

**Task ID:** T-002
**Spec Reference:** §10.3 QSS Integration
**Project Context:** src/styles/
**Language:** Python 3.10
**Scope:** [`src/styles/stylesheet.py`](../../src/styles/stylesheet.py)

**Input/Output:**
- Input: Current stylesheet with hardcoded colors
- Output: Stylesheet using new color constants

**Constraints:**
- No visual changes to UI
- All color values must remain the same
- Use semantic constants where possible

**Implementation Steps:**

1. Import new color classes:
   ```python
   from src.constants.colors import (
       UIColors,
       LogTextColors,
       StatsColors,
       PaletteColors
   )
   ```

2. Replace hardcoded colors in `get_application_stylesheet()`:
   - `#FFFFFF` → `UIColors.BACKGROUND_PRIMARY`
   - `#F5F5F5` → `UIColors.BACKGROUND_SECONDARY`
   - `#F0F0F0` → `UIColors.BACKGROUND_TERTIARY`
   - `#E8E8E8` → `UIColors.BACKGROUND_HOVER`
   - `#DCEBF7` → `UIColors.BACKGROUND_SELECTED`
   - `#C0C0C0` → `UIColors.BORDER_DEFAULT`
   - `#A0A0A0` → `UIColors.BORDER_HOVER`
   - `#0066CC` → `UIColors.BORDER_FOCUS`
   - `#333333` → `UIColors.TEXT_PRIMARY`
   - `#666666` → `UIColors.TEXT_SECONDARY`
   - `#999999` → `UIColors.TEXT_DISABLED`

3. Replace hardcoded colors in `get_table_stylesheet()`:
   - `#B6B6B6` → `PaletteColors.GRAY_2`
   - `#DCEBF7` → `UIColors.BACKGROUND_SELECTED`

4. Replace hardcoded colors in `get_tree_stylesheet()`:
   - `#F5F5F5` → `UIColors.BACKGROUND_SECONDARY`
   - `#E8E8E8` → `UIColors.BACKGROUND_HOVER`
   - `#DCEBF7` → `UIColors.BACKGROUND_SELECTED`

5. Replace hardcoded colors in `get_counter_style()`:
   - Use `StatsColors` constants for all counter colors

**Tests Required:**
- Visual regression test: Compare screenshots before/after
- Unit test: Verify stylesheet strings contain correct color values
- Integration test: Verify UI components render correctly

**Dependencies:** T-001 (colors.py refactoring)

---

### Task 3: Update View Components

**Task ID:** T-003
**Spec Reference:** §10.2 Color Application Patterns
**Project Context:** src/views/
**Language:** Python 3.10
**Scope:** Multiple view files

**Files to Update:**
- [`src/views/category_panel.py`](../../src/views/category_panel.py)
- [`src/views/log_table_view.py`](../../src/views/log_table_view.py)
- [`src/views/main_window.py`](../../src/views/main_window.py)
- [`src/views/components/counter_widget.py`](../../src/views/components/counter_widget.py)
- [`src/views/components/base_panel.py`](../../src/views/components/base_panel.py)
- [`src/views/delegates/highlight_delegate.py`](../../src/views/delegates/highlight_delegate.py)

**Input/Output:**
- Input: Components using hardcoded colors or legacy constants
- Output: Components using new semantic color constants

**Constraints:**
- No visual changes to UI
- Maintain backward compatibility during transition
- Use semantic constants (UIColors) for UI elements
- Use domain constants (LogTextColors, StatsColors) for domain-specific elements

**Implementation Steps:**

1. Update `category_panel.py`:
   - Replace `BACKGROUND_HOVER` → `UIColors.BACKGROUND_HOVER`
   - Replace `SELECTION_HIGHLIGHT_COLOR` → `UIColors.BACKGROUND_SELECTED`
   - Replace `BORDER_COLOR` → `UIColors.BORDER_DEFAULT`

2. Update `log_table_view.py`:
   - Replace `TABLE_ROW_BACKGROUND` → `PaletteColors.GRAY_2`
   - Replace `SELECTION_HIGHLIGHT_COLOR` → `UIColors.BACKGROUND_SELECTED`
   - Use `LogTextColors` for log level text colors

3. Update `main_window.py`:
   - Replace `PRIMARY_BLUE` → `UIColors.BORDER_FOCUS`
   - Replace `HEADER_BACKGROUND` → `UIColors.BACKGROUND_TERTIARY`

4. Update `counter_widget.py`:
   - Use `StatsColors` for all counter colors
   - Replace hardcoded hex values with constants

5. Update `base_panel.py`:
   - Replace `BACKGROUND_HOVER` → `UIColors.BACKGROUND_HOVER`
   - Replace `BORDER_COLOR` → `UIColors.BORDER_DEFAULT`

6. Update `highlight_delegate.py`:
   - Use `UIColors.BACKGROUND_SELECTED` for selection
   - Use `LogTextColors` for log level text colors

**Tests Required:**
- Visual regression test: Compare screenshots before/after
- Unit test: Verify components use correct color constants
- Integration test: Verify UI renders correctly

**Dependencies:** T-001 (colors.py refactoring)

---

### Task 4: Add Deprecation Warnings to Legacy Constants

**Task ID:** T-004
**Spec Reference:** §8.2.2 Deprecation Schedule
**Project Context:** src/constants/
**Language:** Python 3.10
**Scope:** [`src/constants/colors.py`](../../src/constants/colors.py)

**Input/Output:**
- Input: Legacy constants without warnings
- Output: Legacy constants with deprecation warnings

**Constraints:**
- Warnings should be visible but not break existing code
- Use Python's `warnings.warn()` with `DeprecationWarning`
- Document migration path in warning message

**Implementation Steps:**

1. Add `warnings` import at top of file

2. Add deprecation warnings to each legacy constant:
   ```python
   import warnings
   
   warnings.warn(
       "TABLE_ROW_BACKGROUND is deprecated, use PaletteColors.GRAY_2",
       DeprecationWarning,
       stacklevel=2
   )
   TABLE_ROW_BACKGROUND: str = "#B6B6B6"
   ```

3. Create helper function for deprecation warnings:
   ```python
   def _deprecated_constant(old_name: str, new_name: str) -> None:
       """Emit deprecation warning for legacy constant."""
       warnings.warn(
           f"{old_name} is deprecated, use {new_name}",
           DeprecationWarning,
           stacklevel=3
       )
   ```

4. Document migration path in docstrings:
   ```python
   TABLE_ROW_BACKGROUND: str = "#B6B6B6"
   """Legacy constant. Use PaletteColors.GRAY_2 instead.
   
   Deprecated: v1.1
   Removal: v2.0
   Migration: Replace TABLE_ROW_BACKGROUND with PaletteColors.GRAY_2
   """
   ```

**Tests Required:**
- Unit test: Verify deprecation warnings are emitted
- Unit test: Verify legacy constants still work
- Integration test: Verify no warnings break existing code

**Dependencies:** T-001 (colors.py refactoring)

---

### Task 5: Update Documentation and Comments

**Task ID:** T-005
**Spec Reference:** §8 Implementation
**Project Context:** Documentation
**Language:** Markdown
**Scope:** Multiple documentation files

**Files to Update:**
- [`src/constants/__init__.py`](../../src/constants/__init__.py)
- [`src/constants/colors.py`](../../src/constants/colors.py) (docstrings)
- [`docs/specs/features/ui-design-system.md`](../features/ui-design-system.md)
- [`docs/specs/features/table-unified-styles.md`](../features/table-unified-styles.md)
- [`docs/specs/features/category-panel-styles.md`](../features/category-panel-styles.md)

**Input/Output:**
- Input: Documentation referencing old color constants
- Output: Documentation updated with new color system

**Implementation Steps:**

1. Update `src/constants/__init__.py`:
   - Add exports for new color classes
   - Document migration from legacy constants

2. Update `src/constants/colors.py` docstrings:
   - Add class-level docstrings explaining purpose
   - Add spec references (e.g., "Ref: docs/specs/global/color-palette.md §X")
   - Document migration path for legacy constants

3. Update feature specs:
   - Replace references to hardcoded colors with semantic constants
   - Add cross-references to color-palette.md
   - Update code examples to use new constants

**Tests Required:**
- Documentation review: Verify all color references are correct
- Link check: Verify all cross-references work

**Dependencies:** T-001 (colors.py refactoring)

---

### Task 6: Write Comprehensive Tests

**Task ID:** T-006
**Spec Reference:** §11 Testing Requirements
**Project Context:** tests/
**Language:** Python 3.10
**Scope:** [`tests/test_colors.py`](../../tests/test_colors.py) (new file)

**Input/Output:**
- Input: No dedicated color tests
- Output: Comprehensive test suite for color system

**Tests Required:**

1. **Base Color Tests:**
   - Verify all `BaseColors` constants have correct hex values
   - Verify gray scale values are correct
   - Verify accent colors are correct

2. **Palette Color Tests:**
   - Verify all `PaletteColors` family members have correct values
   - Verify color families are ordered from dark to light

3. **UI Color Tests:**
   - Verify all `UIColors` constants have correct hex values
   - Verify background colors are distinct
   - Verify border colors are distinct
   - Verify text colors meet contrast requirements

4. **Log Level Color Tests:**
   - Verify `LogTextColors` constants are correct
   - Verify `LogIconColors` constants are correct
   - Verify `StatsColors` constants are correct

5. **Process Color Tests:**
   - Verify all `ProcessColors` constants are correct
   - Verify `ProcessColors.get_color(0)` returns BLUE
   - Verify `ProcessColors.get_color(5)` returns CREAM
   - Verify `ProcessColors.get_color(6)` cycles back to BLUE

6. **LogViewer Color Tests:**
   - Verify all `LogViewerColors` constants are correct

7. **Legacy Constant Tests:**
   - Verify legacy constants are still accessible
   - Verify legacy constants have correct values
   - Verify deprecation warnings are emitted

8. **Backward Compatibility Tests:**
   - Verify existing imports still work
   - Verify existing code using legacy constants still works

**Dependencies:** T-001, T-004

---

## Execution Order

```
T-001: Refactor colors.py Core Structure
   │
   ├─► T-002: Update stylesheet.py
   │
   ├─► T-003: Update View Components
   │
   ├─► T-004: Add Deprecation Warnings
   │
   ├─► T-005: Update Documentation
   │
   └─► T-006: Write Comprehensive Tests
```

**Recommended Execution:**
1. Complete T-001 first (core refactoring)
2. Execute T-002, T-003, T-004, T-005 in parallel (all depend on T-001)
3. Execute T-006 after T-001 and T-004 (needs both core and deprecation warnings)

---

## Verification Checklist

After all tasks are complete, verify:

- [ ] All color constants are defined in new classes
- [ ] Legacy constants still work with deprecation warnings
- [ ] No visual changes to UI (screenshots match)
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] No breaking changes to existing code
- [ ] Color values match specification exactly
- [ ] Accessibility contrast ratios are maintained

---

## Risk Assessment

### Low Risk
- Adding new color classes (T-001)
- Writing tests (T-006)
- Updating documentation (T-005)

### Medium Risk
- Updating stylesheet.py (T-002) - must ensure no visual changes
- Updating view components (T-003) - must ensure no visual changes

### High Risk
- Adding deprecation warnings (T-004) - may break tests that check for warnings

### Mitigation
- Run visual regression tests before/after changes
- Run full test suite after each task
- Keep legacy constants until v2.0
- Document migration path clearly

---

## Success Criteria

1. **Functional:** All existing code continues to work without changes
2. **Visual:** No visual changes to UI (screenshots match)
3. **Performance:** No performance degradation
4. **Maintainability:** Color system is well-organized and documented
5. **Accessibility:** All contrast ratios meet WCAG 2.1 AA standards
6. **Testability:** Comprehensive test coverage for color system

---

## Rollback Plan

If issues are found:

1. **T-001 Issues:** Revert colors.py to previous version
2. **T-002 Issues:** Revert stylesheet.py to previous version
3. **T-003 Issues:** Revert individual view files as needed
4. **T-004 Issues:** Remove deprecation warnings, keep legacy constants
5. **T-005 Issues:** Revert documentation changes
6. **T-006 Issues:** Fix tests without changing implementation

All changes are backward compatible, so rollback is safe.

---

## Post-Implementation Tasks

After successful implementation:

1. **Monitor:** Check for deprecation warnings in logs
2. **Migrate:** Update internal code to use new constants
3. **Document:** Create migration guide for external users
4. **Plan:** Schedule removal of legacy constants in v2.0

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-19 | Initial implementation plan |