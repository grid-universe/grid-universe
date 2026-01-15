"""Portal teleportation system.

Entities that move onto a portal are teleported to the paired portal's location,
if unblocked.
"""

from dataclasses import replace
from pyrsistent import pset
from pyrsistent.typing import PMap, PSet
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_blocked_at
from grid_universe.runtime import StepContext
from grid_universe.utils.trail import get_augmented_trail


def portal_system_entity(
    state: State,
    ctx: StepContext,
    augmented_trail: PMap[Position, PSet[EntityID]],
    portal_id: EntityID,
) -> State:
    """Teleport entities entering the specified portal to its pair."""
    portal = state.portal.get(portal_id)
    portal_position = state.position.get(portal_id)
    if portal_position is None or portal is None:
        return state

    pair_position = state.position.get(portal.pair_entity)
    if pair_position is None:
        return state

    if is_blocked_at(state, pair_position, check_collidable=True):
        return state  # Teleport not possible

    entity_ids = set(augmented_trail.get(portal_position, pset())) & set(
        state.collidable
    )
    entering_entity_ids = {
        eid
        for eid in entity_ids
        if ctx.prev_position.get(eid) != state.position.get(eid)
        and state.position.get(eid) == portal_position
    }

    state_position = state.position
    for eid in entering_entity_ids:
        state_position = state_position.set(eid, pair_position)
    return replace(state, position=state_position)


def portal_system(state: State, ctx: StepContext) -> State:
    """Apply portal teleportation for all portals in the state."""
    augmented_trail: PMap[Position, PSet[EntityID]] = get_augmented_trail(
        state, ctx, pset(state.collidable)
    )
    for portal_id in state.portal:
        state = portal_system_entity(state, ctx, augmented_trail, portal_id)
    return state
