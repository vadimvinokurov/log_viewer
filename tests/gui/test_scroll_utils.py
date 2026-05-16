"""Tests for scroll_utils module."""

from PySide6.QtWidgets import QScrollArea

from log_viewer.gui.scroll_utils import install_hover_scrollbar


def test_install_hover_scrollbar_is_noop(qtbot):
    """install_hover_scrollbar should not crash and should be a no-op."""
    area = QScrollArea()
    qtbot.addWidget(area)
    area.resize(200, 200)
    install_hover_scrollbar(area)  # should not raise
