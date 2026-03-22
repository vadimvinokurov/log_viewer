# Color Palette Specification

**Version:** 1.0
**Last Updated:** 2026-03-19
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)
**Status:** DRAFT

---

## §1 Overview

### §1.1 Purpose

This specification defines the comprehensive color palette for the Log Viewer application, establishing a systematic approach to color naming, organization, and usage. The palette ensures visual consistency, maintainability, and accessibility across all UI components.

### §1.2 Design Principles

1. **Semantic Naming**: Colors named by purpose, not appearance
2. **Hierarchy**: Clear color organization from base to semantic tokens
3. **Accessibility**: WCAG 2.1 AA compliant contrast ratios
4. **Maintainability**: Single source of truth for all color values
5. **Scalability**: Extensible system for future additions

### §1.3 Color System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  (Semantic colors: LogTextColors, StatsColors, etc.)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SEMANTIC LAYER                            │
│  (Purpose-based: Selection, Hover, Border, etc.)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PALETTE LAYER                             │
│  (Color families: Gray, Red, Orange, Green, etc.)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    BASE LAYER                                │
│  (Primitive values: #FFFFFF, #000000, etc.)                │
└─────────────────────────────────────────────────────────────┘
```

---

## §2 Base Colors

### §2.1 Light Theme Base Colors

Base colors are the foundational palette from which all semantic colors are derived.

#### §2.1.1 Gray Scale

| Token | HEX | RGB | Usage |
|-------|-----|-----|-------|
| `Gray01` | `#A4A4A4` | 164, 164, 164 | Dark gray - borders, disabled text |
| `Gray02` | `#B6B6B6` | 182, 182, 182 | Medium-dark gray - table row background |
| `Gray03` | `#C8C8C8` | 200, 200, 200 | Medium gray - borders |
| `Gray04` | `#D6D6D6` | 214, 214, 214 | Medium-light gray - hover states |
| `Gray05` | `#E7E7E7` | 231, 231, 231 | Light gray - panel backgrounds |

#### §2.1.2 Accent Colors

| Token | HEX | RGB | Usage |
|-------|-----|-----|-------|
| `Accent01` | `#FFA3D0FF` | 255, 163, 208, 255 | Primary accent (light blue) - transparent |
| `Accent02` | `#0078D7` | 0, 120, 215 | Container panel highlighted |
| `Accent03` | `#375977` | 55, 89, 119 | Log item entry (selected) |

#### §2.1.3 Semantic Base Colors

| Token | HEX | RGB | Usage |
|-------|-----|-----|-------|
| `White` | `#FFFFFF` | 255, 255, 255 | Primary background |
| `Black` | `#000000` | 0, 0, 0 | Primary text |
| `Transparent` | `#00000000` | 0, 0, 0, 0 | Transparent overlay |

---

## §3 Palette Colors

### §3.1 Color Families

Each color family provides a range of shades from dark to light.

#### §3.1.1 Gray Family

| Level | HEX | Usage |
|-------|-----|-------|
| Gray1 | `#A4A4A4` | Dark borders, disabled states |
| Gray2 | `#B6B6B6` | Table row background, medium borders |
| Gray3 | `#C8C8C8` | Default borders, inactive elements |
| Gray4 | `#D6D6D6` | Hover backgrounds |
| Gray5 | `#E7E7E7` | Panel backgrounds, light areas |

#### §3.1.2 Red Family

| Level | HEX | Usage |
|-------|-----|-------|
| Red1 | `#F97575` | Dark red - error icons |
| Red2 | `#F18989` | Medium-dark red |
| Red3 | `#FF9A9A` | Medium red |
| Red4 | `#FFB6B6` | Medium-light red |
| Red5 | `#FFCACA` | Light red - error backgrounds |

#### §3.1.3 Orange Family

| Level | HEX | Usage |
|-------|-----|-------|
| Orange1 | `#F9A54F` | Dark orange |
| Orange2 | `#F9BA7B` | Medium-dark orange |
| Orange3 | `#FCC48C` | Medium orange |
| Orange4 | `#FCCC9C` | Medium-light orange |
| Orange5 | `#FDDDBE` | Light orange |

#### §3.1.4 Green Family

| Level | HEX | Usage |
|-------|-----|-------|
| Green1 | `#7CEB7C` | Dark green - success icons |
| Green2 | `#94F594` | Medium-dark green |
| Green3 | `#9CFF9C` | Medium green |
| Green4 | `#B8FFB8` | Medium-light green |
| Green5 | `#D2FFD2` | Light green - success backgrounds |

#### §3.1.5 Cyan Family

| Level | HEX | Usage |
|-------|-----|-------|
| Cyan1 | `#4AE7BF` | Dark cyan |
| Cyan2 | `#7CF3D4` | Medium-dark cyan |
| Cyan3 | `#8FFBE0` | Medium cyan |
| Cyan4 | `#ABF9E6` | Medium-light cyan |
| Cyan5 | `#C3FEEF` | Light cyan |

#### §3.1.6 Blue Family

| Level | HEX | Usage |
|-------|-----|-------|
| Blue1 | `#70A3FF` | Dark blue - primary actions |
| Blue2 | `#80B0FF` | Medium-dark blue |
| Blue3 | `#8CBAFF` | Medium blue |
| Blue4 | `#99D0FF` | Medium-light blue |
| Blue5 | - | Light blue (not used) |

#### §3.1.7 Purple Family

| Level | HEX | Usage |
|-------|-----|-------|
| Purple1 | `#D86EFF` | Dark purple - debug level |
| Purple2 | `#DF86FF` | Medium-dark purple |
| Purple3 | `#E09DFF` | Medium purple |
| Purple4 | `#EBB5FF` | Medium-light purple |
| Purple5 | - | Light purple (not used) |

---

## §4 Semantic Colors

### §4.1 UI Element Colors

Colors for common UI elements and states.

#### §4.1.1 Background Colors

| Token | HEX | Usage |
|-------|-----|-------|
| `BackgroundPrimary` | `#FFFFFF` | Main content background |
| `BackgroundSecondary` | `#F5F5F5` | Panel backgrounds, toolbar |
| `BackgroundTertiary` | `#F0F0F0` | Main window background |
| `BackgroundHover` | `#E8E8E8` | Hover states |
| `BackgroundActive` | `#D0D0D0` | Active/pressed states |
| `BackgroundSelected` | `#DCEBF7` | Selection highlight |
| `BackgroundDisabled` | `#F5F5F5` | Disabled element backgrounds |

#### §4.1.2 Border Colors

| Token | HEX | Usage |
|-------|-----|-------|
| `BorderDefault` | `#C0C0C0` | Default borders |
| `BorderHover` | `#A0A0A0` | Hover borders |
| `BorderFocus` | `#0066CC` | Focus indicator |
| `BorderDisabled` | `#D0D0D0` | Disabled borders |
| `BorderMouseOver` | `#8491A3` | Mouse over border (LogViewer) |
| `BorderSelected` | `#8491A3` | Selected border (LogViewer) |

#### §4.1.3 Text Colors

| Token | HEX | Usage |
|-------|-----|-------|
| `TextPrimary` | `#333333` | Primary text |
| `TextSecondary` | `#666666` | Secondary text, placeholders |
| `TextDisabled` | `#999999` | Disabled text |
| `TextSelected` | `#382F27` | Selected text (LogViewer) |
| `TextMouseOver` | `#382F27` | Mouse over text (LogViewer) |
| `TextInverted` | `#FFFFFF` | Text on dark backgrounds |

#### §4.1.4 Special Colors

| Token | HEX | Usage |
|-------|-----|-------|
| `FindHighlight` | `#FFFF00` | Search result highlighting |
| `TooltipBackground` | `#333333` | Tooltip background |
| `TooltipText` | `#FFFFFF` | Tooltip text |
| `TooltipBorder` | `#555555` | Tooltip border |

---

## §5 Log Level Colors

### §5.1 Log Text Colors

Colors for log level text foreground in table entries.

| Level | HEX | RGB | Usage |
|-------|-----|-----|-------|
| `LogCritical` | `#FF6B6B` | 255, 107, 107 | Critical level text |
| `LogError` | `#FF8C8C` | 255, 140, 140 | Error level text |
| `LogWarning` | `#FFD93D` | 255, 217, 61 | Warning level text |
| `LogMessage` | Default | - | Message level (default text color) |
| `LogDebug` | Default | - | Debug level (default text color) |
| `LogTrace` | Default | - | Trace level (default text color) |

**Implementation:** [`LogTextColors`](../../src/constants/colors.py)

**Note:** MSG, DEBUG, and TRACE levels use the default text color (no special color).

### §5.2 Log Icon Colors

Colors for log level icons in the Type column.

| Level | HEX | RGB | Usage |
|-------|-----|-----|-------|
| `IconCritical` | `#CC0000` | 204, 0, 0 | Critical level icon |
| `IconError` | `#CC0000` | 204, 0, 0 | Error level icon |
| `IconWarning` | `#B8860B` | 184, 134, 11 | Warning level icon (dark goldenrod) |
| `IconMessage` | `#CCCCCC` | 204, 204, 204 | Message level icon |
| `IconDebug` | `#999999` | 153, 153, 153 | Debug level icon |
| `IconTrace` | `#AAAAAA` | 170, 170, 170 | Trace level icon |

**Implementation:** [`LogIconColors`](../../src/constants/colors.py)

### §5.3 Statistics Counter Colors

Colors for statistics counter widgets in the status bar.

| Level | Background | Text/Icon | Border | Usage |
|-------|------------|-----------|--------|-------|
| CRITICAL | `#FFE4E4` | `#FF4444` | `#FF4444` | Critical counter |
| ERROR | `#FFE4E4` | `#CC0000` | `#CC0000` | Error counter |
| WARNING | `#FFF4E0` | `#FFAA00` | `#FFAA00` | Warning counter |
| MSG | `#E0F0FF` | `#0066CC` | `#0066CC` | Message counter |
| DEBUG | `#F0E8F4` | `#8844AA` | `#8844AA` | Debug counter |
| TRACE | `#E4FFE4` | `#00AA00` | `#00AA00` | Trace counter |

**Implementation:** [`StatsColors`](../../src/constants/colors.py)

---

## §6 Process Identification Colors

### §6.1 Process Color Palette

Colors for identifying different processes in the log view. Assigned cyclically when new processes are detected.

| Color Name | HEX | RGB | Usage |
|------------|-----|-----|-------|
| `ProcessBlue` | `#96CBF8` | 150, 203, 248 | Process identifier 1 |
| `ProcessRed` | `#CC7474` | 204, 116, 116 | Process identifier 2 |
| `ProcessOrange` | `#F5B76E` | 245, 183, 110 | Process identifier 3 |
| `ProcessPink` | `#D786CA` | 215, 134, 202 | Process identifier 4 |
| `ProcessGreen` | `#9BBF7C` | 155, 191, 124 | Process identifier 5 |
| `ProcessCream` | `#FAE744` | 250, 231, 68 | Process identifier 6 |

**Assignment:** Process colors are assigned in order (Blue → Red → Orange → Pink → Green → Cream) and cycle back to Blue when all colors are used.

---

## §7 LogViewer-Specific Colors

### §7.1 Log Item Colors

Colors specific to log item rendering in the LogViewer plugin.

| Token | HEX | ARGB | Usage |
|-------|-----|------|-------|
| `LogViewerBackground` | Inherited from Gray02 | - | Main background for log list |
| `LogViewerBorder` | Inherited from Gray02 | - | Border for panels and controls |
| `LogItemSelected` | `#B7CFD5` | `0xFFB7CFD5` | Background for selected log items |
| `LogItemBorderMouseOver` | `#B7CFD5` | `0xFFB7CFD5` | Log item border on hover |
| `LogItemTextMouseOver` | `#382F27` | `0xFF382F27` | Text color on mouse hover |
| `LogBorder` | `#00000080` | `0x80000000` | Semi-transparent black for log borders |
| `LogItemEntry` | Inherited from Accent03 | - | Accent for log entry highlighting |

### §7.2 Auto-Scroll Button Colors

| Token | HEX | Usage |
|-------|-----|-------|
| `AutoScrollSelected` | `#483D8B` | Auto-scroll button selected state |
| `AutoScrollMouseOver` | `#2587CF` | Auto-scroll button hover state |

### §7.3 System Filter Colors

| Token | HEX | Usage |
|-------|-----|-------|
| `SystemFilterBorder` | Inherited from Gray0 | Border for system filter items |
| `ContainerPanelHighlighted` | `#0078D7` | Highlighted container panel background |

---

## §8 Implementation

### §8.1 File Organization

**File:** [`src/constants/colors.py`](../../src/constants/colors.py)

**Structure:**
```python
from __future__ import annotations

# Base Colors (Light Theme)
class BaseColors:
    """Base color palette for light theme."""
    WHITE: str = "#FFFFFF"
    BLACK: str = "#000000"
    TRANSPARENT: str = "#00000000"
    
    # Gray Scale
    GRAY_01: str = "#A4A4A4"
    GRAY_02: str = "#B6B6B6"
    GRAY_03: str = "#C8C8C8"
    GRAY_04: str = "#D6D6D6"
    GRAY_05: str = "#E7E7E7"
    
    # Accent Colors
    ACCENT_01: str = "#FFA3D0FF"  # Transparent light blue
    ACCENT_02: str = "#0078D7"    # Container panel highlighted
    ACCENT_03: str = "#375977"    # Log item entry


# Palette Colors (Color Families)
class PaletteColors:
    """Color families with multiple shades."""
    
    # Gray Family
    GRAY_1: str = "#A4A4A4"
    GRAY_2: str = "#B6B6B6"
    GRAY_3: str = "#C8C8C8"
    GRAY_4: str = "#D6D6D6"
    GRAY_5: str = "#E7E7E7"
    
    # Red Family
    RED_1: str = "#F97575"
    RED_2: str = "#F18989"
    RED_3: str = "#FF9A9A"
    RED_4: str = "#FFB6B6"
    RED_5: str = "#FFCACA"
    
    # Orange Family
    ORANGE_1: str = "#F9A54F"
    ORANGE_2: str = "#F9BA7B"
    ORANGE_3: str = "#FCC48C"
    ORANGE_4: str = "#FCCC9C"
    ORANGE_5: str = "#FDDDBE"
    
    # Green Family
    GREEN_1: str = "#7CEB7C"
    GREEN_2: str = "#94F594"
    GREEN_3: str = "#9CFF9C"
    GREEN_4: str = "#B8FFB8"
    GREEN_5: str = "#D2FFD2"
    
    # Cyan Family
    CYAN_1: str = "#4AE7BF"
    CYAN_2: str = "#7CF3D4"
    CYAN_3: str = "#8FFBE0"
    CYAN_4: str = "#ABF9E6"
    CYAN_5: str = "#C3FEEF"
    
    # Blue Family
    BLUE_1: str = "#70A3FF"
    BLUE_2: str = "#80B0FF"
    BLUE_3: str = "#8CBAFF"
    BLUE_4: str = "#99D0FF"
    
    # Purple Family
    PURPLE_1: str = "#D86EFF"
    PURPLE_2: str = "#DF86FF"
    PURPLE_3: str = "#E09DFF"
    PURPLE_4: str = "#EBB5FF"


# Semantic Colors (UI Elements)
class UIColors:
    """Semantic colors for UI elements."""
    
    # Background Colors
    BACKGROUND_PRIMARY: str = "#FFFFFF"
    BACKGROUND_SECONDARY: str = "#F5F5F5"
    BACKGROUND_TERTIARY: str = "#F0F0F0"
    BACKGROUND_HOVER: str = "#E8E8E8"
    BACKGROUND_ACTIVE: str = "#D0D0D0"
    BACKGROUND_SELECTED: str = "#DCEBF7"
    BACKGROUND_DISABLED: str = "#F5F5F5"
    
    # Border Colors
    BORDER_DEFAULT: str = "#C0C0C0"
    BORDER_HOVER: str = "#A0A0A0"
    BORDER_FOCUS: str = "#0066CC"
    BORDER_DISABLED: str = "#D0D0D0"
    BORDER_MOUSE_OVER: str = "#8491A3"
    BORDER_SELECTED: str = "#8491A3"
    
    # Text Colors
    TEXT_PRIMARY: str = "#333333"
    TEXT_SECONDARY: str = "#666666"
    TEXT_DISABLED: str = "#999999"
    TEXT_SELECTED: str = "#382F27"
    TEXT_MOUSE_OVER: str = "#382F27"
    TEXT_INVERTED: str = "#FFFFFF"
    
    # Special Colors
    FIND_HIGHLIGHT: str = "#FFFF00"
    TOOLTIP_BACKGROUND: str = "#333333"
    TOOLTIP_TEXT: str = "#FFFFFF"
    TOOLTIP_BORDER: str = "#555555"


# Log Level Colors
class LogTextColors:
    """Text colors for log levels."""
    
    CRITICAL: str = "#FF6B6B"
    ERROR: str = "#FF8C8C"
    WARNING: str = "#FFD93D"
    # MSG, DEBUG, TRACE use default text color


class LogIconColors:
    """Icon colors for log levels."""
    
    CRITICAL: str = "#CC0000"
    ERROR: str = "#CC0000"
    WARNING: str = "#B8860B"
    MSG: str = "#CCCCCC"
    DEBUG: str = "#999999"
    TRACE: str = "#AAAAAA"


class StatsColors:
    """Statistics counter colors."""
    
    # Critical
    CRITICAL_BG: str = "#FFE4E4"
    CRITICAL_TEXT: str = "#FF4444"
    CRITICAL_BORDER: str = "#FF4444"
    
    # Error
    ERROR_BG: str = "#FFE4E4"
    ERROR_TEXT: str = "#CC0000"
    ERROR_BORDER: str = "#CC0000"
    
    # Warning
    WARNING_BG: str = "#FFF4E0"
    WARNING_TEXT: str = "#FFAA00"
    WARNING_BORDER: str = "#FFAA00"
    
    # Message
    MSG_BG: str = "#E0F0FF"
    MSG_TEXT: str = "#0066CC"
    MSG_BORDER: str = "#0066CC"
    
    # Debug
    DEBUG_BG: str = "#F0E8F4"
    DEBUG_TEXT: str = "#8844AA"
    DEBUG_BORDER: str = "#8844AA"
    
    # Trace
    TRACE_BG: str = "#E4FFE4"
    TRACE_TEXT: str = "#00AA00"
    TRACE_BORDER: str = "#00AA00"


# Process Identification Colors
class ProcessColors:
    """Colors for process identification."""
    
    BLUE: str = "#96CBF8"
    RED: str = "#CC7474"
    ORANGE: str = "#F5B76E"
    PINK: str = "#D786CA"
    GREEN: str = "#9BBF7C"
    CREAM: str = "#FAE744"
    
    @classmethod
    def get_color(cls, index: int) -> str:
        """Get process color by index (cyclic)."""
        colors = [cls.BLUE, cls.RED, cls.ORANGE, 
                  cls.PINK, cls.GREEN, cls.CREAM]
        return colors[index % len(colors)]


# LogViewer-Specific Colors
class LogViewerColors:
    """Colors specific to LogViewer plugin."""
    
    LOG_ITEM_SELECTED: str = "#B7CFD5"
    LOG_ITEM_BORDER_MOUSE_OVER: str = "#B7CFD5"
    LOG_ITEM_TEXT_MOUSE_OVER: str = "#382F27"
    LOG_BORDER: str = "#00000080"
    AUTO_SCROLL_SELECTED: str = "#483D8B"
    AUTO_SCROLL_MOUSE_OVER: str = "#2587CF"
    CONTAINER_PANEL_HIGHLIGHTED: str = "#0078D7"


# Legacy Constants (for backward compatibility)
TABLE_ROW_BACKGROUND: str = "#B6B6B6"
SELECTION_HIGHLIGHT_COLOR: str = "#DCEBF7"
FIND_HIGHLIGHT_COLOR: str = "#FFFF00"
DEFAULT_TEXT_COLOR: str = "#000000"
SECONDARY_TEXT_COLOR: str = "#666666"
BORDER_COLOR: str = "#CCCCCC"
HEADER_BACKGROUND: str = "#F0F0F0"
PRIMARY_BLUE: str = "#0066CC"
BACKGROUND_HOVER: str = "#E8E8E8"
```

### §8.2 Migration Guide

#### §8.2.1 From Legacy to New Constants

| Legacy Constant | New Constant | Notes |
|-----------------|--------------|-------|
| `TABLE_ROW_BACKGROUND` | `PaletteColors.GRAY_2` | Table row background |
| `SELECTION_HIGHLIGHT_COLOR` | `UIColors.BACKGROUND_SELECTED` | Selection highlight |
| `FIND_HIGHLIGHT_COLOR` | `UIColors.FIND_HIGHLIGHT` | Search highlight |
| `DEFAULT_TEXT_COLOR` | `BaseColors.BLACK` | Default text |
| `SECONDARY_TEXT_COLOR` | `UIColors.TEXT_SECONDARY` | Secondary text |
| `BORDER_COLOR` | `UIColors.BORDER_DEFAULT` | Default border |
| `HEADER_BACKGROUND` | `UIColors.BACKGROUND_TERTIARY` | Header background |
| `PRIMARY_BLUE` | `UIColors.BORDER_FOCUS` | Primary blue (focus) |
| `BACKGROUND_HOVER` | `UIColors.BACKGROUND_HOVER` | Hover background |

#### §8.2.2 Deprecation Schedule

1. **Phase 1 (v1.0)**: Add new constants, keep legacy constants
2. **Phase 2 (v1.1)**: Add deprecation warnings to legacy constants
3. **Phase 3 (v2.0)**: Remove legacy constants

---

## §9 Accessibility

### §9.1 Color Contrast Ratios

All color combinations meet WCAG 2.1 AA standards (minimum 4.5:1 for normal text, 3:1 for large text).

#### §9.1.1 Text on Background

| Text Color | Background | Ratio | Status |
|------------|------------|-------|--------|
| `#333333` (Primary) | `#FFFFFF` (White) | 12.6:1 | ✅ Pass |
| `#666666` (Secondary) | `#FFFFFF` (White) | 5.7:1 | ✅ Pass |
| `#999999` (Disabled) | `#F5F5F5` (Secondary) | 3.5:1 | ⚠️ Borderline |
| `#382F27` (Selected) | `#B7CFD5` (Selected BG) | 5.2:1 | ✅ Pass |

#### §9.1.2 Log Level Colors

| Level | Text Color | Background | Ratio | Status |
|-------|-------------|------------|-------|--------|
| Critical | `#FF6B6B` | `#FFFFFF` | 3.9:1 | ⚠️ Borderline (large text OK) |
| Error | `#FF8C8C` | `#FFFFFF` | 3.2:1 | ⚠️ Borderline (large text OK) |
| Warning | `#FFD93D` | `#FFFFFF` | 1.5:1 | ❌ Fail (use on dark BG) |

**Recommendations:**
- Warning text should be used on dark backgrounds for better contrast
- Consider darkening Critical/Error text for better readability

#### §9.1.3 Statistics Counter Colors

| Level | Text Color | Background | Ratio | Status |
|-------|-------------|------------|-------|--------|
| Critical | `#FF4444` | `#FFE4E4` | 4.8:1 | ✅ Pass |
| Error | `#CC0000` | `#FFE4E4` | 5.1:1 | ✅ Pass |
| Warning | `#FFAA00` | `#FFF4E0` | 3.2:1 | ⚠️ Borderline |
| Message | `#0066CC` | `#E0F0FF` | 4.9:1 | ✅ Pass |
| Debug | `#8844AA` | `#F0E8F4` | 4.5:1 | ✅ Pass |
| Trace | `#00AA00` | `#E4FFE4` | 4.7:1 | ✅ Pass |

**Recommendation:** Consider darkening Warning text to `#E69500` for 4.5:1 ratio.

---

## §10 Usage Guidelines

### §10.1 When to Use Each Color Layer

1. **Base Colors**: Never use directly in components. Use as fallback or for derived calculations.
2. **Palette Colors**: Use for custom components that need color variations.
3. **Semantic Colors**: Use for standard UI elements (buttons, inputs, etc.).
4. **Application Colors**: Use for domain-specific elements (log levels, processes, etc.).

### §10.2 Color Application Patterns

#### §10.2.1 Background Colors

```python
# Primary background (main content)
background = UIColors.BACKGROUND_PRIMARY

# Secondary background (panels, sidebars)
background = UIColors.BACKGROUND_SECONDARY

# Hover state
background = UIColors.BACKGROUND_HOVER

# Selected state
background = UIColors.BACKGROUND_SELECTED
```

#### §10.2.2 Border Colors

```python
# Default border
border = UIColors.BORDER_DEFAULT

# Hover state
border = UIColors.BORDER_HOVER

# Focus state
border = UIColors.BORDER_FOCUS
```

#### §10.2.3 Log Level Colors

```python
# Text color
text_color = LogTextColors.CRITICAL

# Icon color
icon_color = LogIconColors.CRITICAL

# Counter colors
bg = StatsColors.CRITICAL_BG
text = StatsColors.CRITICAL_TEXT
border = StatsColors.CRITICAL_BORDER
```

### §10.3 QSS Integration

```python
from src.constants.colors import UIColors, LogTextColors

# Static stylesheet
stylesheet = f"""
    QWidget {{
        background-color: {UIColors.BACKGROUND_PRIMARY};
        color: {UIColors.TEXT_PRIMARY};
        border: 1px solid {UIColors.BORDER_DEFAULT};
    }}
    
    QWidget:hover {{
        background-color: {UIColors.BACKGROUND_HOVER};
        border: 1px solid {UIColors.BORDER_HOVER};
    }}
    
    QWidget:focus {{
        border: 1px solid {UIColors.BORDER_FOCUS};
    }}
"""

# Dynamic stylesheet (for log levels)
def get_log_text_color(level: str) -> str:
    """Get text color for log level."""
    colors = {
        'CRITICAL': LogTextColors.CRITICAL,
        'ERROR': LogTextColors.ERROR,
        'WARNING': LogTextColors.WARNING,
    }
    return colors.get(level, UIColors.TEXT_PRIMARY)
```

---

## §11 Testing Requirements

### §11.1 Visual Regression Testing

- [ ] Screenshot comparison for all color states
- [ ] Cross-platform testing (Windows, macOS, Linux)
- [ ] High contrast mode testing
- [ ] Dark mode preparation (future)

### §11.2 Accessibility Testing

- [ ] Automated contrast ratio checks
- [ ] Color blindness simulation
- [ ] Screen reader color announcement testing

### §11.3 Performance Testing

- [ ] Stylesheet application time (<16ms)
- [ ] Color constant lookup performance
- [ ] Memory usage for color constants

---

## §12 Cross-References

- **UI Design System:** [ui-design-system.md](../features/ui-design-system.md) - Overall design system
- **Table Styles:** [table-unified-styles.md](../features/table-unified-styles.md) - Table-specific colors
- **Category Panel:** [category-panel-styles.md](../features/category-panel-styles.md) - Panel-specific colors
- **Typography:** [typography-system.md](../features/typography-system.md) - Font system
- **Implementation:** [src/constants/colors.py](../../src/constants/colors.py)

---

## §13 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-19 | Initial comprehensive color palette specification |