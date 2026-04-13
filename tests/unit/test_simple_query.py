"""Tests for simple_query.py — RED phase."""

from __future__ import annotations

import pytest

from log_viewer.core.simple_query import (
    parse_query,
    QuerySyntaxError,
    TermNode,
    AndNode,
    OrNode,
    NotNode,
)


class TestSingleTerm:
    """Test single quoted term."""

    def test_single_term(self) -> None:
        node = parse_query('"error"')
        assert isinstance(node, TermNode)
        assert node.text == "error"

    def test_single_term_case_insensitive(self) -> None:
        node = parse_query('"ERROR"')
        assert isinstance(node, TermNode)
        assert node.text == "ERROR"

    def test_term_with_spaces(self) -> None:
        node = parse_query('"Failed to open"')
        assert isinstance(node, TermNode)
        assert node.text == "Failed to open"

    def test_term_evaluate_matches(self) -> None:
        node = parse_query('"error"')
        assert node.evaluate("An error occurred", case_sensitive=False) is True

    def test_term_evaluate_no_match(self) -> None:
        node = parse_query('"timeout"')
        assert node.evaluate("An error occurred", case_sensitive=False) is False

    def test_term_evaluate_case_sensitive(self) -> None:
        node = parse_query('"ERROR"')
        assert node.evaluate("An error occurred", case_sensitive=True) is False
        assert node.evaluate("An ERROR occurred", case_sensitive=True) is True

    def test_term_evaluate_case_insensitive_default(self) -> None:
        node = parse_query('"error"')
        assert node.evaluate("An ERROR occurred", case_sensitive=False) is True


class TestAndNode:
    """Test AND expressions."""

    def test_two_terms_and(self) -> None:
        node = parse_query('"Failed" AND "config"')
        assert isinstance(node, AndNode)
        assert isinstance(node.left, TermNode)
        assert isinstance(node.right, TermNode)

    def test_and_evaluate_both_match(self) -> None:
        node = parse_query('"Failed" AND "config"')
        assert node.evaluate("Failed to load config file", case_sensitive=False) is True

    def test_and_evaluate_one_match(self) -> None:
        node = parse_query('"Failed" AND "config"')
        assert node.evaluate("Failed to open file", case_sensitive=False) is False

    def test_and_evaluate_none_match(self) -> None:
        node = parse_query('"Failed" AND "config"')
        assert node.evaluate("Successfully loaded", case_sensitive=False) is False

    def test_three_terms_and(self) -> None:
        node = parse_query('"a" AND "b" AND "c"')
        assert isinstance(node, AndNode)
        assert node.evaluate("a b c", case_sensitive=False) is True
        assert node.evaluate("a b", case_sensitive=False) is False


class TestOrNode:
    """Test OR expressions."""

    def test_two_terms_or(self) -> None:
        node = parse_query('"Failed" OR "Successfully"')
        assert isinstance(node, OrNode)

    def test_or_evaluate_first_match(self) -> None:
        node = parse_query('"Failed" OR "Successfully"')
        assert node.evaluate("Failed to open", case_sensitive=False) is True

    def test_or_evaluate_second_match(self) -> None:
        node = parse_query('"Failed" OR "Successfully"')
        assert node.evaluate("Successfully loaded", case_sensitive=False) is True

    def test_or_evaluate_none_match(self) -> None:
        node = parse_query('"Failed" OR "Successfully"')
        assert node.evaluate("Error occurred", case_sensitive=False) is False

    def test_three_terms_or(self) -> None:
        node = parse_query('"a" OR "b" OR "c"')
        assert node.evaluate("x c y", case_sensitive=False) is True
        assert node.evaluate("x y z", case_sensitive=False) is False


class TestNotNode:
    """Test NOT expressions."""

    def test_not_term(self) -> None:
        node = parse_query('NOT "warning"')
        assert isinstance(node, NotNode)
        assert isinstance(node.child, TermNode)

    def test_not_evaluate_match(self) -> None:
        node = parse_query('NOT "warning"')
        assert node.evaluate("this is a warning", case_sensitive=False) is False

    def test_not_evaluate_no_match(self) -> None:
        node = parse_query('NOT "warning"')
        assert node.evaluate("this is an error", case_sensitive=False) is True


class TestPrecedence:
    """Test operator precedence: NOT > AND > OR."""

    def test_and_has_higher_precedence_than_or(self) -> None:
        # "a" OR "b" AND "c" → "a" OR ("b" AND "c")
        node = parse_query('"a" OR "b" AND "c"')
        assert isinstance(node, OrNode)
        assert isinstance(node.right, AndNode)

    def test_not_has_higher_precedence_than_and(self) -> None:
        # NOT "a" AND "b" → (NOT "a") AND "b"
        node = parse_query('NOT "a" AND "b"')
        assert isinstance(node, AndNode)
        assert isinstance(node.left, NotNode)

    def test_not_has_higher_precedence_than_or(self) -> None:
        # NOT "a" OR "b" → (NOT "a") OR "b"
        node = parse_query('NOT "a" OR "b"')
        assert isinstance(node, OrNode)
        assert isinstance(node.left, NotNode)


