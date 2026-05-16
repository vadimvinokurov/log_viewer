"""Log table model and view with vim-style navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QMenu, QTableView

from log_viewer.core.models import Highlight, LogLine
from log_viewer.core.themes import _t
from log_viewer.gui.highlight_delegate import HighlightDelegate
from log_viewer.gui.scroll_utils import install_hover_scrollbar
from log_viewer.core.typography import Typography

if TYPE_CHECKING:
    from log_viewer.core.log_store import LogStore

_COLUMNS = ("Line", "Time", "Category", "Message")

_LEVEL_COLORS: dict[str, str] = {
    "CRITICAL": _t("level_colors")["CRITICAL"],
    "ERROR":    _t("level_colors")["ERROR"],
    "WARNING":  _t("level_colors")["WARNING"],
}


class LogTableModel(QAbstractTableModel):
    """Table model backed by a list of LogLine objects."""

    def __init__(self, lines: list[LogLine] | None = None, store: LogStore | None = None) -> None:
        super().__init__()
        self._lines: list[LogLine] = lines or []
        self._highlights: list[Highlight] = []
        self._pinned_line_numbers: set[int] = set()
        self._monospace_font = Typography.LOG_FONT
        self._store = store

    @property
    def lines(self) -> list[LogLine]:
        return self._lines

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._lines)

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
        if not index.isValid() or index.row() >= len(self._lines):
            return None

        line = self._lines[index.row()]

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
            if index.column() == 3:  # Message column
                return self._monospace_font
            return None

        return None

    def update_lines(self, lines: list[LogLine]) -> None:
        if self._lines is lines or (len(self._lines) == len(lines) and all(a is b for a, b in zip(self._lines, lines))):
            return
        self.beginResetModel()
        self._lines = lines
        self.endResetModel()

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self._highlights = highlights

    def set_pinned_line_numbers(self, line_numbers: set[int]) -> None:
        self._pinned_line_numbers = line_numbers

    def highlights(self) -> list[Highlight]:
        return self._highlights



class LogTableView(QTableView):
    """Table view with vim-style key bindings for log navigation."""

    pin_lines_requested = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setFont(Typography.LOG_FONT)
        self.verticalHeader().setMinimumSectionSize(1)
        self.verticalHeader().setDefaultSectionSize(Typography.TABLE_ROW_HEIGHT)
        self.verticalHeader().hide()

        self.horizontalHeader().setStyleSheet(
            f"""
            QHeaderView::section {{
                background-color: {_t('log_table')};
                color: {_t('graphite')};
                padding: 0px 8px;
                border: none;
                border-bottom: 1px solid {_t('silver_mist')};
                font-weight: 600;
                font-size: 11px;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }}
            """
        )
        self.horizontalHeader().setFixedHeight(Typography.TABLE_ROW_HEIGHT)

        self.setStyleSheet(
            f"""
            QTableView {{
                background-color: {_t('log_table')};
                alternate-background-color: {_t('card')};
            }}
            """
        )
        self._default_widths_set = False
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        install_hover_scrollbar(self)

        self._g_pressed: bool = False
        self._y_pressed: bool = False
        self.setItemDelegateForColumn(3, HighlightDelegate())

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

    def contextMenuEvent(self, event):  # noqa: N802
        """Right-click context menu for selected rows."""
        menu = QMenu(self)
        copy_action = menu.addAction("Copy lines")
        pin_action = menu.addAction("Pin lines")

        action = menu.exec(event.globalPos())
        if action == copy_action:
            self._copy_selected_lines()
        elif action == pin_action:
            self._pin_selected_lines()
