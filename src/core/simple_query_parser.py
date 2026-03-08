"""Simple query language parser."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from beartype import beartype

from src.models.log_entry import LogEntry


@dataclass
class OrExpr:
    """OR expression in AST."""
    operands: list[ASTNode]


@dataclass
class AndExpr:
    """AND expression in AST."""
    operands: list[ASTNode]


@dataclass
class NotExpr:
    """NOT expression in AST."""
    operand: ASTNode


@dataclass
class Literal:
    """Literal text in AST."""
    text: str


ASTNode = OrExpr | AndExpr | NotExpr | Literal


class QueryTokenizer:
    """Tokenizer for simple query language."""
    
    @beartype
    def __init__(self, query: str):
        self.query = query
        self.pos = 0
        self._length = len(query)
    
    @beartype
    def tokenize(self) -> list[tuple[str, str]]:
        """
        Tokenize the query string.
        
        Returns:
            List of (type, value) tuples
            Types: 'LITERAL', 'AND', 'OR', 'NOT', 'LPAREN', 'RPAREN'
            
        Raises:
            ValueError: If query contains invalid tokens
        """
        tokens: list[tuple[str, str]] = []
        
        while self.pos < self._length:
            self._skip_whitespace()
            
            if self.pos >= self._length:
                break
            
            char = self.query[self.pos]
            
            if char == '`':
                tokens.append(self._read_literal())
            elif char == '(':
                tokens.append(('LPAREN', '('))
                self.pos += 1
            elif char == ')':
                tokens.append(('RPAREN', ')'))
                self.pos += 1
            elif self._peek_keyword('and'):
                tokens.append(('AND', 'and'))
                self.pos += 3
            elif self._peek_keyword('or'):
                tokens.append(('OR', 'or'))
                self.pos += 2
            elif self._peek_keyword('not'):
                tokens.append(('NOT', 'not'))
                self.pos += 3
            else:
                raise ValueError(
                    f"Unexpected character at position {self.pos}: '{char}'"
                )
        
        return tokens
    
    def _skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while self.pos < self._length and self.query[self.pos].isspace():
            self.pos += 1
    
    @beartype
    def _peek_keyword(self, keyword: str) -> bool:
        """Check if keyword appears at current position."""
        end_pos = self.pos + len(keyword)
        if end_pos > self._length:
            return False
        
        # Check if the keyword matches
        if self.query[self.pos:end_pos].lower() != keyword:
            return False
        
        # Check that it's followed by whitespace or end of string
        if end_pos < self._length:
            next_char = self.query[end_pos]
            if not next_char.isspace() and next_char not in '()':
                return False
        
        return True
    
    def _read_literal(self) -> tuple[str, str]:
        """
        Read a literal enclosed in backticks.
        
        Handles escaped backticks with backslash.
        """
        # Skip opening backtick
        self.pos += 1
        
        text_chars: list[str] = []
        
        while self.pos < self._length:
            char = self.query[self.pos]
            
            if char == '\\' and self.pos + 1 < self._length:
                # Handle escape sequence
                next_char = self.query[self.pos + 1]
                if next_char == '`':
                    text_chars.append('`')
                    self.pos += 2
                else:
                    # Keep backslash if not escaping backtick
                    text_chars.append(char)
                    self.pos += 1
            elif char == '`':
                # End of literal
                self.pos += 1
                return ('LITERAL', ''.join(text_chars))
            else:
                text_chars.append(char)
                self.pos += 1
        
        raise ValueError("Unterminated literal - missing closing backtick")


class SimpleQueryParser:
    """Parser for simple query language."""
    
    @beartype
    def parse(self, query: str) -> ASTNode:
        """
        Parse a query string into an AST.
        
        Args:
            query: Query string like "`error` and not `warning`"
            
        Returns:
            AST root node
            
        Raises:
            ValueError: If query is malformed
        """
        if not query or not query.strip():
            # Empty query matches everything
            return Literal("")
        
        tokenizer = QueryTokenizer(query)
        tokens = tokenizer.tokenize()
        
        if not tokens:
            return Literal("")
        
        self._tokens = tokens
        self._pos = 0
        
        result = self._parse_or_expr()
        
        if self._pos < len(self._tokens):
            remaining = self._tokens[self._pos:]
            raise ValueError(
                f"Unexpected tokens after query: {remaining}"
            )
        
        return result
    
    @beartype
    def evaluate(self, node: ASTNode, entry: LogEntry) -> bool:
        """
        Evaluate AST against log entry.
        
        Args:
            node: AST node to evaluate
            entry: Log entry to check
            
        Returns:
            True if entry matches the query
        """
        if isinstance(node, Literal):
            if not node.text:
                return True
            # Case-insensitive search in raw line
            return node.text.lower() in entry.raw_line.lower()
        
        if isinstance(node, NotExpr):
            return not self.evaluate(node.operand, entry)
        
        if isinstance(node, AndExpr):
            return all(self.evaluate(op, entry) for op in node.operands)
        
        if isinstance(node, OrExpr):
            return any(self.evaluate(op, entry) for op in node.operands)
        
        # This should never happen with proper AST
        return False
    
    @beartype
    def compile(self, query: str) -> Callable[[LogEntry], bool]:
        """
        Parse and compile query into a callable.
        
        Args:
            query: Query string
            
        Returns:
            Callable that returns True if entry matches
        """
        ast = self.parse(query)
        
        def matcher(entry: LogEntry) -> bool:
            return self.evaluate(ast, entry)
        
        return matcher
    
    def _current_token(self) -> tuple[str, str] | None:
        """Get current token or None if at end."""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None
    
    def _advance(self) -> None:
        """Move to next token."""
        self._pos += 1
    
    def _parse_or_expr(self) -> ASTNode:
        """Parse OR expression: and_expr ( "or" and_expr )*"""
        operands: list[ASTNode] = [self._parse_and_expr()]
        
        while self._current_token() is not None:
            token = self._current_token()
            if token is None or token[0] != 'OR':
                break
            
            self._advance()  # consume 'or'
            operands.append(self._parse_and_expr())
        
        if len(operands) == 1:
            return operands[0]
        
        return OrExpr(operands=operands)
    
    def _parse_and_expr(self) -> ASTNode:
        """Parse AND expression: not_expr ( "and" not_expr )*"""
        operands: list[ASTNode] = [self._parse_not_expr()]
        
        while self._current_token() is not None:
            token = self._current_token()
            if token is None or token[0] != 'AND':
                break
            
            self._advance()  # consume 'and'
            operands.append(self._parse_not_expr())
        
        if len(operands) == 1:
            return operands[0]
        
        return AndExpr(operands=operands)
    
    def _parse_not_expr(self) -> ASTNode:
        """Parse NOT expression: "not" not_expr | primary"""
        token = self._current_token()
        
        if token is not None and token[0] == 'NOT':
            self._advance()  # consume 'not'
            operand = self._parse_not_expr()
            return NotExpr(operand=operand)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> ASTNode:
        """Parse primary: "`" text "`" | "(" or_expr ")" """
        token = self._current_token()
        
        if token is None:
            raise ValueError("Unexpected end of query")
        
        if token[0] == 'LITERAL':
            self._advance()
            return Literal(text=token[1])
        
        if token[0] == 'LPAREN':
            self._advance()  # consume '('
            expr = self._parse_or_expr()
            
            # Expect closing paren
            close_token = self._current_token()
            if close_token is None or close_token[0] != 'RPAREN':
                raise ValueError("Missing closing parenthesis")
            
            self._advance()  # consume ')'
            return expr
        
        raise ValueError(f"Unexpected token: {token}")