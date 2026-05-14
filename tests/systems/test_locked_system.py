from dataclasses import replace
from typing import TypedDict

from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.runtime import make_step_context
from grid_universe.systems.locked import unlock_system
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import (
    Position,
    Agent,
    Collectible,
    Inventory,
    Key,
    Locked,
    Blocking,
    Collidable,
    Appearance,
)
from grid_universe.entity import new_entity_id


class MinimalKeyDoorEntities(TypedDict):
    agent_id: EntityID
    key_id: EntityID
    door_id: EntityID


def add_key_to_inventory(state: State, agent_id: EntityID, key_id: EntityID) -> State:
    inv: Inventory = state.inventory[agent_id]
    new_inv = Inventory(item_ids=inv.item_ids | {key_id})
    return replace(state, inventory={**state.inventory, agent_id: new_inv})


def set_inventory(state: State, agent_id: EntityID, item_ids: set[EntityID]) -> State:
    return replace(
        state, inventory={**state.inventory, agent_id: Inventory(item_ids=item_ids)}
    )


def move_agent_adjacent_to(
    state: State, agent_id: EntityID, target_pos: Position
) -> State:
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        new_x, new_y = (target_pos.x + dx, target_pos.y + dy)
        if 0 <= new_x < state.width and 0 <= new_y < state.height:
            return replace(
                state, position={**state.position, agent_id: Position(new_x, new_y)}
            )
    raise ValueError("No adjacent position found in bounds")


def make_minimal_key_door_state() -> tuple[State, MinimalKeyDoorEntities]:
    """
    Returns a minimal state with: agent, key, locked door.
    """
    pos: dict[EntityID, Position] = {}
    agent: dict[EntityID, Agent] = {}
    inventory: dict[EntityID, Inventory] = {}
    key: dict[EntityID, Key] = {}
    collectible: dict[EntityID, Collectible] = {}
    locked: dict[EntityID, Locked] = {}
    blocking: dict[EntityID, Blocking] = {}
    collidable: dict[EntityID, Collidable] = {}
    appearance: dict[EntityID, Appearance] = {}
    agent_id = new_entity_id()
    key_id = new_entity_id()
    door_id = new_entity_id()
    pos[agent_id] = Position(0, 0)
    pos[key_id] = Position(0, 1)
    pos[door_id] = Position(0, 2)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(set())
    key[key_id] = Key(key_id="red")
    collectible[key_id] = Collectible()
    locked[door_id] = Locked(key_id="red")
    blocking[door_id] = Blocking()
    collidable[agent_id] = Collidable()
    collidable[door_id] = Collidable()
    appearance[agent_id] = Appearance(name="human")
    appearance[key_id] = Appearance(name="key")
    appearance[door_id] = Appearance(name="door")
    state = State(
        width=3,
        height=3,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent),
        locked=dict(locked),
        key=dict(key),
        collectible=dict(collectible),
        inventory=dict(inventory),
        appearance=dict(appearance),
        blocking=dict(blocking),
        collidable=dict(collidable),
    )
    entities = MinimalKeyDoorEntities(agent_id=agent_id, key_id=key_id, door_id=door_id)
    return (state, entities)


def test_unlock_door_with_matching_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id not in state.locked
    assert door_id not in state.blocking
    assert key_id not in state.inventory[agent_id].item_ids


def test_unlock_door_without_matching_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id in state.locked


def test_unlock_door_with_wrong_key_id() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    wrong_key_id: EntityID = new_entity_id()
    state = replace(state, key={**state.key, wrong_key_id: Key(key_id="wrong")})
    state = add_key_to_inventory(state, agent_id, wrong_key_id)
    door_id: EntityID = entities["door_id"]
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id in state.locked
    assert wrong_key_id in state.inventory[agent_id].item_ids


def test_unlock_consumes_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert key_id not in state.inventory[agent_id].item_ids
    assert key_id not in state.key


