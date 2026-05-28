"""Tests for the redesigned core engine (SoA + byte-buffer + FilterPipeline)."""

from __future__ import annotations

import numpy as np

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, LogLevel, SearchMode, _LEVEL_LIST


# ---------------------------------------------------------------------------
# 1. Filter matches text in timestamp / category (full-buffer scan)
# ---------------------------------------------------------------------------


class TestFilterMatchesFullBuffer:
    """Filters scan the raw byte buffer, so they match timestamp and
    category text -- not just the message portion."""

    def test_filter_matches_timestamp(self) -> None:
        buf = bytearray(b"12:00:00.000 app/main [LOG_ERROR] hello world\n")
        store = LogStore()
        store.load_bytes(buf)
        filt = Filter(pattern="12:00", mode=SearchMode.PLAIN)
        mask = store.pipeline.compute_mask(store, filt)
        assert mask[0] is np.True_

    def test_filter_does_not_match_absent_timestamp(self) -> None:
        buf = bytearray(b"12:00:00.000 app/main [LOG_ERROR] hello world\n")
        store = LogStore()
        store.load_bytes(buf)
        filt = Filter(pattern="99:99", mode=SearchMode.PLAIN)
        mask = store.pipeline.compute_mask(store, filt)
        assert mask[0] is np.False_

    def test_filter_matches_category(self) -> None:
        buf = bytearray(b"12:00:00.000 myapp/module [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        filt = Filter(pattern="myapp", mode=SearchMode.PLAIN)
        mask = store.pipeline.compute_mask(store, filt)
        assert mask[0] is np.True_

    def test_filter_matches_level_text(self) -> None:
        """LOG_ERROR appears in the raw buffer, so plain match finds it."""
        buf = bytearray(b"12:00:00.000 app [LOG_ERROR] something\n")
        store = LogStore()
        store.load_bytes(buf)
        filt = Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN)
        mask = store.pipeline.compute_mask(store, filt)
        assert mask[0] is np.True_

    def test_regex_filter_matches_timestamp(self) -> None:
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        filt = Filter(pattern=r"12:\d{2}", mode=SearchMode.REGEX)
        mask = store.pipeline.compute_mask(store, filt)
        assert mask[0] is np.True_


# ---------------------------------------------------------------------------
# 2. get_columns()
# ---------------------------------------------------------------------------


class TestGetColumns:
    def test_get_columns_ksiva(self) -> None:
        buf = bytearray(
            b"2024-01-01T12:00:00.000 app/main [LOG_ERROR] hello world\n"
        )
        store = LogStore()
        store.load_bytes(buf)
        ts, cat, level, msg = store.get_columns(0)
        assert ts == "12:00:00.000"
        assert cat == "app/main"
        assert level == "ERROR"
        assert msg == "hello world"

    def test_get_columns_plain(self) -> None:
        buf = bytearray(
            b"12:00:00.000 1.234 err app/main hello world\n"
        )
        store = LogStore()
        store.load_bytes(buf)
        ts, cat, level, msg = store.get_columns(0)
        assert ts == "12:00:00.000"
        assert cat == "app/main"
        assert level == "ERROR"
        assert msg == "hello world"

    def test_get_columns_out_of_range(self) -> None:
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        ts, cat, level, msg = store.get_columns(99)
        assert ts == ""
        assert cat == ""
        assert level == ""
        assert msg == ""


# ---------------------------------------------------------------------------
# 3. Term cache in FilterPipeline
# ---------------------------------------------------------------------------


