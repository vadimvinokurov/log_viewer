"""Central store for parsed log data (SoA layout)."""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

from log_viewer.core.filter_engine import batch_match, match as filter_match
from log_viewer.core.models import (
    CategoryNode,
    Filter,
    Highlight,
    LogFormat,
    LogLevel,
    OFFSET_DTYPE,
    RowRef,
    SearchDirection,
    SearchMode,
    SearchState,
    _LEVEL_LIST,
)
from log_viewer.core.palette import HIGHLIGHT_PALETTE
from log_viewer.core.parser import detect_format


def _merge_sorted(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Merge two sorted uint32 arrays, removing duplicates."""
    if len(a) == 0:
        return b
    if len(b) == 0:
        return a
    merged = np.union1d(a, b)
    return merged.astype(np.uint32)


class LogStore:
    """Holds parsed log data in Structure-of-Arrays layout.

    Instead of a list of LogLine objects, data is stored in separate
    contiguous numpy arrays indexed by row position (0-based).
    """

    def __init__(self) -> None:
        # --- SoA column arrays (all length n) ---
        self.n: int = 0
        self.timestamps: np.ndarray = np.empty(0, dtype=np.uint64)
        self.category_ids: np.ndarray = np.empty(0, dtype=np.uint16)
        self.levels: np.ndarray = np.empty(0, dtype=np.uint8)
        self.messages: list[str] = []
        self.offsets: np.ndarray = np.empty(0, dtype=OFFSET_DTYPE)

        # --- Category mapping ---
        self._category_names: list[str] = []
        self._category_name_to_id: dict[str, int] = {}
        self.category_tree = CategoryNode(name="root", full_path="")
        self.category_counts: dict[str, int] = {}

        # --- Level stats ---
        self.level_counts: dict[LogLevel, int] = {}
        self.visible_level_counts: dict[LogLevel, int] = {}
        self.level_button_counts: dict[LogLevel, int] = {}

        # --- Filter state ---
        self.current_file: Optional[str] = None
        self.filtered_indices: np.ndarray = np.empty(0, dtype=np.uint32)
        self.filters: list[Filter] = []
        self.highlights: list[Highlight] = []
        self.filter_enabled: list[bool] = []
        self.highlight_enabled: list[bool] = []
        self.search_state: Optional[SearchState] = None
        self.disabled_levels: set[int] = set()  # level_ids
        self.disabled_categories: set[int] = set()  # category_ids
        self._highlight_color_index: int = 0
        self.pinned_line_numbers: set[int] = set()

    # ------------------------------------------------------------------ #
    #  Backward-compatible property: `lines`                              #
    # ------------------------------------------------------------------ #

    @property
    def lines(self) -> list[RowRef]:
        """Build list of RowRef on demand (for backward compat)."""
        return [RowRef(i, self) for i in range(self.n)]

    # ------------------------------------------------------------------ #
    #  File loading                                                       #
    # ------------------------------------------------------------------ #

    def load_lines(self, raw_lines: list[str], file_path: Optional[str] = None) -> None:
        """Parse raw lines and rebuild all indices."""
        self._close_mmap()

        n = len(raw_lines)
        self.n = n

        fmt = detect_format(raw_lines)

        # Compute byte offsets
        offsets_data: list[tuple[int, int]] = []
        offset = 0
        for raw in raw_lines:
            line_bytes = raw.encode("utf-8")
            offsets_data.append((offset, len(line_bytes)))
            offset += len(line_bytes) + 1

        # Parse into separate lists
        from log_viewer.core.parser import parse_line_soa, parse_plain_line_soa

        cat_name_to_id: dict[str, int] = {"uncategorized": 0}
        cat_names: list[str] = ["uncategorized"]

        ts_list: list[int] = [0] * n
        cat_list: list[int] = [0] * n
        lvl_list: list[int] = [3] * n  # default INFO=3
        msg_list: list[str] = [""] * n

        parse_fn = parse_plain_line_soa if fmt == LogFormat.PLAIN else parse_line_soa
        for i, raw in enumerate(raw_lines):
            ts, cat_id, lvl_id, msg = parse_fn(raw, cat_name_to_id, cat_names)
            ts_list[i] = ts
            cat_list[i] = cat_id
            lvl_list[i] = lvl_id
            msg_list[i] = msg

        # Convert to numpy, free temporary lists
        self.timestamps = np.array(ts_list, dtype=np.uint64)
        self.category_ids = np.array(cat_list, dtype=np.uint16)
        self.levels = np.array(lvl_list, dtype=np.uint8)
        self.messages = msg_list
        self.offsets = np.array(offsets_data, dtype=OFFSET_DTYPE)

        del ts_list, cat_list, lvl_list, offsets_data
        del raw_lines

        self._category_names = cat_names
        self._category_name_to_id = cat_name_to_id
        self.current_file = file_path
        self.disabled_levels = set()
        self.disabled_categories = set()

        self._build_category_tree()
        self._count_levels()
        self._apply_filters()

        # Open mmap for raw reading
        if file_path:
            from pathlib import Path

            p = Path(file_path)
            if p.exists() and p.is_file():
                self._file = open(file_path, "rb")
                self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    # ------------------------------------------------------------------ #
    #  Raw line access                                                     #
    # ------------------------------------------------------------------ #

    def _close_mmap(self) -> None:
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def get_raw(self, index: int) -> str:
        """Read raw line from mmap by index."""
        if self._mmap is None or index < 0 or index >= self.n:
            return ""
        off = self.offsets[index]
        try:
            return self._mmap[off["file_offset"]: off["file_offset"] + off["line_length"]].decode(
                "utf-8", errors="replace"
            )
        except (ValueError, IndexError):
            return ""

    # ------------------------------------------------------------------ #
    #  Filters                                                            #
    # ------------------------------------------------------------------ #

    def add_filter(self, filt: Filter) -> None:
        self.filters.append(filt)
        self.filter_enabled.append(True)
        self._apply_filters()

    def remove_filter(self, pattern: str, case_sensitive: bool = False) -> None:
        kept = [
            (f, e)
            for f, e in zip(self.filters, self.filter_enabled)
            if not (f.pattern == pattern and f.case_sensitive == case_sensitive)
        ]
        self.filters = [f for f, _ in kept]
        self.filter_enabled = [e for _, e in kept]
        self._apply_filters()

    def clear_filters(self) -> None:
        self.filters = []
        self.filter_enabled = []
        self._apply_filters()

    # ------------------------------------------------------------------ #
    #  Highlights                                                         #
    # ------------------------------------------------------------------ #

    def add_highlight(self, h: Highlight) -> None:
        h.color = HIGHLIGHT_PALETTE[self._highlight_color_index % len(HIGHLIGHT_PALETTE)]
        self._highlight_color_index += 1
        self.highlights.append(h)
        self.highlight_enabled.append(True)

    def remove_highlight(
        self, pattern: str, case_sensitive: bool = False, color: str = "red"
    ) -> None:
        kept = [
            (h, e)
            for h, e in zip(self.highlights, self.highlight_enabled)
            if not (h.pattern == pattern and h.case_sensitive == case_sensitive and h.color == color)
        ]
        self.highlights = [h for h, _ in kept]
        self.highlight_enabled = [e for _, e in kept]

    def clear_highlights(self) -> None:
        self.highlights = []
        self.highlight_enabled = []

    # ------------------------------------------------------------------ #
    #  Pinned lines                                                       #
    # ------------------------------------------------------------------ #

    def pin_line(self, line_number: int) -> None:
        self.pinned_line_numbers.add(line_number)
        self._apply_filters()

    def pin_lines(self, line_numbers: list[int]) -> None:
        self.pinned_line_numbers.update(line_numbers)
        self._apply_filters()

    def unpin_line(self, line_number: int) -> None:
        self.pinned_line_numbers.discard(line_number)
        self._apply_filters()

    def unpin_lines(self, line_numbers: list[int]) -> None:
        self.pinned_line_numbers.difference_update(line_numbers)
        self._apply_filters()

    def unpin_all(self) -> None:
        self.pinned_line_numbers.clear()
        self._apply_filters()

    # ------------------------------------------------------------------ #
    #  Search                                                             #
    # ------------------------------------------------------------------ #

    def search(
        self,
        pattern: str,
        mode: SearchMode,
        case_sensitive: bool = False,
        direction: SearchDirection = SearchDirection.FORWARD,
    ) -> SearchState:
        matches: list[int] = []
        msgs = self.messages
        # Convert to Python list for fast iteration (avoids numpy scalar overhead)
        indices = self.filtered_indices.tolist()

        if mode == SearchMode.PLAIN and not case_sensitive:
            pat_lower = pattern.lower()
            for idx in indices:
                if pat_lower in msgs[idx].lower():
                    matches.append(idx)
        else:
            filt = Filter(pattern=pattern, mode=mode, case_sensitive=case_sensitive)
            for idx in indices:
                if filter_match(msgs[idx], filt):
                    matches.append(idx)

        start = 0
        if matches and direction == SearchDirection.BACKWARD:
            start = len(matches) - 1

        state = SearchState(
            pattern=pattern,
            mode=mode,
            case_sensitive=case_sensitive,
            direction=direction,
            matches=matches,
            current_index=start,
        )
        self.search_state = state
        return state

    def next_match(self) -> Optional[SearchState]:
        if self.search_state is None or not self.search_state.matches:
            return None
        self.search_state.current_index = (
            self.search_state.current_index + 1
        ) % len(self.search_state.matches)
        return self.search_state

    def prev_match(self) -> Optional[SearchState]:
        if self.search_state is None or not self.search_state.matches:
            return None
        self.search_state.current_index = (
            self.search_state.current_index - 1
        ) % len(self.search_state.matches)
        return self.search_state

    def clear_search(self) -> None:
        self.search_state = None

    # ------------------------------------------------------------------ #
    #  Level toggles                                                      #
    # ------------------------------------------------------------------ #

    def toggle_level(self, level: LogLevel) -> None:
        level_id = _LEVEL_LIST.index(level)
        if level_id in self.disabled_levels:
            self.disabled_levels.discard(level_id)
        else:
            self.disabled_levels.add(level_id)
        self._apply_filters()

    def set_level_enabled(self, level: LogLevel, enabled: bool) -> None:
        level_id = _LEVEL_LIST.index(level)
        if enabled:
            self.disabled_levels.discard(level_id)
        else:
            self.disabled_levels.add(level_id)
        self._apply_filters()

    # ------------------------------------------------------------------ #
    #  Category toggles                                                   #
    # ------------------------------------------------------------------ #

    def enable_category(self, path: str) -> None:
        for node in self._match_categories(path):
            self._set_enabled_recursive(node, True)
        self._apply_filters()

    def disable_category(self, path: str) -> None:
        for node in self._match_categories(path):
            self._set_enabled_recursive(node, False)
        self._apply_filters()

    def enable_all_categories(self) -> None:
        self._set_enabled_recursive(self.category_tree, True)
        self.disabled_categories.clear()
        self._apply_filters()

    def disable_all_categories(self) -> None:
        self._set_enabled_recursive(self.category_tree, False)
        self._apply_filters()

    def set_disabled_categories(self, paths: list[str]) -> None:
        self._set_enabled_recursive(self.category_tree, True)
        self.disabled_categories.clear()
        for path in paths:
            node = self._find_category_node(path)
            if node:
                self._set_enabled_recursive(node, False)
        self._apply_filters()

    def _find_category_node(self, path: str) -> Optional[CategoryNode]:
        if not path:
            return self.category_tree
        parts = path.rstrip("/").split("/")
        node = self.category_tree
        for part in parts:
            if part not in node.children:
                return None
            node = node.children[part]
        return node

    def _match_categories(self, pattern: str) -> list[CategoryNode]:
        if "*" not in pattern:
            node = self._find_category_node(pattern)
            return [node] if node else []
        regex = re.compile(".*".join(re.escape(p) for p in pattern.split("*")))
        return [
            self._find_category_node(path)
            for path in self.category_counts
            if regex.search(path)
        ]

    def _set_enabled_recursive(self, node: CategoryNode, enabled: bool) -> None:
        node.enabled = enabled
        # Update disabled_categories set
        full = node.full_path
        if full:
            cat_id = self._category_name_to_id.get(full)
            if cat_id is not None:
                if enabled:
                    self.disabled_categories.discard(cat_id)
                else:
                    self.disabled_categories.add(cat_id)
        for child in node.children.values():
            self._set_enabled_recursive(child, enabled)

    # ------------------------------------------------------------------ #
    #  Filtering (core)                                                   #
    # ------------------------------------------------------------------ #

    def _apply_filters(self) -> None:
        """Recompute filtered_indices using vectorized numpy operations."""
        if self.n == 0:
            self.filtered_indices = np.empty(0, dtype=np.uint32)
            return

        has_text_filters = any(self.filter_enabled)
        has_level_filters = bool(self.disabled_levels)
        has_cat_filters = bool(self.disabled_categories)
        has_pins = bool(self.pinned_line_numbers)
        no_filters = not has_text_filters and not has_level_filters and not has_cat_filters

        # Fast path: nothing filtered, no pins
        if no_filters and not has_pins:
            self.filtered_indices = np.arange(self.n, dtype=np.uint32)
            self._count_visible_levels()
            self.level_button_counts = dict(self.level_counts)
            return

        # Build category mask: True = category enabled
        if has_cat_filters:
            enabled_cats = np.array(
                [i for i in range(len(self._category_names)) if i not in self.disabled_categories],
                dtype=np.uint16,
            )
            cat_mask = np.isin(self.category_ids, enabled_cats)
        else:
            cat_mask = np.ones(self.n, dtype=bool)

        # Build level mask: True = level enabled
        if has_level_filters:
            enabled_levels = np.array(
                [i for i in range(len(_LEVEL_LIST)) if i not in self.disabled_levels],
                dtype=np.uint8,
            )
            level_mask = np.isin(self.levels, enabled_levels)
        else:
            level_mask = np.ones(self.n, dtype=bool)

        # Category + level combined (before text filter, for level button counts)
        cat_level_mask = cat_mask & level_mask
        cat_level_indices = np.where(cat_level_mask)[0]

        # Would-be-visible: category + level + text filters
        if not has_text_filters:
            would_be_visible = cat_level_indices.astype(np.uint32)
        else:
            active_filters = [f for f, e in zip(self.filters, self.filter_enabled) if e]
            # Build message lists for batch_match
            cat_level_list = cat_level_indices.tolist()
            messages = [self.messages[i] for i in cat_level_list]
            lowered = [self.messages[i].lower() for i in cat_level_list]
            matched_positions = batch_match(messages, active_filters, pre_lowered=lowered)
            would_be_visible = cat_level_indices[np.array(sorted(matched_positions), dtype=np.intp)].astype(np.uint32)

        # Count per level for buttons (category + text filtering, ignoring level toggles)
        if has_text_filters:
            self._count_level_buttons_from_indices(would_be_visible)
        else:
            self._count_level_buttons_from_mask(cat_mask)

        # Result (with level filter already applied since cat_level_mask includes it)
        result = would_be_visible

        # Merge pinned lines
        if has_pins:
            pinned_indices = np.array(
                sorted(n - 1 for n in self.pinned_line_numbers if 0 <= n - 1 < self.n),
                dtype=np.uint32,
            )
            result = _merge_sorted(result, pinned_indices)

        self.filtered_indices = result
        self._count_visible_levels()

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

    def _count_level_buttons_from_mask(self, cat_mask: np.ndarray) -> None:
        """Count per level for category-enabled lines (used by level buttons)."""
        cat_indices = np.where(cat_mask)[0]
        if len(cat_indices) == 0:
            self.level_button_counts = {}
            return
        cat_levels = self.levels[cat_indices]
        counts = np.bincount(cat_levels, minlength=len(_LEVEL_LIST))
        self.level_button_counts = {
            _LEVEL_LIST[i]: int(counts[i]) for i in range(len(_LEVEL_LIST)) if counts[i] > 0
        }

    def _count_level_buttons_from_indices(self, indices: np.ndarray) -> None:
        """Count per level for given indices (category + text filtered, used by level buttons)."""
        if len(indices) == 0:
            self.level_button_counts = {}
            return
        idx_levels = self.levels[indices]
        counts = np.bincount(idx_levels, minlength=len(_LEVEL_LIST))
        self.level_button_counts = {
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
