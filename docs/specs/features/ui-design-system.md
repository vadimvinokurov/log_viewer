# UI Design System Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application - PySide6/Qt)

---

## §1 Overview

This document defines the comprehensive UI Design System for the Log Viewer application, covering visual style, layout, components, accessibility, and micro-animations. The design system ensures consistency, maintainability, and a professional user experience.

### §1.1 Design Principles

1. **Clarity**: Information hierarchy is immediately apparent
2. **Efficiency**: Minimal clicks to accomplish tasks
3. **Consistency**: Uniform visual language across all components
4. **Accessibility**: WCAG 2.1 AA compliance
5. **Performance**: Responsive interactions with minimal latency

### §1.2 Platform Considerations

- **Primary Platform**: Desktop (Windows, macOS)
- **Framework**: PySide6 (Qt for Python)
- **Styling**: QSS (Qt Style Sheets)
- **Font Rendering**: Platform-specific font stacks

---

## §2 Visual Style

### §2.1 Color Palette

#### §2.1.1 Primary Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Primary Blue | `#0066CC` | 0, 102, 204 | Focus states, selection, primary actions |
| Primary Blue Light | `#DCEBF7` | 220, 235, 247 | Selection background, hover states |
| Primary Blue Dark | `#004C99` | 0, 76, 153 | Active states (future use) |

#### §2.1.2 Neutral Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Background Primary | `#FFFFFF` | 255, 255, 255 | Main content background |
| Background Secondary | `#F5F5F5` | 245, 245, 245 | Panel backgrounds, toolbar |
| Background Tertiary | `#F0F0F0` | 240, 240, 240 | Main window background |
| Background Hover | `#E8E8E8` | 232, 232, 232 | Hover states |
| Background Active | `#D0D0D0` | 208, 208, 208 | Active/pressed states |
| Border Default | `#C0C0C0` | 192, 192, 192 | Default borders |
| Border Hover | `#A0A0A0` | 160, 160, 160 | Hover borders |
| Text Primary | `#333333` | 51, 51, 51 | Primary text |
| Text Secondary | `#666666` | 102, 102, 102 | Secondary text |
| Text Disabled | `#999999` | 153, 153, 153 | Disabled text |
| Text Inverted | `#FFFFFF` | 255, 255, 255 | Text on dark backgrounds |

#### §2.1.3 Semantic Colors - Log Levels

| Level | Background | Text/Icon | Border | Usage |
|-------|------------|-----------|--------|-------|
| CRITICAL | `#FFE4E4` | `#FF4444` | `#FF4444` | Critical errors |
| ERROR | `#FFE4E4` | `#CC0000` | `#CC0000` | Error messages |
| WARNING | `#FFF4E0` | `#FFAA00` | `#FFAA00` | Warning messages |
| MSG | `#E0F0FF` | `#0066CC` | `#0066CC` | Informational messages |
| DEBUG | `#F0E8F4` | `#8844AA` | `#8844AA` | Debug messages |
| TRACE | `#E4FFE4` | `#00AA00` | `#00AA00` | Trace messages |

#### §2.1.4 Log Entry Background Colors

| Level | Background | Usage |
|-------|------------|-------|
| CRITICAL | `#FF6B6B` | Critical log row background |
| ERROR | `#FF8C8C` | Error log row background |
| WARNING | `#FFD93D` | Warning log row background |
| MSG | `#FFFFFF` | Message log row background |
| DEBUG | `#E8E8E8` | Debug log row background |
| TRACE | `#F5F5F5` | Trace log row background |

#### §2.1.5 Special Colors

| Name | Hex | Usage |
|------|-----|-------|
| Find Highlight | `#FFFF00` | Search result highlighting |
| Tooltip Background | `#333333` | Tooltip background |
| Tooltip Text | `#FFFFFF` | Tooltip text |
| Tooltip Border | `#555555` | Tooltip border |

### §2.2 Typography

#### §2.2.1 Font Stacks

