"""Tests for CommandParser."""
from __future__ import annotations

import pytest

from src.core.command_parser import CommandParser, ParseError, ParsedCommand


class TestParsePlainSearch:
    """Plain search without flags."""

    def test_simple_text(self) -> None:
        cmd = CommandParser.parse("s Some text")
        assert cmd == ParsedCommand(
            action="s", mode="plain", case_sensitive=False,
            color=None, text="Some text", direction="forward",
        )

    def test_empty_text(self) -> None:
        cmd = CommandParser.parse("s")
        assert cmd.text == ""

    def test_case_sensitive_flag(self) -> None:
        cmd = CommandParser.parse("s/cs/Some text")
        assert cmd.case_sensitive is True
        assert cmd.text == "Some text"


class TestParseRegexSearch:
    """Regex mode search."""

    def test_regex_pattern(self) -> None:
        cmd = CommandParser.parse("sr/error_\\d+")
        assert cmd.mode == "regex"
        assert cmd.text == "error_\\d+"

    def test_regex_case_sensitive(self) -> None:
        cmd = CommandParser.parse("sr/cs/error_\\d+")
        assert cmd.mode == "regex"
        assert cmd.case_sensitive is True
        assert cmd.text == "error_\\d+"


class TestParseSimpleSearch:
    """Simple mode search."""

    def test_simple_query(self) -> None:
        cmd = CommandParser.parse('ss "ERROR" AND "timeout"')
        assert cmd.mode == "simple"
        assert cmd.text == '"ERROR" AND "timeout"'


class TestParseFilter:
    """Filter commands: plain, regex, simple."""

    def test_plain_filter(self) -> None:
        cmd = CommandParser.parse("f Some text")
        assert cmd.action == "f"
        assert cmd.mode == "plain"
        assert cmd.text == "Some text"

    def test_regex_filter(self) -> None:
        cmd = CommandParser.parse("fr/error_\\d+")
        assert cmd.action == "f"
        assert cmd.mode == "regex"
        assert cmd.text == "error_\\d+"

    def test_simple_filter(self) -> None:
        cmd = CommandParser.parse('fs "ERROR" AND "timeout"')
        assert cmd.action == "f"
        assert cmd.mode == "simple"
        assert cmd.text == '"ERROR" AND "timeout"'

    def test_filter_with_case_sensitive(self) -> None:
        cmd = CommandParser.parse("f/cs/Some text")
        assert cmd.action == "f"
        assert cmd.case_sensitive is True
        assert cmd.text == "Some text"


class TestParseHighlight:
    """Highlight commands with color support."""

    def test_default_color(self) -> None:
        cmd = CommandParser.parse("h ERROR")
        assert cmd.action == "h"
        assert cmd.color is None
        assert cmd.text == "ERROR"

    def test_with_color(self) -> None:
        cmd = CommandParser.parse("h/color=red/ERROR")
        assert cmd.color == "red"
        assert cmd.text == "ERROR"

    def test_case_sensitive_with_color(self) -> None:
        cmd = CommandParser.parse("h/cs/color=red/ERROR")
        assert cmd.case_sensitive is True
        assert cmd.color == "red"
        assert cmd.text == "ERROR"

    def test_hex_color(self) -> None:
        cmd = CommandParser.parse("h/color=#ff0000/ERROR")
        assert cmd.color == "#ff0000"
        assert cmd.text == "ERROR"

    def test_regex_highlight(self) -> None:
        cmd = CommandParser.parse("hr/error_\\d+")
        assert cmd.mode == "regex"
        assert cmd.text == "error_\\d+"

    def test_simple_highlight(self) -> None:
        cmd = CommandParser.parse('hs "ERROR" OR "WARN"')
        assert cmd.mode == "simple"
        assert cmd.text == '"ERROR" OR "WARN"'


class TestParseRemoveFilter:
    """Remove filter commands."""

    def test_with_text(self) -> None:
        cmd = CommandParser.parse("rmf Some text")
        assert cmd.action == "rmf"
        assert cmd.text == "Some text"

    def test_with_flags(self) -> None:
        cmd = CommandParser.parse("rmf/cs/Some text")
        assert cmd.action == "rmf"
        assert cmd.case_sensitive is True
        assert cmd.text == "Some text"

    def test_no_text_clears_all(self) -> None:
        cmd = CommandParser.parse("rmf")
        assert cmd.action == "rmf"
        assert cmd.text == ""


class TestParseRemoveHighlight:
    """Remove highlight commands."""

    def test_with_text(self) -> None:
        cmd = CommandParser.parse("rmh ERROR")
        assert cmd.action == "rmh"
        assert cmd.text == "ERROR"

    def test_with_flags(self) -> None:
        cmd = CommandParser.parse("rmh/color=red/ERROR")
        assert cmd.action == "rmh"
        assert cmd.color == "red"
        assert cmd.text == "ERROR"

    def test_no_text_clears_all(self) -> None:
        cmd = CommandParser.parse("rmh")
        assert cmd.action == "rmh"
        assert cmd.text == ""


class TestParseNavigation:
    """Navigation commands n and N."""

    def test_next(self) -> None:
        cmd = CommandParser.parse("n")
        assert cmd.action == "n"
        assert cmd.text == ""

    def test_prev(self) -> None:
        cmd = CommandParser.parse("N")
        assert cmd.action == "N"
        assert cmd.text == ""

    def test_n_ignores_text(self) -> None:
        cmd = CommandParser.parse("n something")
        assert cmd.text == ""

    def test_N_ignores_text(self) -> None:
        cmd = CommandParser.parse("N something")
        assert cmd.text == ""


class TestParseDirection:
    """Direction parameter."""

    def test_forward_default(self) -> None:
        cmd = CommandParser.parse("s text")
        assert cmd.direction == "forward"

    def test_backward(self) -> None:
        cmd = CommandParser.parse("s text", direction="backward")
        assert cmd.direction == "backward"


class TestParseErrors:
    """Error cases."""

    def test_unknown_command(self) -> None:
        with pytest.raises(ParseError, match="Unknown command"):
            CommandParser.parse("xyz text")

    def test_empty_flags(self) -> None:
        with pytest.raises(ParseError, match="Empty flags"):
            CommandParser.parse("s//text")

    def test_empty_input(self) -> None:
        with pytest.raises(ParseError, match="Empty command"):
            CommandParser.parse("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(ParseError, match="Empty command"):
            CommandParser.parse("   ")

    def test_unknown_flag(self) -> None:
        with pytest.raises(ParseError, match="Unknown flag"):
            CommandParser.parse("s/unknown/text")


class TestParseLeadingSpace:
    """Double space preserves leading space in text."""

    def test_double_space_preserves_leading_space(self) -> None:
        cmd = CommandParser.parse("f  text")
        assert cmd.text == " text"

    def test_triple_space(self) -> None:
        cmd = CommandParser.parse("f   text")
        assert cmd.text == "  text"
