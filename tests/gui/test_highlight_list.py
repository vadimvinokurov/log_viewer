import pytest

from log_viewer.core.models import Highlight, SearchMode
from log_viewer.gui.highlight_list import HighlightListWidget


@pytest.fixture
def highlight_list(qtbot):
    widget = HighlightListWidget()
    qtbot.addWidget(widget)
    return widget


def test_empty_highlight_list(highlight_list):
    assert highlight_list.count() == 0


def test_add_highlight(highlight_list):
    h = Highlight(pattern="error", mode=SearchMode.PLAIN, color="red")
    highlight_list.set_highlights([h])
    assert highlight_list.count() == 1


def test_remove_highlight(highlight_list):
    h = Highlight(pattern="error", mode=SearchMode.PLAIN, color="red")
    highlight_list.set_highlights([h])
    highlight_list.remove_highlight(0)
    assert highlight_list.count() == 0


def test_get_active_highlights(highlight_list):
    h1 = Highlight(pattern="error", mode=SearchMode.PLAIN, color="red")
    h2 = Highlight(pattern="200", mode=SearchMode.PLAIN, color="green")
    highlight_list.set_highlights([h1, h2])
    highlight_list.toggle_highlight(1, False)
    active = highlight_list.get_active_highlights()
    assert len(active) == 1
    assert active[0].pattern == "error"
