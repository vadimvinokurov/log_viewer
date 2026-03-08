"""Tests for hover-scrollbar behavior."""

import pytest

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QScrollArea

from log_viewer.gui.scroll_utils import HoverScrollBarFilter


@pytest.fixture
def scroll_area(qtbot):
    area = QScrollArea()
    qtbot.addWidget(area)
    area.resize(200, 200)
    return area


def test_hover_sets_scrollbar_property(scroll_area):
    """Enter event should set _area_hovered=True on scrollbars."""
    filt = HoverScrollBarFilter()
    event = QEvent(QEvent.Type.Enter)
    filt.eventFilter(scroll_area, event)

    assert scroll_area.verticalScrollBar().property("_area_hovered") is True
    assert scroll_area.horizontalScrollBar().property("_area_hovered") is True


def test_leave_clears_scrollbar_property(scroll_area):
    """Leave event should set _area_hovered=False on scrollbars."""
    filt = HoverScrollBarFilter()
    enter = QEvent(QEvent.Type.Enter)
    leave = QEvent(QEvent.Type.Leave)
    filt.eventFilter(scroll_area, enter)
    filt.eventFilter(scroll_area, leave)

    assert scroll_area.verticalScrollBar().property("_area_hovered") is False


def test_default_property_is_none(scroll_area):
    """Before any hover, _area_hovered should be None (unset)."""
    assert scroll_area.verticalScrollBar().property("_area_hovered") is None