def test_unlock_door_with_no_inventory() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state = replace(
        state,
        inventory={
            key: value for key, value in state.inventory.items() if key != agent_id
        },
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id in state.locked


def test_unlock_door_with_empty_inventory() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state = set_inventory(state, agent_id, set())
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id in state.locked


def test_unlock_multiple_doors_with_enough_keys() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = new_entity_id()
    key_id2: EntityID = new_entity_id()
    keyid_str: str = state.locked[door_id1].key_id
    pos2 = Position(0, 2)
    state = replace(
        state,
        key={**state.key, key_id2: Key(key_id=keyid_str)},
        locked={**state.locked, door_id2: Locked(key_id=keyid_str)},
        blocking={**state.blocking, door_id2: Blocking()},
        position={**state.position, door_id2: pos2},
    )
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids | {key_id, key_id2}
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    unlock_system(state, agent_id, make_step_context(state))
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id2])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id1 not in state.locked
    assert door_id2 not in state.locked


def test_unlock_multiple_doors_with_limited_keys() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = new_entity_id()
    keyid_str: str = state.locked[door_id1].key_id
    pos2 = Position(0, 2)
    state = replace(
        state,
        locked={**state.locked, door_id2: Locked(key_id=keyid_str)},
        blocking={**state.blocking, door_id2: Blocking()},
        position={**state.position, door_id2: pos2},
    )
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids | {key_id}
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    unlock_system(state, agent_id, make_step_context(state))
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id2])
    unlock_system(state, agent_id, make_step_context(state))
    unlocked_count: int = int(door_id1 not in state.locked) + int(
        door_id2 not in state.locked
    )
    assert unlocked_count == 1


def test_unlock_with_key_not_in_key_store() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = new_entity_id()
    door_id: EntityID = entities["door_id"]
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids | {key_id}
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id in state.locked
    assert key_id in state.inventory[agent_id].item_ids


def test_unlock_with_nonkey_item_in_inventory() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    nonkey_id: EntityID = new_entity_id()
    door_id: EntityID = entities["door_id"]
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids | {nonkey_id}
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id in state.locked
    assert nonkey_id in state.inventory[agent_id].item_ids


def test_unlock_at_nonlocked_position() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    unused_pos: Position = Position(2, 0)
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, unused_pos)
    unlock_system(state, agent_id, make_step_context(state))
    assert key_id in state.inventory[agent_id].item_ids


def test_unlock_after_picking_up_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    state = add_key_to_inventory(state, agent_id, key_id)
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id])
    unlock_system(state, agent_id, make_step_context(state))
    assert door_id not in state.locked
    assert key_id not in state.inventory[agent_id].item_ids


def test_multi_agent_unlock_affects_only_actor() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id1: EntityID = entities["agent_id"]
    key_id1: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    agent_id2: EntityID = new_entity_id()
    key_id2: EntityID = new_entity_id()
    door_id2: EntityID = new_entity_id()
    pos2: Position = Position(0, 5)
    state = replace(
        state,
        agent={**state.agent, agent_id2: Agent()},
        key={**state.key, key_id2: Key(key_id="blue")},
        locked={**state.locked, door_id2: Locked(key_id="blue")},
        blocking={**state.blocking, door_id2: Blocking()},
        position={**{**state.position, agent_id2: Position(0, 4)}, door_id2: pos2},
        inventory={**state.inventory, agent_id2: Inventory(item_ids=set([key_id2]))},
    )
    state = add_key_to_inventory(state, agent_id1, key_id1)
    state = move_agent_adjacent_to(state, agent_id1, state.position[door_id1])
    unlock_system(state, agent_id1, make_step_context(state))
    assert door_id2 in state.locked
    assert key_id2 in state.inventory[agent_id2].item_ids
    assert door_id1 not in state.locked


def test_unlock_adjacent_to_multiple_locked() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id1: EntityID = entities["key_id"]
    door_id1: EntityID = entities["door_id"]
    door_id2: EntityID = new_entity_id()
    pos2: Position = Position(1, 0)
    keyid_str: str = state.locked[door_id1].key_id
    key_id2: EntityID = new_entity_id()
    state = replace(
        state,
        key={**state.key, key_id2: Key(key_id=keyid_str)},
        locked={**state.locked, door_id2: Locked(key_id=keyid_str)},
        blocking={**state.blocking, door_id2: Blocking()},
        position={**state.position, door_id2: pos2},
    )
    state = set_inventory(
        state, agent_id, state.inventory[agent_id].item_ids | {key_id1, key_id2}
    )
    state = move_agent_adjacent_to(state, agent_id, state.position[door_id1])
    unlock_system(state, agent_id, make_step_context(state))
    unlocked_count: int = int(door_id1 not in state.locked) + int(
        door_id2 not in state.locked
    )
    assert unlocked_count >= 1
