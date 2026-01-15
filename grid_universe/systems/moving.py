"""Autonomous linear movement system.

Updates entities with a ``Moving`` component by translating them along their
configured axis and direction up to ``speed`` tiles per step, bouncing (i.e.
reversing direction) if configured and blocked/out-of-bounds.
"""

from dataclasses import replace
from typing import Tuple
from pyrsistent.typing import PMap
from grid_universe.state import State
from grid_universe.runtime import StepContext
from grid_universe.utils.trail import add_trail_position
from grid_universe.components import Moving, MovingAxis, Position
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_blocked_at, is_in_bounds


def move(
    state: State,
    entity_id: EntityID,
    pos: Position,
    next_pos: Position,
    state_moving: PMap[EntityID, Moving],
    state_position: PMap[EntityID, Position],
) -> Tuple[PMap[EntityID, Moving], PMap[EntityID, Position], bool]:
    """Attempt a single-tile move for a moving entity.

    Returns updated moving/position maps and whether movement was blocked.
    """
    moving = state_moving[entity_id]
    blocked = not is_in_bounds(state, next_pos) or is_blocked_at(
        state, next_pos, check_collidable=entity_id in state.blocking
    )
    if blocked:
        # Reverse direction if bouncing, else leave unchanged
        new_direction = moving.direction * (-1 if moving.bounce else 1)
        state_moving = state_moving.set(
            entity_id,
            replace(moving, direction=new_direction),
        )
    else:
        state_position = state_position.set(entity_id, next_pos)
    return state_moving, state_position, blocked


def moving_system(state: State, ctx: StepContext) -> tuple[State, StepContext]:
    """Advance all moving entities for the current step."""
    state_position = state.position
    state_moving = state.moving

    for entity_id, moving in state_moving.items():
        pos = state_position.get(entity_id)
        if pos is None:
            continue
        if moving.direction not in (-1, 1):
            raise ValueError(
                f"Invalid moving direction for {entity_id}: {moving.direction}"
            )
        dx, dy = (
            (moving.direction, 0)
            if moving.axis == MovingAxis.HORIZONTAL
            else (0, moving.direction)
        )
        for _ in range(moving.speed):
            pos = state_position[entity_id]
            next_pos = Position(pos.x + dx, pos.y + dy)
            state_moving, state_position, blocked = move(
                state, entity_id, pos, next_pos, state_moving, state_position
            )
            ctx = add_trail_position(ctx, entity_id, state_position[entity_id])
            if blocked:
                break

        state = replace(state, position=state_position, moving=state_moving)

    return state, ctx
