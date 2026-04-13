"""Mixin for mouse-drag column resizing in DataTable."""

from __future__ import annotations

from textual import events
from textual.widgets._data_table import Column


class ColumnResizeMixin:
    """Adds mouse-drag column resizing to a Textual DataTable.

    Override points: ``_on_mouse_move``, ``_on_mouse_down``, ``_on_mouse_up``.
    Always calls ``super()`` to preserve original DataTable behaviour.
    """

    MIN_COL_WIDTH: int = 2

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._resizing_col: int | None = None
        self._drag_start_x: int = 0
        self._drag_start_width: int = 0
        self._resize_hover_col: int | None = None

    # ------------------------------------------------------------------
    # Boundary detection
    # ------------------------------------------------------------------

    def _get_column_boundary_at(self, x: int, y: int) -> int | None:
        """Return column index whose right edge is within 1 cell of (x, y).

        Only matches inside the header row (y < header_height).
        """
        if y >= self.header_height:  # type: ignore[attr-defined]
            return None

        adjusted_x = x + self.scroll_x  # type: ignore[attr-defined]
        accumulated = 0
        for i, col in enumerate(self.ordered_columns):  # type: ignore[attr-defined]
            accumulated += col.get_render_width(self)  # type: ignore[attr-defined]
            if abs(adjusted_x - accumulated) <= 1:
                return i
        return None

    # ------------------------------------------------------------------
    # Mouse event handlers
    # ------------------------------------------------------------------

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        if self._resizing_col is not None:
            self._apply_drag(event.x)
        else:
            self._resize_hover_col = self._get_column_boundary_at(event.x, event.y)
        super()._on_mouse_move(event)  # type: ignore[misc]

    def _on_mouse_down(self, event: events.MouseDown) -> None:
        col_idx = self._get_column_boundary_at(event.x, event.y)
        if col_idx is not None:
            col: Column = self.ordered_columns[col_idx]  # type: ignore[attr-defined]
            self._resizing_col = col_idx
            self._drag_start_x = event.x
            self._drag_start_width = col.get_render_width(self)  # type: ignore[attr-defined]
            event.stop()
            return
        super()._on_mouse_down(event)  # type: ignore[misc]

    def _on_mouse_up(self, event: events.MouseUp) -> None:
        if self._resizing_col is not None:
            self._apply_drag(event.x)
            self._resizing_col = None
            event.stop()
            return
        super()._on_mouse_up(event)  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply_drag(self, current_x: int) -> None:
        """Update the column width based on drag delta."""
        if self._resizing_col is None:
            return

        col: Column = self.ordered_columns[self._resizing_col]  # type: ignore[attr-defined]
        delta = current_x - self._drag_start_x
        new_render_width = max(
            self.MIN_COL_WIDTH + 2 * self.cell_padding,  # type: ignore[attr-defined]
            self._drag_start_width + delta,
        )
        new_content_width = new_render_width - 2 * self.cell_padding  # type: ignore[attr-defined]

        col.width = new_content_width
        col.auto_width = False
        self._clear_caches()  # type: ignore[attr-defined]
        self._update_dimensions(())  # type: ignore[attr-defined]
        self.refresh()  # type: ignore[attr-defined]
