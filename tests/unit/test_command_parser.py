"""Tests for command_parser.py."""

from __future__ import annotations

import pytest

from log_viewer.core.command_parser import parse_command, ParseError, ParsedCommand


class TestBasicParsing:
    """Test basic command parsing: name text."""

    def test_simple_filter_command(self) -> None:
        result = parse_command("f ERROR")
        assert result == ParsedCommand(
            name="f",
            text="ERROR",
            raw="f ERROR",
        )

    def test_simple_highlight_command(self) -> None:
        result = parse_command("h ERROR")
        assert result == ParsedCommand(
            name="h",
            text="ERROR",
            raw="h ERROR",
        )

    def test_simple_search_command(self) -> None:
        result = parse_command("s error")
        assert result == ParsedCommand(
            name="s",
            text="error",
            raw="s error",
        )

    def test_text_with_spaces(self) -> None:
        result = parse_command("f Failed to open")
        assert result.text == "Failed to open"

    def test_regex_command(self) -> None:
        result = parse_command("fr error_\\d+")
        assert result == ParsedCommand(
            name="fr",
            text="error_\\d+",
            raw="fr error_\\d+",
        )

    def test_simple_query_command(self) -> None:
        result = parse_command('fs "Failed" AND "config"')
        assert result.text == '"Failed" AND "config"'

    def test_zero_arg_command(self) -> None:
        result = parse_command("reload")
        assert result == ParsedCommand(
            name="reload",
            text="",
            raw="reload",
        )

    def test_quit_command(self) -> None:
        result = parse_command("q")
        assert result.name == "q"
        assert result.text == ""

    def test_open_command_with_path(self) -> None:
        result = parse_command("open /path/to/file.log")
        assert result.name == "open"
        assert result.text == "/path/to/file.log"


class TestRemoveCommands:
    """Test rmf and rmh commands."""

    def test_rmf_with_pattern(self) -> None:
        result = parse_command("rmf ERROR")
        assert result == ParsedCommand(
            name="rmf",
            text="ERROR",
            raw="rmf ERROR",
        )

    def test_rmf_clear_all(self) -> None:
        result = parse_command("rmf")
        assert result.name == "rmf"
        assert result.text == ""

    def test_rmh_with_pattern(self) -> None:
        result = parse_command("rmh ERROR")
        assert result.name == "rmh"
        assert result.text == "ERROR"

    def test_rmh_clear_all(self) -> None:
        result = parse_command("rmh")
        assert result.name == "rmh"
        assert result.text == ""


class TestCategoryCommands:
    """Test category commands."""

    def test_cate_command(self) -> None:
        result = parse_command("cate my_app")
        assert result.name == "cate"
        assert result.text == "my_app"

    def test_catd_command(self) -> None:
        result = parse_command("catd my_app/storage")
        assert result.name == "catd"
        assert result.text == "my_app/storage"

    def test_cate_without_args(self) -> None:
        result = parse_command("cate")
        assert result.name == "cate"
        assert result.text == ""

    def test_catd_without_args(self) -> None:
        result = parse_command("catd")
        assert result.name == "catd"
        assert result.text == ""


class TestMiscCommands:
    """Test misc commands."""

    def test_reload_command(self) -> None:
        result = parse_command("reload")
        assert result.name == "reload"
        assert result.text == ""


class TestErrors:
    """Test error cases."""

    def test_empty_command(self) -> None:
        with pytest.raises(ParseError):
            parse_command("")

    def test_unknown_command(self) -> None:
        with pytest.raises(ParseError, match="[Uu]nknown"):
            parse_command("xyz text")

    def test_missing_text_for_text_required_command(self) -> None:
        with pytest.raises(ParseError, match="[Tt]ext"):
            parse_command("f")


class TestPinCommands:
    """Test pin and rmpin commands."""

    def test_pin_with_line_number(self) -> None:
        result = parse_command("pin 42")
        assert result.name == "pin"
        assert result.text == "42"

    def test_pin_with_different_number(self) -> None:
        result = parse_command("pin 1")
        assert result.text == "1"

    def test_pin_without_number_errors(self) -> None:
        with pytest.raises(ParseError, match="[Tt]ext"):
            parse_command("pin")

    def test_rmpin_with_line_number(self) -> None:
        result = parse_command("rmpin 42")
        assert result.name == "rmpin"
        assert result.text == "42"

    def test_rmpin_without_args_clears_all(self) -> None:
        result = parse_command("rmpin")
        assert result.name == "rmpin"
        assert result.text == ""


class TestEdgeCases:
    """Test edge cases."""

    def test_text_starting_with_space(self) -> None:
        result = parse_command("f  leading space")
        assert result.text == " leading space"

    def test_text_with_slashes(self) -> None:
        result = parse_command("f /path/to/file")
        assert result.text == "/path/to/file"

    def test_raw_preserved(self) -> None:
        raw = "f Some text"
        result = parse_command(raw)
        assert result.raw == raw

    def test_command_name_case_sensitive(self) -> None:
        with pytest.raises(ParseError):
            parse_command("F ERROR")
