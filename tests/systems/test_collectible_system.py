from typing import Tuple, Dict
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.systems.collectible import collectible_system
from grid_universe.components import (
    Agent,
    Inventory,
    Collectible,
    Rewardable,
    Position,
    Requirable,
    Appearance,
)
from grid_universe.entity import new_entity_id
from grid_universe.types import EntityID
from grid_universe.state import State
from grid_universe.runtime import make_step_context


def make_collectible_state(
    agent_pos: Tuple[int, int],
    collectible_pos: Tuple[int, int],
    collectible_id: EntityID,
    collect_type: str = "item",
) -> Tuple[State, EntityID]:
    """
    Build a minimal state with an agent and one collectible of given type at the same position.
    `collect_type` can be "item", "rewardable".
    Returns (state, agent_id)
    """
    agent_id = new_entity_id()
    pos = {agent_id: Position(*agent_pos), collectible_id: Position(*collectible_pos)}
    agent = dict({agent_id: Agent()})
    inventory = dict({agent_id: Inventory(set())})
    collectible = dict({collectible_id: Collectible()})
    rewardable: dict[EntityID, Rewardable] = dict()
    requirable: dict[EntityID, Requirable] = dict()
    appearance: Dict[EntityID, Appearance] = {
        agent_id: Appearance(name="human"),
        collectible_id: Appearance(name="coin" if collect_type == "item" else "core"),
    }
    if collect_type == "rewardable":
        rewardable = dict({collectible_id: Rewardable(amount=10)})
    if collect_type == "required":
        requirable = dict({collectible_id: Requirable()})
    state = State(
        width=3,
        height=1,
        movement=BaseMovement(
            name="test",
            description="Test",
            function=lambda s, eid, dir: [Position(pos[eid].x + 1, 0)],
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=agent,
        collectible=collectible,
        rewardable=rewardable,
        requirable=requirable,
        inventory=inventory,
        appearance=dict(appearance),
    )
    return (state, agent_id)


def collect(state: State, agent_id: EntityID) -> None:
    collectible_system(state, agent_id, make_step_context(state))


def test_pickup_normal_item() -> None:
    item_id = new_entity_id()
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "item")
    collect(state, agent_id)
    new_state = state
    assert item_id in new_state.inventory[agent_id].item_ids
    assert item_id not in new_state.collectible
    assert item_id not in new_state.position


def test_pickup_rewardable_increases_score() -> None:
    item_id = new_entity_id()
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "rewardable")
    collect(state, agent_id)
    new_state = state
    assert new_state.score == 10
    assert item_id in new_state.inventory[agent_id].item_ids


def test_pickup_multiple_collectibles_all_types() -> None:
    agent_id = new_entity_id()
    item_id = new_entity_id()
    rewardable_id = new_entity_id()
    requirable_id = new_entity_id()
    pos = {
        agent_id: Position(0, 0),
        item_id: Position(0, 0),
        rewardable_id: Position(0, 0),
        requirable_id: Position(0, 0),
    }
    agent = dict({agent_id: Agent()})
    inventory = dict({agent_id: Inventory(set())})
    collectible = dict(
        {
            item_id: Collectible(),
            rewardable_id: Collectible(),
            requirable_id: Collectible(),
        }
    )
    rewardable = dict({rewardable_id: Rewardable(amount=10)})
    requirable = dict({requirable_id: Requirable()})
    appearance = {
        agent_id: Appearance(name="human"),
        item_id: Appearance(name="coin"),
        rewardable_id: Appearance(name="core"),
        requirable_id: Appearance(name="core"),
    }
    state = State(
        width=3,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=agent,
        collectible=collectible,
        rewardable=rewardable,
        requirable=requirable,
        inventory=inventory,
        appearance=dict(appearance),
    )
    collect(state, agent_id)
    new_state = state
    for i in [item_id, rewardable_id, requirable_id]:
        assert i not in new_state.collectible
        assert i not in new_state.position
    assert item_id in new_state.inventory[agent_id].item_ids
    assert rewardable_id in new_state.inventory[agent_id].item_ids
    assert requirable_id in new_state.inventory[agent_id].item_ids
    assert new_state.score == 10


def test_pickup_no_inventory_does_nothing() -> None:
    agent_id = new_entity_id()
    item_id = new_entity_id()
    pos = {agent_id: Position(0, 0), item_id: Position(0, 0)}
    agent = dict({agent_id: Agent()})
    collectible = dict({item_id: Collectible()})
    appearance = {agent_id: Appearance(name="human"), item_id: Appearance(name="coin")}
    state = State(
        width=2,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=agent,
        collectible=collectible,
        appearance=dict(appearance),
    )
    collect(state, agent_id)
    new_state = state
    assert item_id in new_state.collectible
    assert agent_id not in new_state.inventory


def test_pickup_nothing_present_does_nothing() -> None:
    agent_id = new_entity_id()
    agent = dict({agent_id: Agent()})
    inventory = dict({agent_id: Inventory(set())})
    appearance = {agent_id: Appearance(name="human")}
    state = State(
        width=1,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict({agent_id: Position(0, 0)}),
        agent=agent,
        inventory=inventory,
        appearance=dict(appearance),
    )
    collect(state, agent_id)
    new_state = state
    assert new_state == state


def test_pickup_required_collectible() -> None:
    agent_id = new_entity_id()
    req_id = new_entity_id()
    pos = {agent_id: Position(0, 0), req_id: Position(0, 0)}
    agent = dict({agent_id: Agent()})
    inventory = dict({agent_id: Inventory(set())})
    collectible = dict({req_id: Collectible()})
    requirable = dict({req_id: Requirable()})
    appearance = {agent_id: Appearance(name="human"), req_id: Appearance(name="core")}
    state = State(
        width=2,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=agent,
        collectible=collectible,
        requirable=requirable,
        inventory=inventory,
        appearance=dict(appearance),
    )
    collect(state, agent_id)
    new_state = state
    assert req_id not in new_state.collectible
    assert req_id in new_state.inventory[agent_id].item_ids
    assert req_id not in new_state.position


def test_pickup_after_collectible_already_removed() -> None:
    agent_id = new_entity_id()
    item_id = new_entity_id()
    agent = dict({agent_id: Agent()})
    inventory = dict({agent_id: Inventory(set([item_id]))})
    appearance = {agent_id: Appearance(name="human")}
    state = State(
        width=1,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict({agent_id: Position(0, 0)}),
        agent=agent,
        inventory=inventory,
        appearance=dict(appearance),
    )
    collect(state, agent_id)
    new_state = state
    assert new_state.inventory[agent_id].item_ids == set([item_id])
