"""Tests for autocomplete integration."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from log_viewer.gui.app import MainWindow


@pytest.fixture
def main_window(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    return win


def test_autocomplete_suggestions_on_open_command(main_window):
    main_window.bottom_bar.command_input.setText(":open /")
    text = main_window.bottom_bar.command_input.text()
    suggestions = main_window._suggester.get_all_suggestions(text)
    # Should get file suggestions starting with :open /
    assert all(s.startswith(":open ") for s in suggestions)


def test_autocomplete_no_suggestions_for_non_colon(main_window):
    suggestions = main_window._suggester.get_all_suggestions("hello")
    assert suggestions == []


def test_autocomplete_category_suggestions(main_window):
    main_window.log_store.load_lines(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main test",
            "2025-01-01T10:00:01 LOG_ERROR app/sub test",
        ]
    )
    suggestions = main_window._suggester.get_all_suggestions(":cate ")
    assert len(suggestions) > 0
    assert all(s.startswith(":cate ") for s in suggestions)


def test_text_changed_updates_suggestions(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test"]
    )
    main_window._on_command_text_changed(":cate ")
    assert len(main_window.bottom_bar.command_input._suggestions) > 0


def test_text_changed_no_update_without_colon(main_window):
    main_window._on_command_text_changed("hello")
    assert main_window.bottom_bar.command_input._suggestions == []
