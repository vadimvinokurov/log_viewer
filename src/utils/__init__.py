"""Utils package."""
from src.utils.settings_manager import (
    SettingsManager,
    AppSettings,
    CustomCategory,
    HighlightPatternData
)
from src.utils.clipboard import copy_to_clipboard, copy_lines_to_clipboard

__all__ = [
    "SettingsManager",
    "AppSettings",
    "CustomCategory",
    "HighlightPatternData",
    "copy_to_clipboard",
    "copy_lines_to_clipboard",
]