"""Tests for LogStore byte-buffer loading."""

from __future__ import annotations

import numpy as np

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, LogLevel, SearchMode

SAMPLE_BYTES = b"""\
01-01-2024T08:00:00.100 my_lib/core version 5.18
01-01-2024T08:00:00.200 my_app/storage/folder LOG_ERROR Failed to open
01-01-2024T08:00:00.200 my_app/storage/db LOG_ERROR Read failed
01-01-2024T08:00:00.200 my_app/storage/folder LOG_WARNING Missing file
01-01-2024T08:00:00.100 SYSTEM test_os
01-01-2024T08:00:00.200 my_app/storage/db LOG_DEBUG Debug info
"""


class TestLoadBytes:
    def test_load_bytes_populates_n(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        assert store.n == 6

    def test_load_bytes_populates_timestamps(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        # Fast path stores timestamp_spans (SPAN_DTYPE) instead of uint64 ms
        assert len(store.timestamp_spans) == 6
        assert store.timestamp_spans.dtype.names == ("offset", "length")

    def test_load_bytes_populates_levels(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        # Lines: INFO, ERROR, ERROR, WARNING, INFO, DEBUG
        assert store.levels[0] == 3  # INFO
        assert store.levels[1] == 1  # ERROR
        assert store.levels[3] == 2  # WARNING
        assert store.levels[5] == 4  # DEBUG

    def test_load_bytes_populates_line_starts(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        assert store.line_starts.dtype == np.uint64
        assert len(store.line_starts) == store.n + 1
        assert store.line_starts[0] == 0

    def test_load_bytes_populates_message_spans(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        assert store.message_spans.dtype.names == ("offset", "length")
        assert len(store.message_spans) == 6

    def test_load_bytes_builds_category_tree(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        assert "my_lib/core" in store.category_counts
        assert "my_app/storage/folder" in store.category_counts
        assert "SYSTEM" in store.category_counts

    def test_load_bytes_empty_buffer(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(b""))
        assert store.n == 0


class TestGetMessage:
    def test_get_message_returns_decoded_text(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        msg = store.get_message(0)
        assert msg == "version 5.18"

    def test_get_message_error_line(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        msg = store.get_message(1)
        assert msg == "Failed to open"


class TestGetRaw:
    def test_get_raw_returns_original_line(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        raw = store.get_raw(0)
        assert "my_lib/core" in raw
        assert "version 5.18" in raw

    def test_get_raw_empty_on_out_of_range(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        assert store.get_raw(-1) == ""
        assert store.get_raw(999) == ""


class TestRowRefWithBytes:
    def test_rowref_message_from_bytes(self) -> None:
        from log_viewer.core.models import RowRef
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        ref = RowRef(0, store)
        assert ref.message == "version 5.18"

    def test_rowref_file_offset_from_line_starts(self) -> None:
        from log_viewer.core.models import RowRef
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        ref = RowRef(0, store)
        assert ref.file_offset == 0

    def test_rowref_line_length(self) -> None:
        from log_viewer.core.models import RowRef
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        ref = RowRef(0, store)
        assert ref.line_length > 0


class TestFilterWithBytes:
    def test_add_filter_on_bytes_store(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        assert len(store.filtered_indices) == 2  # "Failed to open" and "Read failed"

    def test_case_insensitive_filter_on_bytes(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        store.add_filter(Filter(pattern="failed", mode=SearchMode.PLAIN))
        assert len(store.filtered_indices) == 2

    def test_no_filter_shows_all(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        assert len(store.filtered_indices) == 6


class TestSearchWithBytes:
    def test_search_finds_match(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        state = store.search("Failed", SearchMode.PLAIN)
        assert len(state.matches) == 2

    def test_search_no_match(self) -> None:
        store = LogStore()
        store.load_bytes(bytearray(SAMPLE_BYTES))
        state = store.search("xyz_not_found", SearchMode.PLAIN)
        assert len(state.matches) == 0


class TestPlainFormatBytes:
    def test_plain_format_load(self) -> None:
        plain = b"08:00:00.100    0.014 wrn    config    Duplicate entry\n"
        store = LogStore()
        store.load_bytes(bytearray(plain))
        assert store.n == 1
        assert store.levels[0] == 2  # WARNING
        assert store.get_message(0) == "Duplicate entry"
