"""Log table model and view with vim-style navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QMenu, QTableView

from log_viewer.core.models import Highlight, LogLine
from log_viewer.core.themes import _t
from log_viewer.gui.highlight_delegate import HighlightDelegate

from log_viewer.gui.styles import LOG_TABLE, LOG_TABLE_HEADER, styles
from log_viewer.core.typography import Typography

if TYPE_CHECKING:
    from log_viewer.core.log_store import LogStore

_COLUMNS = ("Line", "Time", "Category", "Message")

_LEVEL_COLORS: dict[str, str] = {
    "CRITICAL": _t("level_colors")["CRITICAL"],
    "ERROR":    _t("level_colors")["ERROR"],
    "WARNING":  _t("level_colors")["WARNING"],
    "INFO":     _t("level_colors")["INFO"],
    "DEBUG":    _t("level_colors")["DEBUG"],
    "TRACE":    _t("level_colors")["TRACE"],
}


class LogTableModel(QAbstractTableModel):
    """Table model that resolves rows via index mapping into store.lines.

    Holds filtered_indices and resolves store.lines[idx] on demand in data().
    Avoids creating a 6M-element list of LogLine references on every filter change.
    """

    def __init__(self, store: LogStore | None = None) -> None:
        super().__init__()
        self._store = store
        self._filtered_indices: list[int] = []
        self._highlights: list[Highlight] = []
        self._pinned_line_numbers: set[int] = set()

    @property
    def lines(self) -> list[LogLine]:
        """Compatibility property -- builds list on demand."""
        if self._store is None:
            return []
        return [self._store.lines[i] for i in self._filtered_indices]

    def _line_at(self, row: int) -> LogLine | None:
        """Resolve a LogLine for a visible row. O(1)."""
        if self._store is None or row < 0 or row >= len(self._filtered_indices):
            return None
        return self._store.lines[self._filtered_indices[row]]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._filtered_indices)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(_COLUMNS)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or index.row() >= len(self._filtered_indices):
            return None

        line = self._line_at(index.row())
        if line is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return str(line.line_number)
            if col == 1:
                return line.time_only
            if col == 2:
                return line.category
            if col == 3:
                return line.message
            return None

        if role == Qt.ItemDataRole.ForegroundRole:
            color_name = _LEVEL_COLORS.get(line.level.name)
            return QColor(color_name) if color_name else None

        if role == Qt.ItemDataRole.BackgroundRole:
            if line.line_number in self._pinned_line_numbers:
                return QColor(_t("pinned_bg"))
            return None

        if role == Qt.ItemDataRole.UserRole:
            return line

        if role == Qt.ItemDataRole.FontRole:
            return None

        return None

    def update_indices(
        self,
        filtered_indices: list[int],
        selection_model: object = None,
        table_view: object = None,
    ) -> None:
        """Update visible rows via index list. No LogLine list creation needed."""
        if self._filtered_indices is filtered_indices:
            return
        if (len(self._filtered_indices) == len(filtered_indices)
            and self._filtered_indices
            and filtered_indices
            and self._filtered_indices[0] == filtered_indices[0]
            and self._filtered_indices[-1] == filtered_indices[-1]):
            return
        # Save selected line numbers and viewport offset before reset
        selected_line_numbers: set[int] = set()
        anchor_line_number: int | None = None
        anchor_viewport_y: int | None = None
        if selection_model is not None:
            from PySide6.QtCore import QItemSelectionModel
            if isinstance(selection_model, QItemSelectionModel):
                selected_rows = sorted({idx.row() for idx in selection_model.selectedIndexes()})
                for row in selected_rows:
                    line = self._line_at(row)
                    if line is not None:
                        selected_line_numbers.add(line.line_number)
                if selected_rows and table_view is not None:
                    anchor_line = self._line_at(selected_rows[0])
                    if anchor_line is not None:
                        anchor_line_number = anchor_line.line_number
                        anchor_viewport_y = table_view.rowViewportPosition(selected_rows[0])
        self.beginResetModel()
        self._filtered_indices = filtered_indices
        self.endResetModel()
        # Restore selection for lines that remain visible
        if selected_line_numbers and selection_model is not None:
            from PySide6.QtCore import QItemSelectionModel
            if isinstance(selection_model, QItemSelectionModel):
                for row in range(len(self._filtered_indices)):
                    line = self._line_at(row)
                    if line is not None and line.line_number in selected_line_numbers:
                        selection_model.select(
                            self.index(row, 0),
                            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                        )
        # Restore viewport position
        if anchor_line_number is not None and anchor_viewport_y is not None and table_view is not None:
            for row in range(len(self._filtered_indices)):
                line = self._line_at(row)
                if line is not None and line.line_number == anchor_line_number:
                    table_view.scrollTo(self.index(row, 0))
                    current_y = table_view.rowViewportPosition(row)
                    diff = current_y - anchor_viewport_y
                    if diff != 0:
                        sb = table_view.verticalScrollBar()
                        sb.setValue(max(sb.minimum(), min(sb.value() + diff, sb.maximum())))
                    break

    def update_lines(self, lines: list[LogLine], selection_model: object = None, table_view: object = None) -> None:
        """Compatibility: accept a list of LogLine objects."""
        if self._store is None:
            self.beginResetModel()
            self._filtered_indices = []
            self.endResetModel()
            return
        # Build index mapping: for lines already in store, use their index;
        # for lines not in store, append them and use the new index.
        line_num_to_idx: dict[int, int] = {}
        for i, l in enumerate(self._store.lines):
            line_num_to_idx[l.line_number] = i
        indices: list[int] = []
        for l in lines:
            idx = line_num_to_idx.get(l.line_number)
            if idx is not None:
                indices.append(idx)
            else:
                idx = len(self._store.lines)
                self._store.lines.append(l)
                line_num_to_idx[l.line_number] = idx
                indices.append(idx)
        self.update_indices(indices, selection_model, table_view)

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self._highlights = highlights

    def set_pinned_line_numbers(self, line_numbers: set[int]) -> None:
        self._pinned_line_numbers = line_numbers

    def highlights(self) -> list[Highlight]:
        return self._highlights



class LogTableView(QTableView):
    """Table view with vim-style key bindings for log navigation."""

    pin_lines_requested = Signal(list)
    unpin_lines_requested = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setFont(Typography.UI_FONT)
        self.verticalHeader().setMinimumSectionSize(1)
        self.verticalHeader().setDefaultSectionSize(Typography.TABLE_ROW_HEIGHT)
        self.verticalHeader().hide()

        styles.apply(self.horizontalHeader(), LOG_TABLE_HEADER)
        self.horizontalHeader().setFixedHeight(Typography.TABLE_ROW_HEIGHT)

        styles.apply(self, LOG_TABLE)
        self._default_widths_set = False
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollMode.ScrollPerPixel)

        self._g_pressed: bool = False
        self._y_pressed: bool = False
        self.setItemDelegate(HighlightDelegate())

    def scrollTo(self, index, hint=QTableView.ScrollHint.EnsureVisible):  # noqa: N802
        """Scroll to show the row but preserve horizontal scroll position."""
        h_pos = self.horizontalScrollBar().value()
        super().scrollTo(index, hint)
        self.horizontalScrollBar().setValue(h_pos)

    def setModel(self, model: QAbstractTableModel | None) -> None:  # noqa: N802
        super().setModel(model)
        if model is not None and not self._default_widths_set:
            self.setColumnWidth(0, 50)   # Line
            self.setColumnWidth(1, 110)  # Time
            self.setColumnWidth(2, 150)  # Category
            self.setColumnWidth(3, 600)  # Message
            self._default_widths_set = True

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.angleDelta().x() != 0:
            new_event = QWheelEvent(
                event.position(),
                event.globalPosition(),
                event.pixelDelta(),
                QPoint(0, event.angleDelta().y()),
                event.buttons(),
                event.modifiers(),
                event.phase(),
                event.isInverted(),
            )
            super().wheelEvent(new_event)
        else:
            super().wheelEvent(event)

    def move_cursor_row(self, delta: int) -> None:
        model = self.model()
        if model is None:
            return
        current = self.currentIndex()
        row = max(0, min(current.row() + delta, model.rowCount() - 1))
        index = model.index(row, 0)
        self.setCurrentIndex(index)
        self.selectRow(row)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_J and not modifiers:
            self._g_pressed = False
            self._y_pressed = False
            self.move_cursor_row(1)
            return

        if key == Qt.Key.Key_K and not modifiers:
            self._g_pressed = False
            self._y_pressed = False
            self.move_cursor_row(-1)
            return

        if key == Qt.Key.Key_D and modifiers & Qt.KeyboardModifier.ControlModifier:
            self._g_pressed = False
            self._y_pressed = False
            half = self.height() // max(self.rowHeight(0), 1) // 2
            self.move_cursor_row(half)
            return

        if key == Qt.Key.Key_U and modifiers & Qt.KeyboardModifier.ControlModifier:
            self._g_pressed = False
            self._y_pressed = False
            half = self.height() // max(self.rowHeight(0), 1) // 2
            self.move_cursor_row(-half)
            return

        if key == Qt.Key.Key_G and modifiers & Qt.KeyboardModifier.ShiftModifier:
            self._g_pressed = False
            self._y_pressed = False
            model = self.model()
            if model is not None and model.rowCount() > 0:
                last = model.rowCount() - 1
                self.selectRow(last)
                self.scrollTo(model.index(last, 0))
            return

        if key == Qt.Key.Key_G and not modifiers:
            if self._g_pressed:
                self._g_pressed = False
                self._y_pressed = False
                model = self.model()
                if model is not None and model.rowCount() > 0:
                    self.scrollToTop()
                    self.selectRow(0)
            else:
                self._g_pressed = True
                self._y_pressed = False
            return

        if key == Qt.Key.Key_Y and not modifiers:
            if self._y_pressed:
                self._y_pressed = False
                self._g_pressed = False
                self._copy_current_line()
            else:
                self._y_pressed = True
                self._g_pressed = False
            return

        self._g_pressed = False
        self._y_pressed = False
        super().keyPressEvent(event)

    def _copy_current_line(self) -> None:
        model = self.model()
        if model is None:
            return
        line = model.data(self.currentIndex(), Qt.ItemDataRole.UserRole)
        if isinstance(line, LogLine):
            raw = ""
            if hasattr(model, '_store') and model._store is not None:
                raw = model._store.get_raw(line.line_number - 1)
            QApplication.clipboard().setText(raw if raw else line.message)

    def _selected_lines(self) -> list[LogLine]:
        """Return LogLine objects for all selected rows, sorted by row index."""
        model = self.model()
        if model is None:
            return []
        rows = sorted({idx.row() for idx in self.selectionModel().selectedIndexes()})
        lines: list[LogLine] = []
        for row in rows:
            line = model.data(model.index(row, 0), Qt.ItemDataRole.UserRole)
            if isinstance(line, LogLine):
                lines.append(line)
        return lines

    def _copy_selected_lines(self) -> None:
        """Copy all selected lines to clipboard."""
        lines = self._selected_lines()
        if not lines:
            return
        model = self.model()
        parts: list[str] = []
        for line in lines:
            raw = ""
            if model is not None and hasattr(model, '_store') and model._store is not None:
                raw = model._store.get_raw(line.line_number - 1)
            parts.append(raw if raw else line.message)
        QApplication.clipboard().setText("\n".join(parts))

    def _pin_selected_lines(self) -> None:
        """Emit pin request for all selected line numbers."""
        lines = self._selected_lines()
        if lines:
            self.pin_lines_requested.emit([line.line_number for line in lines])

    def _unpin_selected_lines(self) -> None:
        """Emit unpin request for all selected line numbers."""
        lines = self._selected_lines()
        if lines:
            self.unpin_lines_requested.emit([line.line_number for line in lines])

    def contextMenuEvent(self, event):  # noqa: N802
        """Right-click context menu for selected rows."""
        lines = self._selected_lines()
        pinned = {line.line_number for line in lines if line.line_number in self._pinned_line_numbers()}
        unpinned_count = len(lines) - len(pinned)

        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        pin_action = None
        unpin_action = None

        if unpinned_count > 0:
            pin_action = menu.addAction("Pin")
        if len(pinned) > 0:
            unpin_action = menu.addAction("Unpin")

        action = menu.exec(event.globalPos())
        if action == copy_action:
            self._copy_selected_lines()
        elif action == pin_action:
            self._pin_selected_lines()
        elif action == unpin_action:
            self._unpin_selected_lines()

    def _pinned_line_numbers(self) -> set[int]:
        """Get pinned line numbers from the model."""
        model = self.model()
        if model is not None and hasattr(model, '_pinned_line_numbers'):
            return model._pinned_line_numbers
        return set()
