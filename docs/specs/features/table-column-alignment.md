# Table Column Alignment Specification

**Version:** 1.1
**Last Updated:** 2026-03-15
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This document specifies the text alignment behavior for columns in the LogTableView component. Alignment affects both horizontal positioning and vertical centering within table cells.

---

## §2 Column Alignment Requirements

### §2.1 Alignment Matrix

| Column | Horizontal | Vertical | Qt Flag Combination |
|--------|------------|----------|---------------------|
| Time | Left | Center | `Qt.AlignLeft \| Qt.AlignVCenter` |
| Category | Left | Center | `Qt.AlignLeft \| Qt.AlignVCenter` |
| Type | Center | Center | `Qt.AlignCenter` |
| Message | Left | Center | `Qt.AlignLeft \| Qt.AlignVCenter` |

### §2.2 Alignment Semantics

#### §2.2.1 Left-Aligned Columns (Time, Category, Message)

**Horizontal Alignment:**
- Text starts from the left edge of the cell
- Preserves readability for variable-length content
- Allows natural text flow for log messages

**Vertical Alignment:**
- Vertically centered within the cell
- Ensures consistent row height appearance
- Improves visual consistency across log levels

**Use Cases:**
- **Time**: Timestamps are read left-to-right, most significant digits first
- **Category**: Hierarchical paths (e.g., `System.Network.HTTP`) read naturally left-to-right
- **Message**: Log messages are prose-like, read left-to-right

#### §2.2.2 Center-Aligned Column (Type)

**Horizontal Alignment:**
- Single character icon centered horizontally
- Provides visual balance for narrow column

**Vertical Alignment:**
- Vertically centered within the cell
- Icon appears balanced regardless of row height

**Use Cases:**
- **Type**: Single-character log level icons (⚠, ✗, ⚡, ○, ◯, ·) benefit from centering

---

## §3 Implementation Contract

### §3.1 Model Data Method

The alignment is provided via `Qt.TextAlignmentRole` in the model's `data()` method.

**Location:** `src/views/log_table_view.py` → `LogTableModel.data()`

**Implementation:**
```python
# Ref: docs/specs/features/table-column-alignment.md §3.1
elif role == Qt.TextAlignmentRole:
    if col == self.COL_TYPE:
        # Type column: Center alignment for log level icons
        return Qt.AlignCenter
    else:
        # Time, Category, Message: Left-aligned, vertically centered
        return Qt.AlignLeft | Qt.AlignVCenter
```

### §3.2 Column Index Constants

Reference: `src/views/log_table_view.py` → `LogTableModel`

```python
class LogTableModel(QAbstractTableModel):
    COL_TIME = 0      # Left + VCenter
    COL_CATEGORY = 1  # Left + VCenter
    COL_TYPE = 2      # Center
    COL_MESSAGE = 3   # Left + VCenter
```

### §3.3 Delegate Implementation

The `HighlightDelegate` must respect the alignment from `Qt.TextAlignmentRole` when painting cells.

**Location:** `src/views/delegates/highlight_delegate.py` → `HighlightDelegate.paint()`

**Requirements:**
1. Get alignment from model: `alignment = index.data(Qt.TextAlignmentRole)`
2. Default to `Qt.AlignLeft | Qt.AlignVCenter` if no alignment specified
3. Calculate horizontal offset based on alignment flags
4. Calculate vertical offset based on alignment flags
5. Apply offsets before drawing the text document

**Implementation:**
```python
# Get alignment from model (per docs/specs/features/table-column-alignment.md §3.3)
alignment = index.data(Qt.TextAlignmentRole)
if alignment is None:
    alignment = Qt.AlignLeft | Qt.AlignVCenter

# Set document width for proper text layout
doc.setTextWidth(option.rect.width())

# Calculate horizontal offset
doc_width = doc.idealWidth()
if alignment & Qt.AlignHCenter:
    x_offset = (option.rect.width() - doc_width) / 2
elif alignment & Qt.AlignRight:
    x_offset = option.rect.width() - doc_width
else:
    x_offset = 0

# Calculate vertical offset
doc_height = doc.size().height()
if alignment & Qt.AlignVCenter:
    y_offset = (option.rect.height() - doc_height) / 2
elif alignment & Qt.AlignBottom:
    y_offset = option.rect.height() - doc_height
else:
    y_offset = 0

# Apply offsets and draw
painter.save()
painter.translate(option.rect.topLeft())
painter.translate(x_offset, y_offset)
doc.drawContents(painter)
painter.restore()
```

---

## §4 Performance Considerations

### §4.1 Alignment Flag Caching

**Requirement:** Alignment flags are computed once per column, not per cell.

**Rationale:** Qt's `data()` method is called frequently during painting. The alignment flags are constant per column and should not require computation.

**Implementation Note:** The current implementation returns constant values directly, which is optimal. No caching structure is needed.

### §4.2 Memory Impact

**Allocation:** Zero additional allocations for alignment.
**Ownership:** Qt manages flag lifetime.

---

## §5 Testing Requirements

### §5.1 Unit Tests

```python
def test_time_column_alignment(log_table_model):
    """Time column must be left-aligned, vertically centered."""
    index = log_table_model.index(0, LogTableModel.COL_TIME)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == (Qt.AlignLeft | Qt.AlignVCenter)

def test_category_column_alignment(log_table_model):
    """Category column must be left-aligned, vertically centered."""
    index = log_table_model.index(0, LogTableModel.COL_CATEGORY)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == (Qt.AlignLeft | Qt.AlignVCenter)

def test_type_column_alignment(log_table_model):
    """Type column must be centered."""
    index = log_table_model.index(0, LogTableModel.COL_TYPE)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == Qt.AlignCenter

def test_message_column_alignment(log_table_model):
    """Message column must be left-aligned, vertically centered."""
    index = log_table_model.index(0, LogTableModel.COL_MESSAGE)
    alignment = log_table_model.data(index, Qt.TextAlignmentRole)
    assert alignment == (Qt.AlignLeft | Qt.AlignVCenter)
```

### §5.2 Visual Verification

**Manual Test Procedure:**
1. Open log file with entries of varying message lengths
2. Verify Time column text is left-aligned and vertically centered
3. Verify Category column text is left-aligned and vertically centered
4. Verify Type column icons are centered both horizontally and vertically
5. Verify Message column text is left-aligned and vertically centered
6. Resize window to verify alignment persists

---

## §6 Cross-References

- **UI Components:** [ui-components.md](ui-components.md) §4 (LogTableView)
- **Typography System:** [typography-system.md](typography-system.md) §4 (Font usage)
- **Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py) (Column widths)

---

## §7 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-15 | Added §3.3 Delegate implementation requirements |
| 1.0 | 2026-03-15 | Initial specification |