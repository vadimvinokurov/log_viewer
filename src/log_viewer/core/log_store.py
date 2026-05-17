"""Central store for parsed log data."""

from __future__ import annotations

import mmap
import re
from collections import defaultdict
from typing import IO, Optional

from log_viewer.core.filter_engine import batch_match, match as filter_match
from log_viewer.core.models import (
    CategoryNode,
    Filter,
    Highlight,
    LogFormat,
    LogLevel,
    LogLine,
    SearchDirection,
    SearchMode,
    SearchState,
)
from log_viewer.core.palette import HIGHLIGHT_PALETTE
from log_viewer.core.parser import detect_format


def _merge_sorted(a: list[int], b: list[int]) -> list[int]:
    """Merge two sorted lists, removing duplicates."""
    result: list[int] = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] < b[j]:
            result.append(a[i])
            i += 1
        elif a[i] > b[j]:
            result.append(b[j])
            j += 1
        else:
            result.append(a[i])
            i += 1
            j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result


class LogStore:
    """Holds parsed log lines, category tree, and computed stats."""

    def __init__(self) -> None:
        self.lines: list[LogLine] = []
        self.category_tree = CategoryNode(name="root", full_path="")
        self.category_counts: dict[str, int] = {}
        self.level_counts: dict[LogLevel, int] = {}
        self.current_file: Optional[str] = None
        self.filtered_indices: list[int] = []
        self.visible_level_counts: dict[LogLevel, int] = {}
        self.level_button_counts: dict[LogLevel, int] = {}
        self.filters: list[Filter] = []
        self.highlights: list[Highlight] = []
        self.filter_enabled: list[bool] = []
        self.highlight_enabled: list[bool] = []
        self.search_state: Optional[SearchState] = None
        self.disabled_levels: set[LogLevel] = set()
        self._highlight_color_index: int = 0
        self.pinned_line_numbers: set[int] = set()
        self._file: Optional[IO] = None
        self._mmap: Optional[mmap.mmap] = None
        self._category_index: dict[str, set[int]] = {}
        self._category_enabled_cache: dict[str, bool] = {}
        self._category_visible_set: set[int] = set()

    def load_lines(self, raw_lines: list[str], file_path: Optional[str] = None) -> None:
        """Parse raw lines and rebuild all indices."""
        self._close_mmap()

        fmt = detect_format(raw_lines)

        # Compute byte offsets by encoding each line to UTF-8
        offsets: list[tuple[int, int]] = []
        offset = 0
        for raw in raw_lines:
            line_bytes = raw.encode("utf-8")
            offsets.append((offset, len(line_bytes)))
            offset += len(line_bytes) + 1  # +1 for newline

        from log_viewer.core.parser import parse_lines_batch
        self.lines = parse_lines_batch(raw_lines, offsets, plain=(fmt == LogFormat.PLAIN))

        self.current_file = file_path
        self._build_category_tree()
        self.disabled_levels = set()
        self._count_levels()
        self._apply_filters()

        # Open mmap for raw reading if file exists
        if file_path:
            from pathlib import Path
            p = Path(file_path)
            if p.exists() and p.is_file():
                self._file = open(file_path, "rb")
                self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    def _close_mmap(self) -> None:
        """Close mmap and file handle if open."""
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def get_raw(self, index: int) -> str:
        """Read raw line from mmap by index. Returns empty string if unavailable."""
        if self._mmap is None or index < 0 or index >= len(self.lines):
            return ""
        line = self.lines[index]
        try:
            return self._mmap[line.file_offset:line.file_offset + line.line_length].decode("utf-8", errors="replace")
        except (ValueError, IndexError):
            return ""

    def add_filter(self, filt: Filter) -> None:
        """Add a filter and recompute visible indices."""
        self.filters.append(filt)
        self.filter_enabled.append(True)
        self._apply_filters()

    def remove_filter(self, pattern: str, case_sensitive: bool = False) -> None:
        """Remove filter by exact pattern + case_sensitive match."""
        kept = [(f, e) for f, e in zip(self.filters, self.filter_enabled)
                if not (f.pattern == pattern and f.case_sensitive == case_sensitive)]
        self.filters = [f for f, _ in kept]
        self.filter_enabled = [e for _, e in kept]
        self._apply_filters()

    def clear_filters(self) -> None:
        """Remove all filters."""
        self.filters = []
        self.filter_enabled = []
        self._apply_filters()

    def add_highlight(self, h: Highlight) -> None:
        """Add a highlight (display-only, no filtering)."""
        h.color = HIGHLIGHT_PALETTE[self._highlight_color_index % len(HIGHLIGHT_PALETTE)]
        self._highlight_color_index += 1
        self.highlights.append(h)
        self.highlight_enabled.append(True)

    def remove_highlight(self, pattern: str, case_sensitive: bool = False, color: str = "red") -> None:
        """Remove highlight by exact match."""
        kept = [(h, e) for h, e in zip(self.highlights, self.highlight_enabled)
                if not (h.pattern == pattern and h.case_sensitive == case_sensitive and h.color == color)]
        self.highlights = [h for h, _ in kept]
        self.highlight_enabled = [e for _, e in kept]

    def clear_highlights(self) -> None:
        """Remove all highlights."""
        self.highlights = []
        self.highlight_enabled = []

    def pin_line(self, line_number: int) -> None:
        """Pin a line so it's always visible regardless of filters."""
        self.pinned_line_numbers.add(line_number)
        self._apply_filters()

    def pin_lines(self, line_numbers: list[int]) -> None:
        """Pin multiple lines at once."""
        self.pinned_line_numbers.update(line_numbers)
        self._apply_filters()

    def unpin_line(self, line_number: int) -> None:
        """Unpin a specific line."""
        self.pinned_line_numbers.discard(line_number)
        self._apply_filters()

    def unpin_lines(self, line_numbers: list[int]) -> None:
        """Unpin multiple lines at once."""
        self.pinned_line_numbers.difference_update(line_numbers)
        self._apply_filters()

    def unpin_all(self) -> None:
        """Unpin all lines."""
        self.pinned_line_numbers.clear()
        self._apply_filters()

    def search(
        self,
        pattern: str,
        mode: SearchMode,
        case_sensitive: bool = False,
        direction: SearchDirection = SearchDirection.FORWARD,
    ) -> SearchState:
        """Search within the filtered view and return a SearchState."""
        matches: list[int] = []

        # Fast path: plain case-insensitive — use pre-lowered message
        if mode == SearchMode.PLAIN and not case_sensitive:
            pat_lower = pattern.lower()
            for idx in self.filtered_indices:
                if pat_lower in self.lines[idx].message_lower:
                    matches.append(idx)
        else:
            filt = Filter(pattern=pattern, mode=mode, case_sensitive=case_sensitive)
            for idx in self.filtered_indices:
                if filter_match(self.lines[idx].message, filt):
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
        """Advance to next match (wraps around). Returns None if no search active."""
        if self.search_state is None or not self.search_state.matches:
            return None
        idx = (self.search_state.current_index + 1) % len(self.search_state.matches)
        self.search_state.current_index = idx
        return self.search_state

    def prev_match(self) -> Optional[SearchState]:
        """Go to previous match (wraps around). Returns None if no search active."""
        if self.search_state is None or not self.search_state.matches:
            return None
        idx = (self.search_state.current_index - 1) % len(self.search_state.matches)
        self.search_state.current_index = idx
        return self.search_state

    def clear_search(self) -> None:
        """Clear active search state."""
        self.search_state = None

    def toggle_level(self, level: LogLevel) -> None:
        """Toggle a log level on/off and recompute filtered indices."""
        if level in self.disabled_levels:
            self.disabled_levels.discard(level)
        else:
            self.disabled_levels.add(level)
        self._apply_filters()

    def set_level_enabled(self, level: LogLevel, enabled: bool) -> None:
        """Enable or disable a log level."""
        if enabled:
            self.disabled_levels.discard(level)
        else:
            self.disabled_levels.add(level)
        self._apply_filters()

    def enable_category(self, path: str) -> None:
        """Enable a category and all its children. Supports * wildcards."""
        for node in self._match_categories(path):
            node.enabled = True
            self._set_enabled_recursive(node, True)
        self._rebuild_category_cache()
        self._apply_filters()

    def disable_category(self, path: str) -> None:
        """Disable a category and all its children. Supports * wildcards."""
        for node in self._match_categories(path):
            node.enabled = False
            self._set_enabled_recursive(node, False)
        self._rebuild_category_cache()
        self._apply_filters()

    def enable_all_categories(self) -> None:
        """Enable all categories in the tree."""
        self._set_enabled_recursive(self.category_tree, True)
        self._rebuild_category_cache()
        self._apply_filters()

    def disable_all_categories(self) -> None:
        """Disable all categories in the tree."""
        self._set_enabled_recursive(self.category_tree, False)
        self._rebuild_category_cache()
        self._apply_filters()

    def set_disabled_categories(self, paths: list[str]) -> None:
        """Enable all categories, then disable those in paths. Applies filters once."""
        self._set_enabled_recursive(self.category_tree, True)
        for path in paths:
            node = self._find_category_node(path)
            if node:
                node.enabled = False
                self._set_enabled_recursive(node, False)
        self._rebuild_category_cache()
        self._apply_filters()

    def _find_category_node(self, path: str) -> Optional[CategoryNode]:
        """Navigate the category tree by slash-separated path. Returns None if not found."""
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
        """Find category nodes matching a path. Supports * wildcards."""
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
        """Set enabled state on a node and all its descendants."""
        node.enabled = enabled
        for child in node.children.values():
            self._set_enabled_recursive(child, enabled)

    def _rebuild_category_cache(self) -> None:
        """Rebuild flat cache of category path -> enabled state from tree."""
        self._category_enabled_cache = {}
        for path in self.category_counts:
            node = self._find_category_node(path)
            self._category_enabled_cache[path] = node.enabled if node else True
        self._rebuild_category_visible_set()

    def _rebuild_category_visible_set(self) -> None:
        """Compute union of line indices for all enabled categories."""
        visible: set[int] = set()
        for cat, indices in self._category_index.items():
            if self._is_category_enabled(cat):
                visible |= indices
        self._category_visible_set = visible

    def _is_category_enabled(self, category: str) -> bool:
        """Check if a category is visible.

        A category is visible if the leaf node itself is enabled.
        Leaf priority: explicit child state overrides parent inheritance.
        When a parent is disabled but a child is explicitly re-enabled,
        the child's lines are visible.
        """
        if not category:
            return True
        return self._category_enabled_cache.get(category, True)

    def _apply_filters(self) -> None:
        """Recompute filtered_indices from category state + level state + enabled filters (OR combination)."""
        # Fast path: nothing is filtered — all lines visible
        has_text_filters = any(self.filter_enabled)
        has_level_filters = bool(self.disabled_levels)
        has_pins = bool(self.pinned_line_numbers)
        all_cats_enabled = all(self._category_enabled_cache.get(c, True) for c in self.category_counts)

        if not has_text_filters and not has_level_filters and not has_pins and all_cats_enabled:
            self.filtered_indices = list(range(len(self.lines)))
            self._count_visible_levels()
            self.level_button_counts = dict(self.level_counts)
            return

        # Use pre-computed category visible set (rebuilt only on category state change)
        category_enabled = self._category_visible_set

        # Would-be-visible: category + text filters, ignoring level toggles
        active_filters = [f for f, e in zip(self.filters, self.filter_enabled) if e]
        if not active_filters:
            would_be_visible = category_enabled
        else:
            # Build lists for batch_match: only category-enabled lines
            cat_list = sorted(category_enabled)
            messages = [self.lines[i].message for i in cat_list]
            lowered = [self.lines[i].message_lower for i in cat_list]
            matched_positions = batch_match(messages, active_filters, pre_lowered=lowered)
            would_be_visible = {cat_list[p] for p in matched_positions}

        # Count per level before level filtering (used by level buttons)
        self._count_level_buttons(would_be_visible)

        # Build sorted list directly, skip intermediate set for level filtering
        disabled = self.disabled_levels
        if disabled:
            result = sorted(i for i in would_be_visible if self.lines[i].level not in disabled)
        else:
            result = sorted(would_be_visible)
        if self.pinned_line_numbers:
            pinned_in_range = sorted(n - 1 for n in self.pinned_line_numbers if 0 <= n - 1 < len(self.lines))
            result = _merge_sorted(result, pinned_in_range)

        self.filtered_indices = result

        self._count_visible_levels()

    def _build_category_tree(self) -> None:
        """Build category tree, counts, and index from parsed lines."""
        self.category_tree = CategoryNode(name="root", full_path="")
        self.category_counts = {}
        self._category_index: dict[str, set[int]] = defaultdict(set)

        for i, line in enumerate(self.lines):
            path = line.category
            self.category_counts[path] = self.category_counts.get(path, 0) + 1
            self._category_index[path].add(i)

            parts = path.split("/")
            node = self.category_tree
            built: list[str] = []
            for part in parts:
                built.append(part)
                full = "/".join(built)
                if part not in node.children:
                    node.children[part] = CategoryNode(name=part, full_path=full)
                node = node.children[part]
                node.line_count += 1

        self._rebuild_category_cache()

    def _count_levels(self) -> None:
        """Count log levels across all lines."""
        counts: dict[LogLevel, int] = defaultdict(int)
        for line in self.lines:
            counts[line.level] += 1
        self.level_counts = dict(counts)
        self.visible_level_counts = dict(self.level_counts)
        self.level_button_counts = dict(self.level_counts)

    def _count_visible_levels(self) -> None:
        """Count log levels for currently visible (filtered) lines."""
        counts: dict[LogLevel, int] = defaultdict(int)
        for idx in self.filtered_indices:
            counts[self.lines[idx].level] += 1
        self.visible_level_counts = dict(counts)

    def _count_level_buttons(self, indices: set[int]) -> None:
        """Count per level ignoring level toggles (used for level button display)."""
        counts: dict[LogLevel, int] = defaultdict(int)
        for idx in indices:
            counts[self.lines[idx].level] += 1
        self.level_button_counts = dict(counts)
