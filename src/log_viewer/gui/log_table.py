"""Log table model and view with vim-style navigation."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import QApplication, QTableView

from log_viewer.core.models import LogLine, LogLevel

_COLUMNS = ("Line", "Time", "Category", "Message")

_LEVEL_COLORS: dict[str, str] = {
    "CRITICAL": "darkred",
    "ERROR": "red",
    "WARNING": "gold",
    "INFO": "darkgray",
    "DEBUG": "teal",
    "TRACE": "gray",
}


class LogTableModel(QAbstractTableModel):
    """Table model backed by a list of LogLine objects."""

    def __init__(self, lines: list[LogLine] | None = None) -> None:
        super().__init__()
        self._lines: list[LogLine] = lines or []

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

        if role == Qt.ItemDataRole.UserRole:
            return line

        return None

    def update_lines(self, lines: list[LogLine]) -> None:
        self.beginResetModel()
        self._lines = lines
        self.endResetModel()


class LogTableView(QTableView):
    """Table view with vim-style key bindings for log navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()

        font = QFont("Monospace", 10)
        self.setFont(font)

        self._g_pressed: bool = False
        self._y_pressed: bool = False

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
            QApplication.clipboard().setText(line.raw)
