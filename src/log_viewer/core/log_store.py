"""Central store for parsed log data."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

from log_viewer.core.filter_engine import match as filter_match
from log_viewer.core.models import (
    CategoryNode,
    Filter,
    Highlight,
    LogLevel,
    LogLine,
    SearchDirection,
    SearchMode,
    SearchState,
)
from log_viewer.core.parser import parse_line


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
        self.filters: list[Filter] = []
        self.highlights: list[Highlight] = []
        self.search_state: Optional[SearchState] = None

    def load_lines(self, raw_lines: list[str], file_path: Optional[str] = None) -> None:
        """Parse raw lines and rebuild all indices."""
        self.lines = [parse_line(raw, i + 1) for i, raw in enumerate(raw_lines)]
        self.current_file = file_path
        self._build_category_tree()
        self._count_levels()
        self._apply_filters()

    def add_filter(self, filt: Filter) -> None:
        """Add a filter and recompute visible indices."""
        self.filters.append(filt)
        self._apply_filters()

    def remove_filter(self, pattern: str, case_sensitive: bool = False) -> None:
        """Remove filter by exact pattern + case_sensitive match."""
        self.filters = [
            f for f in self.filters if not (f.pattern == pattern and f.case_sensitive == case_sensitive)
        ]
        self._apply_filters()

    def clear_filters(self) -> None:
        """Remove all filters."""
        self.filters = []
        self._apply_filters()

    def add_highlight(self, h: Highlight) -> None:
        """Add a highlight (display-only, no filtering)."""
        self.highlights.append(h)

    def remove_highlight(self, pattern: str, case_sensitive: bool = False, color: str = "red") -> None:
        """Remove highlight by exact match."""
        self.highlights = [
            h
            for h in self.highlights
            if not (h.pattern == pattern and h.case_sensitive == case_sensitive and h.color == color)
        ]

    def clear_highlights(self) -> None:
        """Remove all highlights."""
        self.highlights = []

    def search(
        self,
        pattern: str,
        mode: SearchMode,
        case_sensitive: bool = False,
        direction: SearchDirection = SearchDirection.FORWARD,
    ) -> SearchState:
        """Search within the filtered view and return a SearchState."""
        matches: list[int] = []
        filt = Filter(pattern=pattern, mode=mode, case_sensitive=case_sensitive)
        for idx in self.filtered_indices:
            if filter_match(self.lines[idx].raw, filt):
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

    def enable_category(self, path: str) -> None:
        """Enable a category and all its children. Supports * wildcards."""
        for node in self._match_categories(path):
            node.enabled = True
            self._set_enabled_recursive(node, True)
        self._apply_filters()

    def disable_category(self, path: str) -> None:
        """Disable a category and all its children. Supports * wildcards."""
        for node in self._match_categories(path):
            node.enabled = False
            self._set_enabled_recursive(node, False)
        self._apply_filters()

    def enable_all_categories(self) -> None:
        """Enable all categories in the tree."""
        self._set_enabled_recursive(self.category_tree, True)
        self._apply_filters()

    def disable_all_categories(self) -> None:
        """Disable all categories in the tree."""
        self._set_enabled_recursive(self.category_tree, False)
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

    def _is_category_enabled(self, category: str) -> bool:
        """Check if a category is visible.

        A category is visible if the leaf node itself is enabled.
        Leaf priority: explicit child state overrides parent inheritance.
        When a parent is disabled but a child is explicitly re-enabled,
        the child's lines are visible.
        """
        if not category:
            return True
        node = self._find_category_node(category)
        if node is None:
            return True  # Unknown category defaults to visible
        return node.enabled

    def _apply_filters(self) -> None:
        """Recompute filtered_indices from category state + filters (OR combination)."""
        # Start with category-enabled lines
        category_enabled = {i for i, line in enumerate(self.lines) if self._is_category_enabled(line.category)}

        if not self.filters:
            self.filtered_indices = sorted(category_enabled)
        else:
            matching: set[int] = set()
            for filt in self.filters:
                for i in category_enabled:
                    if filter_match(self.lines[i].raw, filt):
                        matching.add(i)
            self.filtered_indices = sorted(matching)

        self._count_visible_levels()

    def _build_category_tree(self) -> None:
        """Build category tree and counts from parsed lines."""
        self.category_tree = CategoryNode(name="root", full_path="")
        self.category_counts = {}

        for line in self.lines:
            path = line.category
            self.category_counts[path] = self.category_counts.get(path, 0) + 1

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

    def _count_levels(self) -> None:
        """Count log levels across all lines."""
        counts: dict[LogLevel, int] = defaultdict(int)
        for line in self.lines:
            counts[line.level] += 1
        self.level_counts = dict(counts)
        self.visible_level_counts = dict(self.level_counts)

    def _count_visible_levels(self) -> None:
        """Count log levels for currently visible (filtered) lines."""
        counts: dict[LogLevel, int] = defaultdict(int)
        for idx in self.filtered_indices:
            counts[self.lines[idx].level] += 1
        self.visible_level_counts = dict(counts)