**Primary Font (UI Elements):**
```css
/* macOS */
font-family: "SF Pro Text", "Helvetica Neue", Arial, sans-serif;

/* Windows / Linux */
font-family: "Segoe UI", "Roboto", Arial, sans-serif;
```

**Monospace Font (Code/Logs):**
```css
/* macOS */
font-family: "Menlo", "Monaco", "Courier New", monospace;

/* Windows / Linux */
font-family: "Consolas", "Courier New", monospace;
```

#### §2.2.2 Type Scale

| Element | Size | Weight | Line Height | Usage |
|---------|------|--------|-------------|-------|
| Body | 9pt | Regular (400) | 1.4 | Default text, labels |
| Body Bold | 9pt | Bold (700) | 1.4 | Emphasized text, counters |
| Header | 11pt | Bold (700) | 1.3 | Dialog titles |
| Small | 8pt | Regular (400) | 1.3 | Tooltips, hints |
| Table Header | 9pt | Regular (400) | 1.0 | Column headers |
| Log Entry | 9pt | Regular (400) | 1.0 | Log table rows |

#### §2.2.3 Text Colors

| Context | Color | Usage |
|----------|-------|-------|
| Primary Text | `#333333` | Normal text |
| Secondary Text | `#666666` | Placeholder, hints |
| Disabled Text | `#999999` | Disabled states |
| Link Text | `#0066CC` | Interactive links |
| Selection Text | `#000000` | Selected text |

### §2.3 Iconography

#### §2.3.1 Icon Set

The application uses Unicode symbols for icons to ensure cross-platform compatibility:

| Icon | Unicode | Name | Usage |
|------|---------|------|-------|
| 📁 | U+1F4C1 | Folder | Open file |
| 🔄 | U+1F504 | Refresh | Reload file |
| ⛔ | U+26D4 | Critical | Critical level |
| 🛑 | U+1F6D1 | Error | Error level |
| ⚠️ | U+26A0 | Warning | Warning level |
| ℹ️ | U+2139 | Info | Message level |
| 🟪 | U+1F7EA | Purple | Debug level |
| 🟩 | U+1F7E9 | Green | Trace level |
| 🔍 | U+1F50D | Search | Search, custom category |
| ▼ | U+25BC | Down | Expand indicator |
| ▲ | U+25B2 | Up | Collapse indicator |

#### §2.3.2 Icon Sizing

| Context | Size | Usage |
|---------|------|-------|
| Toolbar Button | 16×16px | Action buttons |
| Counter Icon | 16px width | Statistics counters |
| Tree Indicator | 6pt font | Expand/collapse arrows |
| Status Icon | 16px width | Status bar icons |

---

## §3 Grid System and Layout

### §3.1 Grid Principles

1. **Base Unit**: 4px for all spacing calculations
2. **Grid Columns**: 12-column system for flexible layouts
3. **Gutter Width**: 8px between columns
4. **Breakpoints**: Not applicable (fixed desktop window)

### §3.2 Spacing Scale

All spacing uses multiples of 4px:

| Token | Value | Usage |
|-------|-------|-------|
| `space-xs` | 2px | Tight spacing (icon-text gap) |
| `space-sm` | 4px | Compact spacing (button padding) |
| `space-md` | 8px | Default spacing (widget margins) |
| `space-lg` | 12px | Loose spacing (section gaps) |
| `space-xl` | 16px | Extra loose (panel padding) |

### §3.3 Layout Constants

#### §3.3.1 Window Dimensions

| Property | Value | Description |
|----------|-------|-------------|
| Minimum Width | 1280px | Minimum window width |
| Minimum Height | 720px | Minimum window height |
| Default Width | 1400px | Initial window width |
| Default Height | 900px | Initial window height |

#### §3.3.2 Splitter Ratios

| Panel | Ratio | Description |
|-------|-------|-------------|
| Log Table | 75% | Left panel (log display) |
| Category Panel | 25% | Right panel (filtering) |

