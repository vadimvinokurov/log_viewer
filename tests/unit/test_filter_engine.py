"""Tests for filter_engine.py — RED phase."""

from __future__ import annotations

import pytest

from log_viewer.core.filter_engine import find_spans, match, RegexError
from log_viewer.core.models import Filter, SearchMode


class TestPlainMatch:
    """Test plain text matching."""

    def test_plain_match_found(self) -> None:
        f = Filter(pattern="error", mode=SearchMode.PLAIN, case_sensitive=False)
        assert match("An error occurred", f) is True

    def test_plain_match_not_found(self) -> None:
        f = Filter(pattern="timeout", mode=SearchMode.PLAIN, case_sensitive=False)
        assert match("An error occurred", f) is False

    def test_plain_case_insensitive(self) -> None:
        f = Filter(pattern="error", mode=SearchMode.PLAIN, case_sensitive=False)
        assert match("An ERROR occurred", f) is True
        assert match("An Error occurred", f) is True

    def test_plain_case_sensitive(self) -> None:
        f = Filter(pattern="ERROR", mode=SearchMode.PLAIN, case_sensitive=True)
        assert match("An ERROR occurred", f) is True
        assert match("An error occurred", f) is False

    def test_plain_substring_match(self) -> None:
        f = Filter(pattern="fail", mode=SearchMode.PLAIN, case_sensitive=False)
        assert match("Failed to open", f) is True

    def test_plain_empty_pattern(self) -> None:
        f = Filter(pattern="", mode=SearchMode.PLAIN, case_sensitive=False)
        assert match("any text", f) is True

    def test_plain_empty_text(self) -> None:
        f = Filter(pattern="error", mode=SearchMode.PLAIN, case_sensitive=False)
        assert match("", f) is False

    def test_plain_matches_full_line(self) -> None:
        f = Filter(pattern="LOG_ERROR", mode=SearchMode.PLAIN, case_sensitive=False)
        line = "2024-01-01 app LOG_ERROR Something broke"
        assert match(line, f) is True


class TestRegexMatch:
    """Test regex matching."""

    def test_regex_match(self) -> None:
        f = Filter(pattern=r"error_\d+", mode=SearchMode.REGEX, case_sensitive=False)
        assert match("error_42 occurred", f) is True

    def test_regex_no_match(self) -> None:
        f = Filter(pattern=r"error_\d+", mode=SearchMode.REGEX, case_sensitive=False)
        assert match("no match here", f) is False

    def test_regex_case_insensitive(self) -> None:
        f = Filter(pattern=r"error_\d+", mode=SearchMode.REGEX, case_sensitive=False)
        assert match("ERROR_42 occurred", f) is True

    def test_regex_case_sensitive(self) -> None:
        f = Filter(pattern=r"error_\d+", mode=SearchMode.REGEX, case_sensitive=True)
        assert match("error_42 occurred", f) is True
        assert match("ERROR_42 occurred", f) is False

    def test_regex_invalid_raises(self) -> None:
        f = Filter(pattern=r"[invalid", mode=SearchMode.REGEX, case_sensitive=False)
        with pytest.raises(RegexError):
            match("some text", f)

    def test_regex_complex_pattern(self) -> None:
        f = Filter(
            pattern=r"\d{4}-\d{2}-\d{2}", mode=SearchMode.REGEX, case_sensitive=False
        )
        assert match("Date: 2024-01-15", f) is True
        assert match("No date here", f) is False

    def test_regex_word_boundary(self) -> None:
        f = Filter(pattern=r"\berror\b", mode=SearchMode.REGEX, case_sensitive=False)
        assert match("error occurred", f) is True
        assert match("errors occurred", f) is False


