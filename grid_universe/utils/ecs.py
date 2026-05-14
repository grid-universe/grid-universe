"""ECS convenience queries.

Provides cached queries for common ECS patterns, such as retrieving
entities at a given position or with certain components.

"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from grid_universe.components import Position
from grid_universe.types import EntityID

if TYPE_CHECKING:
    from grid_universe.state import State

PositionIndex = dict[Position, list[EntityID]]


def build_position_index(
    position_store: Mapping[EntityID, Position],
) -> PositionIndex:
    """Build a reverse index from position to entity IDs."""
    index: PositionIndex = {}
    for eid, pos in position_store.items():
        bucket = index.get(pos)
        if bucket is None:
            index[pos] = [eid]
        else:
            bucket.append(eid)
    return index


def update_position_index(
    index: PositionIndex,
    entity_id: EntityID,
    old_pos: Position,
    new_pos: Position,
) -> None:
    """Update a reverse index when an entity moves."""
    if old_pos == new_pos:
        return

    remove_from_position_index(index, entity_id, old_pos)
    index.setdefault(new_pos, []).append(entity_id)


def remove_from_position_index(
    index: PositionIndex,
    entity_id: EntityID,
    old_pos: Position,
) -> None:
    """Remove an entity from a reverse index."""
    bucket = index[old_pos]
    bucket.remove(entity_id)
    if not bucket:
        del index[old_pos]


def entities_at(
    state: State,
    pos: Position,
    position_index: Mapping[Position, Iterable[EntityID]] | None = None,
) -> Iterable[EntityID]:
    """Return entity IDs at the given position."""
    if position_index is not None:
        return position_index.get(pos, ())
    idx = build_position_index(state.position)
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
