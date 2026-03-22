"""Text highlighting engine."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from PySide6.QtGui import QColor


@dataclass
class HighlightPattern:
    """A highlight pattern definition."""
    text: str
    color: QColor
    is_regex: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate pattern after initialization."""
        if not self.text:
            raise ValueError("Pattern text cannot be empty")


@dataclass
class HighlightRange:
    """A highlighted range in text."""
    start: int
    end: int
    color: QColor

    def __lt__(self, other: HighlightRange) -> bool:
        """Compare by start position for sorting."""
        return self.start < other.start


class HighlightEngine:
    """Engine for text highlighting."""

    def __init__(self) -> None:
        """Initialize the highlight engine."""
        self._patterns: List[HighlightPattern] = []

    def add_pattern(self, pattern: HighlightPattern) -> None:
        """Add a highlight pattern.

        Args:
            pattern: The highlight pattern to add.
        """
        self._patterns.append(pattern)

    def remove_pattern(self, index: int) -> None:
        """Remove a pattern by index.

        Args:
            index: Index of the pattern to remove.

        Raises:
            IndexError: If index is out of range.
        """
        if 0 <= index < len(self._patterns):
            del self._patterns[index]
        else:
            raise IndexError(f"Pattern index {index} out of range")

    def clear_patterns(self) -> None:
        """Remove all patterns."""
        self._patterns.clear()

    def get_patterns(self) -> List[HighlightPattern]:
        """Get all patterns.

        Returns:
            Copy of the patterns list.
        """
        return self._patterns.copy()

    def set_patterns(self, patterns: List[HighlightPattern]) -> None:
        """Replace all patterns.

        Args:
            patterns: New list of patterns.
        """
        self._patterns = patterns.copy()

    def highlight(self, text: str) -> List[HighlightRange]:
        """Find all highlight ranges in text.

        Args:
            text: Text to highlight.

        Returns:
            List of HighlightRange sorted by start position.
        """
        if not text:
            return []

        ranges: List[HighlightRange] = []

        for pattern in self._patterns:
            if not pattern.enabled:
                continue

            try:
                if pattern.is_regex:
                    ranges.extend(self._find_regex_matches(text, pattern))
                else:
                    ranges.extend(self._find_text_matches(text, pattern))
            except re.error:
                # Skip invalid regex patterns
                continue

        # Sort by start position and merge overlapping ranges
        return self._merge_overlapping_ranges(sorted(ranges))

    def _find_text_matches(self, text: str, pattern: HighlightPattern) -> List[HighlightRange]:
        """Find all text matches (case-insensitive substring).

        Args:
            text: Text to search in.
            pattern: Pattern to search for.

        Returns:
            List of highlight ranges.
        """
        ranges: List[HighlightRange] = []
        search_text = text.lower()
        pattern_text = pattern.text.lower()

        start = 0
        while True:
            pos = search_text.find(pattern_text, start)
            if pos == -1:
                break
            ranges.append(HighlightRange(
                start=pos,
                end=pos + len(pattern_text),
                color=pattern.color
            ))
            start = pos + 1  # Allow overlapping matches

        return ranges

    def _find_regex_matches(self, text: str, pattern: HighlightPattern) -> List[HighlightRange]:
        """Find all regex matches.

        Args:
            text: Text to search in.
            pattern: Pattern with regex to search for.

        Returns:
            List of highlight ranges.
        """
        ranges: List[HighlightRange] = []

        try:
            regex = re.compile(pattern.text, re.IGNORECASE)
            for match in regex.finditer(text):
                ranges.append(HighlightRange(
                    start=match.start(),
                    end=match.end(),
                    color=pattern.color
                ))
        except re.error:
            pass

        return ranges

    def _merge_overlapping_ranges(self, ranges: List[HighlightRange]) -> List[HighlightRange]:
        """Merge overlapping highlight ranges.

        When ranges overlap, the later range takes precedence (overwrites).

        Args:
            ranges: Sorted list of highlight ranges.

        Returns:
            Merged list of non-overlapping ranges.
        """
        if not ranges:
            return []

        # Simple approach: later ranges overwrite earlier ones
        # For each position, track which color applies
        result: List[HighlightRange] = []

        for current in ranges:
            # Check if this range overlaps with any existing result
            merged = False
            new_result: List[HighlightRange] = []

            for existing in result:
                if merged:
                    new_result.append(existing)
                    continue

                # Check for overlap
                if current.end <= existing.start:
                    # Current is before existing, no overlap
                    new_result.append(current)
                    new_result.append(existing)
                    merged = True
                elif current.start >= existing.end:
                    # Current is after existing, no overlap
                    new_result.append(existing)
                else:
                    # Overlap - split existing range
                    # Part before current
                    if existing.start < current.start:
                        new_result.append(HighlightRange(
                            start=existing.start,
                            end=current.start,
                            color=existing.color
                        ))
                    # Current range (takes precedence)
                    new_result.append(current)
                    # Part after current
                    if current.end < existing.end:
                        new_result.append(HighlightRange(
                            start=current.end,
                            end=existing.end,
                            color=existing.color
                        ))
                    merged = True

            if not merged:
                new_result.append(current)

            result = sorted(new_result)

        return result