#### §3.3.3 Table Dimensions

| Property | Value | Description |
|----------|-------|-------------|
| Row Height | 16px | Height of each log row |
| Header Height | 20px | Table header height |
| Time Column | 80px | Timestamp column width |
| Category Column | 100px | Category column width |
| Type Column | 60px | Log level column width |
| Message Column | Stretch | Message column (fills remaining) |
| Min Column Width | 5px | Minimum column width |

#### §3.3.4 Component Dimensions

| Component | Property | Value |
|-----------|----------|-------|
| Button | Min Width | 60px |
| Button | Padding | 4px 12px |
| Button | Border Radius | 3px |
| Input | Padding | 4px 6px |
| Input | Border Radius | 3px |
| Counter | Padding | 4px 8px (horizontal), 2px (vertical) |
| Counter | Icon Width | 16px |
| Toggle Strip | Height | 6px |
| Status Bar | Min Height | 24px |

### §3.4 Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MENU BAR (QMenuBar)                                                         │
│  Height: auto | Background: #F5F5F5 | Border-Bottom: 1px #C0C0C0            │
├─────────────────────────────────────────────────────────────────────────────┤
│  TOOLBAR AREA (CollapsiblePanel)                                            │
│  Height: ~32px | Background: #F5F5F5 | Border-Bottom: 1px #C0C0C0          │
│  ┌────┬────┬───┬────────────────────────────────────┬───────┐              │
│  │ 📁 │ 🔄 │ | │ [Search Input...]                   │ Mode▼ │              │
│  └────┴────┴───┴────────────────────────────────────┴───────┘              │
│  ──────────────────────────────────────────────────────────────────────────│
│  Toggle Strip (Height: 6px) | Arrow: ▼/▲ | Click to collapse               │
├─────────────────────────────────────────────────────────────────────────────┤
│                           │                                                 │
│    LOG TABLE VIEW         │    CATEGORY PANEL                              │
│    (75% width)            │    (25% width)                                 │
│                           │                                                 │
│  ┌─────┬──────────┬────┬───┐│  ┌─────────────────────────────────────────────┐│
│  │Time │Category  │Type│Msg││  │ [Categories | Processes | Threads]         ││
│  ├─────┼──────────┼────┼───┤│  ├─────────────────────────────────────────────┤│
│  │...  │...       │... │...││  │ 🔍 [Search categories...]                  ││
│  │...  │...       │... │...││  ├─────────────────────────────────────────────┤│
│  │...  │...       │... │...││  │ ☑ Category1                                ││
│  │...  │...       │... │...││  │   ☑ Subcategory1                           ││
│  │...  │...       │... │...││  │   ☑ Subcategory2                           ││
│  └─────┴──────────┴────┴───┘│  │ ☑ Category2                                ││
│                           │  │ [Check All] [Uncheck All]                    ││
│                           │  │ [Add Custom] [Edit Custom] [Remove Custom]   ││
│                           │  └─────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  STATUS BAR (Height: 24px)                                                  │
│  filename.log  │                    │ [⛔ 0] [🛑 0] [⚠️ 0] [ℹ️ 0] [🟪 0] [🟩 0] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## §4 Component Library

### §4.1 Buttons

#### §4.1.1 Push Button

**States:**

| State | Background | Border | Text | Border Radius |
|-------|------------|--------|------|---------------|
| Default | `#F5F5F5` | `#C0C0C0` | `#333333` | 3px |
| Hover | `#E8E8E8` | `#A0A0A0` | `#333333` | 3px |
| Active/Pressed | `#D0D0D0` | `#A0A0A0` | `#333333` | 3px |
| Disabled | `#F5F5F5` | `#D0D0D0` | `#999999` | 3px |
| Focus | `#F5F5F5` | `#0066CC` | `#333333` | 3px |

**Dimensions:**
- Min Width: 60px
- Padding: 4px 12px
- Font: 9pt Regular

