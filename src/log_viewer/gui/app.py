"""Log Viewer GUI — PySide6 application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QThread, Signal
from PySide6.QtGui import QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.command_parser import ParseError, parse_command
from log_viewer.core.config import ConfigManager
from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, Highlight, LogLevel, SearchDirection, SearchMode
from log_viewer.core.preset_manager import PresetManager
from log_viewer.core.suggester import CommandSuggester

from log_viewer.gui.bottom_bar import BottomBar
from log_viewer.gui.log_table import LogTableModel, LogTableView
from log_viewer.gui.side_panel import SidePanel
from log_viewer.gui.styles import APP_BASE, EMPTY_LABEL, AppProxyStyle, styles


class _FileLoadWorker(QThread):
    """Load file lines in a background thread."""

    loaded = Signal(list, str)
    error = Signal(str)

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            if self._path.startswith(("http://", "https://")):
                import urllib.request

                req = urllib.request.Request(self._path)
                with urllib.request.urlopen(req) as resp:
                    if resp.status >= 400:
                        self.error.emit(f"HTTP {resp.status}: {resp.reason}")
                        return
                    data = resp.read().decode("utf-8", errors="replace")
                    self.loaded.emit(data.split("\n"), self._path)
                    return

            file_path = Path(os.path.expanduser(self._path))
            if not file_path.exists():
                self.error.emit(f"File not found: {self._path}")
                return
            lines = file_path.read_text(encoding="utf-8", errors="replace").split("\n")
            self.loaded.emit(lines, self._path)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Log Viewer main window."""

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Log Viewer")
        self.resize(1200, 800)
        self._apply_light_palette()

        # Core state
        self.log_store = LogStore()
        self._config = ConfigManager()
        self._config.load()
        self._presets = PresetManager(self._config)
        self._suggester = CommandSuggester()
        self._suggester.log_store = self.log_store

        # Widgets
        self.log_table = LogTableView()
        self._table_model = LogTableModel(store=self.log_store)
        self.log_table.setModel(self._table_model)
        self.log_table.pin_lines_requested.connect(self._on_pin_lines_requested)
        self.log_table.unpin_lines_requested.connect(self._on_unpin_lines_requested)

        self.side_panel = SidePanel()
        self.bottom_bar = BottomBar()

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
        self.bottom_bar.command_input.textChanged.connect(self._on_command_text_changed)
        self.side_panel.category_tree.category_changed.connect(self._on_category_changed)
        self.side_panel.filter_list.filter_changed.connect(self._on_filter_changed)
        self.side_panel.filter_list.filter_removed.connect(self._on_filter_removed)
        self.side_panel.highlight_list.highlight_changed.connect(self._on_highlight_changed)
        self.side_panel.highlight_list.highlight_color_changed.connect(self._on_highlight_color_changed)
        self.side_panel.highlight_list.highlight_removed.connect(self._on_highlight_removed)
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
        path, _ = QFileDialog.getOpenFileName(self, "Open Log File")
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

    def _on_file_loaded(self, lines: list[str], path: str) -> None:
        self.log_store.load_lines(lines, file_path=path)
        # Update window title with filename
        filename = Path(path).name if not path.startswith(("http://", "https://")) else path
        self.setWindowTitle(f"Log Viewer \u2014 {filename}")
        self._hide_empty_state()
        self._refresh_display()

    def _on_file_error(self, msg: str) -> None:
        self.bottom_bar.set_status(f"Error: {msg}")

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.PaletteChange:
            self._apply_light_palette()
        return super().event(event)

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
        elif raw.startswith("/"):
            self._do_search(raw[1:], SearchMode.PLAIN, SearchDirection.FORWARD)
        elif raw.startswith("?"):
            self._do_search(raw[1:], SearchMode.PLAIN, SearchDirection.BACKWARD)
        self.log_table.setFocus()

    def _on_command_text_changed(self, text: str) -> None:
        if text.startswith(":"):
            suggestions = self._suggester.get_all_suggestions(text)
            self.bottom_bar.command_input.set_suggestions(suggestions)

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
            if not parsed.text:
                self.log_store.clear_filters()
            else:
                self.log_store.remove_filter(parsed.text)
            self._refresh_display()
        elif name == "lsf":
            self._toggle_side_panel()
            self.side_panel.setCurrentIndex(1)
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
        elif name == "lscat":
            self._toggle_side_panel()
        elif name in ("h", "hr", "hs"):
            mode = {"h": SearchMode.PLAIN, "hr": SearchMode.REGEX, "hs": SearchMode.SIMPLE}[name]
            self.log_store.add_highlight(
                Highlight(pattern=parsed.text, mode=mode)
            )
            self._refresh_display()
        elif name == "rmh":
            if not parsed.text:
                self.log_store.clear_highlights()
            else:
                kept = [(h, e) for h, e in zip(self.log_store.highlights, self.log_store.highlight_enabled)
                        if h.pattern != parsed.text]
                self.log_store.highlights = [h for h, _ in kept]
                self.log_store.highlight_enabled = [e for _, e in kept]
            self._refresh_display()
        elif name == "lsh":
            self._toggle_side_panel()
            self.side_panel.setCurrentIndex(2)
        elif name == "preset":
            parts = parsed.text.strip().split(None, 1)
            if len(parts) == 2:
                action, pname = parts
                if action == "save":
                    self._save_preset(pname)
                elif action == "load":
                    self._load_preset(pname)
            self._refresh_display()
        elif name == "rmpreset":
            try:
                self._presets.delete(parsed.text)
            except FileNotFoundError:
                self.bottom_bar.set_status(f"Preset not found: {parsed.text}")
        elif name == "lspreset":
            names = self._presets.list_presets()
            self.bottom_bar.set_status(
                "Presets: " + ", ".join(names) if names else "No presets"
            )
        elif name == "reload":
            if self.log_store.current_file:
                self._open_file(self.log_store.current_file)
            else:
                self.bottom_bar.set_status("No file loaded")
        elif name == "pin":
            try:
                line_num = int(parsed.text.strip())
            except ValueError:
                self.bottom_bar.set_status("Error: pin requires a line number")
                return
            self.log_store.pin_line(line_num)
            self._refresh_display()
        elif name == "unpin":
            if not parsed.text:
                self.log_store.unpin_all()
            else:
                try:
                    line_num = int(parsed.text.strip())
                except ValueError:
                    self.bottom_bar.set_status("Error: unpin requires a line number")
                    return
                self.log_store.unpin_line(line_num)
            self._refresh_display()

    def _do_search(
        self, pattern: str, mode: SearchMode, direction: SearchDirection
    ) -> None:
        if not pattern:
            return
        self.log_store.search(pattern, mode, direction=direction)
        self._update_status()
        self._jump_to_search_match()

    def _save_preset(self, name: str) -> None:
        disabled = [
            path for path, node in self._iter_category_nodes() if not node.enabled
        ]
        state = {
            "filters": self.log_store.filters,
            "highlights": self.log_store.highlights,
            "disabled_categories": disabled,
        }
        self._presets.save(name, state)

    def _load_preset(self, name: str) -> None:
        try:
            data = self._presets.load(name)
        except FileNotFoundError:
            self.bottom_bar.set_status(f"Preset not found: {name}")
            return
        existing = {(f.pattern, f.mode.value) for f in self.log_store.filters}
        for fd in data.get("filters", []):
            if (fd["pattern"], fd["mode"]) not in existing:
                self.log_store.add_filter(
                    Filter(fd["pattern"], SearchMode(fd["mode"]))
                )
        existing_hl_patterns = {h.pattern for h in self.log_store.highlights}
        for hd in data.get("highlights", []):
            if hd["pattern"] not in existing_hl_patterns:
                self.log_store.add_highlight(
                    Highlight(
                        hd["pattern"],
                        SearchMode(hd["mode"]),
                    )
                )
        for cat in data.get("disabled_categories", []):
            self.log_store.disable_category(cat)

    def _iter_category_nodes(self):
        def _walk(node):
            for child in node.children.values():
                yield child.full_path, child
                yield from _walk(child)

        yield from _walk(self.log_store.category_tree)

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

    def _on_pin_removed(self, line_number: int) -> None:
        """Unpin a line from the side panel and refresh."""
        self.log_store.unpin_line(line_number)
        self._refresh_display()

    def _on_pin_lines_requested(self, line_numbers: list[int]) -> None:
        """Pin multiple lines from context menu and refresh."""
        self.log_store.pin_lines(line_numbers)
        self._refresh_display()

    def _on_unpin_lines_requested(self, line_numbers: list[int]) -> None:
        """Unpin multiple lines from context menu and refresh."""
        self.log_store.unpin_lines(line_numbers)
        self._refresh_display()

    def _on_level_clicked(self, level: LogLevel) -> None:
        """Toggle a log level and refresh display."""
        self.log_store.toggle_level(level)
        self._refresh_log_only()

    def _refresh_log_only(self) -> None:
        """Refresh log table and status without rebuilding side panel."""
        store = self.log_store
        store._apply_filters()
        visible_lines = [store.lines[i] for i in store.filtered_indices]
        self._table_model.update_lines(visible_lines)
        self._table_model.set_pinned_line_numbers(store.pinned_line_numbers)
        active_highlights = [h for h, e in zip(store.highlights, store.highlight_enabled) if e]
        self._table_model.set_highlights(active_highlights)
        self._update_status()

    def _refresh_display(self) -> None:
        store = self.log_store
        visible_lines = [store.lines[i] for i in store.filtered_indices]
        self._table_model.update_lines(visible_lines)
        self._table_model.set_pinned_line_numbers(store.pinned_line_numbers)
        active_highlights = [h for h, e in zip(store.highlights, store.highlight_enabled) if e]
        self._table_model.set_highlights(active_highlights)
        self._refresh_side_panel()
        self._update_status()

    def _refresh_side_panel(self) -> None:
        store = self.log_store
        self.side_panel.category_tree.rebuild(store.category_tree)
        self.side_panel.filter_list.set_filters(store.filters, store.filter_enabled)
        self.side_panel.highlight_list.set_highlights(store.highlights, store.highlight_enabled)
        pinned_lines = {ln: store.lines[ln - 1] for ln in store.pinned_line_numbers if 0 <= ln - 1 < len(store.lines)}
        self.side_panel.pinned_list.set_pins(sorted(store.pinned_line_numbers), pinned_lines)

    def _update_status(self) -> None:
        store = self.log_store
        self.bottom_bar.level_bar.sync_from_store(
            store.disabled_levels, store.level_button_counts
        )

    def _jump_to_search_match(self) -> None:
        ss = self.log_store.search_state
        if not ss or not ss.matches:
            return
        matched_idx = ss.matches[ss.current_index]
        if matched_idx in self.log_store.filtered_indices:
            row = self.log_store.filtered_indices.index(matched_idx)
            self.log_table.selectRow(row)
            self.log_table.scrollTo(self._table_model.index(row, 0))

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if event.type() == event.Type.KeyPress:
            text = event.text()
            if text == ":":
                self.bottom_bar.activate_command_mode()
                return True
            if text == "/" and not isinstance(obj, (QLineEdit, QTextEdit)):
                self.bottom_bar.command_input.setText("/")
                self.bottom_bar.command_input.setFocus()
                return True
            if text == "n" and self.log_store.search_state:
                self.log_table.setFocus()
                self.log_store.next_match()
                self._update_status()
                self._jump_to_search_match()
                return True
            if text == "N" and self.log_store.search_state:
                self.log_table.setFocus()
                self.log_store.prev_match()
                self._update_status()
                self._jump_to_search_match()
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
    app.setStyle(AppProxyStyle())
    app.setStyleSheet(styles.resolve(APP_BASE))
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = MainWindow(file_path=file_path)
    window.show()
    window.log_table.setFocus()
    app.installEventFilter(window)
    sys.exit(app.exec())
