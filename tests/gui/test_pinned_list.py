"""Tests for pinned_list.py — PinnedListWidget."""

from __future__ import annotations

import pytest

from log_viewer.core.models import LogLine, LogLevel
from log_viewer.gui.pinned_list import PinnedListWidget


def _make_line(number: int, message: str) -> LogLine:
    return LogLine(
        line_number=number,
        timestamp=f"08:00:00.{number:03d}",
        category="test",
        level=LogLevel.INFO,
        message=message,
        file_offset=number * 10,
        line_length=len(message) + 10,
    )


@pytest.fixture
def pinned_list(qtbot):
    widget = PinnedListWidget()
    qtbot.addWidget(widget)
    return widget


def test_empty_pinned_list(pinned_list):
    assert pinned_list.count() == 0


def test_set_pins_displays_items(pinned_list):
    lines = {2: _make_line(2, "error here"), 5: _make_line(5, "warning there")}
    pinned_list.set_pins([2, 5], lines)
    assert pinned_list.count() == 2


def test_remove_pin(pinned_list):
    lines = {2: _make_line(2, "error here"), 5: _make_line(5, "warning there")}
    pinned_list.set_pins([2, 5], lines)
    pinned_list.remove_pin(0)
    assert pinned_list.count() == 1


def test_remove_pin_emits_signal(pinned_list, qtbot):
    lines = {2: _make_line(2, "error here")}
    pinned_list.set_pins([2], lines)
    with qtbot.waitSignal(pinned_list.pin_removed, timeout=1000) as blocker:
        pinned_list.remove_pin(0)
    assert blocker.args == [2]