**QSS Implementation:**
```css
QPushButton {
    background-color: #F5F5F5;
    border: 1px solid #C0C0C0;
    border-radius: 3px;
    padding: 4px 12px;
    min-width: 60px;
}

QPushButton:hover {
    background-color: #E8E8E8;
    border: 1px solid #A0A0A0;
}

QPushButton:pressed {
    background-color: #D0D0D0;
}

QPushButton:disabled {
    background-color: #F5F5F5;
    color: #999999;
    border: 1px solid #D0D0D0;
}
```

#### §4.1.2 Tool Button

**States:**

| State | Background | Border | Border Radius |
|-------|------------|--------|---------------|
| Default | Transparent | Transparent | 3px |
| Hover | `#E8E8E8` | `#C0C0C0` | 3px |
| Active/Pressed | `#D0D0D0` | `#C0C0C0` | 3px |
| Disabled | Transparent | Transparent | 3px |

**Dimensions:**
- Padding: 4px
- Icon Size: 16×16px

### §4.2 Input Fields

#### §4.2.1 Line Edit (Text Input)

**States:**

| State | Background | Border | Text | Border Radius |
|-------|------------|--------|------|---------------|
| Default | `#FFFFFF` | `#C0C0C0` | `#333333` | 3px |
| Focus | `#FFFFFF` | `#0066CC` | `#333333` | 3px |
| Disabled | `#F5F5F5` | `#C0C0C0` | `#999999` | 3px |
| Error | `#FFFFFF` | `#CC0000` | `#333333` | 3px |

**Dimensions:**
- Padding: 4px 6px
- Min Width: 200px (for search inputs)

**QSS Implementation:**
```css
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #C0C0C0;
    border-radius: 3px;
    padding: 4px 6px;
    selection-background-color: #DCEBF7;
}

QLineEdit:focus {
    border: 1px solid #0066CC;
}

QLineEdit:disabled {
    background-color: #F5F5F5;
    color: #999999;
}
```

#### §4.2.2 Combo Box

**States:**

| State | Background | Border | Dropdown |
|-------|------------|--------|----------|
| Default | `#FFFFFF` | `#C0C0C0` | Arrow icon |
| Hover | `#FFFFFF` | `#A0A0A0` | Arrow icon |
| Disabled | `#F5F5F5` | `#D0D0D0` | Arrow icon |
| Focus | `#FFFFFF` | `#0066CC` | Arrow icon |

**Dimensions:**
- Padding: 4px 8px
- Min Width: 80px
- Dropdown Width: 20px

### §4.3 Tables

#### §4.3.1 Table View

**States:**

| Element | Background | Border | Text |
|---------|------------|--------|------|
| Table Background | `#FFFFFF` | `#C0C0C0` | `#333333` |
| Grid Lines | - | `#E0E0E0` | - |
| Selected Row | `#DCEBF7` | - | `#000000` |
| Header Background | `#F5F5F5` | - | `#333333` |
| Header Hover | `#E8E8E8` | - | `#333333` |

**Dimensions:**
- Row Height: 16px
- Header Height: 20px
- Cell Padding: 0px

**QSS Implementation:**
```css
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #C0C0C0;
    gridline-color: #E0E0E0;
    selection-background-color: #DCEBF7;
    selection-color: #000000;
}

QTableWidget::item {
    padding: 0px;
    border-bottom: 1px solid #E0E0E0;
}

QTableWidget::item:selected {
    background-color: #DCEBF7;
    color: #000000;
}

QHeaderView::section {
    background-color: #F5F5F5;
    border: none;
    border-bottom: 1px solid #C0C0C0;
    border-right: 1px solid #E0E0E0;
    padding: 0px;
    text-align: center;
}

QHeaderView::section:hover {
    background-color: #E8E8E8;
}
```

### §4.4 Tree View

#### §4.4.1 Tree View with Checkboxes

**States:**

