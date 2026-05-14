"""Collectible system.

Resolves item/effect pickups and reward scoring when an entity occupies the
same tile as collectible entities. The system supports three pickup flows:

1. Effect pickup (power-up): adds an effect entity's ID to the entity's
    `Status` if the effect is valid and not expired.
2. Inventory pickup: inserts keys, coins, cores, etc. into the entity's
    `Inventory` (non-effect collectibles).
3. Reward scoring: applies immediate score changes for entities bearing a
    `Rewardable` component (whether or not they are effect/inventory
    pickups) and removes them.

Collected entities are removed from ``position`` and ``collectible`` maps.
The system is idempotent for a given state+entity pairing.
"""

from grid_universe.components import Status
from grid_universe.components.properties.inventory import Inventory
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.position import remove_position_component
from grid_universe.utils.status import has_effect, valid_effect


def collectible_system(
    state: State,
    entity_id: EntityID,
    ctx: StepContext,
) -> None:
    """Process collectible pickups for a single entity.

    Args:
        state (State): Current state.
        entity_id (EntityID): Entity performing collection (typically an agent).
    """
    entity_pos = state.position.get(entity_id)
    if entity_pos is None:
        return

    collectable_ids = entities_with_components_at(
        state, entity_pos, state.collectible, position_index=ctx.position_index
    )
    if not collectable_ids:
        return

    entity_inventory: Inventory | None = state.inventory.get(entity_id)
    entity_status: Status | None = state.status.get(entity_id)
    collected_ids: set[EntityID] = set()
    retained_ids: set[EntityID] = set()

    for collectable_id in collectable_ids:
        # Collectible is a powerup/effect
        if (
            entity_status is not None
            and has_effect(state, collectable_id)
            and valid_effect(state, collectable_id)
        ):
            entity_status = Status(
                effect_ids=entity_status.effect_ids | {collectable_id}
            )
            collected_ids.add(collectable_id)
            retained_ids.add(collectable_id)
        # Collectible is a normal item (e.g., key, coin, core)
        elif entity_inventory is not None and not has_effect(state, collectable_id):
            entity_inventory = Inventory(
                item_ids=entity_inventory.item_ids | {collectable_id}
            )
            collected_ids.add(collectable_id)
            retained_ids.add(collectable_id)
        # Collectible is rewardable
        if collectable_id in state.rewardable:
            state.score += state.rewardable[collectable_id].amount
            collected_ids.add(collectable_id)

    for collected_id in collected_ids:
        remove_position_component(state, ctx, collected_id)
        state.collectible.pop(collected_id, None)
    ctx.removed_entity_ids.update(collected_ids - retained_ids)

    if entity_inventory is not None:
        state.inventory[entity_id] = entity_inventory
    if entity_status is not None:
        state.status[entity_id] = entity_status
