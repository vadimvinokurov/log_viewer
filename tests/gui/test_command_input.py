"""Tests for CommandInput history navigation."""

from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtCore import Qt

from log_viewer.core.command_history import CommandHistory
from log_viewer.core.config import ConfigManager
from log_viewer.gui.command_input import CommandInput


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / ".logviewer"


@pytest.fixture
def cm(config_dir: Path) -> ConfigManager:
    manager = ConfigManager(config_dir=config_dir)
    manager.load()
    return manager


@pytest.fixture
def history(cm: ConfigManager) -> CommandHistory:
    return CommandHistory(cm)


@pytest.fixture
def cmd_input(qtbot, history: CommandHistory):
    widget = CommandInput(history=history)
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_up_arrow_navigates_history(cmd_input, history, qtbot):
    history.add(":f error")
    history.add(":h fail")
    qtbot.keyPress(cmd_input, Qt.Key.Key_Up)
    assert cmd_input.text() == ":h fail"
    qtbot.keyPress(cmd_input, Qt.Key.Key_Up)
    assert cmd_input.text() == ":f error"


def test_down_arrow_navigates_forward(cmd_input, history, qtbot):
    history.add(":a")
    history.add(":b")
    qtbot.keyPress(cmd_input, Qt.Key.Key_Up)
    qtbot.keyPress(cmd_input, Qt.Key.Key_Up)
    qtbot.keyPress(cmd_input, Qt.Key.Key_Down)
    assert cmd_input.text() == ":b"


def test_down_arrow_past_end_clears(cmd_input, history, qtbot):
    history.add(":a")
    qtbot.keyPress(cmd_input, Qt.Key.Key_Up)
    qtbot.keyPress(cmd_input, Qt.Key.Key_Down)
    assert cmd_input.text() == ""


def test_escape_clears_and_emits_editing_finished(cmd_input, qtbot):
    cmd_input.setText(":some text")
    with qtbot.waitSignal(cmd_input.editing_finished):
        qtbot.keyPress(cmd_input, Qt.Key.Key_Escape)
    assert cmd_input.text() == ""


def test_return_submits_and_adds_to_history(cmd_input, history, qtbot):
    cmd_input.setText(":f error")
    with qtbot.waitSignal(cmd_input.command_submitted) as blocker:
        qtbot.keyPress(cmd_input, Qt.Key.Key_Return)
    assert blocker.args == [":f error"]
    assert history.commands == [":f error"]
    assert cmd_input.text() == ""


def test_return_emits_editing_finished(cmd_input, qtbot):
    cmd_input.setText(":f error")
    with qtbot.waitSignal(cmd_input.editing_finished):
        qtbot.keyPress(cmd_input, Qt.Key.Key_Return)
