"""Log table model and view."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QWheelEvent
from PySide6.QtWidgets import QApplication, QMenu, QTableView

from log_viewer.core.models import Highlight, RowRef, SearchMode, _LEVEL_LIST
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
    """Table model that resolves rows via index mapping into SoA store arrays."""

    def __init__(self, store: LogStore | None = None) -> None:
        super().__init__()
        self._store = store
        self._highlights: list[Highlight] = []
        self._prev_len: int = 0
        self._prev_indices: np.ndarray = np.empty(0, dtype=np.uint32)

    @property
    def lines(self) -> list[RowRef]:
        """Compatibility property -- builds list on demand."""
        if self._store is None:
            return []
        return [RowRef(int(idx), self._store) for idx in self._store.filtered_indices]

    def _idx_at(self, row: int) -> int | None:
        """Resolve a raw array index for a visible row. O(1)."""
        if self._store is None or row < 0 or row >= len(self._store.filtered_indices):
            return None
        return int(self._store.filtered_indices[row])

    def _line_at(self, row: int) -> RowRef | None:
        """Resolve a RowRef for a visible row."""
        idx = self._idx_at(row)
        if idx is None:
            return None
        return RowRef(idx, self._store)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._store.filtered_indices) if self._store else 0

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
        if not index.isValid() or self._store is None or index.row() >= len(self._store.filtered_indices):
            return None

        store = self._store
        idx = int(store.filtered_indices[index.row()])

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return str(idx + 1)  # line_number = idx + 1
            # Parse columns lazily — one parse per data() call
            timestamp, category, level_name, message = store.get_columns(idx)
            if col == 1:
                return timestamp
            if col == 2:
                return category
            if col == 3:
                return message
            return None

        if role == Qt.ItemDataRole.ForegroundRole:
            level_id = int(store.levels[idx])
            if 0 <= level_id < len(_LEVEL_LIST):
                color_name = _LEVEL_COLORS.get(_LEVEL_LIST[level_id].name)
                return QColor(color_name) if color_name else None
            return None

        if role == Qt.ItemDataRole.UserRole:
            return RowRef(idx, store)

        if role == Qt.ItemDataRole.FontRole:
            return None

        return None

    def update_indices(
        self,
        filtered_indices: np.ndarray,
        selection_model: object = None,
        table_view: object = None,
    ) -> None:
        """Update visible rows. filtered_indices comes from store."""
        if self._store is None:
            return
        new_len = len(filtered_indices)
        if new_len == 0 and self._prev_len == 0:
            return
        # Short-circuit when indices are identical (avoids unnecessary reset)
        if (
            new_len == self._prev_len
            and new_len > 0
            and len(self._store.filtered_indices) == new_len
            and np.array_equal(filtered_indices, self._store.filtered_indices)
            and selection_model is None
        ):
            return

        # Save selected line numbers and viewport offset before reset
        selected_line_numbers: set[int] = set()
        anchor_line_number: int | None = None
        anchor_viewport_y: int | None = None
        if selection_model is not None:
            from PySide6.QtCore import QItemSelectionModel
            if isinstance(selection_model, QItemSelectionModel):
                selected_rows = sorted({idx.row() for idx in selection_model.selectedIndexes()})
                old_indices = self._prev_indices
                for row in selected_rows:
                    if 0 <= row < len(old_indices):
                        selected_line_numbers.add(int(old_indices[row]) + 1)
                if selected_rows and table_view is not None:
                    anchor_row = selected_rows[0]
                    if 0 <= anchor_row < len(old_indices):
                        anchor_line_number = int(old_indices[anchor_row]) + 1
                        anchor_viewport_y = table_view.rowViewportPosition(anchor_row)

        self.beginResetModel()
        if self._store.filtered_indices is not filtered_indices:
            self._store.filtered_indices = filtered_indices
        self._prev_len = len(filtered_indices)
        self._prev_indices = self._store.filtered_indices.copy()
        self.endResetModel()

        # Restore selection
        if selected_line_numbers and selection_model is not None:
            from PySide6.QtCore import QItemSelectionModel
            if isinstance(selection_model, QItemSelectionModel):
                for row in range(len(self._store.filtered_indices)):
                    line_num = int(self._store.filtered_indices[row]) + 1
                    if line_num in selected_line_numbers:
                        selection_model.select(
                            self.index(row, 0),
                            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                        )

        # Restore viewport position
        if anchor_line_number is not None and anchor_viewport_y is not None and table_view is not None:
            for row in range(len(self._store.filtered_indices)):
                line_num = int(self._store.filtered_indices[row]) + 1
                if line_num == anchor_line_number:
                    table_view.scrollTo(self.index(row, 0))
                    current_y = table_view.rowViewportPosition(row)
                    diff = current_y - anchor_viewport_y
                    if diff != 0:
                        sb = table_view.verticalScrollBar()
                        sb.setValue(max(sb.minimum(), min(sb.value() + diff, sb.maximum())))
                    break

    def update_lines(self, lines: list, selection_model: object = None, table_view: object = None) -> None:
        """Accept a list of RowRef or LogLine objects.

        RowRef: extract index and call update_indices.
        LogLine: repopulate store SoA arrays, then show all indices.
        """
        if self._store is None:
            self.beginResetModel()
            self.endResetModel()
            return

        if lines and hasattr(lines[0], "_idx"):
            # RowRef path
            indices = np.array([r._idx for r in lines], dtype=np.uint32)
            self.update_indices(indices, selection_model, table_view)
        else:
            # LogLine path — repopulate store from scratch
            from log_viewer.core.models import _LEVEL_LIST

            n = len(lines)
            store = self._store
            store.n = n
            if n == 0:
                store._buf = bytearray()
                store._buf_lower = None
                store.category_ids = np.empty(0, dtype=np.uint16)
                store.levels = np.empty(0, dtype=np.uint8)
                store.line_starts = np.empty(0, dtype=np.uint64)
                store._apply_filters()
                self.update_indices(store.filtered_indices, selection_model, table_view)
                return

            # Build byte buffer from full formatted LogLine entries
            buf = bytearray()
            line_starts_list = [0]
            cat_name_to_id: dict[str, int] = {"uncategorized": 0}
            cat_names: list[str] = ["uncategorized"]
            cat_ids: list[int] = []
            level_ids: list[int] = []

            for ln in lines:
                # Format as: timestamp category [LOG_LEVEL] message
                line_text = f"{ln.timestamp} {ln.category} [LOG_{ln.level.name}] {ln.message}\n"
                buf.extend(line_text.encode("utf-8"))
                line_starts_list.append(len(buf))

                cat = ln.category
                if cat not in cat_name_to_id:
                    cat_name_to_id[cat] = len(cat_names)
                    cat_names.append(cat)
                cat_ids.append(cat_name_to_id[cat])

                level_map = {lvl: i for i, lvl in enumerate(_LEVEL_LIST)}
                level_ids.append(level_map.get(ln.level, 3))

            store._buf = buf
            store._buf_lower = None  # lazy
            store.line_starts = np.array(line_starts_list, dtype=np.uint64)
            store.category_ids = np.array(cat_ids, dtype=np.uint16)
            store.levels = np.array(level_ids, dtype=np.uint8)
            store._category_names = cat_names
            store._category_name_to_id = cat_name_to_id
            store._format = "ksiva"

            store._build_category_tree()
            store._count_levels()
            store._apply_filters()
            self.update_indices(store.filtered_indices, selection_model, table_view)

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self._highlights = highlights

    def highlights(self) -> list[Highlight]:
        return self._highlights


class LogTableView(QTableView):
    """Table view for log navigation."""

    pin_lines_requested = Signal(list)
    unpin_lines_requested = Signal(list)
    highlight_lines_requested = Signal(list)
    unhighlight_lines_requested = Signal(list)

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

    def _selected_lines(self) -> list[RowRef]:
        """Return RowRef objects for all selected rows, sorted by row index."""
        model = self.model()
        if model is None:
            return []
        rows = sorted({idx.row() for idx in self.selectionModel().selectedIndexes()})
        lines: list[RowRef] = []
        for row in rows:
            line = model.data(model.index(row, 0), Qt.ItemDataRole.UserRole)
            if isinstance(line, RowRef):
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
                raw = model._store.get_raw(line._idx)
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

    def _highlight_selected_lines(self) -> None:
        """Emit highlight request for all selected line numbers."""
        lines = self._selected_lines()
        if lines:
            self.highlight_lines_requested.emit([line.line_number for line in lines])

    def _unhighlight_selected_lines(self) -> None:
        """Emit unhighlight request for all selected line numbers."""
        lines = self._selected_lines()
        if lines:
            self.unhighlight_lines_requested.emit([line.line_number for line in lines])

    def contextMenuEvent(self, event):  # noqa: N802
        """Right-click context menu for selected rows."""
        lines = self._selected_lines()
        pinned = {line.line_number for line in lines if self._is_pinned(line._idx)}
        highlighted = {line.line_number for line in lines if self._is_highlighted(line._idx)}
        unpinned_count = len(lines) - len(pinned)
        unhighlighted_count = len(lines) - len(highlighted)

        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        pin_action = None
        unpin_action = None
        highlight_action = None
        unhighlight_action = None

        if unpinned_count > 0:
            pin_action = menu.addAction("Pin")
        if len(pinned) > 0:
            unpin_action = menu.addAction("Unpin")
        menu.addSeparator()
        if unhighlighted_count > 0:
            highlight_action = menu.addAction("Highlight")
        if len(highlighted) > 0:
            unhighlight_action = menu.addAction("Remove highlight")

        action = menu.exec(event.globalPos())
        if action == copy_action:
            self._copy_selected_lines()
        elif action == pin_action:
            self._pin_selected_lines()
        elif action == unpin_action:
            self._unpin_selected_lines()
        elif action == highlight_action:
            self._highlight_selected_lines()
        elif action == unhighlight_action:
            self._unhighlight_selected_lines()

    def _is_pinned(self, idx: int) -> bool:
        """Check if line index is matched by any active pin rule."""
        model = self.model()
        if model is None or model._store is None:
            return False
        store = model._store
        for mask, enabled in zip(store._pin_masks, store.pinned_enabled):
            if enabled and idx < len(mask) and mask[idx]:
                return True
        return False

    def _is_highlighted(self, idx: int) -> bool:
        """Check if line index is matched by any active LINE_NUMBER highlight rule."""
        model = self.model()
        if model is None or model._store is None:
            return False
        store = model._store
        line_number = idx + 1
        for h, enabled in zip(store.highlights, store.highlight_enabled):
            if enabled and h.mode == SearchMode.LINE_NUMBER and h.pattern == str(line_number):
                return True
        return False
