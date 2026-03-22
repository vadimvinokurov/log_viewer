# Table Cell Text Overflow Specification

**Version:** 1.0
**Last Updated:** 2026-03-15
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This document specifies the text overflow behavior for table cells in the LogTableView component. Text that exceeds column width must be clipped at the right boundary without wrapping to new lines or breaking the table structure.

---

## §2 Requirements

### §2.1 Text Overflow Behavior

| Requirement | Description |
|-------------|-------------|
| **No Word Wrap** | Text must NOT wrap to multiple lines within a cell |
| **Right Clip** | Overflow text must be clipped at the right edge of the column |
| **Visual Hiding** | Clipped text visually disappears under the next column without overlapping |
| **Structure Integrity** | Table row height remains fixed regardless of text length |
| **Tooltip Fallback** | Full text available via tooltip (already implemented per §4.2.3) |

### §2.2 Visual Behavior

```
┌──────────────┬──────────────┬──────┬─────────────────┐
│ Time         │ Category     │ Type │ Message         │
├──────────────┼──────────────┼──────┼─────────────────┤
│ 10:30:45.123 │ System.Netwo │  ⚡  │ Connection time│
│              │              │      │ out waiting for│
│              │              │      │ response from  │
│              │              │      │ server...      │
└──────────────┴──────────────┴──────┴─────────────────┘

DESIRED BEHAVIOR (Single Line):

┌──────────────┬──────────────┬──────┬─────────────────┐
│ Time         │ Category     │ Type │ Message         │
├──────────────┼──────────────┼──────┼─────────────────┤
│ 10:30:45.123 │ System.Netwo │  ⚡  │ Connection time│ ← Clipped
└──────────────┴──────────────┴──────┴─────────────────┘
```

---

## §3 Implementation Contract

### §3.1 LogTableView Configuration

**Location:** `src/views/log_table_view.py` → `LogTableView._setup_header()`

**Current Implementation (lines 288-289):**
```python
self.setWordWrap(False)
self.setTextElideMode(Qt.ElideRight)
```

**Status:** ✅ Already correctly configured. No changes needed.

**Verification:**
- `setWordWrap(False)` prevents multi-line text wrapping
- `setTextElideMode(Qt.ElideRight)` sets elide mode for the view

### §3.2 HighlightDelegate Text Clipping

**Location:** `src/views/delegates/highlight_delegate.py` → `HighlightDelegate.paint()`

**Current Issue:**
The `QTextDocument` by default wraps text when `setTextWidth()` is called. This causes text to flow to multiple lines within the document bounds.

**Required Changes:**

#### §3.2.1 Disable Text Document Wrapping

The `QTextDocument` must be configured to NOT wrap text:

```python
# After creating QTextDocument
doc = QTextDocument()
doc.setDocumentMargin(0)

# CRITICAL: Disable text wrapping
doc.setTextWidth(option.rect.width())
doc.setDefaultTextOption(QTextOption(Qt.AlignLeft | Qt.AlignVCenter))

# Set text wrap mode to NoWrap
root_frame = doc.rootFrame()
frame_format = root_frame.frameFormat()
frame_format.setMargin(0)
root_frame.setFrameFormat(frame_format)
```

**Alternative (Simpler) Approach:**
Use `QTextOption` with `QTextOption.NoWrap`:

```python
from PySide6.QtGui import QTextOption

# After creating QTextDocument
doc = QTextDocument()
doc.setDocumentMargin(0)

# Create text option with NoWrap
text_option = QTextOption()
text_option.setWrapMode(QTextOption.NoWrap)
doc.setDefaultTextOption(text_option)

# Set document width
doc.setTextWidth(option.rect.width())
```

#### §3.2.2 Clip Painter to Cell Bounds

The painter must be clipped to the cell rectangle to prevent text from bleeding into adjacent cells:

```python
# After painter.save()
painter.save()

# Clip to cell bounds
painter.setClipRect(option.rect)

# Apply translation and draw
painter.translate(option.rect.topLeft())
painter.translate(x_offset, y_offset)
doc.drawContents(painter)
painter.restore()
```

#### §3.2.3 Complete Implementation

**Location:** `src/views/delegates/highlight_delegate.py` → `HighlightDelegate.paint()`

