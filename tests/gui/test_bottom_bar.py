from __future__ import annotations

import pytest

from log_viewer.core.models import LogLevel
from log_viewer.gui.bottom_bar import BottomBar


@pytest.fixture
def bottom_bar(qtbot):
    bar = BottomBar()
    qtbot.addWidget(bar)
    bar.show()
    return bar


def test_bottom_bar_has_command_input(bottom_bar):
    assert bottom_bar.command_input is not None


def test_bottom_bar_has_level_bar(bottom_bar):
    assert bottom_bar.level_bar is not None


def test_level_bar_has_six_buttons(bottom_bar):
    assert len(bottom_bar.level_bar._buttons) == 6


def test_level_bar_set_counts(bottom_bar):
    counts = {
        LogLevel.CRITICAL: 1,
        LogLevel.ERROR: 5,
        LogLevel.WARNING: 10,
        LogLevel.INFO: 200,
        LogLevel.DEBUG: 3,
        LogLevel.TRACE: 0,
    }
    bottom_bar.level_bar.set_counts(counts)
    # Each button text should contain its count
    assert "1" in bottom_bar.level_bar._buttons[0].text()
    assert "200" in bottom_bar.level_bar._buttons[3].text()


def test_level_bar_click_emits_signal(bottom_bar):
    clicked_levels = []
    bottom_bar.level_bar.level_clicked.connect(lambda lvl: clicked_levels.append(lvl))
    # Simulate click on first button (CRITICAL)
    btn = bottom_bar.level_bar._buttons[0]
    btn.clicked.emit()
    assert clicked_levels == [LogLevel.CRITICAL]


def test_level_bar_set_active_state(bottom_bar):
    bottom_bar.level_bar.set_level_active(LogLevel.ERROR, False)
    btn = bottom_bar.level_bar._buttons[1]
    assert btn.property("level_active") is False


def test_bottom_bar_activate_command_mode(bottom_bar):
    bottom_bar.activate_command_mode()
    assert bottom_bar.command_input.text() == ":"
