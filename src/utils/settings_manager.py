"""Settings persistence manager."""
from __future__ import annotations

import json
import logging
import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QByteArray

logger = logging.getLogger(__name__)


# Ref: docs/specs/features/custom-categories-removal.md §3.5
# CustomCategory dataclass removed - feature deprecated

@dataclass
class HighlightPatternData:
    """Highlight pattern for serialization."""
    text: str
    color_hex: str  # Store as hex string
    is_regex: bool = False
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "color_hex": self.color_hex,
            "is_regex": self.is_regex,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HighlightPatternData:
        """Create from dictionary."""
        return cls(
            text=data.get("text", ""),
            color_hex=data.get("color_hex", "#FFFF00"),
            is_regex=data.get("is_regex", False),
            enabled=data.get("enabled", True)
        )


@dataclass
class AppSettings:
    """Application settings."""
    # Ref: docs/specs/features/custom-categories-removal.md §3.5
    # custom_categories field removed - feature deprecated
    highlight_patterns: List[HighlightPatternData] = field(default_factory=list)
    last_file: Optional[str] = None
    window_geometry: Optional[bytes] = None
    column_widths: Dict[str, int] = field(default_factory=dict)
    # Ref: docs/specs/features/category-checkbox-behavior.md §5.1, §5.2, §5.3
    # Per-file category states: {filepath: {category_path: checked}}
    category_states_by_file: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    # Current file path for context (optional, for tracking active file)
    current_file: Optional[str] = None
    # Ref: docs/specs/features/saved-filters.md §6.1
    saved_filters: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1
        return {
            "highlight_patterns": [pat.to_dict() for pat in self.highlight_patterns],
            "last_file": self.last_file,
            "window_geometry": self.window_geometry.hex() if self.window_geometry else None,
            "column_widths": self.column_widths,
            "category_states_by_file": self.category_states_by_file,
            "current_file": self.current_file,
            "saved_filters": self.saved_filters
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppSettings:
        """Create from dictionary.
        
        Backward compatibility: ignores unknown 'custom_categories' field
        if present in older settings files.
        
        Migration: converts old 'category_states' format to new 
        'category_states_by_file' format.
        """
        # Ref: docs/specs/features/custom-categories-removal.md §6.1
        # Ignore custom_categories field for backward compatibility
        # (older settings files may contain this field)
        
        highlight_patterns = [
            HighlightPatternData.from_dict(pat)
            for pat in data.get("highlight_patterns", [])
        ]

        # Parse window geometry from hex string
        window_geometry = None
        geometry_hex = data.get("window_geometry")
        if geometry_hex and isinstance(geometry_hex, str):
            try:
                window_geometry = bytes.fromhex(geometry_hex)
            except ValueError:
                logger.warning("Failed to parse window geometry from settings")

        # Ref: docs/specs/features/category-checkbox-behavior.md §5.1, §5.3
        # Handle migration from old category_states format
        old_states = data.get("category_states", {})
        new_states = data.get("category_states_by_file", {})
        
        if old_states and not new_states:
            # Migrate: use last_file as key
            last_file = data.get("last_file")
            if last_file and old_states:
                new_states = {last_file: old_states}
                logger.info(f"Migrated category_states to category_states_by_file for {last_file}")

        return cls(
            highlight_patterns=highlight_patterns,
            last_file=data.get("last_file"),
            window_geometry=window_geometry,
            column_widths=data.get("column_widths", {}),
            category_states_by_file=new_states,
            current_file=data.get("current_file"),
            saved_filters=data.get("saved_filters", [])
        )


class SettingsManager:
    """Manager for application settings."""

    @staticmethod
    def _get_platform_settings_path() -> Path:
        """Get platform-specific settings directory.
        
        Ref: docs/specs/features/settings-persistence-fix.md §2.1
        
        Returns:
            Path to the settings.json file.
            
        Platform locations:
            - macOS: ~/Library/Application Support/Log Viewer/settings.json
            - Windows: %APPDATA%/LogViewer/settings.json
            - Linux: ~/.config/LogViewer/settings.json
        
        The directory is created if it doesn't exist.
        """
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # ~/Library/Application Support/Log Viewer/
            base = Path.home() / "Library" / "Application Support" / "Log Viewer"
        elif system == "Windows":
            # %APPDATA%/LogViewer/
            appdata = os.environ.get("APPDATA")
            if appdata:
                base = Path(appdata) / "LogViewer"
            else:
                # Fallback if APPDATA not set
                base = Path.home() / "AppData" / "Roaming" / "LogViewer"
        else:  # Linux and others
            # ~/.config/LogViewer/
            base = Path.home() / ".config" / "LogViewer"
        
        # Ensure directory exists
        try:
            base.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to temp directory if permission denied
            import tempfile
            base = Path(tempfile.gettempdir()) / "LogViewer"
            base.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback settings location: {base}")
        
        return base / "settings.json"

    def __init__(self, filepath: str | None = None) -> None:
        """Initialize the settings manager.

        Ref: docs/specs/features/settings-persistence-fix.md §2.2
        
        Args:
            filepath: Path to the settings file. If None, uses platform-specific default.
        """
        if filepath is None:
            self.filepath = self._get_platform_settings_path()
        else:
            self.filepath = Path(filepath)
        
        self._settings = AppSettings()
        
        # Ref: docs/specs/features/settings-persistence-fix.md §2.3
        # Migrate from old location if needed
        self._migrate_from_old_location()

    def _migrate_from_old_location(self) -> None:
        """Migrate settings from old location if exists.
        
        Ref: docs/specs/features/settings-persistence-fix.md §2.3
        
        Checks for settings.json in current directory (old location)
        and migrates to new platform-specific location.
        """
        old_path = Path("settings.json")
        if old_path.exists() and not self.filepath.exists():
            try:
                # Copy old settings to new location
                shutil.copy2(old_path, self.filepath)
                logger.info(f"Migrated settings from {old_path} to {self.filepath}")
                
                # Optionally remove old file (commented out for safety)
                # old_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to migrate settings: {e}")

    def load(self) -> AppSettings:
        """Load settings from file.

        If the file doesn't exist or is corrupt, returns default settings.

        Returns:
            Loaded or default AppSettings.
        """
        if not self.filepath.exists():
            logger.info(f"Settings file not found: {self.filepath}, using defaults")
            return self._settings

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._settings = AppSettings.from_dict(data)
            logger.info(f"Loaded settings from {self.filepath}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse settings file: {e}, using defaults")
            self._settings = AppSettings()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}, using defaults")
            self._settings = AppSettings()

        return self._settings

    def save(self) -> None:
        """Save settings to file."""
        try:
            # Ensure parent directory exists
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._settings.to_dict(), f, indent=2)
            logger.info(f"Saved settings to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings

    # Ref: docs/specs/features/custom-categories-removal.md §3.5
    # Custom category methods removed:
    # - add_custom_category()
    # - remove_custom_category()
    # - get_custom_categories()

    def add_highlight_pattern(self, pattern: HighlightPatternData) -> None:
        """Add a highlight pattern.

        Args:
            pattern: The highlight pattern to add.
        """
        self._settings.highlight_patterns.append(pattern)

    def remove_highlight_pattern(self, index: int) -> bool:
        """Remove a highlight pattern by index.

        Args:
            index: Index of the pattern to remove.

        Returns:
            True if pattern was removed, False if index out of range.
        """
        if 0 <= index < len(self._settings.highlight_patterns):
            del self._settings.highlight_patterns[index]
            return True
        return False

    def get_highlight_patterns(self) -> List[HighlightPatternData]:
        """Get all highlight patterns.

        Returns:
            Copy of the highlight patterns list.
        """
        return self._settings.highlight_patterns.copy()

    def set_last_file(self, filepath: str) -> None:
        """Set last opened file.

        Args:
            filepath: Path to the last opened file.
        """
        self._settings.last_file = filepath

    def set_window_geometry(self, geometry: QByteArray) -> None:
        """Set window geometry.

        Args:
            geometry: Window geometry as QByteArray.
        """
        self._settings.window_geometry = bytes(geometry)

    def get_window_geometry(self) -> Optional[QByteArray]:
        """Get window geometry as QByteArray.

        Returns:
            Window geometry or None if not set.
        """
        if self._settings.window_geometry:
            return QByteArray(self._settings.window_geometry)
        return None

    def set_column_widths(self, widths: Dict[str, int]) -> None:
        """Set column widths.

        Args:
            widths: Dictionary of column name to width.
        """
        self._settings.column_widths = widths.copy()

    def get_column_widths(self) -> Dict[str, int]:
        """Get column widths.

        Returns:
            Copy of column widths dictionary.
        """
        return self._settings.column_widths.copy()

    def set_category_states(self, filepath: str, states: Dict[str, bool]) -> None:
        """Set category checkbox states for a specific file.
        
        Ref: docs/specs/features/category-checkbox-behavior.md §5.1, §5.2

        Args:
            filepath: Path to the log file.
            states: Dictionary of category path to checked state.
        """
        self._settings.category_states_by_file[filepath] = states.copy()

    def get_category_states(self, filepath: str) -> Dict[str, bool]:
        """Get category checkbox states for a specific file.
        
        Ref: docs/specs/features/category-checkbox-behavior.md §5.1, §5.3

        Args:
            filepath: Path to the log file.
            
        Returns:
            Dictionary of category path to checked state.
            Empty dict if no saved state for this file (all categories default to checked).
        """
        return self._settings.category_states_by_file.get(filepath, {}).copy()
    
    def save_saved_filters(self, filters_data: List[Dict[str, Any]]) -> None:
        """Save saved filters to settings.
        
        # Ref: docs/specs/features/saved-filters.md §6.1
        
        Args:
            filters_data: List of filter dictionaries with keys:
                - id: str
                - name: str
                - filter_text: str
                - filter_mode: str
                - created_at: float
                - enabled: bool
        """
        self._settings.saved_filters = filters_data.copy()
    
    def load_saved_filters(self) -> List[Dict[str, Any]]:
        """Load saved filters from settings.
        
        # Ref: docs/specs/features/saved-filters.md §6.1
        
        Returns:
            List of filter dictionaries, empty list if not set.
        """
        return self._settings.saved_filters.copy()