"""Tests for pinned_list.py — PinnedListWidget."""

from __future__ import annotations

import pytest

from log_viewer.core.models import Filter, SearchMode
from log_viewer.gui.pinned_list import PinnedListWidget


@pytest.fixture
def pinned_list(qtbot):
    widget = PinnedListWidget()
    qtbot.addWidget(widget)
    return widget


def test_empty_pinned_list(pinned_list):
    assert pinned_list.count() == 0


def test_set_pins_displays_items(pinned_list):
    rules = [
        Filter(pattern="error", mode=SearchMode.PLAIN),
        Filter(pattern="^warn", mode=SearchMode.REGEX),
    ]
    pinned_list.set_pins(rules)
    assert pinned_list.count() == 2


def test_remove_pin(pinned_list):
    rules = [
        Filter(pattern="error", mode=SearchMode.PLAIN),
        Filter(pattern="^warn", mode=SearchMode.REGEX),
    ]
    pinned_list.set_pins(rules)
    pinned_list.remove_pin(0)
    assert pinned_list.count() == 1


def test_remove_pin_emits_signal(pinned_list, qtbot):
    rules = [Filter(pattern="error", mode=SearchMode.PLAIN)]
    pinned_list.set_pins(rules)
    with qtbot.waitSignal(pinned_list.pin_removed, timeout=1000) as blocker:
        pinned_list.remove_pin(0)
    assert blocker.args == [0]
