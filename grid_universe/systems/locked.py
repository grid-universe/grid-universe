"""Locked / unlocking system.

Handles adjacent-tile interaction between an entity's inventory and any
neighboring locked objects. When the correct key is found, removes both the
``Locked`` and optional ``Blocking`` components so passage is opened. Keys
are single-use: they are removed from inventory (and key map) upon unlocking.
"""

from grid_universe.components import Inventory, Position
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.inventory import has_key_with_id


def unlock(
    state: State,
    entity_id: EntityID,
    next_pos: Position,
    ctx: StepContext,
) -> None:
    """Attempt to unlock all locked entities at ``next_pos``.

    Consumes matching key(s) from the entity's inventory; multiple locks in
    the same tile are processed sequentially.
    """
    locked_ids = entities_with_components_at(
        state, next_pos, state.locked, position_index=ctx.position_index
    )
    if not locked_ids:
        return

    entity_inventory = state.inventory.get(entity_id)
    if entity_inventory is None:
        return

    for locked_id in locked_ids:
        locked_component = state.locked[locked_id]
        key_found = has_key_with_id(
            entity_inventory, state.key, locked_component.key_id
        )
        if key_found is not None:
            state.locked.pop(locked_id, None)
            state.blocking.pop(locked_id, None)
            entity_inventory = Inventory(
                item_ids=entity_inventory.item_ids - {key_found}
            )
            state.key.pop(key_found, None)
            ctx.removed_entity_ids.add(key_found)

    state.inventory[entity_id] = entity_inventory


def unlock_system(state: State, entity_id: EntityID, ctx: StepContext) -> None:
    """
    Attempt to unlock all locks adjacent to the specified entity and on its own tile.

    Args:
        state (State): Current state.
        entity_id (EntityID): Entity whose inventory is used to unlock adjacent locks.
    """
    pos = state.position.get(entity_id)
    if pos is not None:
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            target_pos = Position(pos.x + dx, pos.y + dy)
            unlock(state, entity_id, target_pos, ctx)
