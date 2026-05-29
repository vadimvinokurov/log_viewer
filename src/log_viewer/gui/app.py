"""Log Viewer GUI — PySide6 application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.command_history import CommandHistory
from log_viewer.core.command_parser import ParseError, parse_command
from log_viewer.core.config import ConfigManager
from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, Highlight, LogLevel, RowRef, SearchDirection, SearchMode, _LEVEL_LIST

from log_viewer.core.typography import Typography
from log_viewer.gui.bottom_bar import BottomBar
from log_viewer.gui.log_table import LogTableModel, LogTableView
from log_viewer.gui.side_panel import SidePanel
from log_viewer.gui.styles import APP_BASE, EMPTY_LABEL, AppProxyStyle, styles


class _FileLoadWorker(QThread):
    """Load file bytes in a background thread."""

    loaded = Signal(bytearray, str)
    error = Signal(str)

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            file_path = Path(os.path.expanduser(self._path))
            if not file_path.exists():
                self.error.emit(f"File not found: {self._path}")
                return
            buf = bytearray(file_path.read_bytes())
            self.loaded.emit(buf, self._path)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Log Viewer main window."""

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Log Viewer")
        self.resize(1200, 800)
        self._set_app_icon()
        self._apply_light_palette()

        # Core state
        self.log_store = LogStore()
        self._current_filename: str = ""
        self._config = ConfigManager()
        self._config.load()
        self._command_history = CommandHistory(self._config)

        # Widgets
        self.log_table = LogTableView()
        self._table_model = LogTableModel(store=self.log_store)
        self.log_table.setModel(self._table_model)
        self.log_table.pin_lines_requested.connect(self._on_pin_lines_requested)
        self.log_table.unpin_lines_requested.connect(self._on_unpin_lines_requested)
        self.log_table.highlight_lines_requested.connect(self._on_highlight_lines_requested)
        self.log_table.unhighlight_lines_requested.connect(self._on_unhighlight_lines_requested)

        self.side_panel = SidePanel()
        self.bottom_bar = BottomBar(history=self._command_history)

        # Layout: splitter (log table | side panel) + bottom bar
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self.log_table)
        self._splitter.addWidget(self.side_panel)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes([920, 280])

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._splitter)
        outer.addWidget(self.bottom_bar)
        self.setCentralWidget(central)

        # Side panel visible by default
        self._empty_label: QLabel | None = None
        self._show_empty_state()

        # Menus (removed — keyboard shortcuts only)
        self._build_shortcuts()

        # Signals
        self.bottom_bar.command_input.command_submitted.connect(self._on_command_submitted)
        self.bottom_bar.command_input.editing_finished.connect(self.log_table.setFocus)
        self.side_panel.category_tree.category_changed.connect(self._on_category_changed)
        self.side_panel.filter_list.filter_changed.connect(self._on_filter_changed)
        self.side_panel.filter_list.filter_removed.connect(self._on_filter_removed)
        self.side_panel.highlight_list.highlight_changed.connect(self._on_highlight_changed)
        self.side_panel.highlight_list.highlight_color_changed.connect(self._on_highlight_color_changed)
        self.side_panel.highlight_list.highlight_removed.connect(self._on_highlight_removed)
        self.side_panel.pinned_list.pin_changed.connect(self._on_pin_changed)
        self.side_panel.pinned_list.pin_removed.connect(self._on_pin_removed)
        self.bottom_bar.level_bar.level_clicked.connect(self._on_level_clicked)
        self.bottom_bar.open_clicked.connect(self._file_open_dialog)
        self.bottom_bar.reload_clicked.connect(lambda: self._handle_command("reload"))

        # Drag & Drop
        self.setAcceptDrops(True)

        # File loading
        self._load_worker: _FileLoadWorker | None = None

        # Initial file
        if file_path:
            self._open_file(file_path)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._file_open_dialog)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=lambda: self._handle_command("reload"))
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_side_panel)

    def _file_open_dialog(self) -> None:
        last_dir = self._config.get("last_open_dir", "")
        path, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir)
        if path:
            self._open_file(path)

    def _toggle_side_panel(self) -> None:
        if self.side_panel.isVisible():
            self.side_panel.hide()
        else:
            self._refresh_side_panel()
            self.side_panel.show()

    def _open_file(self, path: str) -> None:
        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.quit()
            self._load_worker.wait()
        self._load_worker = _FileLoadWorker(path)
        self._load_worker.loaded.connect(self._on_file_loaded)
        self._load_worker.error.connect(self._on_file_error)
        self._load_worker.start()

    def _save_last_open_dir(self, path: str) -> None:
        """Persist the directory of an opened file for next dialog start."""
        self._config.set("last_open_dir", os.path.dirname(path))
        self._config.save()

    def _on_file_loaded(self, buf: bytearray, path: str) -> None:
        self.log_store.load_bytes(buf, file_path=path)
        del buf  # Free reference (LogStore has its own copy)
        self._current_filename = Path(path).name
        self._hide_empty_state()
        self._refresh_display()
        self._save_last_open_dir(path)
        self._update_title()

    def _on_file_error(self, msg: str) -> None:
        self.bottom_bar.set_status(f"Error: {msg}")

    def _set_app_icon(self) -> None:
        """Find and set the app icon (works in dev and PyInstaller bundle)."""
        candidates = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "assets" / "icon.png")
        candidates.append(Path(__file__).resolve().parents[2] / "assets" / "icon.png")
        candidates.append(Path.cwd() / "assets" / "icon.png")
        for p in candidates:
            if p.is_file():
                self.setWindowIcon(QIcon(str(p)))
                return

    def _apply_light_palette(self) -> None:
        from log_viewer.core.themes import _t

        palette = QApplication.palette()
        canvas = QColor(_t("canvas"))
        card = QColor(_t("card"))
        ink = QColor(_t("ink"))
        graphite = QColor(_t("graphite"))
        silver = QColor(_t("silver_mist"))
        azure = QColor(_t("azure"))

        palette.setColor(QPalette.ColorRole.Window, canvas)
        palette.setColor(QPalette.ColorRole.AlternateBase, canvas)
        palette.setColor(QPalette.ColorRole.Button, card)
        palette.setColor(QPalette.ColorRole.Base, card)
        palette.setColor(QPalette.ColorRole.Text, ink)
        palette.setColor(QPalette.ColorRole.WindowText, ink)
        palette.setColor(QPalette.ColorRole.ButtonText, ink)
        palette.setColor(QPalette.ColorRole.PlaceholderText, graphite)
        palette.setColor(QPalette.ColorRole.Light, canvas)
        palette.setColor(QPalette.ColorRole.Midlight, silver)
        palette.setColor(QPalette.ColorRole.Dark, silver)
        palette.setColor(QPalette.ColorRole.Highlight, azure)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(_t("selection_fg")))
        QApplication.setPalette(palette)

    def _on_command_submitted(self, raw: str) -> None:
        if raw.startswith(":"):
            self._handle_command(raw[1:].strip())

    def _handle_command(self, cmd: str) -> None:
        if not cmd:
            return
        try:
            parsed = parse_command(cmd)
        except ParseError as e:
            self.bottom_bar.set_status(f"Error: {e}")
            return

        name = parsed.name

        if name == "q":
            self.close()
        elif name == "open":
            self._open_file(parsed.text)
        elif name in ("f", "fr", "fs"):
            mode = {"f": SearchMode.PLAIN, "fr": SearchMode.REGEX, "fs": SearchMode.SIMPLE}[name]
            self.log_store.add_filter(Filter(pattern=parsed.text, mode=mode))
            self._refresh_display()
        elif name == "rmf":
            self.log_store.clear_filters()
            self._refresh_display()
        elif name in ("s", "sr", "ss"):
            mode = {"s": SearchMode.PLAIN, "sr": SearchMode.REGEX, "ss": SearchMode.SIMPLE}[name]
            self._do_search(parsed.text, mode, SearchDirection.FORWARD)
        elif name == "cate":
            if not parsed.text:
                self.log_store.enable_all_categories()
            else:
                self.log_store.enable_category(parsed.text)
            self._refresh_display()
        elif name == "catd":
            if not parsed.text:
                self.log_store.disable_all_categories()
            else:
                self.log_store.disable_category(parsed.text)
            self._refresh_display()
        elif name in ("h", "hr", "hs"):
            mode = {"h": SearchMode.PLAIN, "hr": SearchMode.REGEX, "hs": SearchMode.SIMPLE}[name]
            self.log_store.add_highlight(
                Highlight(pattern=parsed.text, mode=mode)
            )
            self._refresh_display()
        elif name in ("fn", "hn"):
            line_num = self._parse_line_number(parsed.text, name)
            if line_num is None:
                return
            if name == "fn":
                self.log_store.add_filter(Filter(pattern=str(line_num), mode=SearchMode.LINE_NUMBER))
            else:
                self.log_store.add_highlight(Highlight(pattern=str(line_num), mode=SearchMode.LINE_NUMBER))
            self._refresh_display()
        elif name == "sn":
            line_num = self._parse_line_number(parsed.text, name)
            if line_num is None:
                return
            self._navigate_to_line(line_num)
        elif name == "rmh":
            self.log_store.clear_highlights()
            self._refresh_display()
        elif name == "reload":
            if self.log_store.current_file:
                self._open_file(self.log_store.current_file)
            else:
                self.bottom_bar.set_status("No file loaded")
        elif name in ("p", "pr", "ps"):
            mode = {"p": SearchMode.PLAIN, "pr": SearchMode.REGEX, "ps": SearchMode.SIMPLE}[name]
            self.log_store.add_pin(Filter(pattern=parsed.text, mode=mode))
            self._refresh_display()
        elif name == "pn":
            line_num = self._parse_line_number(parsed.text, name)
            if line_num is None:
                return
            self.log_store.add_pin(Filter(pattern=str(line_num), mode=SearchMode.LINE_NUMBER))
            self._refresh_display()
        elif name == "rmp":
            self.log_store.unpin_all()
            self._refresh_display()

    def _do_search(
        self, pattern: str, mode: SearchMode, direction: SearchDirection
    ) -> None:
        if not pattern:
            return
        start_line = 0
        sel = self.log_table.selectionModel().selectedRows()
        if sel:
            pos = sel[0].row()
            indices = self.log_store.filtered_indices
            if pos < len(indices):
                start_line = int(indices[pos])
        self.log_store.search(pattern, mode, direction=direction, start_line=start_line)
        ss = self.log_store.search_state
        if ss and ss.matches:
            ss.in_search = True
        self._update_status()
        self._update_title()
        self._jump_to_search_match()

    def _on_category_changed(self) -> None:
        """Sync category tree checkboxes back to LogStore and refresh."""
        disabled = self.side_panel.category_tree.get_disabled_paths()
        self.log_store.set_disabled_categories(disabled)
        self._refresh_log_only()

    def _on_filter_changed(self) -> None:
        """Sync filter toggles back to LogStore and refresh."""
        self.log_store.filter_enabled = list(self.side_panel.filter_list._enabled)
        self._refresh_log_only()

    def _on_filter_removed(self, index: int) -> None:
        """Remove filter from LogStore and refresh."""
        del self.log_store.filters[index]
        del self.log_store.filter_enabled[index]
        del self.log_store._filter_masks[index]
        self._refresh_log_only()

    def _on_highlight_changed(self) -> None:
        """Sync highlight toggles back to LogStore and refresh."""
        self.log_store.highlight_enabled = list(self.side_panel.highlight_list._enabled)
        self._refresh_log_only()

    def _on_highlight_color_changed(self, index: int, color_hex: str) -> None:
        """Update highlight color and refresh."""
        self.log_store.highlights[index].color = color_hex
        self._refresh_log_only()

    def _on_highlight_removed(self, index: int) -> None:
        """Remove highlight from LogStore and refresh."""
        del self.log_store.highlights[index]
        del self.log_store.highlight_enabled[index]
        self._refresh_log_only()

    def _on_pin_changed(self) -> None:
        """Sync pin toggle state from side panel to store."""
        self.log_store.pinned_enabled = list(self.side_panel.pinned_list._enabled)
        self._refresh_log_only()

    def _on_pin_removed(self, index: int) -> None:
        """Remove a pin rule by index and refresh."""
        self.log_store.remove_pin(index)
        self._refresh_display()

    def _on_pin_lines_requested(self, line_numbers: list[int]) -> None:
        """Pin multiple lines from context menu — each as a LINE_NUMBER rule."""
        for ln in line_numbers:
            self.log_store.add_pin(Filter(pattern=str(ln), mode=SearchMode.LINE_NUMBER))
        self._refresh_display()

    def _on_unpin_lines_requested(self, line_numbers: list[int]) -> None:
        """Unpin multiple lines from context menu — remove matching LINE_NUMBER rules."""
        to_remove = [str(ln) for ln in line_numbers]
        indices = [
            i for i, r in enumerate(self.log_store.pinned_rules)
            if r.mode == SearchMode.LINE_NUMBER and r.pattern in to_remove
        ]
        for i in reversed(indices):
            self.log_store.remove_pin(i)
        self._refresh_display()

    def _on_highlight_lines_requested(self, line_numbers: list[int]) -> None:
        """Highlight multiple lines from context menu — each as a LINE_NUMBER rule."""
        for ln in line_numbers:
            self.log_store.add_highlight(Highlight(pattern=str(ln), mode=SearchMode.LINE_NUMBER))
        self._refresh_display()

    def _on_unhighlight_lines_requested(self, line_numbers: list[int]) -> None:
        """Remove LINE_NUMBER highlights for selected lines."""
        to_remove = [str(ln) for ln in line_numbers]
        indices = [
            i for i, h in enumerate(self.log_store.highlights)
            if h.mode == SearchMode.LINE_NUMBER and h.pattern in to_remove
        ]
        for i in reversed(indices):
            del self.log_store.highlights[i]
            del self.log_store.highlight_enabled[i]
        self._refresh_display()

    def _on_level_clicked(self, level: LogLevel) -> None:
        """Toggle a log level and refresh display."""
        self.log_store.toggle_level(level)
        self._refresh_log_only()

    def _refresh_log_only(self) -> None:
        """Refresh log table and status without rebuilding side panel."""
        store = self.log_store
        store._apply_filters()
        self._table_model.update_indices(
            store.filtered_indices,
            selection_model=self.log_table.selectionModel(),
            table_view=self.log_table,
        )
        active_highlights = [h for h, e in zip(store.highlights, store.highlight_enabled) if e]
        self._table_model.set_highlights(active_highlights)
        self._update_status()

    def _refresh_display(self) -> None:
        store = self.log_store
        self._table_model.update_indices(
            store.filtered_indices,
            selection_model=self.log_table.selectionModel(),
            table_view=self.log_table,
        )
        active_highlights = [h for h, e in zip(store.highlights, store.highlight_enabled) if e]
        self._table_model.set_highlights(active_highlights)
        self._refresh_side_panel()
        self._update_status()

    def _refresh_side_panel(self) -> None:
        store = self.log_store
        self.side_panel.category_tree.rebuild(store.category_tree)
        self.side_panel.filter_list.set_filters(store.filters, store.filter_enabled)
        self.side_panel.highlight_list.set_highlights(store.highlights, store.highlight_enabled)
        self.side_panel.pinned_list.set_pins(store.pinned_rules, store.pinned_enabled)

    def _update_status(self) -> None:
        store = self.log_store
        disabled = {_LEVEL_LIST[lid] for lid in store.disabled_levels}
        self.bottom_bar.level_bar.sync_from_store(
            disabled, store.level_button_counts
        )

    def _update_title(self) -> None:
        ss = self.log_store.search_state
        base = f"Log Viewer \u2014 {self._current_filename}" if self._current_filename else "Log Viewer"
        if ss and ss.in_search:
            self.setWindowTitle(f"{base} \u2014 Search: {ss.pattern}")
        else:
            self.setWindowTitle(base)

    def _parse_line_number(self, text: str, cmd_name: str) -> int | None:
        """Parse and validate a line number from command text."""
        try:
            n = int(text.strip())
        except ValueError:
            self.bottom_bar.set_status(f"Error: {cmd_name} requires a line number")
            return None
        if n < 1 or n > self.log_store.n:
            self.bottom_bar.set_status(f"Error: line {n} out of range (1..{self.log_store.n})")
            return None
        return n

    def _navigate_to_line(self, line_number: int) -> None:
        """Scroll to and select a line by its 1-based line number."""
        idx = line_number - 1
        indices = self.log_store.filtered_indices
        pos = int(np.searchsorted(indices, idx))
        if pos < len(indices) and int(indices[pos]) == idx:
            self.log_table.selectRow(pos)
            self.log_table.scrollTo(
                self._table_model.index(pos, 0),
                LogTableView.ScrollHint.PositionAtCenter,
            )
        else:
            self.bottom_bar.set_status(f"Line {line_number} is filtered out")

    def _jump_to_search_match(self) -> None:
        ss = self.log_store.search_state
        if not ss or not ss.matches:
            return
        matched_idx = ss.matches[ss.current_index]
        indices = self.log_store.filtered_indices
        pos = int(np.searchsorted(indices, matched_idx))
        if pos < len(indices) and int(indices[pos]) == matched_idx:
            self.log_table.selectRow(pos)
            self.log_table.scrollTo(
                self._table_model.index(pos, 0),
                LogTableView.ScrollHint.PositionAtCenter,
            )

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if event.type() == event.Type.KeyPress:
            text = event.text()
            key = event.key()
            ss = self.log_store.search_state

            focused = QApplication.focusWidget()
            in_command_input = isinstance(focused, QLineEdit)

            if text == ":" and not in_command_input:
                self.bottom_bar.activate_command_mode()
                return True

            # Search mode navigation
            if ss and ss.in_search:
                if key == Qt.Key.Key_Down:
                    self.log_table.setFocus()
                    self.log_store.next_match()
                    self._update_status()
                    self._jump_to_search_match()
                    return True
                if key == Qt.Key.Key_Up:
                    self.log_table.setFocus()
                    self.log_store.prev_match()
                    self._update_status()
                    self._jump_to_search_match()
                    return True
                if key == Qt.Key.Key_Escape:
                    ss.in_search = False
                    self._update_title()
                    return True

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        super().keyPressEvent(event)

    def _show_empty_state(self) -> None:
        if self._empty_label is not None:
            return
        self._empty_label = QLabel("Drop a log file here or click Open")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(styles.resolve(EMPTY_LABEL))
        self._splitter.replaceWidget(0, self._empty_label)

    def _hide_empty_state(self) -> None:
        if self._empty_label is None:
            return
        self._splitter.replaceWidget(0, self.log_table)
        self._empty_label.deleteLater()
        self._empty_label = None

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._open_file(path)
                break


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(Typography.UI_FONT)
    app.setStyle(AppProxyStyle())
    app.setStyleSheet(styles.resolve(APP_BASE))
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = MainWindow(file_path=file_path)
    window.show()
    window.log_table.setFocus()
    app.installEventFilter(window)
    sys.exit(app.exec())
