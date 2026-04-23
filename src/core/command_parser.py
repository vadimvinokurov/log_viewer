"""Command parser for Vim-style command bar."""
from __future__ import annotations

from dataclasses import dataclass

from beartype import beartype


@dataclass(frozen=True)
class ParsedCommand:
    """Result of parsing a command string."""

    action: str           # "s", "f", "h", "rmf", "rmh", "n", "N"
    mode: str             # "plain", "regex", "simple"
    case_sensitive: bool  # False by default, True if /cs flag present
    color: str | None     # Highlight color, None if not specified
    text: str             # Query text (empty string for no-arg commands)
    direction: str        # "forward" or "backward"


class ParseError(Exception):
    """Raised when a command cannot be parsed."""


# Multi-char actions checked first, then single-char.
_ACTIONS: tuple[str, ...] = ("rmf", "rmh", "s", "f", "h", "n", "N")
# Actions that accept a mode suffix.
_MODE_ACTIONS: frozenset[str] = frozenset({"s", "f", "h"})
# Actions that never take text.
_NO_TEXT_ACTIONS: frozenset[str] = frozenset({"n", "N"})


def _extract_action(raw: str) -> tuple[str, str]:
    """Return (action, remainder) after stripping the action prefix."""
    for action in _ACTIONS:
        if raw.startswith(action):
            return action, raw[len(action):]
    raise ParseError(f"Unknown command: {raw[:3] if len(raw) > 3 else raw}")


def _extract_flags_and_text(remainder: str) -> tuple[bool, str | None, str]:
    """Parse optional flags and extract text from the remainder after action+mode.

    Flag section starts with '/' and contains '/' delimited flag tokens.
    Known flags: "cs", "color=<value>". We greedily consume known-flag segments
    from the start. The first segment that isn't a known flag marks the boundary:
    everything from there (rejoined with '/') is text.

    Special cases:
    - "//text" (empty first segment) is an error (empty flags).
    - Single segment that isn't a flag (e.g. "/error_\\d+") means the '/' was
      a separator and the whole thing is text.
    """
    if not remainder:
        return False, None, ""

    if remainder[0] == "/":
        segments = remainder[1:].split("/")

        # Empty first segment means "//..." which is empty flags error
        if segments and segments[0] == "" and len(segments) > 1:
            raise ParseError("Empty flags not allowed")

        # Greedily consume valid flag segments from the start
        case_sensitive = False
        color: str | None = None
        flag_count = 0

        for seg in segments:
            if seg == "cs":
                case_sensitive = True
                flag_count += 1
            elif seg.startswith("color="):
                color = seg[6:]
                flag_count += 1
            else:
                break

        if flag_count == 0:
            # Single segment that isn't a flag: "/text" — separator, not flags
            if len(segments) == 1:
                return False, None, remainder[1:]
            # Multiple segments, none valid: likely intended flags but mistyped
            raise ParseError(f"Unknown flag: {segments[0]}")

        text = "/".join(segments[flag_count:])
        return case_sensitive, color, text

    # Space separator: first space is separator, rest is text.
    # Double space preserves leading space.
    if remainder[0] == " ":
        return False, None, remainder[1:]

    # No separator, no flags — remainder is text directly (e.g. after mode suffix)
    return False, None, remainder


class CommandParser:
    """Parses command strings into ParsedCommand objects."""

    @staticmethod
    @beartype
    def parse(raw: str, direction: str = "forward") -> ParsedCommand:
        """Parse a raw command string.

        Args:
            raw: Command text (without the leading : prefix).
            direction: "forward" or "backward".

        Returns:
            ParsedCommand with all fields populated.

        Raises:
            ParseError: If the command cannot be parsed.
        """
        stripped = raw.strip()
        if not stripped:
            raise ParseError("Empty command")

        action, remainder = _extract_action(stripped)

        # Extract mode suffix (only for s, f, h)
        mode = "plain"
        if action in _MODE_ACTIONS and remainder and remainder[0] in ("r", "s"):
            mode_char = remainder[0]
            remainder = remainder[1:]
            if mode_char == "r":
                mode = "regex"
            elif mode_char == "s":
                mode = "simple"

        # Navigation commands never take text
        if action in _NO_TEXT_ACTIONS:
            return ParsedCommand(
                action=action,
                mode=mode,
                case_sensitive=False,
                color=None,
                text="",
                direction=direction,
            )

        case_sensitive, color, text = _extract_flags_and_text(remainder)

        return ParsedCommand(
            action=action,
            mode=mode,
            case_sensitive=case_sensitive,
            color=color,
            text=text,
            direction=direction,
        )
