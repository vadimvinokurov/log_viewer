"""Tests for log parser."""

from log_viewer.core.models import LogLevel
from log_viewer.core.parser import parse_line


class TestParseLineWithLevel:
    def test_error_line(self) -> None:
        raw = "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open file"
        line = parse_line(raw, 1)
        assert line.line_number == 1
        assert line.timestamp == "20-03-2026T12:20:42.305"
        assert line.category == "HordeMode/game_storage/folder"
        assert line.level == LogLevel.ERROR
        assert line.message == "Failed to open file"
        assert line.raw == raw

    def test_warning_line(self) -> None:
        raw = "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_WARNING Unable to find label"
        line = parse_line(raw, 5)
        assert line.level == LogLevel.WARNING
        assert line.category == "HordeMode/game_storage/folder"
        assert line.message == "Unable to find label"

    def test_info_line(self) -> None:
        raw = "20-03-2026T12:20:42.305 SomeCategory LOG_INFO Some info message"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.INFO
        assert line.message == "Some info message"

    def test_debug_line(self) -> None:
        raw = "20-03-2026T12:20:42.305 Cat LOG_DEBUG Debug msg"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.DEBUG

    def test_trace_line(self) -> None:
        raw = "20-03-2026T12:20:42.305 Cat LOG_TRACE Trace msg"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.TRACE

    def test_critical_line(self) -> None:
        raw = "20-03-2026T12:20:42.305 Cat LOG_CRITICAL Critical msg"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.CRITICAL

    def test_message_with_spaces(self) -> None:
        raw = "20-03-2026T12:20:42.305 Cat LOG_ERROR Failed to open file for reading, internal error"
        line = parse_line(raw, 1)
        assert line.message == "Failed to open file for reading, internal error"


class TestParseLineWithoutLevel:
    def test_line_without_log_prefix(self) -> None:
        raw = "20-03-2026T12:20:42.258 LEECH/CORE 5.18.183-ms25.4.2 release"
        line = parse_line(raw, 1)
        assert line.timestamp == "20-03-2026T12:20:42.258"
        assert line.category == "LEECH/CORE"
        assert line.level == LogLevel.INFO
        assert line.message == "5.18.183-ms25.4.2 release"

    def test_line_with_two_fields(self) -> None:
        raw = "20-03-2026T12:20:42.258 PLATFORM win64"
        line = parse_line(raw, 1)
        assert line.timestamp == "20-03-2026T12:20:42.258"
        assert line.category == "PLATFORM"
        assert line.level == LogLevel.INFO
        assert line.message == "win64"


class TestParseLineFallback:
    def test_single_field(self) -> None:
        raw = "20-03-2026T12:20:42.258"
        line = parse_line(raw, 1)
        assert line.category == "uncategorized"
        assert line.level == LogLevel.INFO
        assert line.message == raw

    def test_empty_line(self) -> None:
        line = parse_line("", 1)
        assert line.category == "uncategorized"
        assert line.level == LogLevel.INFO
        assert line.message == ""
        assert line.timestamp == ""

    def test_whitespace_only(self) -> None:
        line = parse_line("   ", 1)
        assert line.category == "uncategorized"


class TestParseMultipleLines:
    def test_parse_all_lines_from_sample(self) -> None:
        lines = [
            "20-03-2026T12:20:42.258 LEECH/CORE 5.18.183-ms25 release",
            "20-03-2026T12:20:42.305 HordeMode/game_storage LOG_ERROR Failed",
            "",
            "20-03-2026T12:20:42.258 PLATFORM win64",
        ]
        parsed = [parse_line(line, i + 1) for i, line in enumerate(lines)]
        assert parsed[0].category == "LEECH/CORE"
        assert parsed[1].level == LogLevel.ERROR
        assert parsed[2].category == "uncategorized"
        assert parsed[3].message == "win64"
