import pytest
from log_viewer.gui.bottom_bar import BottomBar


@pytest.fixture
def bottom_bar(qtbot):
    bar = BottomBar()
    qtbot.addWidget(bar)
    bar.show()
    return bar


def test_bottom_bar_has_command_input(bottom_bar):
    assert bottom_bar.command_input is not None


def test_bottom_bar_has_status_label(bottom_bar):
    assert bottom_bar.status_label is not None


def test_bottom_bar_status_update(bottom_bar):
    bottom_bar.set_status("app.log | 5 lines")
    assert "app.log" in bottom_bar.status_label.text()
    assert "5 lines" in bottom_bar.status_label.text()


def test_bottom_bar_command_input_takes_focus(bottom_bar):
    bottom_bar.command_input.setFocus()
    assert bottom_bar.command_input.hasFocus()


def test_bottom_bar_activate_command_mode(bottom_bar):
    bottom_bar.activate_command_mode()
    assert bottom_bar.command_input.hasFocus()
    assert bottom_bar.command_input.text() == ":"
