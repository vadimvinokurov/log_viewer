from __future__ import annotations

from dataclasses import dataclass, field

from beartype import beartype


@beartype
@dataclass
class SystemNode:
    """System node for tree view."""

    name: str
    path: str
    checked: bool = False
    children: list[SystemNode] = field(default_factory=list)