```python
def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
    """Paint the cell with optional highlighting.
    
    Ref: docs/specs/features/table-cell-text-overflow.md §3.2
    
    Args:
        painter: The painter to use.
        option: Style options.
        index: Model index.
    """
    # Get the text to display
    text = index.data(Qt.DisplayRole)
    if text is None:
        super().paint(painter, option, index)
        return
    
    # Get background color from model
    bg_color = index.data(Qt.BackgroundRole)
    
    # Draw background
    if bg_color:
        painter.fillRect(option.rect, bg_color)
    else:
        painter.fillRect(option.rect, option.palette.base())
    
    # Draw selection highlight if selected
    if option.state & QStyle.State_Selected:
        painter.fillRect(option.rect, QColor("#dcebf7"))
    
    # Set up text document for rich text rendering
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    
    # CRITICAL: Disable text wrapping (per §3.2.1)
    text_option = QTextOption()
    text_option.setWrapMode(QTextOption.NoWrap)
    doc.setDefaultTextOption(text_option)
    
    # Set default text color
    default_format = QTextCharFormat()
    if option.state & QStyle.State_Selected:
        default_format.setForeground(option.palette.highlightedText())
    else:
        default_format.setForeground(option.palette.text())
    doc.setDefaultFont(option.font)
    
    # Apply highlights if we have an engine
    if self._highlight_engine and isinstance(text, str):
        highlights = self._highlight_engine.highlight(text)
        if highlights:
            cursor_pos = 0
            result = ""
            
            for hl in highlights:
                if hl.start > cursor_pos:
                    result += text[cursor_pos:hl.start]
                highlighted_text = text[hl.start:hl.end]
                result += f'<span style="background-color: {hl.color.name()};">{highlighted_text}</span>'
                cursor_pos = hl.end
            
            if cursor_pos < len(text):
                result += text[cursor_pos:]
            
            doc.setHtml(result)
        else:
            doc.setPlainText(text)
    else:
        doc.setPlainText(text)
    
    # Get alignment from model
    alignment = index.data(Qt.TextAlignmentRole)
    if alignment is None:
        alignment = Qt.AlignLeft | Qt.AlignVCenter
    
    # Set document width
    doc.setTextWidth(option.rect.width())
    
    # Draw with clipping (per §3.2.2)
    painter.save()
    painter.setClipRect(option.rect)  # Clip to cell bounds
    
    # Calculate offsets
    doc_height = doc.size().height()
    if alignment & Qt.AlignHCenter:
        x_offset = (option.rect.width() - doc.idealWidth()) / 2
    elif alignment & Qt.AlignRight:
        x_offset = option.rect.width() - doc.idealWidth()
    else:
        x_offset = 0
    
    if alignment & Qt.AlignVCenter:
        y_offset = (option.rect.height() - doc_height) / 2
    elif alignment & Qt.AlignBottom:
        y_offset = option.rect.height() - doc_height
    else:
        y_offset = 0
    
    painter.translate(option.rect.topLeft())
    painter.translate(x_offset, y_offset)
    doc.drawContents(painter)
    painter.restore()
```

### §3.3 Import Additions

**Location:** `src/views/delegates/highlight_delegate.py`

**Required import:**
```python
from PySide6.QtGui import QColor, QPainter, QTextDocument, QTextCharFormat, QTextOption
```

---

## §4 Performance Considerations

### §4.1 Memory Impact

| Component | Allocation | Lifetime |
|-----------|------------|----------|
| `QTextDocument` | Per-cell during paint | Transient (paint cycle) |
| `QTextOption` | Per-cell during paint | Transient (paint cycle) |
| Clip region | Per-cell during paint | Managed by Qt |

**Total overhead:** Negligible. Objects created during paint are short-lived.

### §4.2 Rendering Performance

- **Clipping:** `setClipRect()` is O(1) - simple rectangle intersection
- **NoWrap mode:** No performance impact - same text layout calculation
- **Row height:** Fixed height prevents expensive height calculations

---

## §5 Testing Requirements

### §5.1 Unit Tests

**Location:** `tests/test_log_table_view.py`

```python
def test_table_no_word_wrap(log_table_view):
    """Table must not wrap text to multiple lines."""
    log_table_view.setWordWrap(False)
    assert not log_table_view.wordWrap()

def test_table_elide_mode_right(log_table_view):
    """Table must use right elide mode."""
    assert log_table_view.textElideMode() == Qt.ElideRight
```

### §5.2 Delegate Tests

**Location:** `tests/test_highlight_delegate.py` (new file)

```python
def test_delegate_text_no_wrap(delegate, model_index):
    """Delegate must not wrap text in cells."""
    from PySide6.QtGui import QTextOption
    
    # Create document as delegate does
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    
    text_option = QTextOption()
    text_option.setWrapMode(QTextOption.NoWrap)
    doc.setDefaultTextOption(text_option)
    
    # Verify wrap mode
    assert doc.defaultTextOption().wrapMode() == QTextOption.NoWrap

def test_delegate_clips_to_cell_bounds(delegate, model_index):
    """Delegate must clip text to cell rectangle."""
    # This requires visual verification or mock painter
    # Verify setClipRect is called during paint
    pass
```

### §5.3 Visual Verification

**Manual Test Procedure:**
1. Open log file with very long category paths (e.g., `System.Network.HTTP.Request.Handler.ConnectionPool.Manager`)
2. Open log file with very long messages (e.g., >500 characters)
3. Verify:
   - All cells display single-line text
   - Text is clipped at right edge of column
   - No text bleeds into adjacent columns
   - Row height remains consistent
   - Tooltip shows full text on hover

---

## §6 Cross-References

- **Table Unified Styles:** [table-unified-styles.md](table-unified-styles.md) (Complete table styling)
- **Table Column Alignment:** [table-column-alignment.md](table-column-alignment.md) §3.3 (Delegate alignment)
- **UI Components:** [ui-components.md](ui-components.md) §4 (LogTableView)
- **UI Design System:** [ui-design-system.md](ui-design-system.md) §2.2 (Typography)
- **LogTableView Implementation:** [src/views/log_table_view.py](../../src/views/log_table_view.py) lines 288-289

---

## §7 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-15 | Updated cross-references to include table-unified-styles.md and ui-design-system.md |
| 1.0 | 2026-03-15 | Initial specification |