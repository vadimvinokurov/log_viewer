"""Simple query language parser for Log Viewer.

Grammar:
    expression := or_expr
    or_expr    := and_expr ("OR" and_expr)*
    and_expr   := not_expr ("AND" not_expr)*
    not_expr   := "NOT" not_expr | primary
    primary    := "(" expression ")" | STRING
    STRING     := '"' ... '"'

Precedence: NOT > AND > OR
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class QuerySyntaxError(Exception):
    """Raised when query syntax is invalid."""


class QueryNode(ABC):
    """Base class for query AST nodes."""

    @abstractmethod
    def evaluate(self, text: str, case_sensitive: bool = False) -> bool: ...

    @abstractmethod
    def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]: ...


@dataclass
class TermNode(QueryNode):
    """Leaf node — matches substring in text."""

    text: str

    def evaluate(self, text: str, case_sensitive: bool = False) -> bool:
        if case_sensitive:
            return self.text in text
        return self.text.lower() in text.lower()

    def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        search_text = text if case_sensitive else text.lower()
        search_term = self.text if case_sensitive else self.text.lower()
        start = 0
        while True:
            idx = search_text.find(search_term, start)
            if idx == -1:
                break
            spans.append((idx, idx + len(self.text)))
            start = idx + 1
        return spans


@dataclass
class AndNode(QueryNode):
    """Conjunction — both children must match."""

    left: QueryNode
    right: QueryNode

    def evaluate(self, text: str, case_sensitive: bool = False) -> bool:
        return self.left.evaluate(text, case_sensitive) and self.right.evaluate(
            text, case_sensitive
        )

    def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
        return self.left.find_spans(text, case_sensitive) + self.right.find_spans(text, case_sensitive)


@dataclass
class OrNode(QueryNode):
    """Disjunction — either child must match."""

    left: QueryNode
    right: QueryNode

    def evaluate(self, text: str, case_sensitive: bool = False) -> bool:
        return self.left.evaluate(text, case_sensitive) or self.right.evaluate(
            text, case_sensitive
        )

    def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
        return self.left.find_spans(text, case_sensitive) + self.right.find_spans(text, case_sensitive)


@dataclass
class NotNode(QueryNode):
    """Negation — child must NOT match."""

    child: QueryNode

    def evaluate(self, text: str, case_sensitive: bool = False) -> bool:
        return not self.child.evaluate(text, case_sensitive)

    def find_spans(self, text: str, case_sensitive: bool = False) -> list[tuple[int, int]]:
        return []


class _Parser:
    """Recursive descent parser for the simple query language."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0

    def parse(self) -> QueryNode:
        node = self._or_expr()
        self._skip_whitespace()
        if self.pos < len(self.source):
            raise QuerySyntaxError(
                f"Unexpected character at position {self.pos}: "
                f"'{self.source[self.pos]}'"
            )
        return node

    def _or_expr(self) -> QueryNode:
        left = self._and_expr()
        while self._match_keyword("OR"):
            right = self._and_expr()
            left = OrNode(left=left, right=right)
        return left

    def _and_expr(self) -> QueryNode:
        left = self._not_expr()
        while self._match_keyword("AND"):
            right = self._not_expr()
            left = AndNode(left=left, right=right)
        return left

    def _not_expr(self) -> QueryNode:
        if self._match_keyword("NOT"):
            child = self._not_expr()
            return NotNode(child=child)
        return self._primary()

    def _primary(self) -> QueryNode:
        self._skip_whitespace()

        if self.pos >= len(self.source):
            raise QuerySyntaxError("Unexpected end of query")

        if self.source[self.pos] == "(":
            self.pos += 1  # skip (
            node = self._or_expr()
            self._skip_whitespace()
            if self.pos >= len(self.source) or self.source[self.pos] != ")":
                raise QuerySyntaxError("Missing closing ')'")
            self.pos += 1  # skip )
            return node

        if self.source[self.pos] == '"':
            return self._string()

        raise QuerySyntaxError(
            f"Expected '\"' or '(' at position {self.pos}, "
            f"got '{self.source[self.pos]}'"
        )

    def _string(self) -> TermNode:
        self.pos += 1  # skip opening "
        start = self.pos
        while self.pos < len(self.source) and self.source[self.pos] != '"':
            self.pos += 1

        if self.pos >= len(self.source):
            raise QuerySyntaxError("Unclosed string literal")

        text = self.source[start : self.pos]
        self.pos += 1  # skip closing "

        if not text:
            raise QuerySyntaxError("Empty string")

        return TermNode(text=text)

    def _match_keyword(self, keyword: str) -> bool:
        self._skip_whitespace()
        end = self.pos + len(keyword)
        if end > len(self.source):
            return False
        word = self.source[self.pos : end]
        if word.upper() != keyword:
            return False
        # Ensure keyword boundary — next char must be whitespace or end
        if end < len(self.source) and self.source[end] not in (" ", "\t"):
            return False
        self.pos = end
        self._skip_whitespace()
        return True

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] in (" ", "\t"):
            self.pos += 1


def parse_query(source: str) -> QueryNode:
    """Parse a simple query expression into an AST."""
    parser = _Parser(source)
    return parser.parse()
