"""Tests for LogStore."""

from __future__ import annotations

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
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_WARNING Missing file",
    "20-03-2026T12:20:42.258 PLATFORM win64",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_DEBUG Debug info",
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
        # Categories: LEECH/CORE, HordeMode/game_storage/folder,
        # HordeMode/game_storage/st_game_storage, PLATFORM
        assert "LEECH/CORE" in store.category_counts
        assert "HordeMode/game_storage/folder" in store.category_counts
        assert "HordeMode/game_storage/st_game_storage" in store.category_counts
        assert "PLATFORM" in store.category_counts

    def test_category_tree_root_has_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        root = store.category_tree
        assert "LEECH" in root.children
        assert "HordeMode" in root.children
        assert "PLATFORM" in root.children

    def test_category_tree_nested(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        horde = store.category_tree.children["HordeMode"]
        assert "game_storage" in horde.children
        gs = horde.children["game_storage"]
        assert "folder" in gs.children
        assert "st_game_storage" in gs.children

    def test_category_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert (
            store.category_counts["HordeMode/game_storage/folder"] == 2
        )  # ERROR + WARNING
        assert (
            store.category_counts["HordeMode/game_storage/st_game_storage"] == 2
        )  # ERROR + DEBUG
        assert store.category_counts["LEECH/CORE"] == 1
        assert store.category_counts["PLATFORM"] == 1

    def test_level_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.level_counts[LogLevel.ERROR] == 2
        assert store.level_counts[LogLevel.WARNING] == 1
        assert store.level_counts[LogLevel.INFO] == 2  # LEECH/CORE + PLATFORM
        assert store.level_counts[LogLevel.DEBUG] == 1

    def test_visible_level_counts_initially_equals_total(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.visible_level_counts == store.level_counts

    def test_filtered_indices_initially_all(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert store.filtered_indices == list(range(len(store.lines)))


class TestLogStoreEmpty:
    def test_empty_load(self) -> None:
        store = LogStore()
        store.load_lines([])
        assert len(store.lines) == 0
        assert store.category_counts == {}
        assert store.level_counts == {}
        assert store.filtered_indices == []

    def test_load_replaces_previous(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES[:2])
        assert len(store.lines) == 2

        store.load_lines(SAMPLE_LINES[3:])
        assert len(store.lines) == 3


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
            store.category_tree.children["HordeMode"]
            .children["game_storage"]
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
        store.add_filter(Filter(pattern="PLATFORM", mode=SearchMode.PLAIN))
        # Debug info line + PLATFORM line = 2
        assert len(store.filtered_indices) == 2

    def test_add_regex_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern=r"LOG_ERROR", mode=SearchMode.REGEX))
        assert len(store.filtered_indices) == 2  # Two ERROR lines

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
        f2 = Filter(pattern="PLATFORM", mode=SearchMode.PLAIN)
        store.add_filter(f1)
        store.add_filter(f2)
        assert len(store.filters) == 2

        store.remove_filter("Failed", case_sensitive=False)
        assert len(store.filters) == 1
        # Only PLATFORM line remains
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
        store.add_filter(Filter(pattern="PLATFORM", mode=SearchMode.PLAIN))
        store.clear_filters()
        assert len(store.filters) == 0
        # All lines visible again
        assert len(store.filtered_indices) == 6

    def test_filter_updates_visible_level_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN))
        assert store.visible_level_counts[LogLevel.ERROR] == 2
        assert store.visible_level_counts.get(LogLevel.WARNING, 0) == 0

    def test_clear_filter_restores_visible_counts(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN))
        store.clear_filters()
        assert store.visible_level_counts == store.level_counts

    def test_add_filter_no_match_shows_nothing(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="ZZZZNONEXISTENT", mode=SearchMode.PLAIN))
        assert len(store.filtered_indices) == 0


