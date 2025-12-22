"""Mutable entity specification.

The `grid_universe.levels.entity.Entity` dataclass is an alternative,
mutable representation of an ECS entity in `grid_universe.state.State`.

It stores optional component instances plus additional mutable structure
(nested inventory/status items and cross-entity references) that can be
resolved during conversion.

Use `grid_universe.levels.convert` to convert between this representation
and the immutable runtime `grid_universe.state.State`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

from grid_universe.components.properties import (
    Agent,
    Appearance,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Moving,
    Pathfinding,
    PathfindingType,
    Portal,
    Pushable,
    Requirable,
    Rewardable,
    Status,
)
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)

# Map component class -> State store name (used by convert.py)
COMPONENT_TO_FIELD: Dict[Type[Any], str] = {
    Agent: "agent",
    Appearance: "appearance",
    Blocking: "blocking",
    Collectible: "collectible",
    Collidable: "collidable",
    Cost: "cost",
    Damage: "damage",
    Exit: "exit",
    Health: "health",
    Inventory: "inventory",
    Key: "key",
    LethalDamage: "lethal_damage",
    Locked: "locked",
    Moving: "moving",
    Pathfinding: "pathfinding",
    Portal: "portal",
    Pushable: "pushable",
    Requirable: "requirable",
    Rewardable: "rewardable",
    Status: "status",
    Immunity: "immunity",
    Phasing: "phasing",
    Speed: "speed",
    TimeLimit: "time_limit",
    UsageLimit: "usage_limit",
}


def _empty_objs() -> List["Entity"]:
    return []


@dataclass
class Entity:
    """
    Mutable bag of ECS components used in `grid_universe.levels.grid.Level`.

    - It omits ``Position`` (position is supplied by the containing grid cell).
    - It supports extra mutable structure that is resolved during conversion:
        - wiring refs: ``pathfind_target_ref``, ``pathfinding_type``, ``portal_pair_ref``
        - nested collections: ``inventory_list`` and ``status_list`` (materialized as
            separate entities in `grid_universe.levels.convert.to_state`).
    """

    # Components
    agent: Optional[Agent] = None
    appearance: Optional[Appearance] = None
    blocking: Optional[Blocking] = None
    collectible: Optional[Collectible] = None
    collidable: Optional[Collidable] = None
    cost: Optional[Cost] = None
    damage: Optional[Damage] = None
    exit: Optional[Exit] = None
    health: Optional[Health] = None
    inventory: Optional[Inventory] = None
    key: Optional[Key] = None
    lethal_damage: Optional[LethalDamage] = None
    locked: Optional[Locked] = None
    moving: Optional[Moving] = None
    pathfinding: Optional[Pathfinding] = None
    portal: Optional[Portal] = None
    pushable: Optional[Pushable] = None
    requirable: Optional[Requirable] = None
    rewardable: Optional[Rewardable] = None
    status: Optional[Status] = None

    # Effects
    immunity: Optional[Immunity] = None
    phasing: Optional[Phasing] = None
    speed: Optional[Speed] = None
    time_limit: Optional[TimeLimit] = None
    usage_limit: Optional[UsageLimit] = None

    # Level-only nested objects (not State components)
    inventory_list: List["Entity"] = field(default_factory=_empty_objs)
    status_list: List["Entity"] = field(default_factory=_empty_objs)

    # Level-only reference fields (resolved during conversion)
    pathfind_target_ref: Optional["Entity"] = None
    pathfinding_type: Optional[PathfindingType] = None
    portal_pair_ref: Optional["Entity"] = None

    def iter_components(self) -> List[Tuple[str, Any]]:
        """
        Yield (store_name, component) for non-None component fields that map to State stores.
        """
        out: List[Tuple[str, Any]] = []
        for _, store_name in COMPONENT_TO_FIELD.items():
            comp = getattr(self, store_name, None)
            if comp is not None:
                out.append((store_name, comp))
        return out


__all__ = ["Entity", "COMPONENT_TO_FIELD"]
