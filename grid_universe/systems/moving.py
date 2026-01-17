"""Autonomous linear movement system.

For each entity with a ``Moving`` component, attempt to move it in its
configured direction by its speed. If the destination tile is out of bounds
or blocked, it applies the configured ``on_collision`` behavior.
"""

from dataclasses import replace

from grid_universe.components import Position
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.utils.ecs import (
    build_mutable_position_index,
    update_mutable_position_index,
)
from grid_universe.utils.grid import is_entity_blocked_at, is_in_bounds
from grid_universe.utils.trail import add_trail_position


def moving_system(state: State, ctx: StepContext) -> tuple[State, StepContext]:
    """Advance all moving entities for the current step.

    Parameters:
        state: Current game state.
        ctx: Current step context.

    Returns:
        Updated state and context after processing movement.
    """
    # Optimization: Use a mutable index to avoid rebuilding it on every move
    position_index = build_mutable_position_index(state.position)

    for entity_id, mover in sorted(state.moving.items()):
        if entity_id not in state.position:
            continue

        dx, dy = mover.vector

        for _ in range(mover.speed):
            pos = state.position[entity_id]
            next_pos = Position(pos.x + dx, pos.y + dy)

            blocked = (not is_in_bounds(state, next_pos)) or is_entity_blocked_at(
                state,
                entity_id,
                next_pos,
                position_index=position_index,
            )

            if blocked:
                if mover.on_collision == "bounce":
                    state = replace(
                        state, moving=state.moving.set(entity_id, mover.reversed())
                    )
                break

            state = replace(state, position=state.position.set(entity_id, next_pos))
            ctx = add_trail_position(ctx, entity_id, state.position[entity_id])

            # Update local index
            update_mutable_position_index(position_index, entity_id, pos, next_pos)

    return state, ctx
