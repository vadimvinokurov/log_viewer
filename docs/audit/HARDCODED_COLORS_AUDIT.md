# Hardcoded Colors Audit Report

## Summary
- Total hardcoded colors: 26
- Matching palette: 8
- Mismatching: 12
- Missing from palette: 6

---

## File: src/views/statistics_panel.py

### LevelButton Color Parameters

| Line | Current | Palette Constant | Status | Recommendation |
|------|---------|------------------|--------|----------------|
| 159 | `#CC0000` | StatsColors.ERROR_TEXT | ❌ MISMATCH | Use `StatsColors.ERROR_TEXT` ("#781111") |
| 167 | `#CC7700` | StatsColors.WARNING_TEXT | ❌ MISMATCH | Use `StatsColors.WARNING_TEXT` ("#6A5302") |
| 175 | `#007700` | StatsColors.MSG_TEXT | ❌ MISMATCH | Use `StatsColors.MSG_TEXT` ("#0066CC") |

**Analysis:**
- ERROR button uses `#CC0000` (bright red) but palette defines `#781111` (dark red)
- WARNING button uses `#CC7700` (orange) but palette defines `#6A5302` (amber/brown)
- INFO button uses `#007700` (green) but palette defines `#0066CC` (blue) - Note: INFO and MSG are treated as equivalent

**Recommendation:** Replace hardcoded colors with palette constants from `StatsColors` class.

---

## File: src/constants/log_levels.py

### CRITICAL Level (lines 52-59)

| Line | Property | Current | Palette Constant | Status | Recommendation |
|------|-----------|---------|-------------------|--------|----------------|
| 55 | background_color | `#FF6B6B` | StatsColors.CRITICAL_BG | ❌ MISMATCH | Use `StatsColors.CRITICAL_BG` ("#FFE4E4") |
| 56 | text_color | `#FFFFFF` | BaseColors.WHITE | ✅ MATCH | Already matches palette |
| 57 | border_color | `#CC0000` | StatsColors.CRITICAL_BORDER | ❌ MISMATCH | Use `StatsColors.CRITICAL_BORDER` ("#781111") |

### ERROR Level (lines 60-67)

| Line | Property | Current | Palette Constant | Status | Recommendation |
|------|-----------|---------|-------------------|--------|----------------|
| 63 | background_color | `#FF8C8C` | StatsColors.ERROR_BG | ❌ MISMATCH | Use `StatsColors.ERROR_BG` ("#FFE4E4") |
| 64 | text_color | `#FFFFFF` | BaseColors.WHITE | ✅ MATCH | Already matches palette |
| 65 | border_color | `#CC0000` | StatsColors.ERROR_BORDER | ❌ MISMATCH | Use `StatsColors.ERROR_BORDER` ("#781111") |

### WARNING Level (lines 68-75)

| Line | Property | Current | Palette Constant | Status | Recommendation |
|------|-----------|---------|-------------------|--------|----------------|
| 71 | background_color | `#FFD93D` | StatsColors.WARNING_BG | ❌ MISMATCH | Use `StatsColors.WARNING_BG` ("#FFF4E0") |
| 72 | text_color | `#000000` | BaseColors.BLACK | ✅ MATCH | Already matches palette |
| 73 | border_color | `#B8860B` | StatsColors.WARNING_BORDER | ❌ MISMATCH | Use `StatsColors.WARNING_BORDER` ("#6A5302") |

### MSG Level (lines 76-83)

| Line | Property | Current | Palette Constant | Status | Recommendation |
|------|-----------|---------|-------------------|--------|----------------|
| 79 | background_color | `#FFFFFF` | BaseColors.WHITE | ✅ MATCH | Already matches palette |
| 80 | text_color | `#000000` | BaseColors.BLACK | ✅ MATCH | Already matches palette |
| 81 | border_color | `#CCCCCC` | StatsColors.MSG_BORDER | ❌ MISMATCH | Use `StatsColors.MSG_BORDER` ("#0066CC") |

