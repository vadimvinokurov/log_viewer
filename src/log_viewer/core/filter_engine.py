"""Filter/search/highlight matching engine.

Supports three matching modes:
- PLAIN: literal substring match (always case-insensitive)
- REGEX: regular expression search (always case-insensitive)
- SIMPLE: AND/OR/NOT query language via simple_query parser (always case-insensitive)
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
        return _match_plain(text, filt.pattern)
    elif filt.mode == SearchMode.REGEX:
        return _match_regex(text, filt.pattern)
    elif filt.mode == SearchMode.SIMPLE:
        return _match_simple(text, filt.pattern)
    elif filt.mode == SearchMode.LINE_NUMBER:
        return True
    return False


def _match_plain(text: str, pattern: str) -> bool:
    """Literal substring match (case-insensitive)."""
    return pattern.lower() in text.lower()


def _match_regex(text: str, pattern: str) -> bool:
    """Regular expression search (case-insensitive)."""
    try:
        return re.search(pattern, text, re.IGNORECASE) is not None
    except re.error as e:
        raise RegexError(f"Invalid regex: {e}") from e


def _match_simple(text: str, pattern: str) -> bool:
    """Simple query language match (AND/OR/NOT). Uses cached AST."""
    try:
        ast = parse_query(pattern)
        return ast.evaluate(text)
    except QuerySyntaxError:
        return False


def find_spans(
    text: str, pattern: str, mode: SearchMode
) -> list[tuple[int, int]]:
    """Find all match spans (start, end) for a pattern in text."""
    if mode == SearchMode.PLAIN:
        return _find_plain_spans(text, pattern)
    elif mode == SearchMode.REGEX:
        return _find_regex_spans(text, pattern)
    elif mode == SearchMode.SIMPLE:
        return _find_simple_spans(text, pattern)
    elif mode == SearchMode.LINE_NUMBER:
        return [(0, len(text))] if text else []
    return []


def _find_plain_spans(
    text: str, pattern: str
) -> list[tuple[int, int]]:
    """Find all substring match spans (case-insensitive)."""
    if not pattern:
        return []
    spans: list[tuple[int, int]] = []
    search_text = text.lower()
    search_pattern = pattern.lower()
    start = 0
    while True:
        idx = search_text.find(search_pattern, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(pattern)))
        start = idx + 1
    return spans


def _find_regex_spans(
    text: str, pattern: str
) -> list[tuple[int, int]]:
    """Find all regex match spans (case-insensitive)."""
    try:
        return [(m.start(), m.end()) for m in re.finditer(pattern, text, re.IGNORECASE)]
    except re.error:
        return []


def _find_simple_spans(
    text: str, pattern: str
) -> list[tuple[int, int]]:
    """Find all simple query match spans. Uses cached AST."""
    try:
        ast = parse_query(pattern)
        return ast.find_spans(text)
    except QuerySyntaxError:
        return []


def batch_match(
    texts: list[str],
    filters: list[Filter],
    pre_lowered: list[str] | None = None,
) -> set[int]:
    """Match multiple filters against multiple texts. Returns set of matching indices.

    Plain filters are merged into a single compiled regex
    via alternation for O(n) instead of O(n*m) matching.
    """
    if not texts:
        return set()
    if not filters:
        return set(range(len(texts)))

    matching: set[int] = set()

    # Group plain filters for batch regex
    plain: list[str] = []
    other_filters: list[Filter] = []
    for f in filters:
        if f.mode == SearchMode.PLAIN:
            plain.append(re.escape(f.pattern))
        else:
            other_filters.append(f)

    # Batch-match all plain filters with one compiled regex
    if plain:
        combined = re.compile("|".join(plain), re.IGNORECASE)
        if pre_lowered is not None:
            for i, low in enumerate(pre_lowered):
                if combined.search(low):
                    matching.add(i)
        else:
            for i, text in enumerate(texts):
                if combined.search(text):
                    matching.add(i)

    # Handle remaining filters individually
    for f in other_filters:
        for i, text in enumerate(texts):
            if i not in matching and match(text, f):
                matching.add(i)

    return matching


# --- Bytes-based matching ---


def match_bytes(text: bytes, filt: Filter) -> bool:
    """Check if byte text matches the filter pattern.

    Plain and regex modes work directly on bytes.
    Simple query falls back to str decoding.
    """
    if filt.mode == SearchMode.PLAIN:
        return _match_plain_bytes(text, filt.pattern)
    elif filt.mode == SearchMode.REGEX:
        return _match_regex_bytes(text, filt.pattern)
    elif filt.mode == SearchMode.SIMPLE:
        return _match_simple(text.decode("utf-8", errors="replace"), filt.pattern)
    return False


def _match_plain_bytes(text: bytes, pattern: str) -> bool:
    return pattern.lower().encode("utf-8") in text.lower()


def _match_regex_bytes(text: bytes, pattern: str) -> bool:
    try:
        return re.search(pattern.encode("utf-8"), text, re.IGNORECASE) is not None
    except re.error as e:
        raise RegexError(f"Invalid regex: {e}") from e


def batch_match_bytes(
    messages: list[bytes],
    filters: list[Filter],
) -> set[int]:
    """Match multiple filters against multiple byte messages. Returns set of matching indices.

    Plain filters are merged into a single compiled bytes regex.
    """
    if not messages:
        return set()
    if not filters:
        return set(range(len(messages)))

    matching: set[int] = set()

    plain: list[bytes] = []
    other_filters: list[Filter] = []
    for f in filters:
        if f.mode == SearchMode.PLAIN:
            plain.append(re.escape(f.pattern).encode("utf-8"))
        else:
            other_filters.append(f)

    if plain:
        combined = re.compile(b"|".join(plain), re.IGNORECASE)
        for i, msg in enumerate(messages):
            if combined.search(msg):
                matching.add(i)

    for f in other_filters:
        for i, msg in enumerate(messages):
            if i not in matching and match_bytes(msg, f):
                matching.add(i)

    return matching
