"""ECS convenience queries.

Provides cached queries for common ECS patterns, such as retrieving
entities at a given position or with certain components.

Functions here leverage caching to optimize repeated queries within
a single state instance.
"""

from collections.abc import Iterable, Mapping

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.cache import lru_identity_cache


def build_mutable_position_index(
    position_store: Mapping[EntityID, Position],
) -> dict[Position, list[EntityID]]:
    """Build a mutable reverse index from position to entity IDs."""
    index: dict[Position, list[EntityID]] = {}
    for eid, pos in position_store.items():
        bucket = index.get(pos)
        if bucket is None:
            index[pos] = [eid]
        else:
            bucket.append(eid)
    return index


def update_mutable_position_index(
    index: dict[Position, list[EntityID]],
    entity_id: EntityID,
    old_pos: Position,
    new_pos: Position,
) -> None:
    """Update a mutable reverse index when an entity moves."""
    if old_pos in index:
        try:
            index[old_pos].remove(entity_id)
        except ValueError:
            pass
    if new_pos not in index:
        index[new_pos] = []
    index[new_pos].append(entity_id)


@lru_identity_cache(maxsize=4096)
def _position_index(
    position_store: Mapping[EntityID, Position],
) -> Mapping[Position, tuple[EntityID, ...]]:
    """Build a reverse index from position to entity IDs.

    Args:
        position_store (Mapping[EntityID, Position]): Mapping of entity IDs to positions.

    Returns:
        Mapping[Position, FrozenSet[EntityID]]: Mapping from positions to sets of entity IDs.
    """
    index = build_mutable_position_index(position_store)
    # Freeze lists for cacheability
    return {pos: tuple(eids) for pos, eids in index.items()}


def entities_at(
    state: State,
    pos: Position,
    position_index: Mapping[Position, Iterable[EntityID]] | None = None,
) -> Iterable[EntityID]:
    """Return entity IDs at the given position."""
    if position_index is not None:
        return position_index.get(pos, ())
    idx = _position_index(state.position)
    return idx.get(pos, ())


def entities_with_components_at(
    state: State, pos: Position, *component_stores: Mapping[EntityID, object]
) -> list[EntityID]:
    """Return entity IDs at ``pos`` that have all specified components."""
    ids_at_pos = entities_at(state, pos)
    if not ids_at_pos:
        return []
    out: list[EntityID] = []
    for eid in ids_at_pos:
        if all(eid in store for store in component_stores):
            out.append(eid)
    return out