### DEBUG Level (lines 84-91)

| Line | Property | Current | Palette Constant | Status | Recommendation |
|------|-----------|---------|-------------------|--------|----------------|
| 87 | background_color | `#E8E8E8` | StatsColors.DEBUG_BG | ❌ MISMATCH | Use `StatsColors.DEBUG_BG` ("#F0E8F4") |
| 88 | text_color | `#333333` | UIColors.TEXT_PRIMARY | ✅ MATCH | Already matches palette |
| 89 | border_color | `#999999` | UIColors.TEXT_DISABLED | ✅ MATCH | Already matches palette |

### TRACE Level (lines 92-99)

| Line | Property | Current | Palette Constant | Status | Recommendation |
|------|-----------|---------|-------------------|--------|----------------|
| 95 | background_color | `#F5F5F5` | UIColors.BACKGROUND_SECONDARY | ✅ MATCH | Already matches palette |
| 96 | text_color | `#666666` | UIColors.TEXT_SECONDARY | ✅ MATCH | Already matches palette |
| 97 | border_color | `#AAAAAA` | LogIconColors.TRACE | ❌ MISMATCH | Use `LogIconColors.TRACE` ("#BDBDBD") |

**Analysis:**
- Log level configurations use different color values than the palette
- Background colors for CRITICAL/ERROR use solid colors instead of light tints
- Border colors differ significantly from palette definitions
- DEBUG background uses gray instead of purple tint from palette

**Recommendation:** Import and use palette constants from `src.constants.colors` module.

---

## File: src/views/widgets/highlight_dialog.py

### DEFAULT_COLORS List (lines 19-26)

| Line | Current | Palette Constant | Status | Recommendation |
|------|---------|------------------|--------|----------------|
| 20 | `#FFFF00` | UIColors.FIND_HIGHLIGHT | ✅ MATCH | Already matches palette |
| 21 | `#00FF00` | - | ❌ MISSING | Add `HIGHLIGHT_GREEN` to palette |
| 22 | `#00FFFF` | - | ❌ MISSING | Add `HIGHLIGHT_CYAN` to palette |
| 23 | `#FF00FF` | - | ❌ MISSING | Add `HIGHLIGHT_MAGENTA` to palette |
| 24 | `#FFA500` | - | ❌ MISSING | Add `HIGHLIGHT_ORANGE` to palette |
| 25 | `#FF69B4` | - | ❌ MISSING | Add `HIGHLIGHT_PINK` to palette |

### Button Border Color (lines 113, 138)

| Line | Current | Palette Constant | Status | Recommendation |
|------|---------|------------------|--------|----------------|
| 113 | `#888` | - | ⚠️ NO_EQUIV | Keep as-is (UI component border, no semantic equivalent) |
| 138 | `#888` | - | ⚠️ NO_EQUIV | Keep as-is (UI component border, no semantic equivalent) |

**Analysis:**
- First color (Yellow) matches `UIColors.FIND_HIGHLIGHT`
- Five colors have no palette equivalent
- Button border `#888` is a medium gray for UI component styling - no semantic equivalent needed

**Recommendation:** 
1. Replace `#FFFF00` with `UIColors.FIND_HIGHLIGHT`
2. Add new palette constants for highlight colors:
   - `HIGHLIGHT_GREEN = "#00FF00"`
   - `HIGHLIGHT_CYAN = "#00FFFF"`
   - `HIGHLIGHT_MAGENTA = "#FF00FF"`
   - `HIGHLIGHT_ORANGE = "#FFA500"`
   - `HIGHLIGHT_PINK = "#FF69B4"`
3. Keep `#888` as-is (commented as intentional)

---

## File: src/services/find_service.py

### Default Highlight Color (line 164)

| Line | Current | Palette Constant | Status | Recommendation |
|------|---------|------------------|--------|----------------|
| 164 | `#FFFF00` | UIColors.FIND_HIGHLIGHT | ✅ MATCH | Already matches palette |

