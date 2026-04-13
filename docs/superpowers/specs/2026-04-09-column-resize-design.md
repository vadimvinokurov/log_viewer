# Column Resize by Mouse Drag

## Context

The LogPanel uses Textual's DataTable with 5 auto-sized columns (Line, Timestamp, Level, Category, Message). Users have no way to adjust column widths — long messages get truncated or short columns waste space. Adding mouse-drag column resizing gives users direct control over the layout.

## Approach

**ColumnResizeMixin** — a mixin class added to `VimDataTable` that intercepts mouse events on column header boundaries. Keeps resize logic isolated from existing vim navigation and DataTable internals.

## Interaction

1. **Hover**: Mouse moves over header row within 1 char of a column boundary → visual highlight
2. **Drag start**: MouseDown on boundary → record column index, starting width, drag origin
3. **Drag move**: MouseMove while dragging → update column width by delta, set `auto_width=False`, refresh
4. **Drag end**: MouseUp → finalize width, clear drag state

## Column Boundary Detection

```python
def _get_column_boundary_at(self, x: int, y: int) -> int | None:
    """Return column index whose right edge is near (x, y), or None."""
    if y >= self.header_height:
        return None
    adjusted_x = x + self.scroll_x
    accumulated = 0
    for i, col in enumerate(self.ordered_columns):
        accumulated += col.get_render_width(self)
        if abs(adjusted_x - accumulated) <= 1:
            return i
    return None
```

## Constraints

- Minimum column width: 3 characters
- Resize only from header row
- `auto_width` flips to `False` on first manual resize (column becomes fixed-width)
- `virtual_size` updated after each width change
- `_clear_caches()` + `refresh()` called to re-render

## Files

| File | Action |
|------|--------|
| `src/log_viewer/tui/widgets/column_resize_mixin.py` | **New** — `ColumnResizeMixin` class |
| `src/log_viewer/tui/key_bindings.py` | Modify `VimDataTable` to include mixin |
| `tests/test_column_resize.py` | **New** — unit tests |

## VimDataTable Change

```python
class VimDataTable(ColumnResizeMixin, DataTable):
    ...
```

## Testing

- Boundary detection returns correct column index
- Boundary returns None for non-header rows
- Drag updates column width by expected delta
- Minimum width enforced (3 chars)
- `auto_width` set to `False` after resize
- Vim keybindings unaffected (j/k/g/G still work)
- No crash when table is empty