class TestTermCache:
    def test_term_cache_hit(self) -> None:
        """Second filter with the same term should reuse the cached mask."""
        buf = bytearray(
            b"12:00:00.000 app [LOG_INFO] error found here\n"
            b"12:00:00.001 app [LOG_INFO] all clear\n"
        )
        store = LogStore()
        store.load_bytes(buf)
        pipeline = store.pipeline

        # First simple-query filter populates cache for "error"
        pipeline.add_filter(
            store, Filter(pattern='"error" AND NOT "test"', mode=SearchMode.SIMPLE)
        )
        assert "error" in pipeline._term_cache
        cached_mask = pipeline._term_cache["error"]

        # Clear filters (does NOT invalidate term cache)
        pipeline.clear_filters(store)
        # Add another filter that uses "error" again
        pipeline.add_filter(
            store, Filter(pattern='"error"', mode=SearchMode.SIMPLE)
        )
        # The same ndarray object should be reused
        assert pipeline._term_cache["error"] is cached_mask

    def test_term_cache_invalidation_on_reload(self) -> None:
        """Loading new data should invalidate the term cache."""
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        store.pipeline.add_filter(
            store, Filter(pattern="hello", mode=SearchMode.PLAIN)
        )
        # Load new data -- cache should be cleared
        store.load_bytes(bytearray(b"12:00:00.000 app [LOG_INFO] world\n"))
        assert len(store.pipeline._term_cache) == 0


# ---------------------------------------------------------------------------
# 4. _buf_str lazy initialization
# ---------------------------------------------------------------------------


class TestBufStrLazy:
    def test_buf_str_none_after_load(self) -> None:
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        assert store._buf_str is None

    def test_buf_lower_created_by_regex_filter(self) -> None:
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        assert store._buf_lower is None
        # Regex filter creates _buf_lower (uses lowered buffer, not _buf_str)
        store.add_filter(Filter(pattern="hello", mode=SearchMode.REGEX))
        assert store._buf_lower is not None
        assert store._buf_str is None  # no longer needed for regex

    def test_buf_str_stays_none_with_plain_filter(self) -> None:
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        store.add_filter(Filter(pattern="hello", mode=SearchMode.PLAIN))
        assert store._buf_str is None


# ---------------------------------------------------------------------------
# 5. Two-pass loading
# ---------------------------------------------------------------------------


class TestTwoPassLoading:
    def test_populates_category_ids_and_levels(self) -> None:
        buf = bytearray(
            b"12:00:00.000 app [LOG_ERROR] msg1\n"
            b"12:00:00.001 mod [LOG_DEBUG] msg2\n"
        )
        store = LogStore()
        store.load_bytes(buf)
        assert store.n == 2
        assert len(store.category_ids) == 2
        assert len(store.levels) == 2

    def test_levels_parsed_correctly(self) -> None:
        buf = bytearray(
            b"12:00:00.000 app [LOG_ERROR] msg1\n"
            b"12:00:00.001 mod [LOG_DEBUG] msg2\n"
        )
        store = LogStore()
        store.load_bytes(buf)
        assert store.levels[0] == _LEVEL_LIST.index(LogLevel.ERROR)
        assert store.levels[1] == _LEVEL_LIST.index(LogLevel.DEBUG)

    def test_category_ids_are_dense(self) -> None:
        """Category IDs should be dense (no gaps)."""
        buf = bytearray(
            b"12:00:00.000 cat_a [LOG_INFO] m1\n"
            b"12:00:00.001 cat_b [LOG_INFO] m2\n"
            b"12:00:00.002 cat_a [LOG_INFO] m3\n"
        )
        store = LogStore()
        store.load_bytes(buf)
        unique_ids = sorted(set(store.category_ids.tolist()))
        # uncategorized=0 always present, cat_a and cat_b get 1,2
        assert unique_ids == [1, 2]
        assert store.category_ids[0] == store.category_ids[2]  # same cat


# ---------------------------------------------------------------------------
# 6. No message_spans / timestamp_spans
# ---------------------------------------------------------------------------


class TestNoSpans:
    def test_no_message_spans(self) -> None:
        """After loading, message_spans should not exist on the store."""
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        assert not hasattr(store, "message_spans") or store.message_spans is None

    def test_no_timestamp_spans(self) -> None:
        """After loading, timestamp_spans should not exist on the store."""
        buf = bytearray(b"12:00:00.000 app [LOG_INFO] hello\n")
        store = LogStore()
        store.load_bytes(buf)
        assert not hasattr(store, "timestamp_spans") or store.timestamp_spans is None