**Analysis:**
- Default highlight color matches `UIColors.FIND_HIGHLIGHT`

**Recommendation:** Replace hardcoded value with `UIColors.FIND_HIGHLIGHT` constant for consistency.

---

## File: src/services/highlight_service.py

### Default Highlight Color (line 83)

| Line | Current | Palette Constant | Status | Recommendation |
|------|---------|------------------|--------|----------------|
| 83 | `#FFFF00` | UIColors.FIND_HIGHLIGHT | ✅ MATCH | Already matches palette |

**Analysis:**
- Default highlight color matches `UIColors.FIND_HIGHLIGHT`

**Recommendation:** Replace hardcoded value with `UIColors.FIND_HIGHLIGHT` constant for consistency.

---

## Detailed Recommendations

### 1. src/views/statistics_panel.py

**Current code (lines 158-176):**
```python
self._error_button = LevelButton("ERROR", "#CC0000")
self._warning_button = LevelButton("WARNING", "#CC7700")
self._info_button = LevelButton("INFO", "#007700")
```

**Recommended change:**
```python
from src.constants.colors import StatsColors

self._error_button = LevelButton("ERROR", StatsColors.ERROR_TEXT)
self._warning_button = LevelButton("WARNING", StatsColors.WARNING_TEXT)
self._info_button = LevelButton("INFO", StatsColors.MSG_TEXT)
```

### 2. src/constants/log_levels.py

**Current code (lines 50-100):**
Uses hardcoded hex values for all level configurations.

**Recommended change:**
```python
from src.constants.colors import (
    BaseColors, UIColors, StatsColors, LogIconColors
)

LOG_LEVEL_CONFIGS: dict[LogLevel, LogLevelConfig] = {
    LogLevel.CRITICAL: LogLevelConfig(
        level=LogLevel.CRITICAL,
        icon="⛔",
        background_color=StatsColors.CRITICAL_BG,
        text_color=BaseColors.WHITE,
        border_color=StatsColors.CRITICAL_BORDER,
        tooltip="Critical errors",
    ),
    LogLevel.ERROR: LogLevelConfig(
        level=LogLevel.ERROR,
        icon="🛑",
        background_color=StatsColors.ERROR_BG,
        text_color=BaseColors.WHITE,
        border_color=StatsColors.ERROR_BORDER,
        tooltip="Errors",
    ),
    LogLevel.WARNING: LogLevelConfig(
        level=LogLevel.WARNING,
        icon="⚠️",
        background_color=StatsColors.WARNING_BG,
        text_color=BaseColors.BLACK,
        border_color=StatsColors.WARNING_BORDER,
        tooltip="Warnings",
    ),
    LogLevel.MSG: LogLevelConfig(
        level=LogLevel.MSG,
        icon="ℹ️",
        background_color=BaseColors.WHITE,
        text_color=BaseColors.BLACK,
        border_color=StatsColors.MSG_BORDER,
        tooltip="Messages",
    ),
    LogLevel.DEBUG: LogLevelConfig(
        level=LogLevel.DEBUG,
        icon="🟪",
        background_color=StatsColors.DEBUG_BG,
        text_color=UIColors.TEXT_PRIMARY,
        border_color=UIColors.TEXT_DISABLED,
        tooltip="Debug",
    ),
    LogLevel.TRACE: LogLevelConfig(
        level=LogLevel.TRACE,
        icon="🟩",
        background_color=UIColors.BACKGROUND_SECONDARY,
        text_color=UIColors.TEXT_SECONDARY,
        border_color=LogIconColors.TRACE,
        tooltip="Trace",
    ),
}
```

### 3. src/views/widgets/highlight_dialog.py

**Current code (lines 19-26):**
```python
DEFAULT_COLORS = [
    QColor("#FFFF00"),  # Yellow
    QColor("#00FF00"),  # Green
    QColor("#00FFFF"),  # Cyan
    QColor("#FF00FF"),  # Magenta
    QColor("#FFA500"),  # Orange
    QColor("#FF69B4"),  # Pink
]
```

