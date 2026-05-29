"""Tests for LogTableModel and LogTableView."""

import pytest

import numpy as np
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QApplication

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import LogLine, LogLevel, _LEVEL_LIST, RowRef
from log_viewer.gui.log_table import LogTableModel, LogTableView


def _populate_store(store: LogStore, lines: list[LogLine]) -> None:
    """Populate SoA arrays on an existing LogStore from LogLine objects."""
    n = len(lines)
    store.n = n
    if n == 0:
        store._apply_filters()
        return

    # Build byte buffer from full formatted lines
    buf = bytearray()
    line_starts_list = [0]
    cat_name_to_id: dict[str, int] = {"uncategorized": 0}
    cat_names: list[str] = ["uncategorized"]
    cat_ids: list[int] = []
    level_ids: list[int] = []

    for l in lines:
        line_text = f"{l.timestamp} {l.category} [LOG_{l.level.name}] {l.message}\n"
        buf.extend(line_text.encode("utf-8"))
        line_starts_list.append(len(buf))

        cat = l.category
        if cat not in cat_name_to_id:
            cat_name_to_id[cat] = len(cat_names)
            cat_names.append(cat)
        cat_ids.append(cat_name_to_id[cat])

        level_map = {lvl: i for i, lvl in enumerate(_LEVEL_LIST)}
        level_ids.append(level_map.get(l.level, 3))

    store._buf = buf
    store._buf_lower = bytes(buf).lower()

    store.line_starts = np.array(line_starts_list, dtype=np.uint64)
    store.category_ids = np.array(cat_ids, dtype=np.uint16)
    store._category_names = cat_names
    store._category_name_to_id = cat_name_to_id
    store.levels = np.array(level_ids, dtype=np.uint8)
    store._format = "ksiva"

    store._build_category_tree()
    store._count_levels()
    store._apply_filters()


def _make_store_with_lines(lines: list[LogLine]) -> LogStore:
    """Create a LogStore pre-loaded with the given lines (converted to SoA)."""
    store = LogStore()
    _populate_store(store, lines)
    return store


@pytest.fixture
def sample_lines():
    return [
        LogLine(1, "2026-01-01T12:30:01", "app/api", LogLevel.INFO, "GET /api/users 200", 0, 10),
        LogLine(2, "2026-01-01T12:30:02", "app/api", LogLevel.ERROR, "POST /api/login 401", 11, 20),
        LogLine(3, "2026-01-01T12:30:03", "app/db", LogLevel.DEBUG, "Connection pool: 5/10", 31, 30),
    ]


@pytest.fixture
def model(sample_lines):
    store = _make_store_with_lines(sample_lines)
    m = LogTableModel(store=store)
    m.update_indices(np.arange(len(sample_lines), dtype=np.uint32))
    return m


def test_model_row_count(model, sample_lines):
    assert model.rowCount() == len(sample_lines)


def test_model_column_count(model):
    assert model.columnCount() == 4


def test_model_header_data(model):
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Line"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Time"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Category"
    assert model.headerData(3, Qt.Orientation.Horizontal) == "Message"


def test_model_data_line_number(model):
    assert model.data(model.index(0, 0)) == "1"


def test_model_data_time(model):
    assert model.data(model.index(0, 1)) == "12:30:01"


def test_model_data_category(model):
    assert model.data(model.index(0, 2)) == "app/api"


def test_model_data_message(model):
    assert model.data(model.index(0, 3)) == "GET /api/users 200"


def test_model_data_error_row_has_foreground(model):
    fg = model.data(model.index(1, 3), Qt.ItemDataRole.ForegroundRole)
    assert fg is not None


def test_model_update_lines(model):
    """update_lines with LogLine objects repopulates the store."""
    new = [LogLine(1, "2026-01-01T13:00:00", "sys", LogLevel.INFO, "CPU: 45%", 40, 15)]
    model.update_lines(new)
    assert model.rowCount() == 1
    # Line number is idx+1 = 0+1 = 1 in SoA model
    assert model.data(model.index(0, 0)) == "1"
    assert model.data(model.index(0, 3)) == "CPU: 45%"



