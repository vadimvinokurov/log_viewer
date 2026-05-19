"""Tests for LogStore."""

from __future__ import annotations

import os
import tempfile

import numpy as np

from log_viewer.core.models import (
    Filter,
    Highlight,
    LogLevel,
    LogLine,
    SearchDirection,
    SearchMode,
    SearchState,
)
from log_viewer.core.log_store import LogStore


def _make_lines(raw_lines: list[str]) -> list[LogLine]:
    """Helper: parse raw lines into LogLines."""
    from log_viewer.core.parser import parse_line

    return [parse_line(raw, i + 1) for i, raw in enumerate(raw_lines)]


SAMPLE_LINES = [
    "01-01-2024T08:00:00.100 my_lib/core version 5.18",
    "01-01-2024T08:00:00.200 my_app/storage/folder LOG_ERROR Failed to open",
    "01-01-2024T08:00:00.200 my_app/storage/db LOG_ERROR Read failed",
    "01-01-2024T08:00:00.200 my_app/storage/folder LOG_WARNING Missing file",
    "01-01-2024T08:00:00.100 SYSTEM test_os",
    "01-01-2024T08:00:00.200 my_app/storage/db LOG_DEBUG Debug info",
]


class TestLogStoreLoad:
    def test_load_lines_populates_all_fields(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert len(store.lines) == 6
        assert store.current_file is None

    def test_load_lines_builds_category_tree(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # Categories: my_lib/core, my_app/storage/folder,
        # my_app/storage/db, SYSTEM
        assert "my_lib/core" in store.category_counts
        assert "my_app/storage/folder" in store.category_counts
        assert "my_app/storage/db" in store.category_counts
        assert "SYSTEM" in store.category_counts

    def test_category_tree_root_has_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        root = store.category_tree
        assert "my_lib" in root.children
        assert "my_app" in root.children
        assert "SYSTEM" in root.children

    def test_category_tree_nested(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        horde = store.category_tree.children["my_app"]
        assert "storage" in horde.children
        gs = horde.children["storage"]
        assert "folder" in gs.children
        assert "db" in gs.children

    def test_category_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert (
            store.category_counts["my_app/storage/folder"] == 2
        )  # ERROR + WARNING
        assert (
            store.category_counts["my_app/storage/db"] == 2
        )  # ERROR + DEBUG
        assert store.category_counts["my_lib/core"] == 1
        assert store.category_counts["SYSTEM"] == 1

    def test_category_ids_and_names_built_at_load(self) -> None:
        """Category data stored in category_ids array and _category_names list."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # _category_names contains all category names including "uncategorized"
        assert "my_app/storage/folder" in store._category_names
        assert "my_app/storage/db" in store._category_names
        assert "my_lib/core" in store._category_names
        assert "SYSTEM" in store._category_names
        # category_ids maps each row to its category id
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        core_id = store._category_name_to_id["my_lib/core"]
        system_id = store._category_name_to_id["SYSTEM"]
        # my_app/storage/folder has lines at indices 1 and 3
        assert set(np.where(store.category_ids == folder_id)[0].tolist()) == {1, 3}
        # my_app/storage/db has lines at indices 2 and 5
        assert set(np.where(store.category_ids == db_id)[0].tolist()) == {2, 5}
        assert set(np.where(store.category_ids == core_id)[0].tolist()) == {0}
        assert set(np.where(store.category_ids == system_id)[0].tolist()) == {4}

    def test_level_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.level_counts[LogLevel.ERROR] == 2
        assert store.level_counts[LogLevel.WARNING] == 1
        assert store.level_counts[LogLevel.INFO] == 2  # my_lib/core + SYSTEM
        assert store.level_counts[LogLevel.DEBUG] == 1

    def test_visible_level_counts_initially_equals_total(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.visible_level_counts == store.level_counts

    def test_filtered_indices_initially_all(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.filtered_indices.tolist() == list(range(store.n))


class TestLogStoreEmpty:
    def test_empty_load(self) -> None:
        store = LogStore()
        store.load_lines([])
        assert store.n == 0
        assert store.category_counts == {}
        assert store.level_counts == {}
        assert store.filtered_indices.tolist() == []

    def test_load_replaces_previous(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES[:2])
        assert store.n == 2

        store.load_lines(SAMPLE_LINES[3:])
        assert store.n == 3


class TestLogStoreCurrentFile:
    def test_file_path_stored(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES, file_path="test.log")
        assert store.current_file == "test.log"

    def test_file_path_none_by_default(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.current_file is None


class TestLogStoreCategoryNode:
    def test_category_node_line_count(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        folder_node = (
            store.category_tree.children["my_app"]
            .children["storage"]
            .children["folder"]
        )
        assert folder_node.line_count == 2


class TestLogStoreFilters:
    """Test filter add/remove/clear and OR combination."""

    def test_add_single_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        f = Filter(pattern="Failed", mode=SearchMode.PLAIN, case_sensitive=False)
        store.add_filter(f)
        assert len(store.filters) == 1
        # "Failed to open" and "Read failed" both contain "Failed"
        assert len(store.filtered_indices) == 2

    def test_add_two_filters_or_logic(self) -> None:
        """Multiple filters → OR logic (line shown if ANY filter matches)."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Debug", mode=SearchMode.PLAIN))
        store.add_filter(Filter(pattern="test_os", mode=SearchMode.PLAIN))
        # "Debug info" line + "test_os" line = 2
        assert len(store.filtered_indices) == 2

    def test_add_regex_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # "Failed" matches message in lines 1 ("Failed to open") and 2 ("Read failed")
        store.add_filter(Filter(pattern=r"Failed", mode=SearchMode.REGEX))
        assert len(store.filtered_indices) == 2  # Two lines with "Failed" in message

    def test_add_simple_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(
            Filter(
                pattern='"Failed" AND "open"',
                mode=SearchMode.SIMPLE,
            )
        )
        assert len(store.filtered_indices) == 1  # Only "Failed to open"

    def test_remove_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        f1 = Filter(pattern="Failed", mode=SearchMode.PLAIN)
        f2 = Filter(pattern="test_os", mode=SearchMode.PLAIN)
        store.add_filter(f1)
        store.add_filter(f2)
        assert len(store.filters) == 2

        store.remove_filter("Failed", case_sensitive=False)
        assert len(store.filters) == 1
        # Only "test_os" line remains
        assert len(store.filtered_indices) == 1

    def test_remove_filter_case_sensitive_match(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        f = Filter(pattern="Failed", mode=SearchMode.PLAIN, case_sensitive=True)
        store.add_filter(f)
        # Removing with wrong case_sensitive won't match
        store.remove_filter("Failed", case_sensitive=False)
        assert len(store.filters) == 1  # Still there

        store.remove_filter("Failed", case_sensitive=True)
        assert len(store.filters) == 0

    def test_clear_filters(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        store.add_filter(Filter(pattern="test_os", mode=SearchMode.PLAIN))
        store.clear_filters()
        assert len(store.filters) == 0
        # All lines visible again
        assert len(store.filtered_indices) == 6

    def test_filter_updates_visible_level_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        assert store.visible_level_counts[LogLevel.ERROR] == 2
        assert store.visible_level_counts.get(LogLevel.WARNING, 0) == 0

    def test_clear_filter_restores_visible_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        store.clear_filters()
        assert store.visible_level_counts == store.level_counts

    def test_add_filter_no_match_shows_nothing(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="ZZZZNONEXISTENT", mode=SearchMode.PLAIN))
        assert len(store.filtered_indices) == 0

    def test_filter_matches_message_not_raw(self) -> None:
        """Filtering operates on message field, not the raw line."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # "Failed" is in messages of lines 1 ("Failed to open") and 2 ("Read failed")
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        assert len(store.filtered_indices) == 2
        # "LOG_ERROR" is in raw but NOT in any message — should match nothing
        store2 = LogStore()
        store2.load_lines(SAMPLE_LINES)
        store2.add_filter(Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN))
        assert len(store2.filtered_indices) == 0


class TestLogStoreHighlights:
    """Test highlight add/remove/clear (display-only, no filtering)."""

    def test_add_highlight(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        h = Highlight(pattern="ERROR", mode=SearchMode.PLAIN)
        store.add_highlight(h)
        assert len(store.highlights) == 1
        assert store.highlights[0].color == "#FFD700"

    def test_add_highlight_does_not_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_highlight(Highlight(pattern="ERROR", mode=SearchMode.PLAIN))
        # All lines still visible
        assert len(store.filtered_indices) == 6

    def test_remove_highlight(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        h = Highlight(pattern="ERROR", mode=SearchMode.PLAIN)
        store.add_highlight(h)
        store.remove_highlight("ERROR", case_sensitive=False, color="#FFD700")
        assert len(store.highlights) == 0

    def test_clear_highlights(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_highlight(Highlight(pattern="ERROR", mode=SearchMode.PLAIN))
        store.add_highlight(Highlight(pattern="WARNING", mode=SearchMode.PLAIN))
        store.clear_highlights()
        assert len(store.highlights) == 0

    def test_add_highlight_auto_assigns_first_palette_color(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        h = Highlight(pattern="ERROR", mode=SearchMode.PLAIN)
        store.add_highlight(h)
        assert store.highlights[0].color == "#FFD700"

    def test_add_highlight_cycles_colors(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        for i in range(12):
            store.add_highlight(Highlight(pattern=f"pat{i}", mode=SearchMode.PLAIN))
        assert store.highlights[0].color == "#FFD700"
        assert store.highlights[9].color == "#FD79A8"
        assert store.highlights[10].color == "#FFD700"
        assert store.highlights[11].color == "#FF9F43"


class TestLogStoreSearch:
    """Test search() and match navigation on LogStore."""

    def test_search_plain_forward_finds_matches(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        # "Failed to open" (idx 1) and "Read failed" (idx 2)
        assert state.matches == [1, 2]
        assert state.current_index == 0
        assert state.pattern == "Failed"

    def test_search_case_sensitive(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        state = store.search("failed", SearchMode.PLAIN, case_sensitive=True, direction=SearchDirection.FORWARD)
        # Only "Read failed" has lowercase "failed"
        assert state.matches == [2]

    def test_search_regex(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        state = store.search(r"Failed|Missing", SearchMode.REGEX, case_sensitive=False, direction=SearchDirection.FORWARD)
        # "Failed to open" (idx 1), "Read failed" (idx 2), "Missing file" (idx 3)
        assert state.matches == [1, 2, 3]

    def test_search_no_matches(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        state = store.search("NONEXISTENT", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        assert state.matches == []
        assert state.current_index == 0

    def test_search_backward_starts_from_last(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.BACKWARD)
        assert state.matches == [1, 2]
        assert state.current_index == 1  # Last match

    def test_search_within_filtered_view_only(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # Filter to show only lines with "Failed" in message (indices 1, 2)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        assert store.filtered_indices.tolist() == [1, 2]
        # Search within filtered view
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        # Only indices 1 and 2 are visible, both contain "Failed"
        assert state.matches == [1, 2]

    def test_search_excludes_non_visible_lines(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # Filter to show only "test_os" line (index 4)
        store.add_filter(Filter(pattern="test_os", mode=SearchMode.PLAIN))
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        # "Failed" is not in the "test_os" message
        assert state.matches == []


class TestLogStoreSearchNavigation:
    """Test next_match / prev_match cycling."""

    def _store_with_search(self) -> LogStore:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        return store

    def test_next_match_advances(self) -> None:
        store = self._store_with_search()
        state = store.next_match()
        assert state is not None
        assert state.current_index == 1

    def test_next_match_wraps_around(self) -> None:
        store = self._store_with_search()
        store.next_match()  # index 0 → 1
        state = store.next_match()  # index 1 → wraps to 0
        assert state is not None
        assert state.current_index == 0

    def test_prev_match_goes_back(self) -> None:
        store = self._store_with_search()
        store.next_match()  # index 0 → 1
        state = store.prev_match()
        assert state is not None
        assert state.current_index == 0

    def test_prev_match_wraps_around(self) -> None:
        store = self._store_with_search()
        state = store.prev_match()  # index 0 → wraps to last (1)
        assert state is not None
        assert state.current_index == 1

    def test_next_match_no_search_returns_none(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.next_match() is None

    def test_prev_match_no_search_returns_none(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.prev_match() is None

    def test_next_match_no_results_returns_none(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.search("NONEXISTENT", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        assert store.next_match() is None

    def test_clear_search(self) -> None:
        store = self._store_with_search()
        assert store.search_state is not None
        store.clear_search()
        assert store.search_state is None


class TestLogStoreCategoryEnableDisable:
    """Test enable_category, disable_category with inheritance."""

    def test_disable_category_sets_node_disabled(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        assert store.category_tree.children["my_app"].enabled is False

    def test_disable_category_propagates_to_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        horde = store.category_tree.children["my_app"]
        gs = horde.children["storage"]
        assert gs.enabled is False
        assert gs.children["folder"].enabled is False
        assert gs.children["db"].enabled is False

    def test_enable_category_sets_node_enabled(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app")
        assert store.category_tree.children["my_app"].enabled is True

    def test_enable_category_propagates_to_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app")
        horde = store.category_tree.children["my_app"]
        gs = horde.children["storage"]
        assert gs.enabled is True
        assert gs.children["folder"].enabled is True
        assert gs.children["db"].enabled is True

    def test_leaf_priority_child_re_enabled_under_disabled_parent(self) -> None:
        """Explicit child enable overrides parent disable inheritance."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # Re-enable just the leaf "folder" under disabled my_app
        store.enable_category("my_app/storage/folder")
        horde = store.category_tree.children["my_app"]
        assert horde.enabled is False
        assert horde.children["storage"].enabled is False
        # But the explicitly re-enabled leaf is True
        assert horde.children["storage"].children["folder"].enabled is True
        # Sibling stays disabled
        assert horde.children["storage"].children["db"].enabled is False

    def test_disable_all_categories(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_all_categories()
        assert store.category_tree.children["my_app"].enabled is False
        assert store.category_tree.children["my_lib"].enabled is False
        assert store.category_tree.children["SYSTEM"].enabled is False

    def test_enable_all_categories(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_all_categories()
        store.enable_all_categories()
        for child in store.category_tree.children.values():
            assert child.enabled is True

    def test_enable_all_propagates_to_deep_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_all_categories()
        store.enable_all_categories()
        gs = store.category_tree.children["my_app"].children["storage"]
        assert gs.children["folder"].enabled is True
        assert gs.children["db"].enabled is True

    def test_disable_category_updates_filtered_indices(self) -> None:
        """Disabled category lines should be excluded from filtered view."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert len(store.filtered_indices) == 6
        store.disable_category("my_app")
        # my_app lines: indices 1,2,3,5 (4 lines)
        # Remaining: my_lib/core (0), SYSTEM (4)
        assert len(store.filtered_indices) == 2
        assert 0 in store.filtered_indices
        assert 4 in store.filtered_indices

    def test_enable_category_restores_filtered_indices(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app")
        assert len(store.filtered_indices) == 6

    def test_category_filter_combined_with_text_filter(self) -> None:
        """Category + text filter both active simultaneously."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        # 2 lines with "Failed" in message (indices 1,2)
        assert len(store.filtered_indices) == 2
        # Now also disable my_app — those lines are in my_app
        store.disable_category("my_app")
        # No lines with "Failed" visible outside my_app
        assert len(store.filtered_indices) == 0

    def test_disable_leaf_category_only_affects_that_leaf(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app/storage/folder")
        # Only folder lines hidden (indices 1,3). Others remain.
        assert len(store.filtered_indices) == 4

    def test_disable_nonexistent_category_is_noop(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("NONEXISTENT")
        assert len(store.filtered_indices) == 6

    def test_enable_nonexistent_category_is_noop(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.enable_category("NONEXISTENT")
        assert len(store.filtered_indices) == 6

    def test_disable_category_updates_visible_level_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # Remaining levels: my_lib/core (INFO), SYSTEM (INFO)
        assert store.visible_level_counts.get(LogLevel.INFO, 0) == 2
        assert store.visible_level_counts.get(LogLevel.ERROR, 0) == 0

    def test_category_affects_search_scope(self) -> None:
        """Search operates within category-filtered view."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # "Failed" only exists in my_app lines
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        assert state.matches == []

    def test_leaf_enable_under_disabled_parent_shows_in_filtered(self) -> None:
        """Re-enabled leaf under disabled parent should appear in filtered_indices."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app/storage/folder")
        # folder has 2 lines (indices 1,3)
        # Plus my_lib/core (0) and SYSTEM (4) which are still enabled
        assert len(store.filtered_indices) == 4
        assert 1 in store.filtered_indices
        assert 3 in store.filtered_indices


class TestWildcardCategory:
    """Tests for wildcard (*pattern) support in enable/disable_category."""

    def _store(self) -> LogStore:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        return store

    def test_wildcard_disable_matches_substring(self) -> None:
        store = self._store()
        store.disable_category("*folder")
        # Only my_app/storage/folder lines hidden
        assert len(store.filtered_indices) == 4

    def test_wildcard_disable_contains_match(self) -> None:
        store = self._store()
        store.disable_category("*stora*")
        # All my_app/storage/* lines hidden
        assert len(store.filtered_indices) == 2  # my_lib/core + SYSTEM

    def test_wildcard_enable_after_disable(self) -> None:
        store = self._store()
        store.disable_category("my_app")
        store.enable_category("*folder")
        # folder lines restored
        assert 1 in store.filtered_indices
        assert 3 in store.filtered_indices

    def test_wildcard_no_match_is_noop(self) -> None:
        store = self._store()
        store.disable_category("*zzz_nothing")
        assert len(store.filtered_indices) == 6

    def test_wildcard_disable_top_level(self) -> None:
        store = self._store()
        store.disable_category("*my_app*")
        assert len(store.filtered_indices) == 2  # my_lib/core + SYSTEM


class TestLogStoreLevelToggle:
    """Test toggle_level, set_level_enabled, and disabled_levels filtering."""

    def test_toggle_level_removes_level_from_filtered(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        # 2 ERROR lines removed, 4 remain
        assert len(store.filtered_indices) == 4

    def test_toggle_level_twice_restores(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        store.toggle_level(LogLevel.ERROR)
        assert len(store.filtered_indices) == 6

    def test_set_level_enabled_false(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.set_level_enabled(LogLevel.ERROR, False)
        assert len(store.filtered_indices) == 4

    def test_set_level_enabled_true(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.set_level_enabled(LogLevel.ERROR, False)
        store.set_level_enabled(LogLevel.ERROR, True)
        assert len(store.filtered_indices) == 6

    def test_disabled_levels_default_empty(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.disabled_levels == set()

    def test_disable_multiple_levels(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        store.toggle_level(LogLevel.WARNING)
        # 2 ERROR + 1 WARNING = 3 removed, 3 remain
        assert len(store.filtered_indices) == 3

    def test_disable_all_levels_shows_nothing(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        for level in LogLevel:
            store.toggle_level(level)
        assert len(store.filtered_indices) == 0

    def test_toggle_level_updates_visible_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        assert store.visible_level_counts.get(LogLevel.ERROR, 0) == 0
        assert store.visible_level_counts[LogLevel.INFO] == 2

    def test_level_toggle_combined_with_text_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        # 2 lines with "Failed" in message pass filter (both are ERROR level)
        assert len(store.filtered_indices) == 2
        # Disable ERROR level — those lines vanish
        store.toggle_level(LogLevel.ERROR)
        assert len(store.filtered_indices) == 0

    def test_level_toggle_combined_with_category_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # my_lib/core (INFO idx 0), SYSTEM (INFO idx 4)
        assert len(store.filtered_indices) == 2
        store.toggle_level(LogLevel.INFO)
        assert len(store.filtered_indices) == 0

    def test_load_lines_resets_disabled_levels(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        # disabled_levels now stores int level IDs (ERROR=1)
        assert 1 in store.disabled_levels
        store.load_lines(SAMPLE_LINES)
        assert store.disabled_levels == set()
        assert len(store.filtered_indices) == 6


class TestLevelButtonCounts:
    """level_button_counts shows would-be-visible counts, ignoring level toggles."""

    def test_button_counts_equal_total_on_load(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.level_button_counts[LogLevel.ERROR] == 2
        assert store.level_button_counts[LogLevel.WARNING] == 1
        assert store.level_button_counts[LogLevel.INFO] == 2
        assert store.level_button_counts[LogLevel.DEBUG] == 1

    def test_button_counts_ignore_disabled_levels(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        # ERROR is disabled, but button count still shows 2
        assert store.level_button_counts[LogLevel.ERROR] == 2

    def test_button_counts_respect_category_filters(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # my_app has 2 ERROR, 1 WARNING, 1 DEBUG — all gone
        assert store.level_button_counts.get(LogLevel.ERROR, 0) == 0
        assert store.level_button_counts[LogLevel.INFO] == 2

    def test_button_counts_respect_text_filters(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        assert store.level_button_counts[LogLevel.ERROR] == 2
        assert store.level_button_counts.get(LogLevel.INFO, 0) == 0

    def test_button_counts_unchanged_after_level_toggle(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        before = dict(store.level_button_counts)
        store.toggle_level(LogLevel.ERROR)
        assert store.level_button_counts == before


PLAIN_LINES = [
    "08:00:00.100    0.014 wrn    config    Duplicate entry found",
    "08:00:00.200  100.000 dbg    my_module    Object count: 42",
    "08:00:00.100    0.014 err    network    Connection failed",
    "08:00:00.100    0.014 msg    system    Initialized successfully",
]


class TestLogStorePinnedLines:
    """Test pin_line, unpin_line, unpin_all, and pinned visibility."""

    def test_pin_line_adds_to_pinned(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(2)
        assert 2 in store.pinned_line_numbers

    def test_pin_line_idempotent(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(2)
        store.pin_line(2)
        assert store.pinned_line_numbers == {2}

    def test_unpin_line_removes(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(2)
        store.unpin_line(2)
        assert store.pinned_line_numbers == set()

    def test_unpin_all_clears(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(1)
        store.pin_line(3)
        store.unpin_all()
        assert store.pinned_line_numbers == set()

    def test_pinned_line_visible_with_filter(self) -> None:
        """Pinned line stays visible even when text filter would hide it."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="NONEXISTENT", mode=SearchMode.PLAIN))
        assert len(store.filtered_indices) == 0
        store.pin_line(2)  # line_number=2 → index 1
        assert 1 in store.filtered_indices

    def test_pinned_line_visible_with_disabled_category(self) -> None:
        """Pinned line stays visible even when its category is disabled."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # my_app lines are hidden
        assert 1 not in store.filtered_indices
        store.pin_line(2)  # line_number=2 → index 1
        assert 1 in store.filtered_indices

    def test_pinned_line_visible_with_disabled_level(self) -> None:
        """Pinned line stays visible even when its level is disabled."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.toggle_level(LogLevel.ERROR)
        # ERROR lines hidden
        assert 1 not in store.filtered_indices
        store.pin_line(2)  # line_number=2 → index 1
        assert 1 in store.filtered_indices

    def test_multiple_pinned_lines(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="NONEXISTENT", mode=SearchMode.PLAIN))
        store.pin_line(2)  # line_number=2 → index 1
        store.pin_line(5)  # line_number=5 → index 4
        assert store.filtered_indices.tolist() == [1, 4]

    def test_pin_nonexistent_line_is_noop(self) -> None:
        """Pinning a line number that doesn't exist in the file should still add it,
        but it won't appear in filtered_indices since the line doesn't exist."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(999)
        assert 999 in store.pinned_line_numbers
        # But 999 is not a valid index, so it won't appear
        assert 999 not in store.filtered_indices

    def test_load_lines_clears_pins(self) -> None:
        """Pinned lines are cleared on file reload."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(2)
        store.load_lines(SAMPLE_LINES)
        assert store.pinned_line_numbers == set()

    def test_pin_lines_batch(self) -> None:
        """pin_lines pins multiple lines at once."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_lines([1, 3, 5])
        assert store.pinned_line_numbers == {1, 3, 5}


class TestLogStorePlainFormat:
    def test_load_plain_lines(self) -> None:
        store = LogStore()
        store.load_lines(PLAIN_LINES)
        assert len(store.lines) == 4
        assert store.lines[0].level == LogLevel.WARNING
        assert store.lines[0].category == "config"
        assert store.lines[0].message == "Duplicate entry found"
        assert store.lines[1].level == LogLevel.DEBUG
        assert store.lines[2].level == LogLevel.ERROR
        assert store.lines[3].level == LogLevel.INFO

    def test_plain_format_builds_category_tree(self) -> None:
        store = LogStore()
        store.load_lines(PLAIN_LINES)
        assert "config" in store.category_counts
        assert "my_module" in store.category_counts
        assert "network" in store.category_counts
        assert "system" in store.category_counts


class TestLogStoreGetRaw:
    """Test get_raw reads original line from file on demand."""

    def test_get_raw_returns_original_line(self) -> None:
        lines = [
            "01-01-2024T08:00:00.100 my_lib/core version 5.18",
            "01-01-2024T08:00:00.200 my_app/storage LOG_ERROR Failed to open",
        ]
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False) as f:
            for line in lines:
                f.write(line.encode("utf-8") + b"\n")
            path = f.name
        try:
            store = LogStore()
            store.load_lines(lines, file_path=path)
            assert store.get_raw(0) == "01-01-2024T08:00:00.100 my_lib/core version 5.18"
            assert store.get_raw(1) == "01-01-2024T08:00:00.200 my_app/storage LOG_ERROR Failed to open"
        finally:
            os.unlink(path)

    def test_get_raw_returns_empty_without_file(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.get_raw(0) == ""

    def test_get_raw_out_of_range_returns_empty(self) -> None:
        lines = ["01-01-2024T08:00:00.100 my_lib/core version 5.18"]
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False) as f:
            for line in lines:
                f.write(line.encode("utf-8") + b"\n")
            path = f.name
        try:
            store = LogStore()
            store.load_lines(lines, file_path=path)
            assert store.get_raw(99) == ""
        finally:
            os.unlink(path)


class TestCategoryEnabledState:
    """Test category enabled/disabled state via disabled_categories and tree nodes."""

    def test_all_enabled_on_load(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # No categories disabled by default
        assert store.disabled_categories == set()
        # All tree nodes enabled
        for path in store.category_counts:
            node = store._find_category_node(path)
            assert node is not None
            assert node.enabled is True

    def test_disabled_after_disable(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # my_app category ids should be in disabled_categories
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        assert folder_id in store.disabled_categories
        assert db_id in store.disabled_categories
        # Unrelated categories still enabled
        core_id = store._category_name_to_id["my_lib/core"]
        assert core_id not in store.disabled_categories

    def test_re_enabled_after_enable(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app/storage/folder")
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        assert folder_id not in store.disabled_categories
        assert db_id in store.disabled_categories

    def test_all_enabled_after_enable_all(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_all_categories()
        store.enable_all_categories()
        assert store.disabled_categories == set()
        for path in store.category_counts:
            node = store._find_category_node(path)
            assert node is not None
            assert node.enabled is True

    def test_all_disabled_after_disable_all(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_all_categories()
        for path in store.category_counts:
            cat_id = store._category_name_to_id[path]
            assert cat_id in store.disabled_categories

    def test_set_disabled_categories(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.set_disabled_categories(["my_app/storage/folder"])
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        core_id = store._category_name_to_id["my_lib/core"]
        assert folder_id in store.disabled_categories
        assert db_id not in store.disabled_categories
        assert core_id not in store.disabled_categories

    def test_empty_path_find_returns_root(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store._find_category_node("") is store.category_tree

    def test_unknown_path_find_returns_none(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store._find_category_node("nonexistent/path") is None


class TestCategoryDisabledSet:
    """Test disabled_categories set reflects category filter state."""

    def test_empty_on_load(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # No categories disabled by default
        assert store.disabled_categories == set()

    def test_unchanged_after_text_filter_add(self) -> None:
        """Adding a text filter must not change the disabled categories set."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        assert store.disabled_categories == set()

    def test_populated_after_category_disable(self) -> None:
        """Disabling a category must add its ids to disabled_categories."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        # my_app categories: folder and db should be disabled
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        assert folder_id in store.disabled_categories
        assert db_id in store.disabled_categories
        # filtered_indices should only contain non-my_app lines
        assert set(store.filtered_indices.tolist()) == {0, 4}

    def test_cleared_after_category_enable(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app")
        assert store.disabled_categories == set()
        assert set(store.filtered_indices.tolist()) == {0, 1, 2, 3, 4, 5}

    def test_empty_on_empty_load(self) -> None:
        store = LogStore()
        store.load_lines([])
        assert store.disabled_categories == set()


class TestReloadStatePreservation:
    """Test that filters, highlights, and disabled categories survive reload."""

    def test_preserves_filters_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        store.load_lines(SAMPLE_LINES)
        assert len(store.filters) == 1
        assert store.filters[0].pattern == "Failed"

    def test_preserves_highlights_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_highlight(Highlight(pattern="ERROR", mode=SearchMode.PLAIN))
        store.load_lines(SAMPLE_LINES)
        assert len(store.highlights) == 1
        assert store.highlights[0].pattern == "ERROR"

    def test_preserves_disabled_categories_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        assert len(store.disabled_categories) > 0
        store.load_lines(SAMPLE_LINES)
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        assert folder_id in store.disabled_categories
        assert db_id in store.disabled_categories

    def test_disabled_category_skipped_if_removed_on_reload(self) -> None:
        """Category that no longer exists after reload is silently skipped."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.load_lines(["01-01-2024T08:00:00.100 other LOG_INFO hello"])
        assert store.disabled_categories == set()

    def test_new_category_enabled_by_default_on_reload(self) -> None:
        """Category not in disabled set is enabled after reload."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES[:2])
        store.disable_category("my_lib/core")
        store.load_lines(SAMPLE_LINES)
        core_id = store._category_name_to_id["my_lib/core"]
        assert core_id in store.disabled_categories
        system_id = store._category_name_to_id["SYSTEM"]
        assert system_id not in store.disabled_categories

    def test_clears_pins_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(1)
        store.pin_line(3)
        store.load_lines(SAMPLE_LINES)
        assert store.pinned_line_numbers == set()

    def test_clears_search_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.search("Failed", SearchMode.PLAIN, direction=SearchDirection.FORWARD)
        assert store.search_state is not None
        store.load_lines(SAMPLE_LINES)
        assert store.search_state is None

    def test_disabled_category_tree_nodes_match_set_on_reload(self) -> None:
        """Category tree node.enabled flags match disabled_categories after reload."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.load_lines(SAMPLE_LINES)
        my_app_node = store.category_tree.children["my_app"]
        assert my_app_node.enabled is False
        assert my_app_node.children["storage"].enabled is False

    def test_filtered_indices_correct_after_reload(self) -> None:
        """Filtered indices reflect preserved disabled categories."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.load_lines(SAMPLE_LINES)
        # my_app lines (1,2,3,5) hidden, only my_lib/core (0) and SYSTEM (4)
        assert set(store.filtered_indices.tolist()) == {0, 4}

    def test_leaf_priority_survives_reload(self) -> None:
        """A child re-enabled under a disabled parent stays enabled after reload."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.enable_category("my_app/storage/folder")
        # folder explicitly re-enabled under disabled my_app
        folder_node = (
            store.category_tree.children["my_app"]
            .children["storage"]
            .children["folder"]
        )
        assert folder_node.enabled is True
        store.load_lines(SAMPLE_LINES)
        # After reload, folder should still be enabled
        folder_node = (
            store.category_tree.children["my_app"]
            .children["storage"]
            .children["folder"]
        )
        assert folder_node.enabled is True
        # Parent still disabled
        assert store.category_tree.children["my_app"].enabled is False
