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

PositionIndex = dict[Position, list[EntityID]]


def build_mutable_position_index(
    position_store: Mapping[EntityID, Position],
) -> PositionIndex:
    """Build a mutable reverse index from position to entity IDs."""
    index: PositionIndex = {}
    for eid, pos in position_store.items():
        bucket = index.get(pos)
        if bucket is None:
            index[pos] = [eid]
        else:
            bucket.append(eid)
    return index


def update_mutable_position_index(
    index: PositionIndex,
    entity_id: EntityID,
    old_pos: Position,
    new_pos: Position,
) -> None:
    """Update a mutable reverse index when an entity moves."""
    if old_pos == new_pos:
        return

    remove_from_mutable_position_index(index, entity_id, old_pos)
    index.setdefault(new_pos, []).append(entity_id)


def remove_from_mutable_position_index(
    index: PositionIndex,
    entity_id: EntityID,
    old_pos: Position,
) -> None:
    """Remove an entity from a mutable reverse index."""
    bucket = index[old_pos]
    bucket.remove(entity_id)
    if not bucket:
        del index[old_pos]


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
    state: State,
    pos: Position,
    *component_stores: Mapping[EntityID, object],
    position_index: Mapping[Position, Iterable[EntityID]] | None = None,
) -> list[EntityID]:
    """Return entity IDs at ``pos`` that have all specified components."""
    ids_at_pos = entities_at(state, pos, position_index=position_index)
    if not ids_at_pos:
        return []
    out: list[EntityID] = []
    for eid in ids_at_pos:
        if all(eid in store for store in component_stores):
            out.append(eid)
    return out
