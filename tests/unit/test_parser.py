"""Tests for log parser."""

from log_viewer.core.models import LogFormat, LogLevel
from log_viewer.core.parser import detect_format, parse_line, parse_plain_line


class TestParseLineWithLevel:
    def test_error_line(self) -> None:
        raw = "01-01-2024T08:00:00.100 my_app/module LOG_ERROR Something went wrong"
        line = parse_line(raw, 1)
        assert line.line_number == 1
        assert line.timestamp == "01-01-2024T08:00:00.100"
        assert line.category == "my_app/module"
        assert line.level == LogLevel.ERROR
        assert line.message == "Something went wrong"

    def test_warning_line(self) -> None:
        raw = "01-01-2024T08:00:00.100 my_app/module LOG_WARNING Deprecated feature used"
        line = parse_line(raw, 5)
        assert line.level == LogLevel.WARNING
        assert line.category == "my_app/module"
        assert line.message == "Deprecated feature used"

    def test_info_line(self) -> None:
        raw = "01-01-2024T08:00:00.100 SomeCategory LOG_INFO Some info message"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.INFO
        assert line.message == "Some info message"

    def test_debug_line(self) -> None:
        raw = "01-01-2024T08:00:00.100 Cat LOG_DEBUG Debug msg"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.DEBUG

    def test_trace_line(self) -> None:
        raw = "01-01-2024T08:00:00.100 Cat LOG_TRACE Trace msg"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.TRACE

    def test_critical_line(self) -> None:
        raw = "01-01-2024T08:00:00.100 Cat LOG_CRITICAL Critical msg"
        line = parse_line(raw, 1)
        assert line.level == LogLevel.CRITICAL

    def test_message_with_spaces(self) -> None:
        raw = "01-01-2024T08:00:00.100 Cat LOG_ERROR Failed to open file for reading, internal error"
        line = parse_line(raw, 1)
        assert line.message == "Failed to open file for reading, internal error"

    def test_message_lower_populated(self) -> None:
        raw = "01-01-2024T08:00:00.100 Cat LOG_ERROR Something Went Wrong"
        line = parse_line(raw, 1)
        assert line.message_lower == "something went wrong"


class TestParseLineWithoutLevel:
    def test_line_without_log_prefix(self) -> None:
        raw = "01-01-2024T08:00:00.100 my_lib/core version 1.2.3"
        line = parse_line(raw, 1)
        assert line.timestamp == "01-01-2024T08:00:00.100"
        assert line.category == "my_lib/core"
        assert line.level == LogLevel.INFO
        assert line.message == "version 1.2.3"

    def test_line_with_two_fields(self) -> None:
        raw = "01-01-2024T08:00:00.100 PLATFORM test_value"
        line = parse_line(raw, 1)
        assert line.timestamp == "01-01-2024T08:00:00.100"
        assert line.category == "PLATFORM"
        assert line.level == LogLevel.INFO
        assert line.message == "test_value"


class TestParseLineFallback:
    def test_single_field(self) -> None:
        raw = "01-01-2024T08:00:00.100"
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
            "01-01-2024T08:00:00.100 my_lib/core version 1.0",
            "01-01-2024T08:00:00.200 my_app/storage LOG_ERROR Failed",
            "",
            "01-01-2024T08:00:00.300 PLATFORM test",
        ]
        parsed = [parse_line(line, i + 1) for i, line in enumerate(lines)]
        assert parsed[0].category == "my_lib/core"
        assert parsed[1].level == LogLevel.ERROR
        assert parsed[2].category == "uncategorized"
        assert parsed[3].message == "test"


class TestDetectFormat:
    def test_detects_ksiva_from_log_level(self) -> None:
        lines = [
            "01-01-2024T08:00:00.100 my_app/storage LOG_ERROR Failed",
            "01-01-2024T08:00:00.200 my_lib/core release",
        ]
        assert detect_format(lines) == LogFormat.KSIVA

    def test_detects_ksiva_no_level(self) -> None:
        lines = ["01-01-2024T08:00:00.100 my_lib/core 1.2.3 release"]
        assert detect_format(lines) == LogFormat.KSIVA

    def test_detects_plain(self) -> None:
        lines = [
            "08:00:00.100    0.014 wrn    config    Duplicate entry found",
        ]
        assert detect_format(lines) == LogFormat.PLAIN

    def test_detects_plain_dbg(self) -> None:
        lines = [
            "08:00:00.100  100.000 dbg    my_module    Debug output",
        ]
        assert detect_format(lines) == LogFormat.PLAIN

    def test_skips_empty_lines(self) -> None:
        lines = [
            "",
            "08:00:00.100    0.014 wrn    config    message",
        ]
        assert detect_format(lines) == LogFormat.PLAIN

    def test_defaults_to_ksiva_for_empty(self) -> None:
        assert detect_format([]) == LogFormat.KSIVA
        assert detect_format(["", "  "]) == LogFormat.KSIVA


class TestParsePlainLine:
    def test_warning_line(self) -> None:
        raw = "08:00:00.100    0.014 wrn    config    Duplicate entry found"
        line = parse_plain_line(raw, 1)
        assert line.line_number == 1
        assert line.timestamp == "08:00:00.100"
        assert line.category == "config"
        assert line.level == LogLevel.WARNING
        assert line.message == "Duplicate entry found"

    def test_debug_line(self) -> None:
        raw = "08:00:00.100  100.000 dbg    my_module    Object count: 42/100"
        line = parse_plain_line(raw, 5)
        assert line.timestamp == "08:00:00.100"
        assert line.category == "my_module"
        assert line.level == LogLevel.DEBUG
        assert line.message == "Object count: 42/100"

    def test_error_line(self) -> None:
        raw = "08:00:00.100    0.014 err    network    Connection failed"
        line = parse_plain_line(raw, 1)
        assert line.level == LogLevel.ERROR

    def test_msg_maps_to_info(self) -> None:
        raw = "08:00:00.100    0.014 msg    system    Initialized successfully"
        line = parse_plain_line(raw, 1)
        assert line.level == LogLevel.INFO

    def test_empty_line(self) -> None:
        line = parse_plain_line("", 1)
        assert line.category == "uncategorized"
        assert line.level == LogLevel.INFO
        assert line.message == ""
