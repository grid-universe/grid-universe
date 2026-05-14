"""Portal teleportation system.

Entities that move onto a portal are teleported to the paired portal's location,
if unblocked.
"""

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_entity_blocked_at
from grid_universe.utils.position import set_position_component
from grid_universe.runtime import StepContext
from grid_universe.utils.trail import get_augmented_trail


def portal_system_entity(
    state: State,
    ctx: StepContext,
    augmented_trail: dict[Position, set[EntityID]],
    portal_id: EntityID,
) -> None:
    """Teleport entities entering the specified portal to its pair."""
    portal = state.portal.get(portal_id)
    portal_position = state.position.get(portal_id)
    if portal_position is None or portal is None:
        return

    pair_position = state.position.get(portal.pair_entity)
    if pair_position is None:
        return

    entity_ids = augmented_trail.get(portal_position, set()) & set(state.collidable)
    entering_entity_ids = {
        eid
        for eid in entity_ids
        if ctx.prev_position.get(eid) != state.position.get(eid)
        and state.position.get(eid) == portal_position
    }

    moved_entities: list[tuple[EntityID, Position]] = []
    for eid in entering_entity_ids:
        if is_entity_blocked_at(
            state, eid, pair_position, position_index=ctx.position_index
        ):
            continue  # Can't teleport this entity
        moved_entities.append((eid, pair_position))
    for eid, new_pos in moved_entities:
        set_position_component(state, ctx, eid, new_pos)


def portal_system(state: State, ctx: StepContext) -> None:
    """Apply portal teleportation for all portals in the state."""
    augmented_trail = get_augmented_trail(state, ctx, set(state.collidable))
    for portal_id in state.portal:
        portal_system_entity(state, ctx, augmented_trail, portal_id)
