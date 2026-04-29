"""Tests for MainWindow."""

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


def test_main_window_title(main_window):
    assert main_window.windowTitle() == "Log Viewer"


def test_main_window_has_log_table(main_window):
    assert main_window.log_table is not None


def test_main_window_has_side_panel(main_window):
    assert main_window.side_panel is not None


def test_main_window_has_bottom_bar(main_window):
    assert main_window.bottom_bar is not None


def test_side_panel_hidden_by_default(main_window):
    assert not main_window.side_panel.isVisible()


def test_toggle_side_panel_shows(main_window):
    main_window._toggle_side_panel()
    assert main_window.side_panel.isVisible()


def test_toggle_side_panel_hides(main_window):
    main_window._toggle_side_panel()
    main_window._toggle_side_panel()
    assert not main_window.side_panel.isVisible()


def test_command_dispatch_quit(main_window):
    main_window._handle_command("q")
    assert not main_window.isVisible()


def test_command_dispatch_filter(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test message"]
    )
    main_window._handle_command("f error")
    assert len(main_window.log_store.filters) == 1


def test_command_dispatch_rmf_clears_filters(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test message"]
    )
    main_window._handle_command("f error")
    main_window._handle_command("rmf")
    assert len(main_window.log_store.filters) == 0


def test_command_dispatch_highlight(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test message"]
    )
    main_window._handle_command("h error")
    assert len(main_window.log_store.highlights) == 1
    assert main_window.log_store.highlights[0].color == "red"


def test_command_dispatch_highlight_custom_color(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test message"]
    )
    main_window._handle_command("h/color=blue/error")
    assert main_window.log_store.highlights[0].color == "blue"


def test_command_dispatch_rmh_clears_highlights(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test message"]
    )
    main_window._handle_command("h error")
    main_window._handle_command("rmh")
    assert len(main_window.log_store.highlights) == 0


def test_command_submitted_colon_prefix(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main test message"]
    )
    main_window._on_command_submitted(":f error")
    assert len(main_window.log_store.filters) == 1


def test_command_submitted_slash_search(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main hello world"]
    )
    main_window._on_command_submitted("/hello")
    assert main_window.log_store.search_state is not None
    assert main_window.log_store.search_state.pattern == "hello"


def test_update_status_shows_line_count(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main msg1"],
        file_path="test.log",
    )
    main_window._update_status()
    status = main_window.bottom_bar.status_label.text()
    assert "1/1 lines" in status
    assert "test.log" in status


def test_file_load_updates_table(main_window):
    main_window.log_store.load_lines(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main first",
            "2025-01-01T10:00:01 LOG_ERROR app/main second",
        ],
        file_path="test.log",
    )
    main_window._refresh_display()
    assert main_window._table_model.rowCount() == 2
