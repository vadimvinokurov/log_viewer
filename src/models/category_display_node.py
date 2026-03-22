from __future__ import annotations

from dataclasses import dataclass, field

from beartype import beartype


@beartype
@dataclass
class CategoryDisplayNode:
    """Display node for category tree view in UI.
    
    This is a data transfer object (DTO) that transforms the internal
    CategoryTree/CategoryNode structure into a format suitable for
    display in the CategoryPanel's tree view.
    
    Attributes:
        name: Display name (e.g., "app" from "HordeMode/scripts/app")
        path: Full category path (e.g., "HordeMode/scripts/app")
        checked: Checkbox state for UI display
        children: Child nodes for hierarchical display
    
    Example:
        >>> node = CategoryDisplayNode(
        ...     name="app",
        ...     path="HordeMode/scripts/app",
        ...     checked=True,
        ...     children=[]
        ... )
    """
    
    name: str
    path: str
    checked: bool = False
    children: list[CategoryDisplayNode] = field(default_factory=list)