class TestLogStoreHighlights:
    """Test highlight add/remove/clear (display-only, no filtering)."""

    def test_add_highlight(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        h = Highlight(pattern="ERROR", mode=SearchMode.PLAIN, color="red")
        store.add_highlight(h)
        assert len(store.highlights) == 1

    def test_add_highlight_does_not_filter(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_highlight(Highlight(pattern="ERROR", mode=SearchMode.PLAIN, color="red"))
        # All lines still visible
        assert len(store.filtered_indices) == 6

    def test_remove_highlight(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        h = Highlight(pattern="ERROR", mode=SearchMode.PLAIN, color="red")
        store.add_highlight(h)
        store.remove_highlight("ERROR", case_sensitive=False, color="red")
        assert len(store.highlights) == 0

    def test_clear_highlights(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_highlight(Highlight(pattern="ERROR", mode=SearchMode.PLAIN, color="red"))
        store.add_highlight(Highlight(pattern="WARNING", mode=SearchMode.PLAIN, color="yellow"))
        store.clear_highlights()
        assert len(store.highlights) == 0


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
        state = store.search(r"LOG_ERROR|LOG_WARNING", SearchMode.REGEX, case_sensitive=False, direction=SearchDirection.FORWARD)
        # ERROR lines: 1, 2. WARNING line: 3
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
        # Filter to show only ERROR lines (indices 1, 2)
        store.add_filter(Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN))
        assert store.filtered_indices == [1, 2]
        # Search within filtered view
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        # Only indices 1 and 2 are visible, both contain "Failed"
        assert state.matches == [1, 2]

    def test_search_excludes_non_visible_lines(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        # Filter to show only PLATFORM line (index 4)
        store.add_filter(Filter(pattern="PLATFORM", mode=SearchMode.PLAIN))
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        # "Failed" is not in the PLATFORM line
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
        store.disable_category("HordeMode")
        assert store.category_tree.children["HordeMode"].enabled is False

    def test_disable_category_propagates_to_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        horde = store.category_tree.children["HordeMode"]
        gs = horde.children["game_storage"]
        assert gs.enabled is False
        assert gs.children["folder"].enabled is False
        assert gs.children["st_game_storage"].enabled is False

    def test_enable_category_sets_node_enabled(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        store.enable_category("HordeMode")
        assert store.category_tree.children["HordeMode"].enabled is True

    def test_enable_category_propagates_to_children(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        store.enable_category("HordeMode")
        horde = store.category_tree.children["HordeMode"]
        gs = horde.children["game_storage"]
        assert gs.enabled is True
        assert gs.children["folder"].enabled is True
        assert gs.children["st_game_storage"].enabled is True

    def test_leaf_priority_child_re_enabled_under_disabled_parent(self) -> None:
        """Explicit child enable overrides parent disable inheritance."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        # Re-enable just the leaf "folder" under disabled HordeMode
        store.enable_category("HordeMode/game_storage/folder")
        horde = store.category_tree.children["HordeMode"]
        assert horde.enabled is False
        assert horde.children["game_storage"].enabled is False
        # But the explicitly re-enabled leaf is True
        assert horde.children["game_storage"].children["folder"].enabled is True
        # Sibling stays disabled
        assert horde.children["game_storage"].children["st_game_storage"].enabled is False

    def test_disable_all_categories(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_all_categories()
        assert store.category_tree.children["HordeMode"].enabled is False
        assert store.category_tree.children["LEECH"].enabled is False
        assert store.category_tree.children["PLATFORM"].enabled is False

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
        gs = store.category_tree.children["HordeMode"].children["game_storage"]
        assert gs.children["folder"].enabled is True
        assert gs.children["st_game_storage"].enabled is True

    def test_disable_category_updates_filtered_indices(self) -> None:
        """Disabled category lines should be excluded from filtered view."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        assert len(store.filtered_indices) == 6
        store.disable_category("HordeMode")
        # HordeMode lines: indices 1,2,3,5 (4 lines)
        # Remaining: LEECH/CORE (0), PLATFORM (4)
        assert len(store.filtered_indices) == 2
        assert 0 in store.filtered_indices
        assert 4 in store.filtered_indices

    def test_enable_category_restores_filtered_indices(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        store.enable_category("HordeMode")
        assert len(store.filtered_indices) == 6

    def test_category_filter_combined_with_text_filter(self) -> None:
        """Category + text filter both active simultaneously."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN))
        # 2 ERROR lines (indices 1,2)
        assert len(store.filtered_indices) == 2
        # Now also disable HordeMode — those ERROR lines are in HordeMode
        store.disable_category("HordeMode")
        # No ERROR lines visible outside HordeMode
        assert len(store.filtered_indices) == 0

    def test_disable_leaf_category_only_affects_that_leaf(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode/game_storage/folder")
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
        store.disable_category("HordeMode")
        # Remaining levels: LEECH/CORE (INFO), PLATFORM (INFO)
        assert store.visible_level_counts.get(LogLevel.INFO, 0) == 2
        assert store.visible_level_counts.get(LogLevel.ERROR, 0) == 0

    def test_category_affects_search_scope(self) -> None:
        """Search operates within category-filtered view."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        # "Failed" only exists in HordeMode lines
        state = store.search("Failed", SearchMode.PLAIN, case_sensitive=False, direction=SearchDirection.FORWARD)
        assert state.matches == []

    def test_leaf_enable_under_disabled_parent_shows_in_filtered(self) -> None:
        """Re-enabled leaf under disabled parent should appear in filtered_indices."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("HordeMode")
        store.enable_category("HordeMode/game_storage/folder")
        # folder has 2 lines (indices 1,3)
        # Plus LEECH/CORE (0) and PLATFORM (4) which are still enabled
        assert len(store.filtered_indices) == 4
        assert 1 in store.filtered_indices
        assert 3 in store.filtered_indices