def test_update_lines_same_skips_reset(model):
    """update_indices with identical indices should not trigger a model reset."""
    counter = [0]
    original_reset = model.beginResetModel

    def counting_reset() -> None:
        counter[0] += 1
        original_reset()

    model.beginResetModel = counting_reset

    # Pass same indices — should skip
    same_indices = model._store.filtered_indices.copy()
    model.update_indices(same_indices)
    assert counter[0] == 0

    # Pass same indices again — should also skip
    model.update_indices(same_indices)
    assert counter[0] == 0

    # Different indices — should reset
    model.update_indices(np.array([0], dtype=np.uint32))
    assert counter[0] == 1


def test_update_lines_different_triggers_reset(model):
    """update_indices with different indices should trigger a model reset."""
    counter = [0]
    original_reset = model.beginResetModel

    def counting_reset() -> None:
        counter[0] += 1
        original_reset()

    model.beginResetModel = counting_reset

    model.update_indices(np.array([0], dtype=np.uint32))
    assert counter[0] == 1


# --- Multi-selection and context menu tests ---


@pytest.fixture
def table_view(qtbot, sample_lines):
    store = _make_store_with_lines(sample_lines)
    view = LogTableView()
    m = LogTableModel(store=store)
    m.update_indices(np.arange(len(sample_lines), dtype=np.uint32))
    view.setModel(m)
    qtbot.addWidget(view)
    return view


def test_extended_selection_mode(table_view):
    """Selection mode should allow multi-select via Ctrl/Shift."""
    from PySide6.QtWidgets import QAbstractItemView
    assert table_view.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection


