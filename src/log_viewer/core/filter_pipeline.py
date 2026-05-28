"""Filter pipeline: owns all filter/highlight/pin state and filtering logic."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import numpy as np

from log_viewer.core.models import (
    CategoryNode,
    Filter,
    Highlight,
    LogLevel,
    SearchMode,
    _LEVEL_LIST,
)
from log_viewer.core.palette import HIGHLIGHT_PALETTE

if TYPE_CHECKING:
    from log_viewer.core.log_store import LogStore


class FilterPipeline:
    """Owns filter/highlight/pin state and computes filtered_indices.

    All methods take ``store`` as a parameter so the pipeline can read
    raw data (buffer, levels, category_ids) and write results
    (filtered_indices, level counts) back to the store.
    """

    def __init__(self) -> None:
        # --- Filter state ---
        self.filters: list[Filter] = []
        self.filter_enabled: list[bool] = []
        self._filter_masks: list[np.ndarray] = []

        # --- Highlight state ---
        self.highlights: list[Highlight] = []
        self.highlight_enabled: list[bool] = []
        self._highlight_color_index: int = 0

        # --- Pin state ---
        self.pinned_rules: list[Filter] = []
        self.pinned_enabled: list[bool] = []
        self._pin_masks: list[np.ndarray] = []

        # --- Level / category toggles ---
        self.disabled_levels: set[int] = set()
        self.disabled_categories: set[int] = set()

        # --- Term cache for simple-query optimization ---
        self._term_cache: dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------ #
    #  Cache management                                                    #
    # ------------------------------------------------------------------ #

    def invalidate_cache(self) -> None:
        """Clear the term cache (call after load_bytes)."""
        self._term_cache.clear()

    # ------------------------------------------------------------------ #
    #  Filters                                                            #
    # ------------------------------------------------------------------ #

    def add_filter(self, store: LogStore, filt: Filter) -> None:
        self.filters.append(filt)
        self.filter_enabled.append(True)
        self._filter_masks.append(self._compute_mask(store, filt))
        self.apply(store)

    def remove_filter(self, store: LogStore, pattern: str) -> None:
        kept = [
            (i, f, e)
            for i, (f, e) in enumerate(zip(self.filters, self.filter_enabled))
            if f.pattern != pattern
        ]
        self.filters = [f for _, f, _ in kept]
        self.filter_enabled = [e for _, _, e in kept]
        self._filter_masks = [self._filter_masks[i] for i, _, _ in kept]
        self.apply(store)

    def clear_filters(self, store: LogStore) -> None:
        self.filters = []
        self.filter_enabled = []
        self._filter_masks = []
        self.apply(store)

    # ------------------------------------------------------------------ #
    #  Highlights                                                         #
    # ------------------------------------------------------------------ #

    def add_highlight(self, h: Highlight) -> None:
        h.color = HIGHLIGHT_PALETTE[self._highlight_color_index % len(HIGHLIGHT_PALETTE)]
        self._highlight_color_index += 1
        self.highlights.append(h)
        self.highlight_enabled.append(True)

    def remove_highlight(self, pattern: str, color: str = "red") -> None:
        kept = [
            (h, e)
            for h, e in zip(self.highlights, self.highlight_enabled)
            if not (h.pattern == pattern and h.color == color)
        ]
        self.highlights = [h for h, _ in kept]
        self.highlight_enabled = [e for _, e in kept]

    def clear_highlights(self) -> None:
        self.highlights = []
        self.highlight_enabled = []

    # ------------------------------------------------------------------ #
    #  Pinned lines                                                       #
    # ------------------------------------------------------------------ #

    def add_pin(self, store: LogStore, filt: Filter) -> None:
        self.pinned_rules.append(filt)
        self.pinned_enabled.append(True)
        self._pin_masks.append(self._compute_mask(store, filt))
        self.apply(store)

    def remove_pin(self, store: LogStore, index: int) -> None:
        del self.pinned_rules[index]
        del self.pinned_enabled[index]
        del self._pin_masks[index]
        self.apply(store)

    def unpin_all(self, store: LogStore) -> None:
        self.pinned_rules.clear()
        self.pinned_enabled.clear()
        self._pin_masks.clear()
        self.apply(store)

    def reset_pins(self) -> None:
        """Clear all pin state without calling apply (used during _finalize_load)."""
        self.pinned_rules = []
        self.pinned_enabled = []
        self._pin_masks = []

    # ------------------------------------------------------------------ #
    #  Level toggles                                                      #
    # ------------------------------------------------------------------ #

    def toggle_level(self, store: LogStore, level: LogLevel) -> None:
        level_id = _LEVEL_LIST.index(level)
        if level_id in self.disabled_levels:
            self.disabled_levels.discard(level_id)
        else:
            self.disabled_levels.add(level_id)
        self.apply(store)

    def set_level_enabled(self, store: LogStore, level: LogLevel, enabled: bool) -> None:
        level_id = _LEVEL_LIST.index(level)
        if enabled:
            self.disabled_levels.discard(level_id)
        else:
            self.disabled_levels.add(level_id)
        self.apply(store)

    # ------------------------------------------------------------------ #
    #  Category toggles                                                   #
    # ------------------------------------------------------------------ #

    def enable_category(self, store: LogStore, path: str) -> None:
        for node in self._match_categories(store, path):
            self._set_enabled_recursive(store, node, True)
        self.apply(store)

    def disable_category(self, store: LogStore, path: str) -> None:
        for node in self._match_categories(store, path):
            self._set_enabled_recursive(store, node, False)
        self.apply(store)

    def enable_all_categories(self, store: LogStore) -> None:
        self._set_enabled_recursive(store, store.category_tree, True)
        self.disabled_categories.clear()
        self.apply(store)

    def disable_all_categories(self, store: LogStore) -> None:
        self._set_enabled_recursive(store, store.category_tree, False)
        self.apply(store)

    def set_disabled_categories(self, store: LogStore, paths: list[str]) -> None:
        self._set_enabled_recursive(store, store.category_tree, True)
        self.disabled_categories.clear()
        for path in paths:
            node = self._find_category_node(store, path)
            if node:
                self._set_enabled_recursive(store, node, False)
        self.apply(store)

    # ------------------------------------------------------------------ #
    #  Mask computation                                                   #
    # ------------------------------------------------------------------ #

    def compute_mask(self, store: LogStore, filt: Filter) -> np.ndarray:
        """Public entry point for computing a single filter mask (used by search)."""
        return self._compute_mask(store, filt)

    def recompute_masks(self, store: LogStore) -> None:
        """Rebuild all filter masks (called after file load)."""
        self._filter_masks = [self._compute_mask(store, f) for f in self.filters]

    def _compute_mask(self, store: LogStore, filt: Filter) -> np.ndarray:
        """Compute boolean mask for ALL lines matching a single filter."""
        n = store.n
        if n == 0:
            return np.empty(0, dtype=bool)

        mask = np.zeros(n, dtype=bool)

        if filt.mode == SearchMode.LINE_NUMBER:
            idx = int(filt.pattern) - 1
            if 0 <= idx < n:
                mask[idx] = True
            return mask

        if filt.mode in (SearchMode.PLAIN, SearchMode.REGEX):
            if filt.mode == SearchMode.PLAIN:
                if store._buf_lower is None:
                    store._buf_lower = bytes(store._buf).lower()
                pattern = re.escape(filt.pattern.lower()).encode("utf-8")
                try:
                    combined = re.compile(pattern)
                except re.error:
                    return mask
                positions = np.array(
                    [m.start() for m in combined.finditer(store._buf_lower)],
                    dtype=np.int64,
                )
                if len(positions) > 0:
                    line_indices = np.searchsorted(store.line_starts, positions, side="right") - 1
                    valid = (line_indices >= 0) & (line_indices < n)
                    mask[line_indices[valid]] = True
            else:
                # REGEX: lower both pattern and buffer, use case-sensitive
                # bytes regex on _buf_lower. This is ~50x faster than
                # bytes IGNORECASE regex (Python has no lookup tables for that).
                if store._buf_lower is None:
                    store._buf_lower = bytes(store._buf).lower()
                try:
                    combined = re.compile(filt.pattern.lower().encode("utf-8"))
                except re.error:
                    return mask
                positions = np.array(
                    [m.start() for m in combined.finditer(store._buf_lower)],
                    dtype=np.int64,
                )
                if len(positions) > 0:
                    line_indices = np.searchsorted(
                        store.line_starts, positions, side="right"
                    ) - 1
                    valid = (line_indices >= 0) & (line_indices < n)
                    mask[line_indices[valid]] = True
        else:
            # Simple query: decompose AST into terms, buffer-scan each,
            # then combine masks via AND/OR/NOT numpy operations.
            # Uses _term_cache to avoid re-scanning terms seen before.
            from log_viewer.core.simple_query import parse_query

            ast = parse_query(filt.pattern)
            unique_terms = list(set(ast.collect_terms()))

            if store._buf_lower is None:
                store._buf_lower = bytes(store._buf).lower()

            term_masks: dict[str, np.ndarray] = {}
            for term in unique_terms:
                if term in self._term_cache:
                    cached = self._term_cache[term]
                    # Cached mask may be wrong length if file changed
                    # and cache wasn't invalidated — check length.
                    if len(cached) == n:
                        term_masks[term] = cached
                        continue
                tmask = np.zeros(n, dtype=bool)
                pattern = re.escape(term.lower()).encode("utf-8")
                combined = re.compile(pattern)
                positions = np.array(
                    [m.start() for m in combined.finditer(store._buf_lower)],
                    dtype=np.int64,
                )
                if len(positions) > 0:
                    line_indices = np.searchsorted(store.line_starts, positions, side="right") - 1
                    valid = (line_indices >= 0) & (line_indices < n)
                    tmask[line_indices[valid]] = True
                self._term_cache[term] = tmask
                term_masks[term] = tmask

            mask = ast.eval_masks(term_masks, n)

        return mask

    # ------------------------------------------------------------------ #
    #  Apply filters (core)                                               #
    # ------------------------------------------------------------------ #

    def apply(self, store: LogStore) -> None:
        """Recompute store.filtered_indices using combined filter logic."""
        if store.n == 0:
            store.filtered_indices = np.empty(0, dtype=np.uint32)
            return

        has_text_filters = any(self.filter_enabled)
        has_level_filters = bool(self.disabled_levels)
        has_cat_filters = bool(self.disabled_categories)
        has_pins = any(self.pinned_enabled)
        no_filters = not has_text_filters and not has_level_filters and not has_cat_filters

        # Fast path: nothing filtered, no pins
        if no_filters and not has_pins:
            store.filtered_indices = np.arange(store.n, dtype=np.uint32)
            store._count_visible_levels()
            store.level_button_counts = dict(store.level_counts)
            return

        # Build category mask: True = category enabled
        if has_cat_filters:
            enabled_cats = np.array(
                [i for i in range(len(store._category_names)) if i not in self.disabled_categories],
                dtype=np.uint16,
            )
            cat_mask = np.isin(store.category_ids, enabled_cats)
        else:
            cat_mask = np.ones(store.n, dtype=bool)

        # Build level mask: True = level enabled
        if has_level_filters:
            enabled_levels = np.array(
                [i for i in range(len(_LEVEL_LIST)) if i not in self.disabled_levels],
                dtype=np.uint8,
            )
            level_mask = np.isin(store.levels, enabled_levels)
        else:
            level_mask = np.ones(store.n, dtype=bool)

        # Category + level combined (before text filter, for level button counts)
        cat_level_mask = cat_mask & level_mask

        # Build text filter mask
        if has_text_filters:
            if len(self._filter_masks) != len(self.filters):
                self.recompute_masks(store)
            active_masks = [m for m, e in zip(self._filter_masks, self.filter_enabled) if e]
            if active_masks:
                text_mask = np.zeros(store.n, dtype=bool)
                for m in active_masks:
                    text_mask |= m
            else:
                text_mask = np.ones(store.n, dtype=bool)
        else:
            text_mask = np.ones(store.n, dtype=bool)

        # Combined mask: category & level & text
        combined = cat_level_mask & text_mask

        # Count per level for buttons (category + text filtering, ignoring level toggles)
        self._count_level_buttons_from_mask(
            store, cat_mask & text_mask if has_text_filters else cat_mask
        )

        # OR in pin mask — pinned lines bypass all filters
        if has_pins:
            active_pin_masks = [m for m, e in zip(self._pin_masks, self.pinned_enabled) if e]
            if active_pin_masks:
                pin_mask = np.zeros(store.n, dtype=bool)
                for m in active_pin_masks:
                    pin_mask |= m
                combined = combined | pin_mask

        store.filtered_indices = np.where(combined)[0].astype(np.uint32)
        store._count_visible_levels()

    # ------------------------------------------------------------------ #
    #  Category helpers                                                   #
    # ------------------------------------------------------------------ #

    def collect_disabled_paths(
        self, tree: CategoryNode, out: set[str]
    ) -> None:
        """Collect full_path of all disabled nodes in the category tree."""
        if not tree.enabled and tree.full_path:
            out.add(tree.full_path)
        for child in tree.children.values():
            self.collect_disabled_paths(child, out)

    def find_category_node(
        self, store: LogStore, path: str
    ) -> Optional[CategoryNode]:
        if not path:
            return store.category_tree
        parts = path.rstrip("/").split("/")
        node = store.category_tree
        for part in parts:
            if part not in node.children:
                return None
            node = node.children[part]
        return node

    # ------------------------------------------------------------------ #
    #  Private helpers                                                    #
    # ------------------------------------------------------------------ #

    def _match_categories(
        self, store: LogStore, pattern: str
    ) -> list[CategoryNode]:
        if "*" not in pattern:
            node = self._find_category_node(store, pattern)
            return [node] if node else []
        regex = re.compile(".*".join(re.escape(p) for p in pattern.split("*")))
        return [
            self._find_category_node(store, path)
            for path in store.category_counts
            if regex.search(path)
        ]

    def _find_category_node(
        self, store: LogStore, path: str
    ) -> Optional[CategoryNode]:
        if not path:
            return store.category_tree
        parts = path.rstrip("/").split("/")
        node = store.category_tree
        for part in parts:
            if part not in node.children:
                return None
            node = node.children[part]
        return node

    def _set_enabled_recursive(
        self, store: LogStore, node: CategoryNode, enabled: bool
    ) -> None:
        node.enabled = enabled
        full = node.full_path
        if full:
            cat_id = store._category_name_to_id.get(full)
            if cat_id is not None:
                if enabled:
                    self.disabled_categories.discard(cat_id)
                else:
                    self.disabled_categories.add(cat_id)
        for child in node.children.values():
            self._set_enabled_recursive(store, child, enabled)

    def _count_level_buttons_from_mask(
        self, store: LogStore, cat_mask: np.ndarray
    ) -> None:
        """Count per level for category-enabled lines (used by level buttons)."""
        cat_indices = np.where(cat_mask)[0]
        if len(cat_indices) == 0:
            store.level_button_counts = {}
            return
        cat_levels = store.levels[cat_indices]
        counts = np.bincount(cat_levels, minlength=len(_LEVEL_LIST))
        store.level_button_counts = {
            _LEVEL_LIST[i]: int(counts[i]) for i in range(len(_LEVEL_LIST)) if counts[i] > 0
        }