class TestSimpleMatch:
    """Test simple query matching (AND/OR/NOT)."""

    def test_simple_single_term(self) -> None:
        f = Filter(pattern='"error"', mode=SearchMode.SIMPLE, case_sensitive=False)
        assert match("An error occurred", f) is True

    def test_simple_single_term_no_match(self) -> None:
        f = Filter(pattern='"error"', mode=SearchMode.SIMPLE, case_sensitive=False)
        assert match("No issues", f) is False

    def test_simple_and(self) -> None:
        f = Filter(
            pattern='"Failed" AND "config"', mode=SearchMode.SIMPLE, case_sensitive=False
        )
        assert match("Failed to load config", f) is True
        assert match("Failed to open file", f) is False

    def test_simple_or(self) -> None:
        f = Filter(
            pattern='"Failed" OR "Successfully"',
            mode=SearchMode.SIMPLE,
            case_sensitive=False,
        )
        assert match("Failed to load", f) is True
        assert match("Successfully loaded", f) is True
        assert match("Error occurred", f) is False

    def test_simple_not(self) -> None:
        f = Filter(
            pattern='NOT "warning"', mode=SearchMode.SIMPLE, case_sensitive=False
        )
        assert match("error occurred", f) is True
        assert match("warning issued", f) is False

    def test_simple_case_sensitive(self) -> None:
        f = Filter(
            pattern='"ERROR"', mode=SearchMode.SIMPLE, case_sensitive=True
        )
        assert match("ERROR occurred", f) is True
        assert match("error occurred", f) is False

    def test_simple_invalid_query_raises(self) -> None:
        f = Filter(pattern="unquoted", mode=SearchMode.SIMPLE, case_sensitive=False)
        with pytest.raises(Exception):
            match("some text", f)


class TestFindSpansPlain:
    """Test find_spans with plain text mode."""

    def test_plain_single_span(self) -> None:
        spans = find_spans("An error occurred", "error", SearchMode.PLAIN)
        assert spans == [(3, 8)]

    def test_plain_multiple_spans(self) -> None:
        spans = find_spans("error and error again", "error", SearchMode.PLAIN)
        assert spans == [(0, 5), (10, 15)]

    def test_plain_no_match(self) -> None:
        spans = find_spans("no match here", "timeout", SearchMode.PLAIN)
        assert spans == []

    def test_plain_case_insensitive(self) -> None:
        spans = find_spans("An ERROR occurred", "error", SearchMode.PLAIN, case_sensitive=False)
        assert spans == [(3, 8)]

    def test_plain_case_sensitive(self) -> None:
        spans = find_spans("An ERROR occurred", "error", SearchMode.PLAIN, case_sensitive=True)
        assert spans == []

    def test_plain_case_sensitive_match(self) -> None:
        spans = find_spans("An ERROR occurred", "ERROR", SearchMode.PLAIN, case_sensitive=True)
        assert spans == [(3, 8)]

    def test_plain_empty_text(self) -> None:
        spans = find_spans("", "error", SearchMode.PLAIN)
        assert spans == []

    def test_plain_empty_pattern(self) -> None:
        spans = find_spans("hello", "", SearchMode.PLAIN)
        assert spans == []


class TestFindSpansRegex:
    """Test find_spans with regex mode."""

    def test_regex_single_span(self) -> None:
        spans = find_spans("error_42 occurred", r"error_\d+", SearchMode.REGEX)
        assert spans == [(0, 8)]

    def test_regex_multiple_spans(self) -> None:
        spans = find_spans("error_1 and error_2", r"error_\d+", SearchMode.REGEX)
        assert spans == [(0, 7), (12, 19)]

    def test_regex_no_match(self) -> None:
        spans = find_spans("no match", r"error_\d+", SearchMode.REGEX)
        assert spans == []

    def test_regex_case_insensitive(self) -> None:
        spans = find_spans("ERROR_42", r"error_\d+", SearchMode.REGEX, case_sensitive=False)
        assert spans == [(0, 8)]

    def test_regex_case_sensitive(self) -> None:
        spans = find_spans("ERROR_42", r"error_\d+", SearchMode.REGEX, case_sensitive=True)
        assert spans == []

    def test_regex_invalid_pattern_returns_empty(self) -> None:
        spans = find_spans("some text", r"[invalid", SearchMode.REGEX)
        assert spans == []


class TestFindSpansSimple:
    """Test find_spans with simple query mode."""

    def test_simple_single_term(self) -> None:
        spans = find_spans("An error occurred", '"error"', SearchMode.SIMPLE)
        assert spans == [(3, 8)]

    def test_simple_and_combines_spans(self) -> None:
        spans = find_spans("Failed to load config", '"Failed" AND "config"', SearchMode.SIMPLE)
        assert (0, 6) in spans  # "Failed"
        assert (15, 21) in spans  # "config"

    def test_simple_or_combines_spans(self) -> None:
        spans = find_spans("Failed but ok", '"Failed" OR "ok"', SearchMode.SIMPLE)
        assert (0, 6) in spans
        assert (11, 13) in spans

    def test_simple_not_returns_empty(self) -> None:
        spans = find_spans("warning issued", 'NOT "warning"', SearchMode.SIMPLE)
        assert spans == []

    def test_simple_invalid_query_returns_empty(self) -> None:
        spans = find_spans("some text", "unquoted", SearchMode.SIMPLE)
        assert spans == []
