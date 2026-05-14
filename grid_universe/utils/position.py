"""Helpers for keeping position state and reverse indexes synchronized."""

from grid_universe.components import Position
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import (
    remove_from_position_index,
    update_position_index,
)


def set_position_component(
    state: State,
    ctx: StepContext,
    entity_id: EntityID,
    new_pos: Position,
) -> None:
    """Set an entity position and keep the reverse index synchronized."""
    update_position_index(
        ctx.position_index, entity_id, state.position[entity_id], new_pos
    )
    state.position[entity_id] = new_pos


def remove_position_component(
    state: State,
    ctx: StepContext,
    entity_id: EntityID,
) -> None:
    """Remove an entity position and keep the reverse index synchronized."""
    remove_from_position_index(ctx.position_index, entity_id, state.position[entity_id])
    del state.position[entity_id]