| Element | Background | Border | Text |
|---------|------------|--------|------|
| Tree Background | `#F5F5F5` | None | `#333333` |
| Selected Item | `#DCEBF7` | - | `#000000` |
| Hover Item | `#E8E8E8` | - | `#333333` |

**Checkbox States:**

| State | Border | Background | Check Color |
|-------|--------|------------|-------------|
| Unchecked | `#A0A0A0` | `#FFFFFF` | - |
| Checked | `#0066CC` | `#0066CC` | White checkmark |
| Partially Checked | `#0066CC` | `#DCEBF7` | Partial indicator |

**Dimensions:**
- Item Padding: 2px 4px
- Checkbox Size: 14×14px
- Indentation: 16px per level

**QSS Implementation:**
```css
QTreeView {
    background-color: #F5F5F5;
    border: none;
    selection-background-color: #DCEBF7;
    selection-color: #000000;
}

QTreeView::item {
    padding: 2px 4px;
    border: none;
}

QTreeView::item:selected {
    background-color: #DCEBF7;
    color: #000000;
}

QTreeView::item:hover {
    background-color: #E8E8E8;
}

QTreeView::indicator {
    width: 14px;
    height: 14px;
}

QTreeView::indicator:unchecked {
    border: 1px solid #A0A0A0;
    background-color: #FFFFFF;
}

QTreeView::indicator:checked {
    border: 1px solid #0066CC;
    background-color: #0066CC;
}
```

### §4.5 Tabs

#### §4.5.1 Tab Widget

**States:**

| Element | Background | Border | Text |
|---------|------------|--------|------|
| Pane | `#FFFFFF` | `#C0C0C0` | - |
| Tab Default | `#E8E8E8` | None | `#333333` |
| Tab Selected | `#F0F0F0` | Bottom: `#0066CC` | `#333333` |
| Tab Hover | `#F0F0F0` | None | `#333333` |

**Dimensions:**
- Tab Padding: 6px 16px
- Tab Margin: 2px (right)
- Selected Border: 2px solid `#0066CC` (bottom)

**QSS Implementation:**
```css
QTabWidget::pane {
    border: 1px solid #C0C0C0;
    background-color: #FFFFFF;
}

QTabBar::tab {
    background-color: #E8E8E8;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 16px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #F0F0F0;
    border-bottom: 2px solid #0066CC;
}

QTabBar::tab:hover:!selected {
    background-color: #F0F0F0;
}
```

### §4.6 Counter Widget

#### §4.6.1 Statistics Counter

**States:**

| State | Background | Border | Text |
|-------|------------|--------|------|
| Active | Level color (light) | Level color | Level color (dark) |
| Inactive | `#F5F5F5` | Level color (2px) | `#999999` |
| Hover | Level color (light) | Level color (bold) | Level color (dark) |

**Dimensions:**
- Padding: 4px 8px (horizontal), 2px (vertical)
- Icon Width: 16px
- Border Radius: 3px

**Color Mapping:**

| Level | Background | Text/Border | Inactive Border |
|-------|------------|-------------|-----------------|
| Critical | `#FFE4E4` | `#FF4444` | `#FF4444` |
| Error | `#FFE4E4` | `#CC0000` | `#CC0000` |
| Warning | `#FFF4E0` | `#FFAA00` | `#FFAA00` |
| Msg | `#E0F0FF` | `#0066CC` | `#0066CC` |
| Debug | `#F0E8F4` | `#8844AA` | `#8844AA` |
| Trace | `#E4FFE4` | `#00AA00` | `#00AA00` |

### §4.7 Scroll Bars

#### §4.7.1 Vertical Scroll Bar

**States:**

| Element | Background | Dimensions |
|---------|------------|-------------|
| Track | `#F0F0F0` | Width: 12px |
| Handle Default | `#C0C0C0` | Min Height: 20px, Radius: 6px |
| Handle Hover | `#A0A0A0` | Min Height: 20px, Radius: 6px |

