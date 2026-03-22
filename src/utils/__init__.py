"""Utils package."""
from src.utils.settings_manager import (
    SettingsManager,
    AppSettings,
    HighlightPatternData
)
from src.utils.clipboard import copy_to_clipboard, copy_lines_to_clipboard

__all__ = [
    "SettingsManager",
    "AppSettings",
    "HighlightPatternData",
    "copy_to_clipboard",
    "copy_lines_to_clipboard",
]