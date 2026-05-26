"""Command parser for Log Viewer.

Grammar:
    command := name text
            |  name (zero-arg commands)
"""

from __future__ import annotations

from dataclasses import dataclass


class ParseError(Exception):
    """Raised when command syntax is invalid."""


_VALID_COMMANDS: set[str] = {
    "s", "sr", "ss",
    "f", "fr", "fs",
    "fn", "sn", "hn",
    "h", "hr", "hs",
    "rmf", "rmh",
    "cate", "catd",
    "open", "reload",
    "p", "pr", "ps", "pn",
    "rmp",
    "q",
}

_ZERO_ARG_COMMANDS: set[str] = {
    "cate", "catd",
    "q",
    "reload",
    "rmf", "rmh",
    "rmp",
}


@dataclass
class ParsedCommand:
    name: str
    text: str = ""
    raw: str = ""


def parse_command(raw: str) -> ParsedCommand:
    """Parse a command string into a ParsedCommand."""
    stripped = raw.strip()

    if not stripped:
        raise ParseError("Empty command")

    name, text = _extract_name(stripped)
    _validate_name(name)

    if not text and name not in _ZERO_ARG_COMMANDS:
        raise ParseError(f"Missing text argument for command '{name}'")

    return ParsedCommand(name=name, text=text, raw=raw)


def _extract_name(s: str) -> tuple[str, str]:
    """Extract command name and remaining text."""
    for i, ch in enumerate(s):
        if ch == " ":
            return s[:i], s[i + 1:]
    return s, ""


def _validate_name(name: str) -> None:
    """Validate command name is known."""
    if name not in _VALID_COMMANDS:
        raise ParseError(f"Unknown command: '{name}'")
