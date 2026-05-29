"""Central store for parsed log data (SoA layout with byte buffer)."""

from __future__ import annotations

from typing import Optional

import numpy as np

from log_viewer.core.filter_pipeline import FilterPipeline
from log_viewer.core.models import (
    CategoryNode,
    Filter,
    Highlight,
    LogLevel,
    RowRef,
    SearchDirection,
    SearchMode,
    SearchState,
    _LEVEL_LIST,
)
from log_viewer.core.search_engine import SearchEngine

# dtype for message spans: offset into _buf and length
SPAN_DTYPE = np.dtype([("offset", np.uint64), ("length", np.uint32)])



class LogStore:
    """Holds parsed log data in Structure-of-Arrays layout.

    Data is stored in a single byte buffer (_buf) with numpy arrays
    of indices for compact, cache-friendly access.
    """

    def __init__(self) -> None:
        # --- Byte buffer ---
        self._buf: bytearray = bytearray()
        self._buf_lower: Optional[bytes] = None  # cached lowered buffer

        # --- SoA column arrays (all length n) ---
        self.n: int = 0
        self.category_ids: np.ndarray = np.empty(0, dtype=np.uint16)
        self.levels: np.ndarray = np.empty(0, dtype=np.uint8)

        # --- Line boundaries (length n+1, last = len(_buf)) ---
        self.line_starts: np.ndarray = np.empty(0, dtype=np.uint64)

        # --- Detected format ---
        self._format: str = "ksiva"

        # --- Category mapping ---
        self._category_names: list[str] = []
        self._category_name_to_id: dict[str, int] = {}
        self.category_tree = CategoryNode(name="root", full_path="")
        self.category_counts: dict[str, int] = {}

        # --- Level stats ---
        self.level_counts: dict[LogLevel, int] = {}
        self.visible_level_counts: dict[LogLevel, int] = {}
        self.level_button_counts: dict[LogLevel, int] = {}

        # --- Filter state (delegated to pipeline) ---
        self.current_file: Optional[str] = None
        self.filtered_indices: np.ndarray = np.empty(0, dtype=np.uint32)
        self.pipeline = FilterPipeline()
        self.search_engine = SearchEngine()

    # ------------------------------------------------------------------ #
    #  Pipeline delegation properties                                      #
    # ------------------------------------------------------------------ #

    @property
    def filters(self) -> list[Filter]:
        return self.pipeline.filters

    @filters.setter
    def filters(self, value: list[Filter]) -> None:
        self.pipeline.filters = value

    @property
    def filter_enabled(self) -> list[bool]:
        return self.pipeline.filter_enabled

    @filter_enabled.setter
    def filter_enabled(self, value: list[bool]) -> None:
        self.pipeline.filter_enabled = value

    @property
    def highlights(self) -> list[Highlight]:
        return self.pipeline.highlights

    @highlights.setter
    def highlights(self, value: list[Highlight]) -> None:
        self.pipeline.highlights = value

    @property
    def highlight_enabled(self) -> list[bool]:
        return self.pipeline.highlight_enabled

    @highlight_enabled.setter
    def highlight_enabled(self, value: list[bool]) -> None:
        self.pipeline.highlight_enabled = value

    @property
    def disabled_levels(self) -> set[int]:
        return self.pipeline.disabled_levels

    @disabled_levels.setter
    def disabled_levels(self, value: set[int]) -> None:
        self.pipeline.disabled_levels = value

    @property
    def disabled_categories(self) -> set[int]:
        return self.pipeline.disabled_categories

    @disabled_categories.setter
    def disabled_categories(self, value: set[int]) -> None:
        self.pipeline.disabled_categories = value

    @property
    def _filter_masks(self) -> list[np.ndarray]:
        return self.pipeline._filter_masks

    @_filter_masks.setter
    def _filter_masks(self, value: list[np.ndarray]) -> None:
        self.pipeline._filter_masks = value

    @property
    def _highlight_color_index(self) -> int:
        return self.pipeline._highlight_color_index

    @_highlight_color_index.setter
    def _highlight_color_index(self, value: int) -> None:
        self.pipeline._highlight_color_index = value

    @property
    def pinned_rules(self) -> list[Filter]:
        return self.pipeline.pinned_rules

    @pinned_rules.setter
    def pinned_rules(self, value: list[Filter]) -> None:
        self.pipeline.pinned_rules = value

    @property
    def pinned_enabled(self) -> list[bool]:
        return self.pipeline.pinned_enabled

    @pinned_enabled.setter
    def pinned_enabled(self, value: list[bool]) -> None:
        self.pipeline.pinned_enabled = value

    @property
    def _pin_masks(self) -> list[np.ndarray]:
        return self.pipeline._pin_masks

    @_pin_masks.setter
    def _pin_masks(self, value: list[np.ndarray]) -> None:
        self.pipeline._pin_masks = value

    @property
    def search_state(self):
        return self.search_engine.search_state

    # ------------------------------------------------------------------ #
    #  Backward-compatible properties                                      #
    # ------------------------------------------------------------------ #

    @property
    def lines(self) -> list[RowRef]:
        """Build list of RowRef on demand (for backward compat)."""
        return [RowRef(i, self) for i in range(self.n)]

    @property
    def messages(self) -> list[str]:
        """Decode all messages on demand (for backward compat)."""
        return [self.get_message(i) for i in range(self.n)]

    @messages.setter
    def messages(self, value: list[str]) -> None:
        """No-op setter for backward compat (load_bytes handles data)."""
        pass

    @property
    def offsets(self) -> np.ndarray:
        """Compute offsets from line_starts for backward compat."""
        if self.n == 0:
            return np.empty(0, dtype=np.dtype([("file_offset", np.uint64), ("line_length", np.uint32)]))
        dt = np.dtype([("file_offset", np.uint64), ("line_length", np.uint32)])
        result = np.empty(self.n, dtype=dt)
        for i in range(self.n):
            result[i]["file_offset"] = self.line_starts[i]
            result[i]["line_length"] = self.line_starts[i + 1] - self.line_starts[i]
        return result

    @offsets.setter
    def offsets(self, value: np.ndarray) -> None:
        """No-op setter for backward compat."""
        pass

    # ------------------------------------------------------------------ #
    #  File loading                                                        #
    # ------------------------------------------------------------------ #

    def load_bytes(self, buf: bytearray, file_path: Optional[str] = None) -> None:
        """Parse a byte buffer and rebuild all indices."""
        from log_viewer.core.parser import (
            _HAS_CYTHON,
            detect_format_bytes,
            parse_batch_fast,
            parse_minimal_batch,
            scan_line_starts_fast,
        )

        self._buf = buf
        self._buf_lower = None  # lazy, created on first filter/search

        # Pass 1: scan line boundaries
        line_starts = scan_line_starts_fast(buf)
        n = len(line_starts) - 1
        self.n = n

        if n == 0:
            self.category_ids = np.empty(0, dtype=np.uint16)
            self.levels = np.empty(0, dtype=np.uint8)
            self.line_starts = line_starts
            self._finalize_load(file_path)
            return

        self.line_starts = line_starts

        # Detect format
        fmt = detect_format_bytes(bytes(buf))
        self._format = fmt

        # Pass 2: parse category_ids and levels
        # Use Cython-accelerated parse_batch_fast when available (much faster
        # for large files). It returns extra arrays we discard immediately.
        if _HAS_CYTHON:
            _ts, cat_names, cat_name_to_id, cat_ids, levels, _msg = parse_batch_fast(
                buf, line_starts, fmt
            )
        else:
            cat_names, cat_name_to_id, cat_ids, levels = parse_minimal_batch(
                bytes(buf), line_starts, fmt
            )

        self.category_ids = cat_ids
        self.levels = levels
        self._category_names = cat_names
        self._category_name_to_id = cat_name_to_id

        self._finalize_load(file_path)

    def load_lines(self, raw_lines: list[str], file_path: Optional[str] = None) -> None:
        """Parse raw string lines and rebuild all indices (backward compat)."""
        # Convert strings to a single bytearray
        buf = bytearray("\n".join(raw_lines).encode("utf-8"))
        self.load_bytes(buf, file_path=file_path)

    def _finalize_load(self, file_path: Optional[str]) -> None:
        """Common post-load logic: restore state, build tree, apply filters."""
        # Snapshot disabled category paths from tree (includes intermediate nodes)
        disabled_cat_names: set[str] = set()
        self.pipeline.collect_disabled_paths(self.category_tree, disabled_cat_names)

        self.current_file = file_path
        # disabled_levels intentionally not reset — preserved across reload
        self.disabled_categories = set()
        self.pipeline.reset_pins()
        self.search_engine.clear_search()
        self.pipeline.invalidate_cache()

        # Restore disabled categories by name (new IDs)
        for name in disabled_cat_names:
            if name in self._category_name_to_id:
                self.disabled_categories.add(self._category_name_to_id[name])

        self._build_category_tree()

        # Sync tree node.enabled flags with restored disabled set.
        for name in disabled_cat_names:
            node = self.pipeline.find_category_node(self, name)
            if node:
                node.enabled = False

        self._count_levels()
        self.pipeline.recompute_masks(self)
        self.pipeline.apply(self)

    # ------------------------------------------------------------------ #
    #  Message / raw line access                                           #
    # ------------------------------------------------------------------ #

    def get_columns(self, index: int) -> tuple[str, str, str, str]:
        """Return (timestamp, category, level_name, message) for one line."""
        if index < 0 or index >= self.n:
            return ("", "", "", "")
        raw = self._buf[self.line_starts[index]:self.line_starts[index + 1]]
        from log_viewer.core.parser import parse_columns
        return parse_columns(raw, self._category_names, self._format)

    def get_message(self, index: int) -> str:
        """Decode message text on demand."""
        return self.get_columns(index)[3]

    def get_timestamp(self, index: int) -> str:
        """Decode timestamp on demand."""
        return self.get_columns(index)[0]

    def get_raw(self, index: int) -> str:
        """Return raw line text from byte buffer."""
        if index < 0 or index >= self.n:
            return ""
        start = int(self.line_starts[index])
        end = int(self.line_starts[index + 1])
        return self._buf[start:end].decode("utf-8", errors="replace").rstrip("\n\r")

    # ------------------------------------------------------------------ #
    #  Filters                                                            #
    # ------------------------------------------------------------------ #

    def add_filter(self, filt: Filter) -> None:
        self.pipeline.add_filter(self, filt)

    def remove_filter(self, pattern: str) -> None:
        self.pipeline.remove_filter(self, pattern)

    def clear_filters(self) -> None:
        self.pipeline.clear_filters(self)

    # ------------------------------------------------------------------ #
    #  Highlights                                                         #
    # ------------------------------------------------------------------ #

    def add_highlight(self, h: Highlight) -> None:
        self.pipeline.add_highlight(h)

    def remove_highlight(
        self, pattern: str, color: str = "red"
    ) -> None:
        self.pipeline.remove_highlight(pattern, color)

    def clear_highlights(self) -> None:
        self.pipeline.clear_highlights()

    # ------------------------------------------------------------------ #
    #  Pinned lines                                                       #
    # ------------------------------------------------------------------ #

    def add_pin(self, filt: Filter) -> None:
        self.pipeline.add_pin(self, filt)

    def remove_pin(self, index: int) -> None:
        self.pipeline.remove_pin(self, index)

    def unpin_all(self) -> None:
        self.pipeline.unpin_all(self)

    # ------------------------------------------------------------------ #
    #  Search                                                             #
    # ------------------------------------------------------------------ #

    def search(
        self,
        pattern: str,
        mode: SearchMode,
        direction: SearchDirection = SearchDirection.FORWARD,
        start_line: int = 0,
    ) -> SearchState:
        return self.search_engine.search(self, self.pipeline, pattern, mode, direction, start_line)

    def next_match(self) -> Optional[SearchState]:
        return self.search_engine.next_match()

    def prev_match(self) -> Optional[SearchState]:
        return self.search_engine.prev_match()

    def clear_search(self) -> None:
        self.search_engine.clear_search()

    # ------------------------------------------------------------------ #
    #  Level toggles                                                      #
    # ------------------------------------------------------------------ #

    def toggle_level(self, level: LogLevel) -> None:
        self.pipeline.toggle_level(self, level)

    def set_level_enabled(self, level: LogLevel, enabled: bool) -> None:
        self.pipeline.set_level_enabled(self, level, enabled)

    # ------------------------------------------------------------------ #
    #  Category toggles                                                   #
    # ------------------------------------------------------------------ #

    def enable_category(self, path: str) -> None:
        self.pipeline.enable_category(self, path)

    def disable_category(self, path: str) -> None:
        self.pipeline.disable_category(self, path)

    def enable_all_categories(self) -> None:
        self.pipeline.enable_all_categories(self)

    def disable_all_categories(self) -> None:
        self.pipeline.disable_all_categories(self)

    def set_disabled_categories(self, paths: list[str]) -> None:
        self.pipeline.set_disabled_categories(self, paths)

    def _apply_filters(self) -> None:
        """Delegate to pipeline for backward compat (GUI calls this directly)."""
        self.pipeline.apply(self)

    def _find_category_node(self, path: str) -> Optional[CategoryNode]:
        """Delegate to pipeline for backward compat."""
        return self.pipeline.find_category_node(self, path)

    # ------------------------------------------------------------------ #
    #  Level counting                                                     #
    # ------------------------------------------------------------------ #

    def _count_levels(self) -> None:
        """Count log levels across all lines using vectorized bincount."""
        if self.n == 0:
            self.level_counts = {}
            self.visible_level_counts = {}
            self.level_button_counts = {}
            return
        counts = np.bincount(self.levels, minlength=len(_LEVEL_LIST))
        self.level_counts = {
            _LEVEL_LIST[i]: int(counts[i]) for i in range(len(_LEVEL_LIST)) if counts[i] > 0
        }
        self.visible_level_counts = dict(self.level_counts)
        self.level_button_counts = dict(self.level_counts)

    def _count_visible_levels(self) -> None:
        """Count log levels for currently visible lines."""
        if len(self.filtered_indices) == 0:
            self.visible_level_counts = {}
            return
        visible_levels = self.levels[self.filtered_indices]
        counts = np.bincount(visible_levels, minlength=len(_LEVEL_LIST))
        self.visible_level_counts = {
            _LEVEL_LIST[i]: int(counts[i]) for i in range(len(_LEVEL_LIST)) if counts[i] > 0
        }

    # ------------------------------------------------------------------ #
    #  Category tree                                                      #
    # ------------------------------------------------------------------ #

    def _build_category_tree(self) -> None:
        """Build category tree and counts from numpy arrays."""
        self.category_tree = CategoryNode(name="root", full_path="")
        self.category_counts = {}

        # Use np.unique for fast category counting
        unique_ids, counts = np.unique(self.category_ids, return_counts=True)
        for cat_id, count in zip(unique_ids, counts):
            cat_name = self._category_names[int(cat_id)]
            self.category_counts[cat_name] = int(count)

            # Insert into tree
            parts = cat_name.split("/")
            node = self.category_tree
            built: list[str] = []
            for part in parts:
                built.append(part)
                full = "/".join(built)
                if part not in node.children:
                    node.children[part] = CategoryNode(name=part, full_path=full)
                node = node.children[part]
                node.line_count += int(count)
