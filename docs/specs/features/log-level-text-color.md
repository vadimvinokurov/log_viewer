# Log Level Text Color Specification

**Version:** 1.0  
**Last Updated:** 2026-03-18  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This specification defines the change from background-color-based log level highlighting to text-color-based highlighting. Instead of coloring the entire row background, the text color will be changed based on the log level.

### §1.1 Current Behavior

Log levels (CRITICAL, ERROR, WARNING, MSG, DEBUG, TRACE) currently display with colored backgrounds:
- CRITICAL: Red background (#FF6B6B)
- ERROR: Light red background (#FF8C8C)
- WARNING: Yellow background (#FFD93D)
- MSG/DEBUG/TRACE: Gray background (#B6B6B6)

### §1.2 New Behavior

Log levels will display with colored text instead of colored backgrounds:
- CRITICAL: Red text (#FF6B6B)
- ERROR: Light red text (#FF8C8C)
- WARNING: Yellow text (#FFD93D)
- MSG/DEBUG/TRACE: Default text color (no special highlighting)

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LogTableModel                             │
│  - Provides ForegroundRole for log level text color         │
│  - No longer provides BackgroundRole for log levels         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    HighlightDelegate                          │
│  - Renders text with foreground color                        │
│  - Applies log level color to entire row text                │
│  - User highlights still use background color                │
└─────────────────────────────────────────────────────────────┘
```

### §2.2 Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/constants/colors.py` | Modify | Rename `LogColors` to `LogTextColors` |
| `src/constants/log_levels.py` | No change | Already has `text_color` field |
| `src/views/log_table_view.py` | Modify | Change `LEVEL_COLORS` to text colors |
| `src/views/delegates/highlight_delegate.py` | Modify | Apply foreground color instead of background |
| `src/styles/stylesheet.py` | No change | Default row background remains white |

---

## §3 Data Model

### §3.1 Color Constants

**Current (to be removed):**
```python
# src/constants/colors.py
class LogColors:
    """Background colors for log levels."""
    CRITICAL: str = "#FF6B6B"
    ERROR: str = "#FF8C8C"
    WARNING: str = "#FFD93D"
    MSG: str = "#B6B6B6"
    DEBUG: str = "#B6B6B6"
    TRACE: str = "#B6B6B6"
```

**New (to be added):**
```python
# src/constants/colors.py
class LogTextColors:
    """Text colors for log levels.
    
    These colors are used for the text foreground in log entries
    to visually distinguish different log levels.
    
    Ref: docs/specs/features/log-level-text-color.md §3.1
    
    Note: MSG, DEBUG, and TRACE levels use default text color (no special color).
    """
    
    CRITICAL: str = "#FF6B6B"
    """Text color for CRITICAL level log entries."""
    
    ERROR: str = "#FF8C8C"
    """Text color for ERROR level log entries."""
    
    WARNING: str = "#FFD93D"
    """Text color for WARNING level log entries."""
    
    # MSG, DEBUG, TRACE use default text color (no special color)
```

### §3.2 Level-to-Color Mapping

**Current (in `log_table_view.py`):**
```python
LEVEL_COLORS = {
    LogLevel.CRITICAL: QColor(LogColors.CRITICAL),
    LogLevel.ERROR: QColor(LogColors.ERROR),
    LogLevel.WARNING: QColor(LogColors.WARNING),
    LogLevel.MSG: None,  # Default white
    LogLevel.DEBUG: QColor(LogColors.DEBUG),
    LogLevel.TRACE: QColor(LogColors.TRACE),
}
```

**New:**
```python
LEVEL_TEXT_COLORS = {
    LogLevel.CRITICAL: QColor(LogTextColors.CRITICAL),
    LogLevel.ERROR: QColor(LogTextColors.ERROR),
    LogLevel.WARNING: QColor(LogTextColors.WARNING),
    LogLevel.MSG: None,  # Default text color
    LogLevel.DEBUG: None,  # Default text color
    LogLevel.TRACE: None,  # Default text color
}
```

---

## §4 API Changes

### §4.1 LogTableModel.data()

**Current Implementation (lines 188-193):**
```python
elif role == Qt.BackgroundRole:
    return LEVEL_COLORS.get(entry.level)

elif role == Qt.ForegroundRole:
    if col == self.COL_TYPE:
        return LEVEL_ICON_COLORS.get(entry.level)
```

**New Implementation:**
```python
elif role == Qt.ForegroundRole:
    # Log level text color applies to all columns
    level_color = LEVEL_TEXT_COLORS.get(entry.level)
    if level_color:
        return level_color
    
    # Icon column still uses icon colors if no level color
    if col == self.COL_TYPE:
        return LEVEL_ICON_COLORS.get(entry.level)
```

### §4.2 HighlightDelegate.paint()

**Current Implementation (lines 59-71):**
```python
# Get background color from model
bg_color = index.data(Qt.BackgroundRole)

# Draw background
if bg_color:
    painter.fillRect(option.rect, bg_color)
else:
    # Draw default background
    painter.fillRect(option.rect, option.palette.base())

# Draw selection highlight if selected
if option.state & QStyle.State_Selected:
    painter.fillRect(option.rect, QColor("#dcebf7"))
```

**New Implementation:**
```python
# Get foreground color from model (log level text color)
fg_color = index.data(Qt.ForegroundRole)

# Draw selection highlight if selected
if option.state & QStyle.State_Selected:
    painter.fillRect(option.rect, QColor("#dcebf7"))

# Set up text document for rich text rendering
doc = QTextDocument()
doc.setDocumentMargin(0)

# ... text option setup ...

# Set default text color (log level color or default)
default_format = QTextCharFormat()
if option.state & QStyle.State_Selected:
    default_format.setForeground(option.palette.highlightedText())
elif fg_color:
    default_format.setForeground(fg_color)
else:
    default_format.setForeground(option.palette.text())
doc.setDefaultFont(option.font)
```

---

## §5 Visual Design

### §5.1 Color Mapping

| Log Level | Old Background | New Text Color | Notes |
|-----------|---------------|----------------|-------|
| CRITICAL | #FF6B6B | #FF6B6B | Same color, applied to text |
| ERROR | #FF8C8C | #FF8C8C | Same color, applied to text |
| WARNING | #FFD93D | #FFD93D | Same color, applied to text |
| MSG | #B6B6B6 | Default | No special color (black text) |
| DEBUG | #B6B6B6 | Default | No special color (black text) |
| TRACE | #B6B6B6 | Default | No special color (black text) |

### §5.2 Row Background

All rows now use the default background:
- Normal rows: White (#FFFFFF)
- Alternate rows: Light gray (if alternating row colors enabled)
- Selected rows: Selection highlight (#dcebf7)

### §5.3 Text Color Application

The text color applies to ALL columns in the row:
- Time column
- Category column
- Type column (icon)
- Message column

---

## §6 Interaction with User Highlights

### §6.1 Priority Order

User-defined highlights (from HighlightEngine) take precedence over log level colors:

1. **User highlight background** - Applied as background-color span in HTML
2. **Log level text color** - Applied as default text color for the cell

### §6.2 Combined Rendering

When a user highlight matches text in a log entry:
- The matched text has the user-defined background color
- The rest of the text has the log level text color
- Example: ERROR row with user highlight on "error":
  - "error" has yellow background (user highlight)
  - Rest of text is red (#FF8C8C) from ERROR level

### §6.3 Implementation in HighlightDelegate

```python
# Apply highlights if we have an engine
if self._highlight_engine and isinstance(text, str):
    highlights = self._highlight_engine.highlight(text)
    if highlights:
        # Build highlighted text
        cursor_pos = 0
        result = ""
        
        for hl in highlights:
            # Add text before highlight (with log level color)
            if hl.start > cursor_pos:
                result += text[cursor_pos:hl.start]
            # Add highlighted text (user highlight as background)
            highlighted_text = text[hl.start:hl.end]
            result += f'<span style="background-color: {hl.color.name()};">{highlighted_text}</span>'
            cursor_pos = hl.end
        
        # Add remaining text (with log level color)
        if cursor_pos < len(text):
            result += text[cursor_pos:]
        
        doc.setHtml(result)
```

---

## §7 Performance

### §7.1 Rendering Performance

| Metric | Current | New | Impact |
|--------|---------|-----|--------|
| Background fill | O(1) per row | N/A | Removed |
| Text color lookup | N/A | O(1) per row | Added |
| Net change | - | - | Neutral |

### §7.2 Memory

No change in memory usage. QColor objects are created once and stored in dictionary.

---

## §8 Testing

### §8.1 Unit Tests

```python
def test_log_level_text_colors():
    """Test that log levels return correct text colors."""
    model = LogTableModel()
    
    # Create test entries
    critical_entry = LogEntry(
        category="test",
        time="12:00:00",
        level=LogLevel.CRITICAL,
        message="Critical error"
    )
    
    model.set_entries([critical_entry])
    index = model.index(0, 0)
    
    # Check foreground color
    fg_color = model.data(index, Qt.ForegroundRole)
    assert fg_color == QColor(LogTextColors.CRITICAL)

def test_log_level_no_background():
    """Test that log levels no longer return background colors."""
    model = LogTableModel()
    
    critical_entry = LogEntry(
        category="test",
        time="12:00:00",
        level=LogLevel.CRITICAL,
        message="Critical error"
    )
    
    model.set_entries([critical_entry])
    index = model.index(0, 0)
    
    # Check that background role returns None
    bg_color = model.data(index, Qt.BackgroundRole)
    assert bg_color is None

def test_msg_level_default_color():
    """Test that MSG level uses default text color."""
    model = LogTableModel()
    
    msg_entry = LogEntry(
        category="test",
        time="12:00:00",
        level=LogLevel.MSG,
        message="Regular message"
    )
    
    model.set_entries([msg_entry])
    index = model.index(0, 0)
    
    # Check that foreground color is None (default)
    fg_color = model.data(index, Qt.ForegroundRole)
    assert fg_color is None
```

### §8.2 Visual Tests

Manual testing checklist:
- [ ] CRITICAL rows show red text
- [ ] ERROR rows show light red text
- [ ] WARNING rows show yellow text
- [ ] MSG/DEBUG/TRACE rows show default black text
- [ ] User highlights still work with background colors
- [ ] Selection highlight still works correctly
- [ ] Text is readable on white background

---

## §9 Migration

### §9.1 Breaking Changes

- `LogColors` class renamed to `LogTextColors`
- `LEVEL_COLORS` dictionary renamed to `LEVEL_TEXT_COLORS`
- `Qt.BackgroundRole` no longer returns log level colors

### §9.2 Compatibility

- Existing user highlights (background colors) continue to work
- No changes to highlight engine or highlight service
- No changes to settings file format

---

## §10 Cross-References

- **Colors:** [../constants/colors.py](../../src/constants/colors.py)
- **Log Levels:** [../constants/log_levels.py](../../src/constants/log_levels.py)
- **Table View:** [../views/log_table_view.py](../../src/views/log_table_view.py)
- **Highlight Delegate:** [../views/delegates/highlight_delegate.py](../../src/views/delegates/highlight_delegate.py)
- **Highlight Service:** [highlight-service.md](highlight-service.md)
- **Table Styles:** [table-unified-styles.md](table-unified-styles.md)

---

## §11 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-18 | Initial specification for text color highlighting |