from pyrsistent import pset, PSet

from grid_universe.state import State
from grid_universe.step import step
from grid_universe.types import EntityID
from grid_universe.components import (
    Position,
    Agent,
    Inventory,
    Key,
    Locked,
    Blocking,
    Collectible,
)
from grid_universe.actions import Action
from tests.test_utils import make_minimal_key_door_state, replace_state as replace


def add_key_to_inventory(state: State, agent_id: EntityID, key_id: EntityID) -> State:
    inv: Inventory = state.inventory[agent_id]
    new_inv: Inventory = Inventory(item_ids=inv.item_ids.add(key_id))
    return replace(state, inventory=state.inventory.set(agent_id, new_inv))


def set_inventory(state: State, agent_id: EntityID, item_ids: PSet[EntityID]) -> State:
    return replace(
        state, inventory=state.inventory.set(agent_id, Inventory(item_ids=item_ids))
    )


def add_key_entity(state: State, key_id: EntityID, key_id_str: str) -> State:
    return replace(
        state,
        key=state.key.set(key_id, Key(key_id=key_id_str)),
    )


def add_door_with_lock(
    state: State, door_id: EntityID, pos: Position, key_id_str: str
) -> State:
    return replace(
        state,
        locked=state.locked.set(door_id, Locked(key_id=key_id_str)),
        blocking=state.blocking.set(door_id, Blocking()),
        position=state.position.set(door_id, pos),
    )


def move_agent_adjacent_to(
    state: State, agent_id: EntityID, target_pos: Position
) -> State:
    # Try all four possible adjacent positions, use the first one that is in-bounds
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        new_x, new_y = target_pos.x + dx, target_pos.y + dy
        if 0 <= new_x < state.width and 0 <= new_y < state.height:
            return replace(
                state, position=state.position.set(agent_id, Position(new_x, new_y))
            )
    raise ValueError("No adjacent position found in bounds")


def test_unlock_door_with_matching_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id not in state.locked
    assert door_id not in state.blocking
    assert key_id not in state.inventory[agent_id].item_ids


def test_unlock_door_without_matching_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id in state.locked


def test_unlock_door_with_wrong_key_id() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    wrong_key_id: EntityID = 999
    state = add_key_entity(state, wrong_key_id, "wrong")
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(wrong_key_id)
    )
    door_id: EntityID = entities["door_id"]
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id in state.locked
    assert wrong_key_id in state.inventory[agent_id].item_ids


def test_unlock_consumes_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert key_id not in state.inventory[agent_id].item_ids
    assert key_id not in state.key


def test_unlock_door_with_no_inventory() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state = replace(state, inventory=state.inventory.remove(agent_id))
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id in state.locked


def test_unlock_door_with_empty_inventory() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state = set_inventory(state, agent_id, pset())
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id in state.locked


def test_unlock_multiple_doors_with_enough_keys() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = door_id1 + 100
    key_id2: EntityID = key_id + 100
    pos: Position = Position(0, 2)
    keyid_str: str = state.locked[door_id1].key_id
    state = add_key_entity(state, key_id2, keyid_str)
    state = add_door_with_lock(state, door_id2, pos, keyid_str)
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(key_id).add(key_id2)
    )
    # Move next to both doors, call UseKeyAction twice to unlock both
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id2])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id1 not in state.locked
    assert door_id2 not in state.locked
    assert key_id not in state.inventory[agent_id].item_ids
    assert key_id2 not in state.inventory[agent_id].item_ids


def test_unlock_multiple_doors_with_limited_keys() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = door_id1 + 200
    keyid_str: str = state.locked[door_id1].key_id
    pos: Position = Position(0, 2)
    state = add_door_with_lock(state, door_id2, pos, keyid_str)
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(key_id)
    )
    # Move to each locked door, attempt to unlock both sequentially
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id2])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    unlocked_count: int = int(door_id1 not in state.locked) + int(
        door_id2 not in state.locked
    )
    assert unlocked_count == 1
    assert key_id not in state.inventory[agent_id].item_ids


def test_unlock_with_key_not_in_key_store() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = 98765
    door_id: EntityID = entities["door_id"]
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(key_id)
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id in state.locked
    assert key_id in state.inventory[agent_id].item_ids


def test_unlock_with_nonkey_item_in_inventory() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    nonkey_id: EntityID = 3333
    door_id: EntityID = entities["door_id"]
    state = replace(state, collectible=state.collectible.set(nonkey_id, Collectible()))
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(nonkey_id)
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id in state.locked
    assert nonkey_id in state.inventory[agent_id].item_ids


def test_unlock_at_nonlocked_position() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    unused_pos: Position = Position(2, 0)  # Some position with no locked door
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, unused_pos)
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert key_id in state.inventory[agent_id].item_ids


def test_unlock_after_picking_up_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    # Simulate picking up the key by adding to inventory
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id not in state.locked
    assert key_id not in state.inventory[agent_id].item_ids


def test_unlock_multiple_doors_same_key_id() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id1: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = door_id1 + 333
    key_id2: EntityID = key_id1 + 333
    keyid_str: str = state.locked[door_id1].key_id
    pos: Position = Position(0, 2)
    state = add_key_entity(state, key_id2, keyid_str)
    state = add_door_with_lock(state, door_id2, pos, keyid_str)
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(key_id1).add(key_id2)
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id2])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    assert door_id1 not in state.locked
    assert door_id2 not in state.locked


def test_multi_agent_unlock_affects_only_actor() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id1: EntityID = entities["agent_id"]
    key_id1: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]

    # Add a second agent with their own door/key
    agent_id2: EntityID = 401
    key_id2: EntityID = 402
    door_id2: EntityID = 403
    pos2: Position = Position(0, 5)
    state = replace(
        state,
        agent=state.agent.set(agent_id2, Agent()),
        key=state.key.set(key_id2, Key(key_id="blue")),
        locked=state.locked.set(door_id2, Locked(key_id="blue")),
        blocking=state.blocking.set(door_id2, Blocking()),
        position=state.position.set(agent_id2, Position(0, 4)).set(door_id2, pos2),
        inventory=state.inventory.set(agent_id2, Inventory(item_ids=pset([key_id2]))),
    )
    state = add_key_to_inventory(state, agent_id1, key_id1)
    state = move_agent_adjacent_to(state, agent_id1, state.position[door_id1])
    state = step(state, Action.USE_KEY, agent_id=agent_id1)
    assert door_id2 in state.locked
    assert key_id2 in state.inventory[agent_id2].item_ids
    assert door_id1 not in state.locked


def test_unlock_adjacent_to_multiple_locked() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id1: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = door_id1 + 55
    pos2: Position = Position(1, 0)
    keyid_str: str = state.locked[door_id1].key_id
    state = add_door_with_lock(state, door_id2, pos2, keyid_str)
    key_id2: EntityID = key_id1 + 55
    state = add_key_entity(state, key_id2, keyid_str)
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids.add(key_id1).add(key_id2)
    )
    # Move agent adjacent to both doors (let's use the position next to door_id1)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    state = step(state, Action.USE_KEY, agent_id=agent_id)
    # Agent may need to move again and use key to unlock the other if ECS only unlocks one per action
    unlocked_count: int = int(door_id1 not in state.locked) + int(
        door_id2 not in state.locked
    )
    assert unlocked_count >= 1
