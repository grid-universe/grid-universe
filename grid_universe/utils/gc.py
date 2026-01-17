"""
Garbage collection utilities.

Removes unreachable entities from the state.

An entity is considered reachable if it is present in the position map,
or referenced by status effects or inventories of other reachable entities.
"""

from dataclasses import replace
from pyrsistent import pmap
from grid_universe.types import EntityID
from grid_universe.state import State
from typing import Any, cast
from pyrsistent.typing import PMap


def compute_alive_entities(state: State) -> set[EntityID]:
    """Compute the set of all reachable entity IDs in the state."""
    alive: set[EntityID] = set(state.position.keys())
    for stats in state.status.values():
        alive |= set(stats.effect_ids)
    for inv in state.inventory.values():
        alive |= set(inv.item_ids)
    return alive


def run_garbage_collector(state: State) -> State:
    """Return a new state with unreachable entities removed."""
    alive = compute_alive_entities(state)
    new_fields: dict[str, Any] = {}
    for field in state.__dataclass_fields__:
        value = getattr(state, field)
        if isinstance(value, type(pmap())):
            value_map = cast(PMap[EntityID, Any], value)
            filtered = pmap({k: v for k, v in value_map.items() if k in alive})
            new_fields[field] = filtered
    return replace(state, **new_fields)
