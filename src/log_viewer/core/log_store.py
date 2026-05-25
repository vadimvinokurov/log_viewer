"""Central store for parsed log data (SoA layout with byte buffer)."""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

from log_viewer.core import filter_engine
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
from log_viewer.core.palette import HIGHLIGHT_PALETTE

# dtype for message spans: offset into _buf and length
SPAN_DTYPE = np.dtype([("offset", np.uint64), ("length", np.uint32)])


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

    Data is stored in a single byte buffer (_buf) with numpy arrays
    of indices for compact, cache-friendly access.
    """

    def __init__(self) -> None:
        # --- Byte buffer ---
        self._buf: bytearray = bytearray()

        # --- SoA column arrays (all length n) ---
        self.n: int = 0
        self.timestamps: np.ndarray = np.empty(0, dtype=np.uint64)
        self.timestamp_spans: np.ndarray = np.empty(0, dtype=SPAN_DTYPE)
        self.category_ids: np.ndarray = np.empty(0, dtype=np.uint16)
        self.levels: np.ndarray = np.empty(0, dtype=np.uint8)
        self.message_spans: np.ndarray = np.empty(0, dtype=SPAN_DTYPE)

        # --- Line boundaries (length n+1, last = len(_buf)) ---
        self.line_starts: np.ndarray = np.empty(0, dtype=np.uint64)

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
        self._filter_masks: list[np.ndarray] = []  # one bool mask per filter

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
            detect_format_bytes,
            parse_batch_fast,
            scan_line_starts_fast,
        )

        self._buf = buf

        # Scan line boundaries using numpy (SIMD)
        line_starts = scan_line_starts_fast(buf)
        n = len(line_starts) - 1
        self.n = n

        if n == 0:
            self.timestamps = np.empty(0, dtype=np.uint64)
            self.timestamp_spans = np.empty(0, dtype=SPAN_DTYPE)
            self.category_ids = np.empty(0, dtype=np.uint16)
            self.levels = np.empty(0, dtype=np.uint8)
            self.message_spans = np.empty(0, dtype=SPAN_DTYPE)
            self.line_starts = line_starts
            self._finalize_load(file_path)
            return

        self.line_starts = line_starts

        # Detect format
        fmt = detect_format_bytes(bytes(buf))

        # Batch parse
        ts_spans, cat_names, cat_name_to_id, cat_ids, levels, msg_spans = parse_batch_fast(
            buf, line_starts, fmt
        )

        self.timestamp_spans = ts_spans
        self.timestamps = np.empty(0, dtype=np.uint64)  # legacy, unused in fast path
        self.category_ids = cat_ids
        self.levels = levels
        self.message_spans = msg_spans
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
        self._collect_disabled_paths(self.category_tree, disabled_cat_names)

        self.current_file = file_path
        # disabled_levels intentionally not reset — preserved across reload
        self.disabled_categories = set()
        self.pinned_line_numbers = set()
        self.search_state = None

        # Restore disabled categories by name (new IDs)
        for name in disabled_cat_names:
            if name in self._category_name_to_id:
                self.disabled_categories.add(self._category_name_to_id[name])

        self._build_category_tree()

        # Sync tree node.enabled flags with restored disabled set.
        for name in disabled_cat_names:
            node = self._find_category_node(name)
            if node:
                node.enabled = False

        self._count_levels()
        self._recompute_all_filter_masks()
        self._apply_filters()

    # ------------------------------------------------------------------ #
    #  Message / raw line access                                           #
    # ------------------------------------------------------------------ #

    def get_message(self, index: int) -> str:
        """Decode message text on demand from byte buffer."""
        if index < 0 or index >= self.n:
            return ""
        off = int(self.message_spans[index]["offset"])
        ln = int(self.message_spans[index]["length"])
        return self._buf[off:off + ln].decode("utf-8", errors="replace")

    def get_message_bytes(self, index: int) -> bytes:
        """Return message as bytes (zero-copy view)."""
        if index < 0 or index >= self.n:
            return b""
        off = int(self.message_spans[index]["offset"])
        ln = int(self.message_spans[index]["length"])
        return bytes(self._buf[off:off + ln])

    def get_timestamp(self, index: int) -> str:
        """Decode timestamp on demand from byte buffer or legacy uint64 array."""
        if index < 0 or index >= self.n:
            return ""
        # Fast path: byte spans from parse_batch_fast
        if len(self.timestamp_spans) > 0:
            off = int(self.timestamp_spans[index]["offset"])
            ln = int(self.timestamp_spans[index]["length"])
            if ln == 0:
                return ""
            raw = self._buf[off:off + ln].decode("utf-8", errors="replace")
            return raw.split("T")[-1] if "T" in raw else raw
        # Legacy path: pre-parsed uint64 milliseconds
        if len(self.timestamps) > 0:
            from log_viewer.core.models import format_timestamp
            return format_timestamp(int(self.timestamps[index]))
        return ""

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
        self.filters.append(filt)
        self.filter_enabled.append(True)
        self._filter_masks.append(self._compute_filter_mask(filt))
        self._apply_filters()

    def remove_filter(self, pattern: str, case_sensitive: bool = False) -> None:
        kept = [
            (i, f, e)
            for i, (f, e) in enumerate(zip(self.filters, self.filter_enabled))
            if not (f.pattern == pattern and f.case_sensitive == case_sensitive)
        ]
        self.filters = [f for _, f, _ in kept]
        self.filter_enabled = [e for _, _, e in kept]
        self._filter_masks = [self._filter_masks[i] for i, _, _ in kept]
        self._apply_filters()

    def clear_filters(self) -> None:
        self.filters = []
        self.filter_enabled = []
        self._filter_masks = []
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
        buf = self._buf
        spans = self.message_spans
        indices = self.filtered_indices.tolist()

        if mode == SearchMode.PLAIN and not case_sensitive:
            pat_lower = pattern.lower().encode("utf-8")
            for idx in indices:
                off = int(spans[idx]["offset"])
                ln = int(spans[idx]["length"])
                msg = bytes(buf[off:off + ln])
                if pat_lower in msg.lower():
                    matches.append(idx)
        elif mode == SearchMode.PLAIN and case_sensitive:
            pat_bytes = pattern.encode("utf-8")
            for idx in indices:
                off = int(spans[idx]["offset"])
                ln = int(spans[idx]["length"])
                msg = bytes(buf[off:off + ln])
                if pat_bytes in msg:
                    matches.append(idx)
        else:
            # Regex and simple query: use filter engine on bytes
            filt = Filter(pattern=pattern, mode=mode, case_sensitive=case_sensitive)
            for idx in indices:
                off = int(spans[idx]["offset"])
                ln = int(spans[idx]["length"])
                msg = bytes(buf[off:off + ln])
                if filter_engine.match_bytes(msg, filt):
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

    def _collect_disabled_paths(
        self, node: CategoryNode, out: set[str]
    ) -> None:
        if not node.enabled and node.full_path:
            out.add(node.full_path)
        for child in node.children.values():
            self._collect_disabled_paths(child, out)

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

    def _compute_filter_mask(self, filt: Filter) -> np.ndarray:
        """Compute boolean mask for ALL lines matching a single filter."""
        n = self.n
        if n == 0:
            return np.empty(0, dtype=bool)

        mask = np.zeros(n, dtype=bool)

        if filt.mode == SearchMode.PLAIN and not filt.case_sensitive:
            # Buffer-wide regex scan
            combined = re.compile(re.escape(filt.pattern).encode("utf-8"), re.IGNORECASE)
            msg_off = self.message_spans["offset"].astype(np.int64)
            msg_len = self.message_spans["length"].astype(np.int64)
            positions = np.array(
                [m.start() for m in combined.finditer(self._buf)], dtype=np.int64
            )
            if len(positions) > 0:
                si = np.searchsorted(msg_off, positions, side="right") - 1
                valid = (si >= 0) & (si < n)
                si, pv = si[valid], positions[valid]
                ends = msg_off[si] + msg_len[si]
                in_msg = (pv >= msg_off[si]) & (pv < ends)
                mask[si[in_msg]] = True
        else:
            # Per-line decode + match
            buf = self._buf
            spans = self.message_spans
            for idx in range(n):
                off = int(spans[idx]["offset"])
                ln = int(spans[idx]["length"])
                msg = buf[off:off + ln].decode("utf-8", errors="replace")
                if filter_engine.match(msg, filt):
                    mask[idx] = True

        return mask

    def _recompute_all_filter_masks(self) -> None:
        """Rebuild all filter masks (called after file load)."""
        self._filter_masks = [self._compute_filter_mask(f) for f in self.filters]

    def _apply_filters(self) -> None:
        """Recompute filtered_indices using vectorized numpy + byte matching."""
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
            # Rebuild masks if out of sync (e.g. filters set directly)
            if len(self._filter_masks) != len(self.filters):
                self._recompute_all_filter_masks()
            # Combine active filter masks with OR logic
            active_masks = [m for m, e in zip(self._filter_masks, self.filter_enabled) if e]
            if active_masks:
                text_mask = np.zeros(self.n, dtype=bool)
                for m in active_masks:
                    text_mask |= m
                combined = cat_level_mask & text_mask
            else:
                combined = cat_level_mask
            would_be_visible = np.where(combined)[0].astype(np.uint32)

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

    def _bulk_match(
        self, indices: list[int], filters: list[Filter]
    ) -> set[int]:
        """Bulk regex on entire buffer for plain-CI filters, per-line fallback for others."""
        if not indices or not filters:
            return set(range(len(indices))) if not filters else set()

        plain_ci: list[bytes] = []
        other_filters: list[Filter] = []
        for f in filters:
            if f.mode == SearchMode.PLAIN and not f.case_sensitive:
                plain_ci.append(re.escape(f.pattern).encode("utf-8"))
            else:
                other_filters.append(f)

        matching_lines: set[int] = set()

        if plain_ci:
            combined = re.compile(b"|".join(plain_ci), re.IGNORECASE)
            msg_off = self.message_spans["offset"].astype(np.int64)
            msg_len = self.message_spans["length"].astype(np.int64)

            positions = np.array(
                [m.start() for m in combined.finditer(self._buf)], dtype=np.int64
            )
            if len(positions) > 0:
                si = np.searchsorted(msg_off, positions, side="right") - 1
                valid = (si >= 0) & (si < self.n)
                si, pv = si[valid], positions[valid]
                ends = msg_off[si] + msg_len[si]
                in_msg = (pv >= msg_off[si]) & (pv < ends)
                matching_lines = set(si[in_msg].tolist())

        if other_filters:
            buf = self._buf
            spans = self.message_spans
            for idx in indices:
                if idx in matching_lines:
                    continue
                off = int(spans[idx]["offset"])
                ln = int(spans[idx]["length"])
                msg = buf[off:off + ln].decode("utf-8", errors="replace")
                for f in other_filters:
                    if filter_engine.match(msg, f):
                        matching_lines.add(idx)
                        break

        return {i for i, idx in enumerate(indices) if idx in matching_lines}

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
