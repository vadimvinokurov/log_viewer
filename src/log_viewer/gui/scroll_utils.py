"""Scrollbar utilities for scroll areas."""

from __future__ import annotations

from PySide6.QtWidgets import QAbstractScrollArea


def install_hover_scrollbar(widget: QAbstractScrollArea) -> None:
    """No-op placeholder kept for API compatibility.

    Scrollbars now use the native system style instead of a custom overlay QSS.
    """
    pass