**QSS Implementation:**
```css
QScrollBar:vertical {
    background-color: #F0F0F0;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #C0C0C0;
    min-height: 20px;
    border-radius: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #A0A0A0;
}
```

### §4.8 Collapsible Panel

#### §4.8.1 Toggle Strip

**States:**

| State | Background | Border | Arrow |
|-------|------------|--------|-------|
| Default | `#F0F0F0` | Top: `#C0C0C0` | `#888888` |
| Hover | `#E8E8E8` | Top: `#A0A0A0` | `#888888` |

**Dimensions:**
- Height: 6px
- Arrow Font Size: 6pt
- Arrow: ▼ (expanded) / ▲ (collapsed)

**Animation:**
- Duration: 150ms
- Easing: OutCubic
- Property: Arrow rotation (0° → 180°)

### §4.9 Status Bar

#### §4.9.1 Main Status Bar

**States:**

| Element | Background | Border | Text |
|---------|------------|--------|------|
| Background | `#F5F5F5` | Top: `#C0C0C0` | `#333333` |
| File Label | Transparent | None | `#333333` |
| Status Message | Transparent | None | `#666666` |

**Dimensions:**
- Min Height: 24px
- File Label Padding: 0 8px

### §4.10 Tooltips

**States:**

| Element | Background | Border | Text |
|---------|------------|--------|------|
| Tooltip | `#333333` | `#555555` | `#FFFFFF` |

**Dimensions:**
- Padding: 4px
- Border Radius: 2px

**QSS Implementation:**
```css
QToolTip {
    background-color: #333333;
    color: #FFFFFF;
    border: 1px solid #555555;
    padding: 4px;
    border-radius: 2px;
}
```

---

## §5 Accessibility (WCAG 2.1)

### §5.1 Perceivable

#### §5.1.1 Text Alternatives

- All icons have Unicode alternatives (text-based)
- Images use descriptive tooltips
- Custom categories show pattern in tooltip

#### §5.1.2 Color Contrast

**Minimum Contrast Ratios (WCAG AA):**

| Text Type | Foreground | Background | Ratio | Status |
|-----------|-------------|------------|-------|--------|
| Primary Text | `#333333` | `#FFFFFF` | 12.6:1 | ✅ Pass |
| Secondary Text | `#666666` | `#FFFFFF` | 5.7:1 | ✅ Pass |
| Disabled Text | `#999999` | `#F5F5F5` | 3.5:1 | ⚠️ Borderline |
| Critical Counter | `#FF4444` | `#FFE4E4` | 4.8:1 | ✅ Pass |
| Error Counter | `#CC0000` | `#FFE4E4` | 5.1:1 | ✅ Pass |
| Warning Counter | `#FFAA00` | `#FFF4E0` | 3.2:1 | ⚠️ Borderline |
| Msg Counter | `#0066CC` | `#E0F0FF` | 4.9:1 | ✅ Pass |
| Debug Counter | `#8844AA` | `#F0E8F4` | 4.5:1 | ✅ Pass |
| Trace Counter | `#00AA00` | `#E4FFE4` | 4.7:1 | ✅ Pass |

**Recommendations:**
- Warning counter text: Consider darkening to `#E69500` (4.5:1 ratio)
- Disabled text: Consider using `#777777` for better contrast

#### §5.1.3 Distinguishable

- **Separation**: Clear visual separation between sections
- **Hover States**: Distinct hover feedback on all interactive elements
- **Focus Indicators**: Blue border (`#0066CC`) on focus
- **Selection**: Light blue background (`#DCEBF7`) for selection

### §5.2 Operable

#### §5.2.1 Keyboard Navigation

