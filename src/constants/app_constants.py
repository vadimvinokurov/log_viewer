"""Application-wide constants for the Log Viewer application.

This module defines global application constants including window dimensions,
timeouts, and other application-level settings.
"""


# Timeouts
STATUS_MESSAGE_TIMEOUT: int = 3000
"""Duration in milliseconds for status bar messages to remain visible."""


# Application metadata
APPLICATION_NAME: str = "Log Viewer"
"""Display name of the application."""

APPLICATION_VERSION: str = "1.0.0"
"""Version string for the application."""


# File handling
MAX_RECENT_FILES: int = 10
"""Maximum number of recent files to track."""

FILE_WATCHER_DELAY: int = 500
"""Delay in milliseconds before processing file changes."""


# UI behavior
AUTO_SCROLL_ENABLED: bool = True
"""Default state for auto-scroll feature."""

DEFAULT_CASE_SENSITIVE: bool = False
"""Default state for case-sensitive search."""