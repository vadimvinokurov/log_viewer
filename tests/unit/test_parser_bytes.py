"""Tests for byte-buffer-based parser functions."""

from __future__ import annotations

from log_viewer.core.parser import (
    detect_format_bytes,
    parse_line_soa_bytes,
    parse_plain_line_soa_bytes,
    scan_line_starts,
)


class TestScanLineStarts:
    def test_basic(self) -> None:
        buf = b"line1\nline2\nline3\n"
        starts = scan_line_starts(buf)
        assert starts == [0, 6, 12, 18]

    def test_no_trailing_newline(self) -> None:
        buf = b"line1\nline2\nline3"  # len=17, no trailing \n
        starts = scan_line_starts(buf)
        assert starts == [0, 6, 12, 17]

    def test_empty_buffer(self) -> None:
        buf = b""
        starts = scan_line_starts(buf)
        assert starts == [0]

    def test_single_newline(self) -> None:
        buf = b"\n"
        starts = scan_line_starts(buf)
        assert starts == [0, 1]

    def test_empty_lines(self) -> None:
        buf = b"\n\n\n"
        starts = scan_line_starts(buf)
        assert starts == [0, 1, 2, 3]


class TestDetectFormatBytes:
    def test_detects_ksiva(self) -> None:
        buf = b"01-01-2024T08:00:00.100 my_app/storage LOG_ERROR Failed\n"
        assert detect_format_bytes(buf) == "ksiva"

    def test_detects_plain(self) -> None:
        buf = b"08:00:00.100    0.014 wrn    config    Duplicate entry\n"
        assert detect_format_bytes(buf) == "plain"

    def test_defaults_ksiva_for_empty(self) -> None:
        assert detect_format_bytes(b"") == "ksiva"
        assert detect_format_bytes(b"\n\n") == "ksiva"


class TestParseLineSoaBytes:
    def _parse(self, raw: bytes) -> tuple:
        """Helper: parse a single line with fresh category state."""
        cat_name_to_id: dict[str, int] = {"uncategorized": 0}
        cat_names: list[str] = ["uncategorized"]
        return parse_line_soa_bytes(raw, 0, cat_name_to_id, cat_names)

    def test_full_ksiva_line(self) -> None:
        raw = b"2024-01-01T10:00:00.100 app/main LOG_INFO Starting app"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert ts_ms == 10 * 3_600_000 + 0 * 60_000 + 0 * 1_000 + 100
        assert cat_id == 1  # first non-uncategorized
        assert lvl_id == 3  # INFO
        assert raw[msg_off:msg_off + msg_len] == b"Starting app"

    def test_error_level(self) -> None:
        raw = b"2024-01-01T10:00:00 app LOG_ERROR fail"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert lvl_id == 1  # ERROR
        assert raw[msg_off:msg_off + msg_len] == b"fail"

    def test_no_level_defaults_info(self) -> None:
        raw = b"2024-01-01T10:00:00 app/main version 1.2.3"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert lvl_id == 3  # INFO default
        assert raw[msg_off:msg_off + msg_len] == b"version 1.2.3"

    def test_empty_line(self) -> None:
        raw = b""
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert ts_ms == 0
        assert cat_id == 0  # uncategorized
        assert lvl_id == 3  # INFO
        assert msg_len == 0

    def test_message_with_spaces(self) -> None:
        raw = b"2024-01-01T10:00:00 cat LOG_ERROR Failed to open file"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert raw[msg_off:msg_off + msg_len] == b"Failed to open file"

    def test_category_dedup(self) -> None:
        cat_name_to_id: dict[str, int] = {"uncategorized": 0}
        cat_names: list[str] = ["uncategorized"]
        raw1 = b"2024-01-01T10:00:00 app/main LOG_INFO hello"
        raw2 = b"2024-01-01T10:00:00 app/main LOG_INFO world"
        r1 = parse_line_soa_bytes(raw1, 0, cat_name_to_id, cat_names)
        r2 = parse_line_soa_bytes(raw2, 0, cat_name_to_id, cat_names)
        assert r1[1] == r2[1]  # same cat_id
        assert len(cat_names) == 2  # uncategorized + app/main


class TestParsePlainLineSoaBytes:
    def _parse(self, raw: bytes) -> tuple:
        cat_name_to_id: dict[str, int] = {"uncategorized": 0}
        cat_names: list[str] = ["uncategorized"]
        return parse_plain_line_soa_bytes(raw, 0, cat_name_to_id, cat_names)

    def test_full_plain_line(self) -> None:
        raw = b"08:00:00.100    0.014 wrn    config    Duplicate entry"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert ts_ms == 8 * 3_600_000 + 0 * 60_000 + 0 * 1_000 + 100
        assert lvl_id == 2  # WARNING
        assert raw[msg_off:msg_off + msg_len] == b"Duplicate entry"

    def test_msg_maps_to_info(self) -> None:
        raw = b"08:00:00.100  100.000 msg    system    Initialized"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert lvl_id == 3  # INFO
        assert raw[msg_off:msg_off + msg_len] == b"Initialized"

    def test_empty_line(self) -> None:
        raw = b""
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert ts_ms == 0
        assert cat_id == 0
        assert lvl_id == 3
        assert msg_len == 0

    def test_debug_line(self) -> None:
        raw = b"08:00:00.100  100.000 dbg    my_module    Object count: 42"
        ts_ms, cat_id, lvl_id, msg_off, msg_len = self._parse(raw)
        assert lvl_id == 4  # DEBUG
        assert raw[msg_off:msg_off + msg_len] == b"Object count: 42"
