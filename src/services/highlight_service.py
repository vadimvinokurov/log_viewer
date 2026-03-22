"""Service for managing highlight patterns and combining highlight engines."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtGui import QColor

from src.constants.colors import UIColors
from src.core.highlight_engine import HighlightEngine, HighlightPattern


class HighlightService:
    """Service for managing highlight patterns.
    
    This service handles:
    - Managing user-defined highlight patterns
    - Combining multiple highlight engines (user + find)
    - Providing highlight engines for rendering
    
    The service is decoupled from the UI and can be tested independently.
    """
    
    def __init__(self) -> None:
        """Initialize the highlight service."""
        self._user_engine: HighlightEngine = HighlightEngine()
        self._find_engine: HighlightEngine = HighlightEngine()
        self._combined_engine: HighlightEngine = HighlightEngine()
        self._user_patterns: List[HighlightPattern] = []
    
    def add_user_pattern(
        self,
        pattern: str,
        color: QColor,
        is_regex: bool = False,
        enabled: bool = True
    ) -> None:
        """Add a user-defined highlight pattern.
        
        Args:
            pattern: Pattern text or regex.
            color: Highlight color.
            is_regex: Whether pattern is a regex.
            enabled: Whether pattern is enabled.
        """
        highlight_pattern = HighlightPattern(
            text=pattern,
            color=color,
            is_regex=is_regex,
            enabled=enabled
        )
        self._user_patterns.append(highlight_pattern)
        self._user_engine.add_pattern(highlight_pattern)
        self._update_combined()
    
    def remove_user_pattern(self, pattern: str) -> None:
        """Remove a user-defined highlight pattern.
        
        Args:
            pattern: Pattern text to remove.
        """
        self._user_patterns = [
            p for p in self._user_patterns if p.text != pattern
        ]
        self._user_engine.clear_patterns()
        for p in self._user_patterns:
            self._user_engine.add_pattern(p)
        self._update_combined()
    
    def set_user_patterns(self, patterns: List[HighlightPattern]) -> None:
        """Set all user patterns at once.
        
        Args:
            patterns: List of highlight patterns.
        """
        self._user_patterns = patterns.copy()
        self._user_engine.clear_patterns()
        for p in self._user_patterns:
            self._user_engine.add_pattern(p)
        self._update_combined()
    
    def set_find_pattern(
        self,
        text: str,
        color: QColor = QColor(UIColors.FIND_HIGHLIGHT),
        case_sensitive: bool = False
    ) -> None:
        """Set the find highlight pattern.
        
        Args:
            text: Text to find.
            color: Highlight color (default yellow).
            case_sensitive: Whether search is case-sensitive.
            
        Ref: docs/specs/global/color-palette.md §4.1 (UIColors.FIND_HIGHLIGHT)
        """
        self._find_engine.clear_patterns()
        if text:
            pattern = HighlightPattern(
                text=text,
                color=color,
                is_regex=False,
                enabled=True
            )
            self._find_engine.add_pattern(pattern)
        self._update_combined()
    
    def clear_find_pattern(self) -> None:
        """Clear the find highlight pattern."""
        self._find_engine.clear_patterns()
        self._update_combined()
    
    def get_combined_engine(self) -> HighlightEngine:
        """Get the combined highlight engine.
        
        Returns:
            HighlightEngine with all patterns combined.
        """
        return self._combined_engine
    
    def get_user_engine(self) -> HighlightEngine:
        """Get the user highlight engine.
        
        Returns:
            HighlightEngine with user patterns only.
        """
        return self._user_engine
    
    def get_find_engine(self) -> HighlightEngine:
        """Get the find highlight engine.
        
        Returns:
            HighlightEngine with find pattern only.
        """
        return self._find_engine
    
    def _update_combined(self) -> None:
        """Update the combined engine with all patterns."""
        self._combined_engine.clear_patterns()
        
        # Add user patterns first
        for pattern in self._user_patterns:
            if pattern.enabled:
                self._combined_engine.add_pattern(pattern)
        
        # Add find patterns
        for pattern in self._find_engine.get_patterns():
            if pattern.enabled:
                self._combined_engine.add_pattern(pattern)
    
    def clear_all(self) -> None:
        """Clear all patterns."""
        self._user_patterns.clear()
        self._user_engine.clear_patterns()
        self._find_engine.clear_patterns()
        self._combined_engine.clear_patterns()
    
    def get_user_patterns(self) -> List[HighlightPattern]:
        """Get all user patterns.
        
        Returns:
            Copy of user patterns list.
        """
        return self._user_patterns.copy()
    
    def has_highlights(self) -> bool:
        """Check if there are any active highlights.
        
        Returns:
            True if there are active highlights.
        """
        return bool(self._user_patterns) or bool(self._find_engine.get_patterns())