"""Push interaction system.

Entities that attempt to move into a tile occupied by a pushable entity
will attempt to push that entity one tile further in the same direction,
provided the destination tile is unblocked.
"""

from dataclasses import replace
from grid_universe.moves import wrap_around_move_fn
from grid_universe.state import State
from grid_universe.components import Position
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.grid import is_entity_blocked_at, is_in_bounds, wrap_position
from grid_universe.utils.trail import add_trail_position
from grid_universe.runtime import StepContext


def compute_destination(
    state: State, current_pos: Position, next_pos: Position
) -> Position | None:
    """Compute push destination given current and occupant next positions.

    Args:
        state (State): Current immutable state.
        current_pos (Position): Position of the entity initiating the push.
        next_pos (Position): Position of the entity being pushed.
    """
    dx = next_pos.x - current_pos.x
    dy = next_pos.y - current_pos.y
    dest_x = next_pos.x + dx
    dest_y = next_pos.y + dy

    if state.move_fn is wrap_around_move_fn:
        return wrap_position(dest_x, dest_y, state.width, state.height)

    target_position = Position(dest_x, dest_y)
    if not is_in_bounds(state, target_position):
        return None

    return target_position


def push_system(
    state: State, ctx: StepContext, eid: EntityID, next_pos: Position
) -> tuple[State, StepContext]:
    """Attempt to push all pushable entities at ``next_pos``.

    Args:
        state (State): Current immutable state.
        ctx (StepContext): Current step context.
        eid (EntityID): Entity initiating the push (must have a position).
        next_pos (Position): Adjacent position the entity is trying to move into.

    Returns:
        State: Updated state after applying any pushes.
        StepContext: Updated step context after applying any pushes.
    """
    current_pos = state.position.get(eid)
    if current_pos is None:
        return state, ctx

    # Is there a pushable object at next_pos?
    pushable_ids = entities_with_components_at(state, next_pos, state.pushable)
    if not pushable_ids:
        return state, ctx  # Nothing to push

    push_to = compute_destination(state, current_pos, next_pos)
    if push_to is None:
        return state, ctx

    # Destination must be unblocked for the (first) pushable entity.
    # All pushables share the same collision rules.
    if is_entity_blocked_at(state, pushable_ids[0], push_to):
        return state, ctx  # Push not possible

    new_position = state.position.set(eid, next_pos)
    for pushable_id in pushable_ids:
        new_position = new_position.set(pushable_id, push_to)
        ctx = add_trail_position(ctx, pushable_id, push_to)

    return replace(state, position=new_position), ctx
