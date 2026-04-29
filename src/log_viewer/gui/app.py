"""Log Viewer GUI — PySide6 application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from log_viewer.core.command_parser import ParseError, parse_command
from log_viewer.core.config import ConfigManager
from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, Highlight, SearchDirection, SearchMode
from log_viewer.core.preset_manager import PresetManager
from log_viewer.core.suggester import CommandSuggester

from log_viewer.gui.bottom_bar import BottomBar
from log_viewer.gui.log_table import LogTableModel, LogTableView
from log_viewer.gui.side_panel import SidePanel


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
                    self.loaded.emit(data.splitlines(), self._path)
                    return

            file_path = Path(os.path.expanduser(self._path))
            if not file_path.exists():
                self.error.emit(f"File not found: {self._path}")
                return
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            self.loaded.emit(lines, self._path)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Log Viewer main window."""

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Log Viewer")
        self.resize(1200, 800)

        # Core state
        self.log_store = LogStore()
        self._config = ConfigManager()
        self._config.load()
        self._presets = PresetManager(self._config)
        self._suggester = CommandSuggester()
        self._suggester.log_store = self.log_store

        # Widgets
        self.log_table = LogTableView()
        self._table_model = LogTableModel()
        self.log_table.setModel(self._table_model)

        self.side_panel = SidePanel()
        self.bottom_bar = BottomBar()

        # Layout: splitter (log table | side panel) + bottom bar
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self.log_table)
        self._splitter.addWidget(self.side_panel)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._splitter)
        outer.addWidget(self.bottom_bar)
        self.setCentralWidget(central)

        # Side panel hidden by default
        self.side_panel.hide()

        # Menus
        self._build_menus()

        # Signals
        self.bottom_bar.command_input.command_submitted.connect(self._on_command_submitted)

        # Drag & Drop
        self.setAcceptDrops(True)

        # File loading
        self._load_worker: _FileLoadWorker | None = None

        # Initial file
        if file_path:
            self._open_file(file_path)

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._file_open_dialog)
        file_menu.addAction(open_action)

        reload_action = QAction("Reload", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(lambda: self._handle_command("reload"))
        file_menu.addAction(reload_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = menu_bar.addMenu("Edit")
        copy_action = QAction("Copy Line", self)
        copy_action.triggered.connect(lambda: self.log_table._copy_current_line())
        edit_menu.addAction(copy_action)

        view_menu = menu_bar.addMenu("View")
        toggle_panel = QAction("Toggle Side Panel", self)
        toggle_panel.triggered.connect(self._toggle_side_panel)
        view_menu.addAction(toggle_panel)

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
        self._refresh_display()

    def _on_file_error(self, msg: str) -> None:
        self.bottom_bar.set_status(f"Error: {msg}")

    def _on_command_submitted(self, raw: str) -> None:
        if raw.startswith(":"):
            self._handle_command(raw[1:].strip())
        elif raw.startswith("/"):
            self._do_search(raw[1:], SearchMode.PLAIN, SearchDirection.FORWARD)
        elif raw.startswith("?"):
            self._do_search(raw[1:], SearchMode.PLAIN, SearchDirection.BACKWARD)
        self.log_table.setFocus()

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
            color = parsed.flags.get("color", "red")
            self.log_store.add_highlight(
                Highlight(pattern=parsed.text, mode=mode, color=color)
            )
            self._refresh_display()
        elif name == "rmh":
            if not parsed.text:
                self.log_store.clear_highlights()
            else:
                self.log_store.highlights = [
                    h for h in self.log_store.highlights if h.pattern != parsed.text
                ]
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
        existing_hl = {(h.pattern, h.color) for h in self.log_store.highlights}
        for hd in data.get("highlights", []):
            if (hd["pattern"], hd.get("color", "red")) not in existing_hl:
                self.log_store.add_highlight(
                    Highlight(
                        hd["pattern"],
                        SearchMode(hd["mode"]),
                        color=hd.get("color", "red"),
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

    def _refresh_display(self) -> None:
        store = self.log_store
        visible_lines = [store.lines[i] for i in store.filtered_indices]
        self._table_model.update_lines(visible_lines)
        self._refresh_side_panel()
        self._update_status()

    def _refresh_side_panel(self) -> None:
        store = self.log_store
        self.side_panel.category_tree.rebuild(store.category_tree)
        self.side_panel.filter_list.set_filters(store.filters)
        self.side_panel.highlight_list.set_highlights(store.highlights)

    def _update_status(self) -> None:
        store = self.log_store
        filename = store.current_file or "no file"
        visible = len(store.filtered_indices)
        total = len(store.lines)
        parts = [filename, f"{visible}/{total} lines"]
        for level, count in store.visible_level_counts.items():
            if count:
                parts.append(f"{level.icon_plain}{count}")
        if store.search_state and store.search_state.matches:
            ss = store.search_state
            parts.append(f"match {ss.current_index + 1}/{len(ss.matches)}")
        self.bottom_bar.set_status(" | ".join(parts))

    def _jump_to_search_match(self) -> None:
        ss = self.log_store.search_state
        if not ss or not ss.matches:
            return
        matched_idx = ss.matches[ss.current_index]
        if matched_idx in self.log_store.filtered_indices:
            row = self.log_store.filtered_indices.index(matched_idx)
            self.log_table.selectRow(row)
            self.log_table.scrollTo(self._table_model.index(row, 0))

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if self.log_table.hasFocus():
            text = event.text()
            if text == ":":
                self.bottom_bar.activate_command_mode()
                return
            if text == "/":
                self.bottom_bar.command_input.setText("/")
                self.bottom_bar.command_input.setFocus()
                return
            if text == "n" and self.log_store.search_state:
                self.log_store.next_match()
                self._update_status()
                self._jump_to_search_match()
                return
            if text == "N" and self.log_store.search_state:
                self.log_store.prev_match()
                self._update_status()
                self._jump_to_search_match()
                return
        super().keyPressEvent(event)

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
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = MainWindow(file_path=file_path)
    window.show()
    sys.exit(app.exec())
