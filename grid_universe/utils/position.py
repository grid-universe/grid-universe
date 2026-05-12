"""Helpers for keeping position state and reverse indexes synchronized."""

from dataclasses import replace

from pyrsistent.typing import PMap

from grid_universe.components import Position
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import (
    remove_from_mutable_position_index,
    update_mutable_position_index,
)

PositionStore = PMap[EntityID, Position]


def set_position_component(
    position: PositionStore,
    ctx: StepContext,
    entity_id: EntityID,
    new_pos: Position,
) -> PositionStore:
    """Set an entity position and update the step position index."""
    update_mutable_position_index(
        ctx.position_index, entity_id, position[entity_id], new_pos
    )
    return position.set(entity_id, new_pos)


def remove_position_component(
    position: PositionStore,
    ctx: StepContext,
    entity_id: EntityID,
) -> PositionStore:
    """Remove an entity position and update the step position index."""
    remove_from_mutable_position_index(
        ctx.position_index, entity_id, position[entity_id]
    )
    return position.remove(entity_id)


def set_entity_position(
    state: State,
    ctx: StepContext,
    entity_id: EntityID,
    new_pos: Position,
) -> State:
    """Return state with an updated entity position and synchronized index."""
    return replace(
        state,
        position=set_position_component(state.position, ctx, entity_id, new_pos),
    )