**Recommended change:**
Add new constants to `src/constants/colors.py`:
```python
class HighlightColors:
    """Colors for highlight patterns.
    
    Ref: docs/specs/global/color-palette.md §X.X
    """
    YELLOW: str = "#FFFF00"  # Same as UIColors.FIND_HIGHLIGHT
    GREEN: str = "#00FF00"
    CYAN: str = "#00FFFF"
    MAGENTA: str = "#FF00FF"
    ORANGE: str = "#FFA500"
    PINK: str = "#FF69B4"
```

Then update highlight_dialog.py:
```python
from src.constants.colors import UIColors, HighlightColors

DEFAULT_COLORS = [
    QColor(UIColors.FIND_HIGHLIGHT),
    QColor(HighlightColors.GREEN),
    QColor(HighlightColors.CYAN),
    QColor(HighlightColors.MAGENTA),
    QColor(HighlightColors.ORANGE),
    QColor(HighlightColors.PINK),
]
```

### 4. src/services/find_service.py & highlight_service.py

**Current code:**
```python
color: QColor = QColor("#FFFF00")
```

**Recommended change:**
```python
from src.constants.colors import UIColors

color: QColor = QColor(UIColors.FIND_HIGHLIGHT)
```

---

## Missing Palette Constants

The following constants should be added to `src/constants/colors.py`:

| Constant Name | Hex Value | Description |
|---------------|-----------|-------------|
| `HighlightColors.GREEN` | `#00FF00` | Green highlight color |
| `HighlightColors.CYAN` | `#00FFFF` | Cyan highlight color |
| `HighlightColors.MAGENTA` | `#FF00FF` | Magenta highlight color |
| `HighlightColors.ORANGE` | `#FFA500` | Orange highlight color |
| `HighlightColors.PINK` | `#FF69B4` | Pink highlight color |

---

## Color Value Discrepancies

The following table shows colors that differ between hardcoded values and palette:

| File | Property | Hardcoded | Palette | Difference |
|------|----------|-----------|---------|------------|
| statistics_panel.py | ERROR text | `#CC0000` | `#781111` | Bright red vs dark red |
| statistics_panel.py | WARNING text | `#CC7700` | `#6A5302` | Orange vs amber/brown |
| statistics_panel.py | MSG text | `#007700` | `#0066CC` | Green vs blue |
| log_levels.py | CRITICAL bg | `#FF6B6B` | `#FFE4E4` | Solid vs light tint |
| log_levels.py | CRITICAL border | `#CC0000` | `#781111` | Bright red vs dark red |
| log_levels.py | ERROR bg | `#FF8C8C` | `#FFE4E4` | Solid vs light tint |
| log_levels.py | ERROR border | `#CC0000` | `#781111` | Bright red vs dark red |
| log_levels.py | WARNING bg | `#FFD93D` | `#FFF4E0` | Solid yellow vs light amber |
| log_levels.py | WARNING border | `#B8860B` | `#6A5302` | Dark goldenrod vs amber/brown |
| log_levels.py | MSG border | `#CCCCCC` | `#0066CC` | Gray vs blue |
| log_levels.py | DEBUG bg | `#E8E8E8` | `#F0E8F4` | Gray vs purple tint |
| log_levels.py | TRACE border | `#AAAAAA` | `#BDBDBD` | Medium gray vs light gray |

---

## Conclusion

This audit identified **26 hardcoded color values** across 5 files:
- **8 colors** already match palette constants (can be replaced directly)
- **12 colors** have mismatching values (need decision on which value to use)
- **6 colors** are missing from palette (need new constants added)

**Priority Actions:**
1. Add missing `HighlightColors` class to palette
2. Replace matching colors with palette constants
3. Decide on mismatching values (recommend using palette values for consistency)
4. Update `log_levels.py` to use palette constants
5. Update `statistics_panel.py` to use `StatsColors` constants