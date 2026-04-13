"""Vim-style key bindings for DataTable."""

from __future__ import annotations

from textual.widgets import DataTable

from log_viewer.tui.widgets.column_resize_mixin import ColumnResizeMixin


class VimDataTable(ColumnResizeMixin, DataTable):
    """DataTable with vim-style navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.cursor_type = "row"
        self._g_pressed = False
        self._number_buffer = ""

    def key_j(self) -> None:
        self.action_cursor_down()

    def key_k(self) -> None:
        self.action_cursor_up()

    def key_g(self) -> None:
        if self._g_pressed:
            self.move_cursor(row=0)
            self._g_pressed = False
        else:
            self._g_pressed = True
            self.set_timer(0.2, self._reset_g)

    def _reset_g(self) -> None:
        self._g_pressed = False

    def _goto_line(self, line_number: int) -> None:
        """Jump to a 1-based line number (clamped to valid range)."""
        if self.row_count == 0:
            return
        row = max(0, min(line_number - 1, self.row_count - 1))
        self.move_cursor(row=row)

    def key_upper_g(self) -> None:
        """Handle uppercase G — real terminals send key='G' → name='upper_g'."""
        if self._number_buffer:
            line_number = int(self._number_buffer)
            self._number_buffer = ""
            self._goto_line(line_number)
        elif self.row_count > 0:
            self.move_cursor(row=self.row_count - 1)

    # shift+g: kept for pilot.press("shift+g") in tests
    def key_shift_g(self) -> None:
        self.key_upper_g()

    def key_ctrl_d(self) -> None:
        for _ in range(self._half_page_size()):
            self.action_cursor_down()

    def key_ctrl_u(self) -> None:
        for _ in range(self._half_page_size()):
            self.action_cursor_up()

    def _handle_digit(self, digit: str) -> None:
        """Accumulate digit into the number buffer."""
        self._number_buffer += digit
        self.set_timer(1.0, self._clear_number_buffer)

    def _clear_number_buffer(self) -> None:
        self._number_buffer = ""

    def _half_page_size(self) -> int:
        if self.row_count:
            return max(1, self.virtual_size.height // 2)
        return 10


# Generate key_0 .. key_9 methods dynamically
for _d in "0123456789":

    def _make_digit_handler(digit: str):  # type: ignore[misc]
        def handler(self: VimDataTable) -> None:
            self._handle_digit(digit)

        return handler

    setattr(VimDataTable, f"key_{_d}", _make_digit_handler(_d))