**Required Shortcuts:**

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+O` | Open file | Global |
| `F5` | Refresh | Global |
| `Ctrl+W` | Close file | Global |
| `Ctrl+F` | Find | Global |
| `Ctrl+Q` | Exit | Global |
| `Ctrl+C` | Copy | Table |
| `Ctrl+A` | Select all | Table |
| `Escape` | Clear search | Search input |
| `Enter` | Apply filter | Search input |
| `Tab` | Next field | Global |
| `Shift+Tab` | Previous field | Global |

#### §5.2.2 Focus Management

- **Tab Order**: Logical left-to-right, top-to-bottom
- **Focus Visible**: Blue border (`#0066CC`) on all focusable elements
- **Focus Trap**: Dialogs trap focus within
- **Initial Focus**: First interactive element in panel

#### §5.2.3 Timing

- No time limits on user interactions
- Animations are optional and can be disabled
- Status messages auto-dismiss after 3 seconds

### §5.3 Understandable

#### §5.3.1 Readable

- **Language**: English (en-US)
- **Abbreviations**: Tooltips for abbreviated labels
- **Reading Level**: Technical audience assumed

#### §5.3.2 Predictable

- **Consistent Navigation**: Same layout across all views
- **Consistent Identification**: Same icons for same actions
- **Change on Request**: No automatic context changes

#### §5.3.3 Input Assistance

- **Error Identification**: Red border on invalid input
- **Labels**: All inputs have associated labels
- **Help**: Tooltips on complex controls
- **Error Recovery**: Clear error messages with recovery suggestions

### §5.4 Robust

#### §5.4.1 Compatible

- **Assistive Technology**: Qt accessibility features enabled
- **Name, Role, Value**: All widgets have accessible names
- **Status Changes**: Status bar announces changes

### §5.5 Accessibility Testing Checklist

- [ ] All interactive elements keyboard accessible
- [ ] Focus order is logical
- [ ] Focus indicators visible
- [ ] Color contrast meets AA standards
- [ ] Text resizable up to 200%
- [ ] No text in images
- [ ] Error messages clear and actionable
- [ ] Status changes announced
- [ ] Tooltips available for all controls
- [ ] Alternative text for icons

---

## §6 Micro-Animations

### §6.1 Animation Principles

1. **Purpose**: Every animation serves a functional purpose
2. **Performance**: Animations complete within 200ms
3. **Subtlety**: Animations enhance, not distract
4. **Consistency**: Same animation for same interaction type

### §6.2 Animation Catalog

#### §6.2.1 Toggle Strip Arrow Rotation

**Trigger:** User clicks toggle strip  
**Duration:** 150ms  
**Easing:** OutCubic  
**Property:** Rotation (0° → 180°)  
**Implementation:**
```python
self._rotation_animation = QPropertyAnimation(self, b"arrowRotation")
self._rotation_animation.setDuration(150)
self._rotation_animation.setEasingCurve(QEasingCurve.OutCubic)
```

#### §6.2.2 Tree Expansion

**Trigger:** User expands/collapses tree node  
**Duration:** System default (typically 200ms)  
**Easing:** Linear  
**Property:** Height animation  
**Implementation:**
```python
self._tree_view.setAnimated(True)
```

#### §6.2.3 Button Press

**Trigger:** User presses button  
**Duration:** Immediate (no animation)  
**Effect:** Background color change to `#D0D0D0`  
**Recovery:** On release, return to hover or default state

#### §6.2.4 Hover Transitions

**Trigger:** Mouse enter/leave  
**Duration:** Immediate (no animation)  
**Effect:** Background color change  
**Elements:** Buttons, tree items, counters, toggle strip

#### §6.2.5 Focus Ring

**Trigger:** Element receives focus  
**Duration:** Immediate  
**Effect:** Border color change to `#0066CC`  
**Recovery:** On blur, return to default border

### §6.3 Animation Performance

| Animation | Duration | CPU Impact | GPU Accelerated |
|-----------|----------|------------|-----------------|
| Arrow Rotation | 150ms | Low | Yes (transform) |
| Tree Expansion | 200ms | Low | Yes (height) |
| Hover State | 0ms | None | N/A |
| Focus State | 0ms | None | N/A |

### §6.4 Animation Best Practices