class TestGrouping:
    """Test parenthesized expressions."""

    def test_grouped_or_with_and(self) -> None:
        # ("a" OR "b") AND "c" → AND(OR(a, b), c)
        node = parse_query('("a" OR "b") AND "c"')
        assert isinstance(node, AndNode)
        assert isinstance(node.left, OrNode)

    def test_nested_grouping(self) -> None:
        node = parse_query('(("a"))')
        assert isinstance(node, TermNode)
        assert node.text == "a"


class TestComplexExpressions:
    """Test complex real-world expressions."""

    def test_and_or_combined(self) -> None:
        node = parse_query('"Failed" AND "config" OR "timeout"')
        # Precedence: AND first → OR(Term("timeout"), AND(Term("Failed"), Term("config")))
        assert isinstance(node, OrNode)

    def test_not_with_and(self) -> None:
        node = parse_query('NOT "warning" AND "error"')
        # (NOT "warning") AND "error"
        assert isinstance(node, AndNode)
        assert node.evaluate("error occurred", case_sensitive=False) is True
        assert node.evaluate("warning error", case_sensitive=False) is False

    def test_full_complex(self) -> None:
        # NOT "debug" AND ("error" OR "critical")
        node = parse_query('NOT "debug" AND ("error" OR "critical")')
        assert node.evaluate("error occurred", case_sensitive=False) is True
        assert node.evaluate("debug error", case_sensitive=False) is False
        assert node.evaluate("info message", case_sensitive=False) is False


class TestCaseInsensitiveKeywords:
    """Test that AND/OR/NOT keywords work in any case."""

    def test_lowercase_or(self) -> None:
        node = parse_query('"Channel 0" or "LEECH"')
        assert isinstance(node, OrNode)
        assert node.evaluate("Channel 0 active", case_sensitive=False) is True
        assert node.evaluate("LEECH connected", case_sensitive=False) is True
        assert node.evaluate("random text", case_sensitive=False) is False

    def test_lowercase_and(self) -> None:
        node = parse_query('"error" and "config"')
        assert isinstance(node, AndNode)
        assert node.evaluate("error in config file", case_sensitive=False) is True

    def test_lowercase_not(self) -> None:
        node = parse_query('not "warning"')
        assert isinstance(node, NotNode)
        assert node.evaluate("this is an error", case_sensitive=False) is True

    def test_mixed_case_keywords(self) -> None:
        node = parse_query('"a" Or "b"')
        assert isinstance(node, OrNode)

    def test_mixed_case_and_or(self) -> None:
        node = parse_query('"a" And "b" Or "c"')
        assert isinstance(node, OrNode)
        assert isinstance(node.left, AndNode)


class TestErrors:
    """Test syntax errors."""

    def test_unquoted_term(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query("error")

    def test_missing_closing_quote(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query('"error')

    def test_empty_string(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query('""')

    def test_missing_right_operand_and(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query('"error" AND')

    def test_missing_right_operand_or(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query('"error" OR')

    def test_missing_operand_after_not(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query("NOT")

    def test_unclosed_parenthesis(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query('("error"')

    def test_empty_parentheses(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query("()")

    def test_extra_closing_paren(self) -> None:
        with pytest.raises(QuerySyntaxError):
            parse_query('"error")')


class TestFindSpans:
    """Test find_spans on QueryNode AST nodes."""

    def test_term_find_spans_single(self) -> None:
        node = parse_query('"error"')
        assert node.find_spans("An error occurred", case_sensitive=False) == [(3, 8)]

    def test_term_find_spans_multiple(self) -> None:
        node = parse_query('"error"')
        spans = node.find_spans("error and error again", case_sensitive=False)
        assert spans == [(0, 5), (10, 15)]

    def test_term_find_spans_case_sensitive(self) -> None:
        node = parse_query('"ERROR"')
        assert node.find_spans("An ERROR occurred", case_sensitive=True) == [(3, 8)]
        assert node.find_spans("An error occurred", case_sensitive=True) == []

    def test_term_find_spans_no_match(self) -> None:
        node = parse_query('"timeout"')
        assert node.find_spans("An error occurred", case_sensitive=False) == []

    def test_and_find_spans_combines_children(self) -> None:
        node = parse_query('"Failed" AND "config"')
        spans = node.find_spans("Failed to load config", case_sensitive=False)
        assert (0, 6) in spans  # "Failed"
        assert (15, 21) in spans  # "config"

    def test_or_find_spans_combines_children(self) -> None:
        node = parse_query('"Failed" OR "ok"')
        spans = node.find_spans("Failed but ok", case_sensitive=False)
        assert (0, 6) in spans  # "Failed"
        assert (11, 13) in spans  # "ok"

    def test_not_find_spans_returns_empty(self) -> None:
        node = parse_query('NOT "warning"')
        assert node.find_spans("warning issued", case_sensitive=False) == []
