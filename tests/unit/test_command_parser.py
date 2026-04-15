"""Tests for command_parser.py — RED phase."""

from __future__ import annotations

import pytest

from log_viewer.core.command_parser import parse_command, ParseError, ParsedCommand


class TestBasicParsing:
    """Test basic command parsing: name text."""

    def test_simple_filter_command(self) -> None:
        result = parse_command("f ERROR")
        assert result == ParsedCommand(
            name="f",
            flags={},
            text="ERROR",
            raw="f ERROR",
        )

    def test_simple_highlight_command(self) -> None:
        result = parse_command("h ERROR")
        assert result == ParsedCommand(
            name="h",
            flags={},
            text="ERROR",
            raw="h ERROR",
        )

    def test_simple_search_command(self) -> None:
        result = parse_command("s error")
        assert result == ParsedCommand(
            name="s",
            flags={},
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
            flags={},
            text="error_\\d+",
            raw="fr error_\\d+",
        )

    def test_simple_query_command(self) -> None:
        result = parse_command('fs "Failed" AND "config"')
        assert result.text == '"Failed" AND "config"'

    def test_zero_arg_command(self) -> None:
        result = parse_command("lsf")
        assert result == ParsedCommand(
            name="lsf",
            flags={},
            text="",
            raw="lsf",
        )

    def test_quit_command(self) -> None:
        result = parse_command("q")
        assert result.name == "q"
        assert result.text == ""

    def test_open_command_with_path(self) -> None:
        result = parse_command("open /path/to/file.log")
        assert result.name == "open"
        assert result.text == "/path/to/file.log"


class TestFlagsParsing:
    """Test command parsing with flags: name/flags/text."""

    def test_case_sensitive_flag(self) -> None:
        result = parse_command("f/cs/Failed to open")
        assert result == ParsedCommand(
            name="f",
            flags={"cs": ""},
            text="Failed to open",
            raw="f/cs/Failed to open",
        )

    def test_color_flag_named(self) -> None:
        result = parse_command("h/color=red/ERROR")
        assert result == ParsedCommand(
            name="h",
            flags={"color": "red"},
            text="ERROR",
            raw="h/color=red/ERROR",
        )

    def test_color_flag_hex(self) -> None:
        result = parse_command("h/color=#FF5733/timeout")
        assert result == ParsedCommand(
            name="h",
            flags={"color": "#FF5733"},
            text="timeout",
            raw="h/color=#FF5733/timeout",
        )

    def test_multiple_flags(self) -> None:
        result = parse_command("h/cs,color=yellow/WARNING")
        assert result.flags == {"cs": "", "color": "yellow"}
        assert result.text == "WARNING"

    def test_case_sensitive_search(self) -> None:
        result = parse_command("s/cs/error")
        assert result.flags == {"cs": ""}
        assert result.text == "error"


class TestRemoveCommands:
    """Test rmf and rmh commands."""

    def test_rmf_with_pattern(self) -> None:
        result = parse_command("rmf ERROR")
        assert result == ParsedCommand(
            name="rmf",
            flags={},
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
        result = parse_command("cate HordeMode")
        assert result.name == "cate"
        assert result.text == "HordeMode"

    def test_catd_command(self) -> None:
        result = parse_command("catd HordeMode/game_storage")
        assert result.name == "catd"
        assert result.text == "HordeMode/game_storage"

    def test_cate_without_args(self) -> None:
        result = parse_command("cate")
        assert result.name == "cate"
        assert result.text == ""

    def test_catd_without_args(self) -> None:
        result = parse_command("catd")
        assert result.name == "catd"
        assert result.text == ""


class TestPresetCommands:
    """Test preset commands."""

    def test_preset_save(self) -> None:
        result = parse_command("preset save my-debug")
        assert result.name == "preset"
        assert result.text == "save my-debug"

    def test_preset_load(self) -> None:
        result = parse_command("preset load my-debug")
        assert result.name == "preset"
        assert result.text == "load my-debug"

    def test_rmpreset(self) -> None:
        result = parse_command("rmpreset my-debug")
        assert result.name == "rmpreset"
        assert result.text == "my-debug"

    def test_lspreset(self) -> None:
        result = parse_command("lspreset")
        assert result.name == "lspreset"
        assert result.text == ""


class TestMiscCommands:
    """Test misc commands."""

    def test_theme_command(self) -> None:
        result = parse_command("theme light")
        assert result.name == "theme"
        assert result.text == "light"

    def test_reload_command(self) -> None:
        result = parse_command("reload")
        assert result.name == "reload"
        assert result.text == ""


class TestErrors:
    """Test error cases."""

    def test_empty_flags_error(self) -> None:
        with pytest.raises(ParseError, match="[Ff]lag"):
            parse_command("f//text")

    def test_unknown_flag_error(self) -> None:
        with pytest.raises(ParseError, match="[Uu]nknown"):
            parse_command("f/unknown/text")

    def test_empty_command(self) -> None:
        with pytest.raises(ParseError):
            parse_command("")

    def test_unknown_command(self) -> None:
        with pytest.raises(ParseError, match="[Uu]nknown"):
            parse_command("xyz text")

    def test_missing_text_for_text_required_command(self) -> None:
        with pytest.raises(ParseError, match="[Tt]ext"):
            parse_command("f")


class TestEdgeCases:
    """Test edge cases."""

    def test_text_starting_with_space(self) -> None:
        result = parse_command("f  leading space")
        assert result.text == " leading space"

    def test_text_with_slashes(self) -> None:
        result = parse_command("f /path/to/file")
        assert result.text == "/path/to/file"

    def test_raw_preserved(self) -> None:
        raw = "f/cs/Some text"
        result = parse_command(raw)
        assert result.raw == raw

    def test_command_name_case_sensitive(self) -> None:
        with pytest.raises(ParseError):
            parse_command("F ERROR")
