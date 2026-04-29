import pytest

from log_viewer.core.models import Filter, SearchMode
from log_viewer.gui.filter_list import FilterListWidget


@pytest.fixture
def filter_list(qtbot):
    widget = FilterListWidget()
    qtbot.addWidget(widget)
    return widget


def test_empty_filter_list(filter_list):
    assert filter_list.count() == 0


def test_add_filter(filter_list):
    f = Filter(pattern="error", mode=SearchMode.PLAIN)
    filter_list.set_filters([f])
    assert filter_list.count() == 1


def test_remove_filter(filter_list):
    f = Filter(pattern="error", mode=SearchMode.PLAIN)
    filter_list.set_filters([f])
    filter_list.remove_filter(0)
    assert filter_list.count() == 0


def test_toggle_filter(filter_list):
    f = Filter(pattern="error", mode=SearchMode.PLAIN)
    filter_list.set_filters([f])
    filter_list.toggle_filter(0, False)
    assert filter_list.count() == 1


def test_get_active_filters(filter_list):
    f1 = Filter(pattern="error", mode=SearchMode.PLAIN)
    f2 = Filter(pattern="timeout", mode=SearchMode.REGEX)
    filter_list.set_filters([f1, f2])
    filter_list.toggle_filter(1, False)
    active = filter_list.get_active_filters()
    assert len(active) == 1
    assert active[0].pattern == "error"
