"""Log Viewer TUI application."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.events import Key
from textual.worker import get_current_worker
from textual.widgets import Header
from rich.text import Text

from log_viewer.core.command_parser import parse_command, ParseError
from log_viewer.core.command_history import CommandHistory
from log_viewer.core.config import ConfigManager
from log_viewer.core.log_store import LogStore
from log_viewer.core.models import (
    Filter,
    Highlight,
    InputMode,
    SearchDirection,
    SearchMode,
)
from log_viewer.core.preset_manager import PresetManager
from log_viewer.core.filter_engine import find_spans
from log_viewer.tui.screens.category_list import CategoryListScreen
from log_viewer.tui.screens.filter_list import FilterListScreen
from log_viewer.tui.screens.highlight_list import HighlightListScreen
from log_viewer.tui.widgets.category_panel import CategoryPanel
from log_viewer.tui.widgets.command_input import CommandInput
from log_viewer.tui.widgets.log_panel import LogPanel
from log_viewer.tui.widgets.status_bar import StatusBar


def _apply_highlights(text: str, base_style: str, highlights: list[Highlight]) -> Text:
    """Create a Rich Text with highlight color spans applied on top of base style."""
    rich = Text(text, style=base_style)
    for h in highlights:
        spans = find_spans(text, h.pattern, h.mode, h.case_sensitive)
        for start, end in spans:
            rich.stylize(f"on {h.color}", start, end)
    return rich


class LogViewerApp(App):
    """Log Viewer v2.0 — TUI application."""

    TITLE = "Log Viewer v2.0"

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-content {
        layout: horizontal;
        height: 1fr;
    }
    LogPanel {
        width: 3fr;
    }
    CategoryPanel {
        width: 1fr;
    }
    .bottom-bar {
        dock: bottom;
        height: 1;
        layout: horizontal;
        overflow: hidden;
    }
    """

    def __init__(
        self, file_path: str | None = None, config_dir: Path | None = None
    ) -> None:
        super().__init__()
        self.log_store = LogStore()
        self._input_mode = InputMode.NORMAL
        self._exit = False
        self._initial_file = file_path
        self._config_manager = ConfigManager(config_dir=config_dir)
        self._config_manager.load()
        self._preset_manager = PresetManager(self._config_manager)
        self._command_history = CommandHistory(self._config_manager)
        self._y_pressed = False

    @property
    def input_mode(self) -> InputMode:
        return self._input_mode

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-content"):
            yield LogPanel()
            yield CategoryPanel(self.log_store)
        with Horizontal(classes="bottom-bar"):
            yield CommandInput()
            yield StatusBar()

    def on_mount(self) -> None:
        self._update_status()
        self.query_one(LogPanel).focus()
        cmd_input = self.query_one(CommandInput)
        cmd_input.set_log_store(self.log_store)
        if self._initial_file:
            self._open_file(self._initial_file)

    def on_key(self, event: Key) -> None:
        """Intercept :, /, ?, q, yy when LogPanel is focused."""
        if isinstance(self.focused, LogPanel):
            if event.character == "q":
                event.prevent_default()
                self._exit = True
                self.exit()
            elif event.character == ":":
                event.prevent_default()
                self._enter_input_mode(":", InputMode.COMMAND)
            elif event.character == "/":
                event.prevent_default()
                self._enter_input_mode("/", InputMode.SEARCH_FORWARD)
            elif event.character == "?":
                event.prevent_default()
                self._enter_input_mode("?", InputMode.SEARCH_BACKWARD)
            elif event.character == "n" and self.log_store.search_state:
                event.prevent_default()
                self.log_store.next_match()
                self._update_status()
                self._update_search_highlight()
            elif event.key == "N" and self.log_store.search_state:
                event.prevent_default()
                self.log_store.prev_match()
                self._update_status()
                self._update_search_highlight()
            elif event.character == "y":
                event.prevent_default()
                if self._y_pressed:
                    self._y_pressed = False
                    self._copy_current_line()
                else:
                    self._y_pressed = True
                    self.set_timer(0.3, self._reset_y)
            else:
                self._y_pressed = False

    def _reset_y(self) -> None:
        self._y_pressed = False

    def _copy_current_line(self) -> None:
        """Copy current line raw text to clipboard."""
        panel = self.query_one(LogPanel)
        row = panel.cursor_row
        store = self.log_store
        if row < len(store.filtered_indices):
            idx = store.filtered_indices[row]
            raw = store.lines[idx].raw
            try:
                import pyperclip
                pyperclip.copy(raw)
                self._show_status_message(f"Copied line {idx + 1}")
            except pyperclip.PyperclipException:
                self._show_error("Clipboard not available")

    def _enter_input_mode(self, prefix: str, mode: InputMode) -> None:
        """Switch focus to CommandInput with the given prefix and mode."""
        cmd_input = self.query_one(CommandInput)
        cmd_input.value = prefix
        cmd_input.focus()
        cmd_input.cursor_position = len(prefix)
        self._input_mode = mode

    def _return_to_log_panel(self) -> None:
        """Clear input and return focus to LogPanel."""
        if self._input_mode in (InputMode.SEARCH_FORWARD, InputMode.SEARCH_BACKWARD):
            self.log_store.clear_search()
            self._update_status()
        self.query_one(CommandInput).value = ""
        self.query_one(LogPanel).focus()
        self._input_mode = InputMode.NORMAL

    def on_input_submitted(self, event: CommandInput.Submitted) -> None:
        """Handle command submission from CommandInput."""
        raw = event.value
        event.input.value = ""

        if raw.startswith(":"):
            self._command_history.add(raw)
            cmd = raw[1:].strip()
            self._handle_command(cmd)
        elif raw.startswith("/"):
            pattern = raw[1:]
            self._do_search(
                pattern,
                SearchMode.PLAIN,
                case_sensitive=False,
                direction=SearchDirection.FORWARD,
            )
        elif raw.startswith("?"):
            pattern = raw[1:]
            self._do_search(
                pattern,
                SearchMode.PLAIN,
                case_sensitive=False,
                direction=SearchDirection.BACKWARD,
            )

        self._return_to_log_panel()

    def _handle_command(self, cmd: str) -> None:
        """Parse and execute a command string."""
        if not cmd:
            return

        try:
            parsed = parse_command(cmd)
        except ParseError as e:
            self._show_error(str(e))
            return

        name = parsed.name

        if name == "q":
            self._exit = True
            self.exit()
        elif name == "open":
            self._open_file(parsed.text)
        elif name == "f":
            self._add_filter(
                parsed.text, SearchMode.PLAIN, parsed.flags.get("cs") == ""
            )
        elif name == "fr":
            self._add_filter(
                parsed.text, SearchMode.REGEX, parsed.flags.get("cs") == ""
            )
        elif name == "fs":
            self._add_filter(
                parsed.text, SearchMode.SIMPLE, parsed.flags.get("cs") == ""
            )
        elif name == "rmf":
            self._rmf(parsed.text, parsed.flags.get("cs") == "")
        elif name == "lsf":
            self._lsf()
        elif name == "s":
            self._do_search(
                parsed.text,
                SearchMode.PLAIN,
                parsed.flags.get("cs") == "",
                SearchDirection.FORWARD,
            )
        elif name == "sr":
            self._do_search(
                parsed.text,
                SearchMode.REGEX,
                parsed.flags.get("cs") == "",
                SearchDirection.FORWARD,
            )
        elif name == "ss":
            self._do_search(
                parsed.text,
                SearchMode.SIMPLE,
                parsed.flags.get("cs") == "",
                SearchDirection.FORWARD,
            )
        elif name == "cate":
            self._cate(parsed.text)
        elif name == "catd":
            self._catd(parsed.text)
        elif name == "catea":
            self._catea()
        elif name == "catda":
            self._catda()
        elif name == "lscat":
            self._lscat()
        elif name == "h":
            color = parsed.flags.get("color", "red")
            self._h(parsed.text, SearchMode.PLAIN, parsed.flags.get("cs") == "", color)
        elif name == "hr":
            color = parsed.flags.get("color", "red")
            self._h(parsed.text, SearchMode.REGEX, parsed.flags.get("cs") == "", color)
        elif name == "hs":
            color = parsed.flags.get("color", "red")
            self._h(parsed.text, SearchMode.SIMPLE, parsed.flags.get("cs") == "", color)
        elif name == "rmh":
            self._rmh(parsed.text)
        elif name == "lsh":
            self._lsh()
        elif name == "preset":
            self._preset(parsed.text)
        elif name == "rmpreset":
            self._rmpreset(parsed.text)
        elif name == "lspreset":
            self._lspreset()
        elif name == "reload":
            self._reload()
        elif name == "theme":
            self._theme(parsed.text)

    def _do_search(
        self,
        pattern: str,
        mode: SearchMode,
        case_sensitive: bool,
        direction: SearchDirection,
    ) -> None:
        """Execute search and update display."""
        if not pattern:
            return
        self.log_store.search(
            pattern, mode, case_sensitive=case_sensitive, direction=direction
        )
        self._update_status()
        self._update_search_highlight()

    def _add_filter(self, pattern: str, mode: SearchMode, case_sensitive: bool) -> None:
        """Add a filter and refresh the display."""
        self.log_store.add_filter(
            Filter(pattern=pattern, mode=mode, case_sensitive=case_sensitive)
        )
        self.refresh_log_panel()

    def _rmf(self, pattern: str, case_sensitive: bool) -> None:
        """Remove filter(s). Empty pattern clears all."""
        if not pattern:
            self.log_store.clear_filters()
        else:
            self.log_store.remove_filter(pattern, case_sensitive=case_sensitive)
        self.refresh_log_panel()

    def _lsf(self) -> None:
        """Show filter list modal."""
        self.push_screen(FilterListScreen(self.log_store.filters))

    def _h(
        self, pattern: str, mode: SearchMode, case_sensitive: bool, color: str
    ) -> None:
        """Add a highlight and refresh."""
        self.log_store.add_highlight(
            Highlight(
                pattern=pattern, mode=mode, case_sensitive=case_sensitive, color=color
            )
        )
        self.refresh_log_panel()

    def _rmh(self, pattern: str) -> None:
        """Remove highlight(s) by pattern. Empty pattern clears all."""
        if not pattern:
            self.log_store.clear_highlights()
        else:
            # Remove ALL highlights with matching pattern (regardless of color)
            self.log_store.highlights = [
                h for h in self.log_store.highlights if h.pattern != pattern
            ]
        self.refresh_log_panel()

    def _lsh(self) -> None:
        """Show highlight list modal."""
        self.push_screen(HighlightListScreen(self.log_store.highlights))

    def _preset(self, text: str) -> None:
        """Handle :preset save <name> or :preset load <name>."""
        parts = text.strip().split(None, 1)
        if len(parts) < 2:
            return
        action, name = parts[0], parts[1]
        if action == "save":
            disabled = [
                cat
                for cat, node in self._iter_category_nodes()
                if not node.enabled
            ]
            state = {
                "filters": self.log_store.filters,
                "highlights": self.log_store.highlights,
                "disabled_categories": disabled,
            }
            self._preset_manager.save(name, state)
        elif action == "load":
            try:
                data = self._preset_manager.load(name)
            except FileNotFoundError:
                self._show_error(f"Preset not found: {name}")
                return
            self._apply_preset(data)
        self.refresh_log_panel()

    def _rmpreset(self, name: str) -> None:
        """Delete a preset by name."""
        try:
            self._preset_manager.delete(name)
        except FileNotFoundError:
            self._show_error(f"Preset not found: {name}")

    def _lspreset(self) -> None:
        """List all presets in status bar."""
        names = self._preset_manager.list_presets()
        if names:
            self._show_status_message("Presets: " + ", ".join(names))
        else:
            self._show_status_message("No presets saved")

    def _apply_preset(self, data: dict) -> None:
        """Apply loaded preset data to LogStore (skip duplicates)."""
        existing_filters = {(f.pattern, f.mode.value, f.case_sensitive) for f in self.log_store.filters}
        for fd in data.get("filters", []):
            key = (fd["pattern"], fd["mode"], fd.get("case_sensitive", False))
            if key not in existing_filters:
                self.log_store.add_filter(
                    Filter(
                        pattern=fd["pattern"],
                        mode=SearchMode(fd["mode"]),
                        case_sensitive=fd.get("case_sensitive", False),
                    )
                )

        existing_hl = {(h.pattern, h.mode.value, h.case_sensitive, h.color) for h in self.log_store.highlights}
        for hd in data.get("highlights", []):
            key = (hd["pattern"], hd["mode"], hd.get("case_sensitive", False), hd.get("color", "red"))
            if key not in existing_hl:
                self.log_store.add_highlight(
                    Highlight(
                        pattern=hd["pattern"],
                        mode=SearchMode(hd["mode"]),
                        case_sensitive=hd.get("case_sensitive", False),
                        color=hd.get("color", "red"),
                    )
                )

        for cat in data.get("disabled_categories", []):
            self.log_store.disable_category(cat)

    def _iter_category_nodes(self):
        """Iterate all category nodes in the tree."""
        def _walk(node):
            for child in node.children.values():
                yield child.full_path, child
                yield from _walk(child)

        yield from _walk(self.log_store.category_tree)

    def _show_status_message(self, msg: str) -> None:
        """Show a temporary message in the status bar."""
        status = self.query_one(StatusBar)
        status.update(msg)

    def _show_error(self, msg: str) -> None:
        """Show an error in the status bar, auto-clears after 3 seconds."""
        status = self.query_one(StatusBar)
        status.show_error(msg)

    def _reload(self) -> None:
        """Re-read current file preserving filters/highlights/categories."""
        if not self.log_store.current_file:
            self._show_error("No file loaded")
            return
        path = self.log_store.current_file
        self._open_file_worker(path)

    def _theme(self, name: str) -> None:
        """Toggle between dark and light themes."""
        if name not in ("dark", "light"):
            self._show_error("Usage: :theme dark|light")
            return
        self._config_manager.set("theme", name)
        self._config_manager.save()
        self.dark = name == "dark"
        self._update_status()

    def _cate(self, path: str) -> None:
        """Enable a category by path. Empty path enables all."""
        if not path:
            self.log_store.enable_all_categories()
        else:
            self.log_store.enable_category(path)
        self.refresh_log_panel()

    def _catd(self, path: str) -> None:
        """Disable a category by path. Empty path disables all."""
        if not path:
            self.log_store.disable_all_categories()
        else:
            self.log_store.disable_category(path)
        self.refresh_log_panel()

    def _catea(self) -> None:
        """Enable all categories."""
        self.log_store.enable_all_categories()
        self.refresh_log_panel()

    def _catda(self) -> None:
        """Disable all categories."""
        self.log_store.disable_all_categories()
        self.refresh_log_panel()

    def _lscat(self) -> None:
        """Show category list modal."""
        self.push_screen(CategoryListScreen(self.log_store))

    def _open_file(self, path: str) -> None:
        """Open and load a log file or HTTP URL via worker thread."""
        if not path:
            return
        if path.startswith("http://") or path.startswith("https://"):
            self._open_http_worker(path)
        else:
            self._open_file_worker(path)

    @work(exclusive=True, thread=True, group="file_load")
    def _open_file_worker(self, path: str) -> None:
        """Load file in background thread."""
        worker = get_current_worker()
        file_path = Path(path)
        if not file_path.exists():
            if not worker.is_cancelled:
                self.call_from_thread(self._show_error, f"File not found: {path}")
            return
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not worker.is_cancelled:
            self.call_from_thread(self._on_file_loaded, lines, path)

    def _on_file_loaded(self, lines: list[str], path: str) -> None:
        """Called from main thread after worker loads file."""
        self.log_store.load_lines(lines, file_path=path)
        self.refresh_log_panel()

    @work(exclusive=True, thread=True, group="file_load")
    def _open_http_worker(self, url: str) -> None:
        """Load a file from HTTP URL in background thread."""
        worker = get_current_worker()
        try:
            import urllib.request
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                if resp.status >= 400:
                    self.call_from_thread(
                        self._show_error,
                        f"HTTP {resp.status}: {resp.reason}",
                    )
                    return
                data = resp.read().decode("utf-8", errors="replace")
                lines = data.splitlines()
                if not worker.is_cancelled:
                    self.call_from_thread(self._on_file_loaded, lines, url)
        except urllib.error.HTTPError as e:
            if not worker.is_cancelled:
                self.call_from_thread(
                    self._show_error, f"HTTP {e.code}: {e.reason}"
                )
        except urllib.error.URLError as e:
            if not worker.is_cancelled:
                self.call_from_thread(self._show_error, f"URL error: {e.reason}")
        except Exception as e:
            if not worker.is_cancelled:
                self.call_from_thread(self._show_error, f"Load error: {e}")

    def refresh_log_panel(self) -> None:
        """Rebuild LogPanel rows and CategoryPanel from LogStore state."""
        panel = self.query_one(LogPanel)
        panel.clear()
        store = self.log_store
        highlights = store.highlights
        for idx in store.filtered_indices:
            line = store.lines[idx]
            style = line.level.row_style
            panel.add_row(
                Text(str(line.line_number), style=style),
                Text(line.time_only, style=style),
                _apply_highlights(line.category, style, highlights),
                _apply_highlights(line.message, style, highlights),
            )
        try:
            cat_panel = self.query_one(CategoryPanel)
            cat_panel.rebuild()
        except Exception:
            pass  # CategoryPanel may not be in DOM during tests
        self._update_status()
        self._update_search_highlight()

    def _update_search_highlight(self) -> None:
        """Move cursor to current search match row."""
        store = self.log_store
        if not store.search_state or not store.search_state.matches:
            return
        ss = store.search_state
        matched_line_idx = ss.matches[ss.current_index]
        # Find which row in filtered_indices corresponds to this match
        if matched_line_idx in store.filtered_indices:
            row = store.filtered_indices.index(matched_line_idx)
            panel = self.query_one(LogPanel)
            if row < panel.row_count:
                panel.move_cursor(row=row)

    def _update_status(self) -> None:
        status = self.query_one(StatusBar)
        store = self.log_store
        level_counts = {
            level.name: c for level, c in store.visible_level_counts.items()
        }
        match_info = None
        if store.search_state and store.search_state.matches:
            ss = store.search_state
            match_info = f"match {ss.current_index + 1}/{len(ss.matches)}"
        status.update_stats(
            visible=len(store.filtered_indices),
            total=len(store.lines),
            level_counts=level_counts,
            filename=store.current_file,
            match_info=match_info,
        )


def main() -> None:
    import sys

    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = LogViewerApp(file_path=file_path)
    app.run()


if __name__ == "__main__":
    main()
