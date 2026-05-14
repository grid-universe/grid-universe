"""Autonomous linear movement system.

For each entity with a ``Moving`` component, attempt to move it in its
configured direction by its speed. If the destination tile is out of bounds
or blocked, it applies the configured ``on_collision`` behavior.
"""

from grid_universe.components import Position
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.utils.grid import is_entity_blocked_at, is_in_bounds
from grid_universe.utils.position import set_position_component
from grid_universe.utils.trail import add_trail_position


def moving_system(state: State, ctx: StepContext) -> None:
    """Advance all moving entities for the current step.

    Parameters:
        state: Current game state.
        ctx: Current step context.

    """
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
                position_index=ctx.position_index,
            )

            if blocked:
                if mover.on_collision == "bounce":
                    state.moving[entity_id] = mover.reversed()
                break

            set_position_component(state, ctx, entity_id, next_pos)
            add_trail_position(ctx, entity_id, next_pos)