def test_selected_lines_returns_all_selected(table_view):
    """_selected_lines returns RowRef objects for all selected rows."""
    table_view.selectRow(0)
    table_view.selectionModel().select(
        table_view.model().index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    lines = table_view._selected_lines()
    assert len(lines) == 2
    assert lines[0].line_number == 1
    assert lines[1].line_number == 3


def test_copy_selected_lines_puts_text_in_clipboard(table_view):
    """_copy_selected_lines copies all selected line messages to clipboard."""
    table_view.selectRow(0)
    table_view.selectionModel().select(
        table_view.model().index(1, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    table_view._copy_selected_lines()
    clipboard = QApplication.clipboard().text()
    assert "GET /api/users 200" in clipboard
    assert "POST /api/login 401" in clipboard
    assert clipboard.count("\n") == 1


def test_pin_selected_lines_emits_signal(table_view):
    """_pin_selected_lines emits pin_lines_requested with line numbers."""
    table_view.selectRow(0)
    table_view.selectionModel().select(
        table_view.model().index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    received = []
    table_view.pin_lines_requested.connect(received.append)
    table_view._pin_selected_lines()
    assert received == [[1, 3]]


# --- Selection preservation across model updates ---


def test_selection_preserved_after_update_indices(table_view):
    """Selected rows that remain visible should stay selected after update_indices."""
    model = table_view.model()
    sel = table_view.selectionModel()

    # Select rows 0 and 2 (line_number 1 and 3)
    table_view.selectRow(0)
    sel.select(
        model.index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )

    # Remove row 1 (line_number 2): show only indices 0 and 2
    model.update_indices(
        np.array([0, 2], dtype=np.uint32),
        selection_model=sel,
    )

    # Rows for line_number 1 and 3 should still be selected (now at rows 0 and 1)
    selected_rows = sorted({idx.row() for idx in sel.selectedIndexes()})
    assert selected_rows == [0, 1]


def test_selection_preserved_single_row(table_view):
    """A single selected row that remains visible stays selected."""
    model = table_view.model()
    sel = table_view.selectionModel()

    # Select row 1 (line_number 2)
    table_view.selectRow(1)

    # Show only index 1 (line_number 2)
    model.update_indices(
        np.array([1], dtype=np.uint32),
        selection_model=sel,
    )

    selected_rows = sorted({idx.row() for idx in sel.selectedIndexes()})
    assert selected_rows == [0]  # line_number 2 is now at row 0


def test_selection_cleared_for_removed_rows(table_view):
    """Rows that are filtered out should no longer be selected."""
    model = table_view.model()
    sel = table_view.selectionModel()

    # Select all rows
    table_view.selectRow(0)
    sel.select(
        model.index(1, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    sel.select(
        model.index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )

    # Show only index 0 (line_number 1)
    model.update_indices(
        np.array([0], dtype=np.uint32),
        selection_model=sel,
    )

    # Only row 0 (line_number 1) should be selected
    selected_rows = sorted({idx.row() for idx in sel.selectedIndexes()})
    assert selected_rows == [0]


# --- Selection preservation through _apply_filters path ---


def test_selection_preserved_after_apply_filters(qtbot):
    """Selection survives the _refresh_log_only path where _apply_filters
    changes store.filtered_indices BEFORE update_indices is called."""
    from log_viewer.core.models import Filter, SearchMode

    lines = [
        LogLine(1, "2026-01-01T12:30:01", "app", LogLevel.INFO, "alpha message", 0, 10),
        LogLine(2, "2026-01-01T12:30:02", "app", LogLevel.ERROR, "beta error", 11, 20),
        LogLine(3, "2026-01-01T12:30:03", "app", LogLevel.INFO, "gamma message", 31, 30),
    ]
    store = _make_store_with_lines(lines)

    model = LogTableModel(store=store)
    model.update_indices(np.arange(3, dtype=np.uint32))
    view = LogTableView()
    view.setModel(model)
    view.resize(800, 400)
    qtbot.addWidget(view)

    # Select row 1 (line_number 2 — "beta error")
    view.selectRow(1)
    sel = view.selectionModel()

    # Add a filter that hides "alpha" — same pattern as _refresh_log_only:
    # _apply_filters runs first, then update_indices gets the new list.
    store.filters = [Filter(pattern="beta", mode=SearchMode.PLAIN)]
    store.filter_enabled = [True]
    store._apply_filters()  # changes store.filtered_indices to [1] only

    model.update_indices(
        store.filtered_indices,
        selection_model=sel,
        table_view=view,
    )

    # line_number 2 ("beta error") should still be selected, now at row 0
    selected_rows = sorted({idx.row() for idx in sel.selectedIndexes()})
    assert selected_rows == [0]
    line = model._line_at(0)
    assert line is not None and line.line_number == 2


# --- Viewport position preservation ---


@pytest.fixture
def many_lines():
    """50 lines to allow scrolling."""
    return [
        LogLine(i + 1, f"2026-01-01T12:30:{i % 60:02d}", "app", LogLevel.INFO, f"Message {i + 1}", i * 20, 20)
        for i in range(50)
    ]


@pytest.fixture
def scrollable_view(qtbot, many_lines):
    store = _make_store_with_lines(many_lines)
    view = LogTableView()
    m = LogTableModel(store=store)
    m.update_indices(np.arange(len(many_lines), dtype=np.uint32))
    view.setModel(m)
    view.resize(800, 400)
    qtbot.addWidget(view)
    view.show()
    return view


def test_viewport_position_preserved_after_update(scrollable_view):
    """Selected row should keep its viewport position after indices are updated."""
    model = scrollable_view.model()
    sel = scrollable_view.selectionModel()

    # Use a row deep enough that removing rows above still leaves enough
    # content to maintain the same viewport position
    target_row = 35
    scrollable_view.scrollTo(model.index(target_row, 0))
    scrollable_view.selectRow(target_row)

    # Record viewport y of the selected row
    y_before = scrollable_view.rowViewportPosition(target_row)

    # Remove rows 0-4 (5 rows before the anchor area)
    # Row 35 (line_number 36) becomes row 30 in new list
    new_indices = np.arange(5, 50, dtype=np.uint32)
    model.update_indices(new_indices, selection_model=sel, table_view=scrollable_view)

    # After update, line_number 36 should now be at row 30
    new_row = 30
    y_after = scrollable_view.rowViewportPosition(new_row)

    assert y_before == y_after
