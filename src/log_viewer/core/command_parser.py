"""Command parser for Log Viewer TUI.

Grammar:
    command := name [ "/" flags "/" ] text
            |  name text
            |  name (zero-arg commands)

    flags   := flag ("," flag)*
    flag    := "cs" | "color=" <name> | "color=#" <hex>
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ParseError(Exception):
    """Raised when command syntax is invalid."""


_VALID_COMMANDS: set[str] = {
    "s", "sr", "ss",
    "f", "fr", "fs",
    "h", "hr", "hs",
    "rmf", "rmh",
    "lsf", "lsh", "lscat",
    "cate", "catd", "catea", "catda",
    "open", "reload",
    "preset", "presetl", "rmpreset", "lspreset",
    "theme", "q", "n", "N",
}

_ZERO_ARG_COMMANDS: set[str] = {
    "lsf", "lsh", "lscat",
    "catea", "catda",
    "q", "n", "N",
    "reload", "lspreset", "presetl",
    "rmf", "rmh",
}

_FLAG_COMMANDS: set[str] = {
    "s", "sr", "ss",
    "f", "fr", "fs",
    "h", "hr", "hs",
}


@dataclass
class ParsedCommand:
    name: str
    flags: dict[str, str] = field(default_factory=dict)
    text: str = ""
    raw: str = ""


def parse_command(raw: str) -> ParsedCommand:
    """Parse a command string into a ParsedCommand."""
    stripped = raw.strip()

    if not stripped:
        raise ParseError("Empty command")

    name, rest, slash_delim = _extract_name(stripped)
    _validate_name(name)

    flags: dict[str, str] = {}
    text = ""

    if slash_delim and rest:
        flags, text = _parse_flagged(rest)
    elif rest:
        text = rest

    if not text and name not in _ZERO_ARG_COMMANDS:
        raise ParseError(f"Missing text argument for command '{name}'")

    return ParsedCommand(name=name, flags=flags, text=text, raw=raw)


def _extract_name(s: str) -> tuple[str, str, bool]:
    """Extract command name, remaining text, and whether '/' was the delimiter.

    Space always separates name from text.
    '/' only separates if the name is a flag-supporting command.
    """
    for i, ch in enumerate(s):
        if ch == " ":
            return s[:i], s[i + 1:], False
        if ch == "/":
            name = s[:i]
            if name in _FLAG_COMMANDS:
                return name, s[i + 1:], True
    return s, "", False


def _validate_name(name: str) -> None:
    """Validate command name is known."""
    if name not in _VALID_COMMANDS:
        raise ParseError(f"Unknown command: '{name}'")


def _parse_flagged(rest: str) -> tuple[dict[str, str], str]:
    """Parse flags/text after the first '/'. rest = 'flags/text'."""
    slash_idx = rest.find("/")

    if slash_idx == -1:
        raise ParseError("Missing closing '/' in flags")

    flags_str = rest[:slash_idx]
    text = rest[slash_idx + 1:]

    if not flags_str:
        raise ParseError("Empty flags section")

    flags = _parse_flags(flags_str)
    return flags, text


def _parse_flags(flags_str: str) -> dict[str, str]:
    """Parse comma-separated flags into dict."""
    flags: dict[str, str] = {}
    for part in flags_str.split(","):
        part = part.strip()
        if part == "cs":
            flags["cs"] = ""
        elif part.startswith("color="):
            flags["color"] = part[len("color="):]
        else:
            raise ParseError(f"Unknown flag: '{part}'")
    return flags
