"""Search engine for navigating matches in log data."""

from __future__ import annotations

from bisect import bisect_left
from typing import Optional

import numpy as np

from log_viewer.core.models import Filter, SearchDirection, SearchMode, SearchState


class SearchEngine:
    """Handles search navigation across filtered log lines."""

    def __init__(self) -> None:
        self.search_state: Optional[SearchState] = None

    def search(
        self,
        store,  # LogStore
        pipeline,  # FilterPipeline
        pattern: str,
        mode: SearchMode,
        direction: SearchDirection = SearchDirection.FORWARD,
        start_line: int = 0,
    ) -> SearchState:
        """Find all matching lines among currently visible lines."""
        filt = Filter(pattern=pattern, mode=mode)
        mask = pipeline.compute_mask(store, filt)

        visible_mask = mask[store.filtered_indices]
        local_indices = np.where(visible_mask)[0]
        matches = store.filtered_indices[local_indices].tolist()

        start = 0
        if matches and direction == SearchDirection.BACKWARD:
            start = len(matches) - 1
        elif matches:
            idx = bisect_left(matches, start_line)
            start = 0 if idx == len(matches) else idx

        state = SearchState(
            pattern=pattern,
            mode=mode,
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
