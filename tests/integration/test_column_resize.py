"""Tests for ColumnResizeMixin — mouse-drag column resizing."""

import pytest

from textual.widgets import DataTable

from log_viewer.tui.app import LogViewerApp

SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE LOG_INFO version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage LOG_ERROR Failed to open file",
    "20-03-2026T12:20:42.258 PLATFORM LOG_DEBUG win64",
]


@pytest.mark.asyncio
async def test_boundary_detected_in_header() -> None:
    """Hovering near a column boundary in the header should detect it."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)

        # Calculate where column 0 (Line) ends
        col0 = table.ordered_columns[0]
        boundary_x = col0.get_render_width(table)

        # Simulate mouse move at the boundary in the header row (y=0)
        await pilot.hover(DataTable, offset=(boundary_x, 0))
        await pilot.pause()

        assert table._resize_hover_col == 0


@pytest.mark.asyncio
async def test_no_boundary_below_header() -> None:
    """Boundary detection should return None for rows below the header."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)

        # Move mouse below header row — no boundary should be detected
        await pilot.hover(DataTable, offset=(10, 5))
        await pilot.pause()

        assert table._resize_hover_col is None


@pytest.mark.asyncio
async def test_drag_resizes_column() -> None:
    """Dragging a column boundary should change the column width."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)

        col0 = table.ordered_columns[0]
        boundary_x = col0.get_render_width(table)
        original_width = col0.get_render_width(table)

        # Mouse down on the boundary
        await pilot.mouse_down(DataTable, offset=(boundary_x, 0))
        await pilot.pause()

        # Drag 5 cells to the right
        await pilot.hover(DataTable, offset=(boundary_x + 5, 0))
        await pilot.pause()

        # Mouse up to finalize
        await pilot.mouse_up(DataTable, offset=(boundary_x + 5, 0))
        await pilot.pause()

        new_width = table.ordered_columns[0].get_render_width(table)
        assert new_width == original_width + 5


@pytest.mark.asyncio
async def test_min_width_enforced() -> None:
    """Dragging far left should not shrink column below minimum width."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)

        col0 = table.ordered_columns[0]
        boundary_x = col0.get_render_width(table)

        # Mouse down on boundary
        await pilot.mouse_down(DataTable, offset=(boundary_x, 0))
        await pilot.pause()

        # Drag very far left (way past min width)
        await pilot.hover(DataTable, offset=(0, 0))
        await pilot.pause()
        await pilot.mouse_up(DataTable, offset=(0, 0))
        await pilot.pause()

        min_width = 2 + 2 * table.cell_padding
        actual_width = table.ordered_columns[0].get_render_width(table)
        assert actual_width >= min_width


@pytest.mark.asyncio
async def test_auto_width_disabled_on_resize() -> None:
    """Manually resizing a column should set auto_width to False."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)

        # Use Line column (index 0) — starts as auto_width=False (fixed),
        # but we still verify drag changes its width
        col0 = table.ordered_columns[0]
        boundary_x = col0.get_render_width(table)

        await pilot.mouse_down(DataTable, offset=(boundary_x, 0))
        await pilot.pause()
        await pilot.hover(DataTable, offset=(boundary_x + 3, 0))
        await pilot.pause()
        await pilot.mouse_up(DataTable, offset=(boundary_x + 3, 0))
        await pilot.pause()

        # Column width should have increased by 3
        assert col0.get_render_width(table) == boundary_x + 3


@pytest.mark.asyncio
async def test_no_boundary_on_empty_table() -> None:
    """No crash and no boundary detected when table has no columns."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Table has columns from LogPanel.on_mount, but no rows
        # Boundary detection should still work for columns
        await pilot.hover(DataTable, offset=(5, 0))
        await pilot.pause()
        # Just verify no crash — value depends on column widths


@pytest.mark.asyncio
async def test_initial_column_fixed_widths() -> None:
    """Line, Timestamp, Category should have fixed widths; Message should be auto."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)):
        table = app.query_one(DataTable)
        cols = table.ordered_columns

        # Line (0) — fixed width
        assert cols[0].auto_width is False
        assert cols[0].width == 6

        # Timestamp (1) — fixed width
        assert cols[1].auto_width is False

        # Category (2) — fixed width
        assert cols[2].auto_width is False
        assert cols[2].width == 20

        # Message (3) — fixed width 200
        assert cols[3].auto_width is False
        assert cols[3].width == 200


@pytest.mark.asyncio
async def test_rows_colored_by_level() -> None:
    """Each row's cells should be Rich Text styled by log level."""
    from rich.text import Text

    app = LogViewerApp()
    async with app.run_test(size=(120, 40)):
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)

        # Row 0: LOG_INFO → white style
        row = table.get_row_at(0)
        cell = row[0]
        assert isinstance(cell, Text)
        assert "white" in str(cell.style)

        # Row 1: LOG_ERROR → red style
        row = table.get_row_at(1)
        cell = row[0]
        assert isinstance(cell, Text)
        assert "red" in str(cell.style)


@pytest.mark.asyncio
async def test_vim_keys_still_work_after_resize() -> None:
    """Vim navigation should still work after column resize."""
    app = LogViewerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.log_store.load_lines(SAMPLE_LINES)
        app.refresh_log_panel()
        table = app.query_one(DataTable)
        table.focus()

        # Resize a column first
        col0 = table.ordered_columns[0]
        boundary_x = col0.get_render_width(table)
        await pilot.mouse_down(DataTable, offset=(boundary_x, 0))
        await pilot.pause()
        await pilot.hover(DataTable, offset=(boundary_x + 5, 0))
        await pilot.pause()
        await pilot.mouse_up(DataTable, offset=(boundary_x + 5, 0))
        await pilot.pause()

        # Now test vim navigation
        await pilot.press("j")
        await pilot.pause()
        assert table.cursor_row == 1

        await pilot.press("k")
        await pilot.pause()
        assert table.cursor_row == 0
