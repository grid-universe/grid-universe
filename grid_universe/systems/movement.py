"""Player (agent) movement system.

Attempts to move the controlled agent to ``next_pos`` applying effect logic:

1. If the agent has an active Phasing effect (consuming a usage/time limit) it
    ignores blocking components entirely.
2. Otherwise the move is allowed only if destination is in-bounds and not
    blocked by Blocking/Pushable/Collidable entities (push handling occurs in a
    separate system before this is called).

Leaves state unchanged if movement is not possible; otherwise updates the
entity position and possibly decrements usage limits.
"""

from grid_universe.components import Position
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_entity_blocked_at, is_in_bounds
from grid_universe.utils.position import set_position_component
from grid_universe.utils.status import use_status_effect_if_present


def movement_system(
    state: State,
    entity_id: EntityID,
    next_pos: Position,
    ctx: StepContext,
) -> None:
    """Move agent one tile if allowed.

    Args:
        state (State): Current state.
        entity_id (EntityID): Agent entity id (ignored if not an agent).
        next_pos (Position): Desired destination position.

    """
    if entity_id not in state.agent:
        return

    if not is_in_bounds(state, next_pos):
        return

    # Check for phasing
    if entity_id in state.status:
        effect_id = use_status_effect_if_present(
            state.status[entity_id].effect_ids,
            state.phasing,
            state.time_limit,
            state.usage_limit,
        )
        if effect_id is not None:
            set_position_component(state, ctx, entity_id, next_pos)
            return

    if is_entity_blocked_at(
        state, entity_id, next_pos, position_index=ctx.position_index
    ):
        return

    set_position_component(state, ctx, entity_id, next_pos)
