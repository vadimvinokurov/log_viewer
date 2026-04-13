"""Filter/search/highlight matching engine.

Supports three matching modes:
- PLAIN: literal substring match
- REGEX: regular expression search
- SIMPLE: AND/OR/NOT query language via simple_query parser
"""

from __future__ import annotations

import re

from log_viewer.core.models import Filter, SearchMode
from log_viewer.core.simple_query import parse_query, QuerySyntaxError


class RegexError(Exception):
    """Raised when a regex pattern is invalid."""


def match(text: str, filt: Filter) -> bool:
    """Check if text matches the filter pattern."""
    if filt.mode == SearchMode.PLAIN:
        return _match_plain(text, filt.pattern, filt.case_sensitive)
    elif filt.mode == SearchMode.REGEX:
        return _match_regex(text, filt.pattern, filt.case_sensitive)
    elif filt.mode == SearchMode.SIMPLE:
        return _match_simple(text, filt.pattern, filt.case_sensitive)
    return False


def _match_plain(text: str, pattern: str, case_sensitive: bool) -> bool:
    """Literal substring match."""
    if case_sensitive:
        return pattern in text
    return pattern.lower() in text.lower()


def _match_regex(text: str, pattern: str, case_sensitive: bool) -> bool:
    """Regular expression search."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.search(pattern, text, flags) is not None
    except re.error as e:
        raise RegexError(f"Invalid regex: {e}") from e


def _match_simple(text: str, pattern: str, case_sensitive: bool) -> bool:
    """Simple query language match (AND/OR/NOT)."""
    try:
        ast = parse_query(pattern)
        return ast.evaluate(text, case_sensitive)
    except QuerySyntaxError as e:
        raise QuerySyntaxError(f"Invalid query: {e}") from e


def find_spans(
    text: str, pattern: str, mode: SearchMode, case_sensitive: bool = False
) -> list[tuple[int, int]]:
    """Find all match spans (start, end) for a pattern in text."""
    if mode == SearchMode.PLAIN:
        return _find_plain_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.REGEX:
        return _find_regex_spans(text, pattern, case_sensitive)
    elif mode == SearchMode.SIMPLE:
        return _find_simple_spans(text, pattern, case_sensitive)
    return []


def _find_plain_spans(
    text: str, pattern: str, case_sensitive: bool
) -> list[tuple[int, int]]:
    """Find all substring match spans."""
    if not pattern:
        return []
    spans: list[tuple[int, int]] = []
    search_text = text if case_sensitive else text.lower()
    search_pattern = pattern if case_sensitive else pattern.lower()
    start = 0
    while True:
        idx = search_text.find(search_pattern, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(pattern)))
        start = idx + 1
    return spans


def _find_regex_spans(
    text: str, pattern: str, case_sensitive: bool
) -> list[tuple[int, int]]:
    """Find all regex match spans."""
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        return [(m.start(), m.end()) for m in re.finditer(pattern, text, flags)]
    except re.error:
        return []


def _find_simple_spans(
    text: str, pattern: str, case_sensitive: bool
) -> list[tuple[int, int]]:
    """Find all simple query match spans."""
    try:
        ast = parse_query(pattern)
        return ast.find_spans(text, case_sensitive)
    except QuerySyntaxError:
        return []
