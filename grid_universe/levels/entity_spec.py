"""Authoring-time mutable entity specification.

``EntitySpec`` instances gather optional component instances plus authoring
metadata (inventory/status lists and wiring references). They are converted to
immutable ECS entities by :mod:`levels.convert`.
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


def _empty_objs() -> List["EntitySpec"]:
    return []


@dataclass
class EntitySpec:
    """
    Mutable bag of ECS components for authoring (no Position here).
    Authoring-only wiring refs:
      - pathfind_target_ref: reference to another EntityObject to target
      - pathfinding_type: desired path type when wiring (if target ref set)
      - portal_pair_ref: reference to another EntityObject to pair with as a portal
    Authoring-only nested collections:
      - inventory: list of EntityObject (items carried; materialized as separate entities)
      - status: list of EntityObject (effects active; materialized as separate entities)
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

    # Authoring-only nested objects (not State components)
    inventory_list: List["EntitySpec"] = field(default_factory=_empty_objs)
    status_list: List["EntitySpec"] = field(default_factory=_empty_objs)

    # Authoring-only wiring refs (resolved during conversion)
    pathfind_target_ref: Optional["EntitySpec"] = None
    pathfinding_type: Optional[PathfindingType] = None
    portal_pair_ref: Optional["EntitySpec"] = None

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


__all__ = ["EntitySpec", "COMPONENT_TO_FIELD"]
