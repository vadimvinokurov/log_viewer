"""Unit tests for SelectionState and ViewportState models.

Ref: docs/specs/features/selection-preservation.md §4.2
Ref: docs/specs/features/selection-preservation.md §7.3
Master: docs/SPEC.md §1
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.models.selection_state import SelectionState, ViewportState
from src.views.log_table_view import LogEntryDisplay
from src.constants.log_levels import LogLevel


@pytest.fixture
def sample_entries() -> list[LogEntryDisplay]:
    """Create sample LogEntryDisplay entries for testing.

    Returns:
        List of LogEntryDisplay objects with distinct file_offset values.

    Ref: docs/specs/features/selection-preservation.md §4.2
    """
    return [
        LogEntryDisplay(
            category="System.Network",
            time="18:31:00.965",
            time_full="2024-01-15 18:31:00.965",
            level=LogLevel.ERROR,
            message="Connection failed",
            file_offset=0,
        ),
        LogEntryDisplay(
            category="System.Core",
            time="18:31:01.043",
            time_full="2024-01-15 18:31:01.043",
            level=LogLevel.WARNING,
            message="Memory warning",
            file_offset=100,
        ),
        LogEntryDisplay(
            category="App.UI",
            time="18:31:02.123",
            time_full="2024-01-15 18:31:02.123",
            level=LogLevel.MSG,
            message="User action",
            file_offset=200,
        ),
        LogEntryDisplay(
            category="App.Database",
            time="18:31:03.456",
            time_full="2024-01-15 18:31:03.456",
            level=LogLevel.DEBUG,
            message="Query executed",
            file_offset=300,
        ),
        LogEntryDisplay(
            category="System",
            time="18:31:04.789",
            time_full="2024-01-15 18:31:04.789",
            level=LogLevel.TRACE,
            message="Trace message",
            file_offset=400,
        ),
    ]


class TestSelectionStateCreation:
    """Tests for SelectionState creation and initialization.

    Ref: docs/specs/features/selection-preservation.md §4.2
    """

    def test_from_entries_creates_state_with_offsets(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """from_entries must extract file_offset values from entries.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        Style: Follows test pattern from tests/test_log_table_view.py
        """
        # Select entries at indices 0, 2, 4
        selected = [sample_entries[0], sample_entries[2], sample_entries[4]]
        
        state = SelectionState.from_entries(selected)
        
        # Verify offsets match selected entries
        assert 0 in state.offsets
        assert 200 in state.offsets
        assert 400 in state.offsets
        assert len(state.offsets) == 3

    def test_from_entries_empty_list_creates_empty_state(self) -> None:
        """from_entries with empty list must create empty SelectionState.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        state = SelectionState.from_entries([])
        
        assert state.is_empty()
        assert len(state.offsets) == 0

    def test_from_entries_sets_timestamp(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """from_entries must set timestamp to current time.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        before = datetime.now()
        state = SelectionState.from_entries([sample_entries[0]])
        after = datetime.now()
        
        assert before <= state.timestamp <= after

    def test_selection_state_is_frozen(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """SelectionState must be immutable (frozen dataclass).

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        state = SelectionState.from_entries([sample_entries[0]])
        
        with pytest.raises(AttributeError):
            state.offsets = frozenset({999})  # type: ignore[misc]

    def test_from_entries_with_current_entry(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """from_entries must store current_entry offset for keyboard navigation.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §5.1
        """
        # Select entries at indices 0, 2, 4, with current at index 2
        selected = [sample_entries[0], sample_entries[2], sample_entries[4]]
        current = sample_entries[2]
        
        state = SelectionState.from_entries(selected, current)
        
        # Verify current_offset is set
        assert state.current_offset == 200
        assert 200 in state.offsets

    def test_from_entries_without_current_entry(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """from_entries without current_entry must set current_offset to None.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §5.1
        """
        selected = [sample_entries[0], sample_entries[2]]
        
        state = SelectionState.from_entries(selected)
        
        # Verify current_offset is None when not provided
        assert state.current_offset is None

    def test_from_entries_current_entry_not_in_selection(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """from_entries can have current_entry different from selection.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §5.1
        """
        # Select entries at indices 0, 2
        selected = [sample_entries[0], sample_entries[2]]
        # Current entry is at index 1 (not in selection)
        current = sample_entries[1]
        
        state = SelectionState.from_entries(selected, current)
        
        # Verify current_offset is set even if not in selection
        assert state.current_offset == 100
        assert 100 not in state.offsets  # current not in selection


class TestSelectionStateIsEmpty:
    """Tests for SelectionState.is_empty method.

    Ref: docs/specs/features/selection-preservation.md §4.2
    """

    def test_is_empty_returns_true_for_empty_state(self) -> None:
        """is_empty must return True when no rows selected.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        state = SelectionState(offsets=frozenset())
        
        assert state.is_empty()

    def test_is_empty_returns_false_for_non_empty_state(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """is_empty must return False when rows are selected.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        state = SelectionState.from_entries([sample_entries[0]])
        
        assert not state.is_empty()


class TestSelectionStateRestoreIndices:
    """Tests for SelectionState.restore_indices method.

    Ref: docs/specs/features/selection-preservation.md §4.2
    """

    def test_restore_indices_returns_empty_for_no_matches(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices must return empty list when no offsets match.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        # Create state with offsets that don't exist in sample_entries
        state = SelectionState(offsets=frozenset({999, 1000}))
        
        indices = state.restore_indices(sample_entries)
        
        assert indices == []

    def test_restore_indices_returns_correct_indices(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices must return correct row indices for matching offsets.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        # Select entries at offsets 0, 200, 400 (indices 0, 2, 4)
        state = SelectionState(offsets=frozenset({0, 200, 400}))
        
        indices = state.restore_indices(sample_entries)
        
        assert indices == [0, 2, 4]

    def test_restore_indices_preserves_order(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices must return indices in ascending order.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        # Select entries in non-sequential order
        state = SelectionState(offsets=frozenset({400, 0, 200}))  # Unordered
        
        indices = state.restore_indices(sample_entries)
        
        # Indices should be in ascending order
        assert indices == [0, 2, 4]

    def test_restore_indices_with_subset_of_entries(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices must work with filtered subset of entries.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        # Select entries at offsets 100 and 300 (indices 1 and 3)
        state = SelectionState(offsets=frozenset({100, 300}))
        
        # Simulate filtered view with only entries at indices 1, 2, 3
        filtered_entries = [
            sample_entries[1],  # offset 100
            sample_entries[2],  # offset 200
            sample_entries[3],  # offset 300
        ]
        
        indices = state.restore_indices(filtered_entries)
        
        # Only offsets 100 and 300 should match (indices 0 and 2 in filtered view)
        assert indices == [0, 2]

    def test_restore_indices_empty_state_returns_empty_list(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices with empty state must return empty list.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        state = SelectionState(offsets=frozenset())
        
        indices = state.restore_indices(sample_entries)
        
        assert indices == []

    def test_restore_indices_all_entries_match(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices must handle case where all entries match.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §4.2
        """
        # Select all entries
        state = SelectionState.from_entries(sample_entries)
        
        indices = state.restore_indices(sample_entries)
        
        # All indices should be returned
        assert indices == [0, 1, 2, 3, 4]


class TestSelectionStatePerformance:
    """Tests for SelectionState performance characteristics.

    Ref: docs/specs/features/selection-preservation.md §4.2
    Ref: docs/specs/features/selection-preservation.md §6.1
    """

    def test_restore_indices_performance_linear(
        self, sample_entries: list[LogEntryDisplay]
    ) -> None:
        """restore_indices must be O(m) where m = number of new entries.

        This test verifies the implementation uses a set lookup
        rather than linear search.

        Args:
            sample_entries: Fixture providing sample entries.

        Ref: docs/specs/features/selection-preservation.md §6.1
        """
        import time
        
        # Create state with many offsets
        many_offsets = frozenset(range(0, 10000, 2))  # 5000 offsets
        state = SelectionState(offsets=many_offsets)
        
        # Create large entry list
        large_entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-15 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i,
            )
            for i in range(10000)
        ]
        
        # Measure time for restore_indices
        start = time.perf_counter()
        indices = state.restore_indices(large_entries)
        elapsed = time.perf_counter() - start
        
        # Should complete in reasonable time (< 100ms for 10K entries)
        assert elapsed < 0.1
        # Should find approximately half the entries
        assert len(indices) == 5000


class TestViewportStateCreation:
    """Tests for ViewportState creation and initialization.

    Ref: docs/specs/features/selection-preservation.md §7.3
    """

    def test_viewport_state_creation_with_required_fields(self) -> None:
        """ViewportState must be created with required fields.

        Ref: docs/specs/features/selection-preservation.md §7.3
        """
        state = ViewportState(selected_offset=100, viewport_offset=50)

        assert state.selected_offset == 100
        assert state.viewport_offset == 50
        assert state.row_height is None

    def test_viewport_state_with_optional_row_height(self) -> None:
        """ViewportState must accept optional row_height parameter.

        Ref: docs/specs/features/selection-preservation.md §7.3
        """
        state = ViewportState(selected_offset=200, viewport_offset=75, row_height=24)

        assert state.selected_offset == 200
        assert state.viewport_offset == 75
        assert state.row_height == 24

    def test_viewport_state_is_frozen(self) -> None:
        """ViewportState must be immutable (frozen dataclass).

        Ref: docs/specs/features/selection-preservation.md §7.3
        """
        state = ViewportState(selected_offset=0, viewport_offset=0)

        with pytest.raises(AttributeError):
            state.selected_offset = 100  # type: ignore[misc]

        with pytest.raises(AttributeError):
            state.viewport_offset = 50  # type: ignore[misc]

        with pytest.raises(AttributeError):
            state.row_height = 24  # type: ignore[misc]

    def test_viewport_state_zero_values(self) -> None:
        """ViewportState must accept zero values for offsets.

        Ref: docs/specs/features/selection-preservation.md §7.3
        """
        state = ViewportState(selected_offset=0, viewport_offset=0)

        assert state.selected_offset == 0
        assert state.viewport_offset == 0

    def test_viewport_state_negative_viewport_offset(self) -> None:
        """ViewportState must accept negative viewport_offset (row above viewport).

        Ref: docs/specs/features/selection-preservation.md §7.3
        """
        state = ViewportState(selected_offset=500, viewport_offset=-100)

        assert state.viewport_offset == -100

    def test_viewport_state_large_values(self) -> None:
        """ViewportState must handle large file offsets.

        Ref: docs/specs/features/selection-preservation.md §7.3
        """
        state = ViewportState(selected_offset=10_000_000, viewport_offset=500)

        assert state.selected_offset == 10_000_000
        assert state.viewport_offset == 500