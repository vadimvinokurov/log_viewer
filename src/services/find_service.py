"""Service for find/search functionality in log entries."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtGui import QColor

from src.constants.colors import UIColors
from src.core.highlight_engine import HighlightEngine, HighlightPattern


@dataclass
class FindMatch:
    """A single find match location."""
    row: int
    column: int
    start: int
    end: int


class FindService:
    """Service for finding text in log entries.
    
    This service handles:
    - Finding text in log entries (case-sensitive or insensitive)
    - Navigating between matches (next/previous)
    - Highlighting matches using HighlightEngine
    
    The service is decoupled from the UI and can be tested independently.
    """
    
    def __init__(self) -> None:
        """Initialize the find service."""
        self._matches: List[FindMatch] = []
        self._current_match: int = -1
        self._find_text: str = ""
        self._find_case_sensitive: bool = False
        self._find_engine: HighlightEngine = HighlightEngine()
    
    def find_text(
        self,
        text: str,
        entries: List,
        case_sensitive: bool = False
    ) -> int:
        """Find text in log entries.
        
        Args:
            text: Text to search for.
            entries: List of log entries to search in.
            case_sensitive: Whether search is case-sensitive.
            
        Returns:
            Number of matches found.
        """
        if not text:
            self.clear()
            return 0
        
        self._find_text = text
        self._find_case_sensitive = case_sensitive
        self._matches.clear()
        self._current_match = -1
        
        # Compile regex pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(re.escape(text), flags)
        except re.error:
            return 0
        
        # Search in all entries
        for row, entry in enumerate(entries):
            # Get cell texts for each column
            cell_texts = self._get_cell_texts(entry)
            for col, cell_text in enumerate(cell_texts):
                for match in pattern.finditer(cell_text):
                    self._matches.append(FindMatch(
                        row=row,
                        column=col,
                        start=match.start(),
                        end=match.end()
                    ))
        
        # Navigate to first match if any
        if self._matches:
            self._current_match = 0
        
        return len(self._matches)
    
    def _get_cell_texts(self, entry) -> List[str]:
        """Get cell texts for an entry.
        
        Args:
            entry: Log entry to get texts from.
            
        Returns:
            List of cell texts (time, system, type, message).
        """
        # Handle LogEntryDisplay or similar
        if hasattr(entry, 'time') and hasattr(entry, 'system'):
            return [
                entry.time,
                entry.system,
                entry.level_icon if hasattr(entry, 'level_icon') else str(entry.level),
                entry.message
            ]
        # Fallback for other entry types
        return [str(entry)]
    
    def find_next(self) -> Optional[FindMatch]:
        """Navigate to next match.
        
        Returns:
            Next match or None if no matches.
        """
        if not self._matches:
            return None
        
        self._current_match = (self._current_match + 1) % len(self._matches)
        return self._matches[self._current_match]
    
    def find_previous(self) -> Optional[FindMatch]:
        """Navigate to previous match.
        
        Returns:
            Previous match or None if no matches.
        """
        if not self._matches:
            return None
        
        self._current_match = (self._current_match - 1) % len(self._matches)
        return self._matches[self._current_match]
    
    def get_current_match(self) -> Optional[FindMatch]:
        """Get current match.
        
        Returns:
            Current match or None if no match selected.
        """
        if 0 <= self._current_match < len(self._matches):
            return self._matches[self._current_match]
        return None
    
    def get_match_count(self) -> int:
        """Get number of matches.
        
        Returns:
            Number of matches found.
        """
        return len(self._matches)
    
    def get_current_match_index(self) -> int:
        """Get current match index (1-based for display).
        
        Returns:
            Current match index (1-based) or 0 if no match.
        """
        if self._current_match >= 0:
            return self._current_match + 1
        return 0
    
    def get_highlight_engine(self, highlight_color: QColor = QColor(UIColors.FIND_HIGHLIGHT)) -> HighlightEngine:
        """Get highlight engine with find pattern.
        
        Args:
            highlight_color: Color for highlighting matches.
            
        Returns:
            HighlightEngine configured with find pattern.
            
        Ref: docs/specs/global/color-palette.md §4.1 (UIColors.FIND_HIGHLIGHT)
        """
        self._find_engine.clear_patterns()
        if self._find_text:
            pattern = HighlightPattern(
                text=self._find_text,
                color=highlight_color,
                is_regex=False,
                enabled=True
            )
            self._find_engine.add_pattern(pattern)
        return self._find_engine
    
    def clear(self) -> None:
        """Clear all matches and reset state."""
        self._matches.clear()
        self._current_match = -1
        self._find_text = ""
        self._find_engine.clear_patterns()
    
    def has_matches(self) -> bool:
        """Check if there are any matches.
        
        Returns:
            True if there are matches.
        """
        return len(self._matches) > 0
    
    def get_find_text(self) -> str:
        """Get the current find text.
        
        Returns:
            Current find text or empty string if not set.
        """
        return self._find_text
    
    def is_case_sensitive(self) -> bool:
        """Check if search is case-sensitive.
        
        Returns:
            True if case-sensitive.
        """
        return self._find_case_sensitive
    
    def get_match_at(self, index: int) -> Optional[FindMatch]:
        """Get match at specific index.
        
        Args:
            index: Index of match to get.
            
        Returns:
            Match at index or None if index is invalid.
        """
        if 0 <= index < len(self._matches):
            return self._matches[index]
        return None