1. **Avoid over-animation**: Only animate state changes
2. **Keep it fast**: All animations under 200ms
3. **Use easing**: OutCubic for smooth deceleration
4. **Test on low-end**: Verify performance on slower hardware
5. **Respect preferences**: Check system animation settings

---

## §7 Implementation Guidelines

### §7.1 QSS Organization

**File Structure:**
```
src/styles/
├── __init__.py
└── stylesheet.py
```

**Function Organization:**
```python
# Global styles
def get_application_stylesheet() -> str

# Component styles
def get_table_stylesheet() -> str
def get_tree_stylesheet() -> str
def get_tab_stylesheet() -> str
def get_toolbar_stylesheet() -> str
def get_search_input_stylesheet() -> str
def get_collapsible_panel_stylesheet() -> str

# Dynamic styles
def get_counter_style(counter_type: str) -> dict[str, str]
def get_statistics_counter_stylesheet(bg_color: str, text_color: str, border_color: str | None = None) -> str
```

### §7.2 Color Constants

**File:** `src/constants/colors.py`

**Organization:**
```python
class LogColors:
    """Background colors for log entries."""
    CRITICAL: str = "#FF6B6B"
    ERROR: str = "#FF8C8C"
    # ...

class LogIconColors:
    """Icon colors for log levels."""
    CRITICAL: str = "#CC0000"
    # ...

class StatsColors:
    """Statistics counter colors."""
    CRITICAL_BG: str = "#FFE4E4"
    CRITICAL_TEXT: str = "#FF4444"
    # ...

# UI element colors
SELECTION_HIGHLIGHT_COLOR: str = "#dcebf7"
FIND_HIGHLIGHT_COLOR: str = "#FFFF00"
# ...
```

### §7.3 Dimension Constants

**File:** `src/constants/dimensions.py`

**Organization:**
```python
# Table dimensions
TABLE_ROW_HEIGHT: int = 16
TABLE_HEADER_HEIGHT: int = 20

# Column widths
TIME_COLUMN_WIDTH: int = 80
CATEGORY_COLUMN_WIDTH: int = 100
# ...

# Layout ratios
SPLITTER_LEFT_RATIO: int = 75
SPLITTER_RIGHT_RATIO: int = 25
```

### §7.4 Component Implementation

**Pattern:**
1. Define constants in `src/constants/`
2. Reference constants in QSS
3. Apply QSS via `setStyleSheet()`
4. Use dynamic styles for state-dependent styling

**Example:**
```python
from src.constants.colors import StatsColors
from src.styles.stylesheet import get_counter_style

class CounterWidget(QWidget):
    def _apply_style(self) -> None:
        colors = get_counter_style(self._counter_type)
        if self._visible:
            style = f"""
                CounterWidget {{
                    background-color: {colors['bg']};
                    border: 1px solid {colors['border']};
                    border-radius: 3px;
                }}
            """
        else:
            style = f"""
                CounterWidget {{
                    background-color: #f5f5f5;
                    border: 2px solid {colors['border']};
                    border-radius: 3px;
                }}
            """
        self.setStyleSheet(style)
```

---

## §8 Testing Requirements

### §8.1 Visual Regression Testing

- Screenshot comparison for all components
- State variations (default, hover, active, disabled, focus)
- Cross-platform testing (Windows, macOS)

### §8.2 Accessibility Testing

- Automated contrast ratio checks
- Keyboard navigation testing
- Screen reader compatibility testing

### §8.3 Performance Testing

- Animation frame rate (target: 60fps)
- Style application time (target: <16ms)
- Memory usage for stylesheets

---

## §9 Cross-References

- **Colors:** [src/constants/colors.py](../../src/constants/colors.py)
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)
- **Stylesheet:** [src/styles/stylesheet.py](../../src/styles/stylesheet.py)
- **UI Components:** [ui-components.md](ui-components.md)
- **Main Controller:** [main-controller.md](main-controller.md)

---

## §10 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial UI Design System specification |