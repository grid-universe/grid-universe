"""Locked / unlocking system.

Handles adjacent-tile interaction between an entity's inventory and any
neighboring locked objects. When the correct key is found, removes both the
``Locked`` and optional ``Blocking`` components so passage is opened. Keys
are single-use: they are removed from inventory (and key map) upon unlocking.
"""

from dataclasses import replace
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.inventory import has_key_with_id, remove_item


def unlock(state: State, entity_id: EntityID, next_pos: Position) -> State:
    """Attempt to unlock all locked entities at ``next_pos``.

    Consumes matching key(s) from the entity's inventory; multiple locks in
    the same tile are processed sequentially.
    """
    locked_ids = entities_with_components_at(state, next_pos, state.locked)
    if not locked_ids:
        return state

    entity_inventory = state.inventory.get(entity_id)
    if entity_inventory is None:
        return state  # No inventory, can't unlock

    state_locked = state.locked
    state_blocking = state.blocking
    state_key = state.key

    for locked_id in locked_ids:
        locked_component = state_locked[locked_id]
        key_found = has_key_with_id(
            entity_inventory, state_key, locked_component.key_id
        )
        if key_found is not None:
            # Remove Locked and Blocking component (if any)
            state_locked = state_locked.remove(locked_id)
            if locked_id in state_blocking:
                state_blocking = state_blocking.remove(locked_id)
            # Remove key from inventory and key store
            entity_inventory = remove_item(entity_inventory, key_found)
            state_key = (
                state_key.remove(key_found) if key_found in state_key else state_key
            )

    # Update inventory
    state_inventory = state.inventory.set(entity_id, entity_inventory)

    return replace(
        state,
        locked=state_locked,
        blocking=state_blocking,
        inventory=state_inventory,
        key=state_key,
    )


def unlock_system(state: State, entity_id: EntityID) -> State:
    """
    Attempt to unlock all locks adjacent to the specified entity and on its own tile.

    Args:
        state (State): Current immutable state.
        entity_id (EntityID): Entity whose inventory is used to unlock adjacent locks.

    Returns:
        State: Updated state.
    """
    pos = state.position.get(entity_id)
    if pos is not None:
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            target_pos = Position(pos.x + dx, pos.y + dy)
            state = unlock(state, entity_id, target_pos)
    return state
