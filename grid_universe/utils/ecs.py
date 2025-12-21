"""ECS convenience queries.

Provides cached queries for common ECS patterns, such as retrieving
entities at a given position or with certain components.

Functions here leverage caching to optimize repeated queries within
a single state instance.
"""

from functools import lru_cache
from typing import Dict, FrozenSet, Mapping, List, Set

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


@lru_cache(maxsize=4096)
def _position_index(
    position_store: Mapping[EntityID, Position],
) -> Mapping[Position, FrozenSet[EntityID]]:
    """Build a reverse index from position to entity IDs.

    Args:
        position_store (Mapping[EntityID, Position]): Mapping of entity IDs to positions.

    Returns:
        Mapping[Position, FrozenSet[EntityID]]: Mapping from positions to sets of entity IDs.
    """
    index: Dict[Position, Set[EntityID]] = {}
    for eid, pos in position_store.items():
        index.setdefault(pos, set()).add(eid)
    # Freeze sets for cacheability
    return {pos: frozenset(eids) for pos, eids in index.items()}


def entities_at(state: State, pos: Position) -> Set[EntityID]:
    """Return entity IDs at the given position."""
    idx = _position_index(state.position)
    return set(idx.get(pos, ()))


def entities_with_components_at(
    state: State, pos: Position, *component_stores: Mapping[EntityID, object]
) -> List[EntityID]:
    """Return entity IDs at ``pos`` that have all specified components."""
    ids_at_pos: Set[EntityID] = entities_at(state, pos)
    for store in component_stores:
        ids_at_pos &= set(store.keys())
    return list(ids_at_pos)
