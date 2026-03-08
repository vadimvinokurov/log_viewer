"""Clipboard operations."""
from __future__ import annotations

from typing import List

from PySide6.QtWidgets import QApplication


def copy_to_clipboard(text: str) -> None:
    """Copy text to clipboard.

    Args:
        text: Text to copy.
    """
    clipboard = QApplication.clipboard()
    if clipboard:
        clipboard.setText(text)


def copy_lines_to_clipboard(lines: List[str]) -> None:
    """Copy multiple lines to clipboard.

    Args:
        lines: List of lines to copy.
    """
    text = "\n".join(lines)
    copy_to_clipboard(text)