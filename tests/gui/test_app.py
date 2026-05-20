"""Tests for MainWindow."""

from __future__ import annotations

import pytest

from log_viewer.core.models import SearchDirection, SearchMode
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


def test_side_panel_visible_by_default(main_window):
    assert main_window.side_panel.isVisible()


def test_toggle_side_panel_hides(main_window):
    main_window._toggle_side_panel()
    assert not main_window.side_panel.isVisible()


def test_toggle_side_panel_shows(main_window):
    main_window._toggle_side_panel()
    main_window._toggle_side_panel()
    assert main_window.side_panel.isVisible()


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
    assert main_window.log_store.highlights[0].color == "#FFD700"



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



def test_update_status_does_not_crash(main_window):
    main_window.log_store.load_lines(
        ["2025-01-01T10:00:00 LOG_INFO app/main msg1"],
        file_path="test.log",
    )
    main_window._update_status()  # set_status is now a no-op; just verify no crash


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


def test_command_pin_adds_pinned_line(main_window):
    main_window.log_store.load_lines(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main first",
            "2025-01-01T10:00:01 LOG_ERROR app/main second",
        ],
        file_path="test.log",
    )
    main_window._refresh_display()
    main_window._handle_command("pin 2")
    assert 2 in main_window.log_store.pinned_line_numbers


def test_command_rmpin_clears_all(main_window):
    main_window.log_store.load_lines(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main first",
            "2025-01-01T10:00:01 LOG_ERROR app/main second",
        ],
        file_path="test.log",
    )
    main_window._refresh_display()
    main_window._handle_command("pin 1")
    main_window._handle_command("pin 2")
    main_window._handle_command("rmpin")
    assert main_window.log_store.pinned_line_numbers == set()


def test_command_rmpin_specific_line(main_window):
    main_window.log_store.load_lines(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main first",
            "2025-01-01T10:00:01 LOG_ERROR app/main second",
        ],
        file_path="test.log",
    )
    main_window._refresh_display()
    main_window._handle_command("pin 1")
    main_window._handle_command("pin 2")
    main_window._handle_command("rmpin 1")
    assert 1 not in main_window.log_store.pinned_line_numbers
    assert 2 in main_window.log_store.pinned_line_numbers


def test_do_search_activates_in_search_when_matches_found(main_window):
    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state is not None
    assert main_window.log_store.search_state.in_search is True


def test_do_search_does_not_activate_when_no_matches(main_window):
    main_window._on_file_loaded(
        ["2025-01-01T10:00:00 LOG_INFO app/main hello"],
        "test.log",
    )
    main_window._do_search("nonexistent", SearchMode.PLAIN, SearchDirection.FORWARD)
    ss = main_window.log_store.search_state
    assert ss is None or ss.in_search is False


def test_update_title_shows_search_mode(main_window):
    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert "Search: error" in main_window.windowTitle()
    assert "test.log" in main_window.windowTitle()


def test_update_title_reverts_on_search_exit(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert "Search: error" in main_window.windowTitle()
    esc_event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, esc_event)
    assert main_window.windowTitle() == "Log Viewer \u2014 test.log"


def test_arrow_down_navigates_next_match_in_search_mode(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main error one",
            "2025-01-01T10:00:01 LOG_INFO app/main error two",
            "2025-01-01T10:00:02 LOG_INFO app/main other",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state.current_index == 0

    down = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, down)
    assert main_window.log_store.search_state.current_index == 1


def test_arrow_up_navigates_prev_match_in_search_mode(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main error one",
            "2025-01-01T10:00:01 LOG_INFO app/main error two",
            "2025-01-01T10:00:02 LOG_INFO app/main other",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    up = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier
    )
    main_window.eventFilter(main_window.log_table, up)
    assert main_window.log_store.search_state.current_index == 1


def test_arrow_keys_normal_when_not_in_search(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main world",
        ],
        "test.log",
    )
    down = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
    )
    result = main_window.eventFilter(main_window.log_table, down)
    assert result is False


def test_n_key_no_longer_navigates_search(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main error one",
            "2025-01-01T10:00:01 LOG_INFO app/main error two",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    initial_index = main_window.log_store.search_state.current_index

    n_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_N,
        Qt.KeyboardModifier.NoModifier,
        "n",
    )
    main_window.eventFilter(main_window.log_table, n_event)
    assert main_window.log_store.search_state.current_index == initial_index


def test_file_reload_resets_search_mode(main_window):
    main_window._on_file_loaded(
        [
            "2025-01-01T10:00:00 LOG_INFO app/main hello",
            "2025-01-01T10:00:01 LOG_INFO app/main error found",
        ],
        "test.log",
    )
    main_window._do_search("error", SearchMode.PLAIN, SearchDirection.FORWARD)
    assert main_window.log_store.search_state.in_search is True
    assert "Search" in main_window.windowTitle()

    main_window._on_file_loaded(
        ["2025-01-01T10:00:00 LOG_INFO app/main hello"],
        "other.log",
    )
    assert "Search" not in main_window.windowTitle()
    assert "other.log" in main_window.windowTitle()
