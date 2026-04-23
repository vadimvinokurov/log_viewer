"""Tests for CommandService."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.command_parser import ParsedCommand
from src.models.filter_state import FilterMode
from src.services.command_service import CommandService


def _make_service() -> tuple[CommandService, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Create a CommandService with all mock deps."""
    filter_ctrl = MagicMock()
    highlight_svc = MagicMock()
    log_table = MagicMock()
    status_cb = MagicMock()
    svc = CommandService(
        filter_controller=filter_ctrl,
        highlight_service=highlight_svc,
        log_table=log_table,
        status_callback=status_cb,
    )
    return svc, filter_ctrl, highlight_svc, log_table, status_cb


def _cmd(action: str, **kwargs: object) -> ParsedCommand:
    """Build a ParsedCommand with sensible defaults."""
    defaults: dict[str, object] = {
        "action": action,
        "mode": "plain",
        "case_sensitive": False,
        "color": None,
        "text": "query",
        "direction": "forward",
    }
    defaults.update(kwargs)
    return ParsedCommand(**defaults)  # type: ignore[arg-type]


class TestSearch:
    """Search handler: find_text called, direction stored, status reported."""

    def test_forward_search(self) -> None:
        svc, _, _, log_table, status_cb = _make_service()
        log_table.find_text.return_value = 5

        svc.execute(_cmd("s", text="hello", case_sensitive=True))

        log_table.find_text.assert_called_once_with("hello", True)
        assert svc.direction == "forward"
        status_cb.assert_called_once()
        assert "5" in status_cb.call_args[0][0]

    def test_backward_search(self) -> None:
        svc, _, _, log_table, _ = _make_service()
        log_table.find_text.return_value = 3

        svc.execute(_cmd("s", text="hello", direction="backward"))

        assert svc.direction == "backward"
        log_table.find_text.assert_called_once_with("hello", False)


class TestFilter:
    """Filter handler: set_filter_text + set_filter_mode + apply_filter."""

    @pytest.mark.parametrize(
        "mode, expected",
        [
            ("plain", FilterMode.PLAIN),
            ("regex", FilterMode.REGEX),
            ("simple", FilterMode.SIMPLE),
        ],
    )
    def test_mode_mapping(self, mode: str, expected: FilterMode) -> None:
        svc, filter_ctrl, _, _, _ = _make_service()

        svc.execute(_cmd("f", mode=mode, text="error"))

        filter_ctrl.set_filter_text.assert_called_once_with("error")
        filter_ctrl.set_filter_mode.assert_called_once_with(expected)
        filter_ctrl.apply_filter.assert_called_once()


class TestHighlight:
    """Highlight handler: add_user_pattern + update engine."""

    def test_default_color(self) -> None:
        svc, _, highlight_svc, log_table, _ = _make_service()

        svc.execute(_cmd("h", text="ERROR", mode="plain"))

        highlight_svc.add_user_pattern.assert_called_once()
        args, kwargs = highlight_svc.add_user_pattern.call_args
        assert args[0] == "ERROR"
        # Default color is red
        assert args[1].name() == "#ff0000"
        assert kwargs["is_regex"] is False
        log_table.set_highlight_engine.assert_called_once_with(
            highlight_svc.get_combined_engine.return_value
        )

    def test_custom_color(self) -> None:
        svc, _, highlight_svc, log_table, _ = _make_service()

        svc.execute(_cmd("h", text="WARN", color="blue", mode="plain"))

        args, _kwargs = highlight_svc.add_user_pattern.call_args
        assert args[1].name() == "#0000ff"

    def test_regex_mode(self) -> None:
        svc, _, highlight_svc, _, _ = _make_service()

        svc.execute(_cmd("h", text=r"\d+", mode="regex"))

        args = highlight_svc.add_user_pattern.call_args
        assert args[1]["is_regex"] is True


class TestRemoveFilter:
    """Remove filter: with text does set+apply, without text clears."""

    def test_with_text(self) -> None:
        svc, filter_ctrl, _, _, _ = _make_service()

        svc.execute(_cmd("rmf", text="something"))

        filter_ctrl.set_filter_text.assert_called_once_with("")
        filter_ctrl.apply_filter.assert_called_once()
        filter_ctrl.clear_filter.assert_not_called()

    def test_without_text(self) -> None:
        svc, filter_ctrl, _, _, _ = _make_service()

        svc.execute(_cmd("rmf", text=""))

        filter_ctrl.clear_filter.assert_called_once()
        filter_ctrl.set_filter_text.assert_not_called()


class TestRemoveHighlight:
    """Remove highlight: with text removes pattern, without text clears all."""

    def test_with_text(self) -> None:
        svc, _, highlight_svc, log_table, _ = _make_service()

        svc.execute(_cmd("rmh", text="ERROR"))

        highlight_svc.remove_user_pattern.assert_called_once_with("ERROR")
        highlight_svc.clear_all.assert_not_called()
        log_table.set_highlight_engine.assert_called_once_with(
            highlight_svc.get_combined_engine.return_value
        )

    def test_without_text(self) -> None:
        svc, _, highlight_svc, log_table, _ = _make_service()

        svc.execute(_cmd("rmh", text=""))

        highlight_svc.clear_all.assert_called_once()
        highlight_svc.remove_user_pattern.assert_not_called()
        log_table.set_highlight_engine.assert_called_once_with(
            highlight_svc.get_combined_engine.return_value
        )


class TestNext:
    """Next navigation: respects stored direction."""

    def test_forward_direction(self) -> None:
        svc, _, _, log_table, _ = _make_service()
        svc._direction = "forward"

        svc.execute(_cmd("n"))

        log_table.find_next.assert_called_once()
        log_table.find_previous.assert_not_called()

    def test_backward_direction(self) -> None:
        svc, _, _, log_table, _ = _make_service()
        svc._direction = "backward"

        svc.execute(_cmd("n"))

        log_table.find_previous.assert_called_once()
        log_table.find_next.assert_not_called()


class TestPrev:
    """Prev navigation: reverses stored direction."""

    def test_forward_direction(self) -> None:
        svc, _, _, log_table, _ = _make_service()
        svc._direction = "forward"

        svc.execute(_cmd("N"))

        log_table.find_previous.assert_called_once()
        log_table.find_next.assert_not_called()

    def test_backward_direction(self) -> None:
        svc, _, _, log_table, _ = _make_service()
        svc._direction = "backward"

        svc.execute(_cmd("N"))

        log_table.find_next.assert_called_once()
        log_table.find_previous.assert_not_called()
