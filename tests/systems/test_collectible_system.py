from typing import Tuple, Dict
from pyrsistent.typing import PMap
from grid_universe.objectives import default_objective_fn
from grid_universe.systems.collectible import collectible_system
from grid_universe.components import (
    Agent,
    Inventory,
    Collectible,
    Rewardable,
    Position,
    Requirable,
    Appearance,
    AppearanceName,
)
from grid_universe.entity import new_entity_id
from grid_universe.types import EntityID
from pyrsistent import pmap, pset
from grid_universe.state import State


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
    pos = {
        agent_id: Position(*agent_pos),
        collectible_id: Position(*collectible_pos),
    }
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap({collectible_id: Collectible()})
    rewardable: PMap[EntityID, Rewardable] = pmap()
    requirable: PMap[EntityID, Requirable] = pmap()
    appearance: Dict[EntityID, Appearance] = {
        agent_id: Appearance(name=AppearanceName.HUMAN),
        collectible_id: Appearance(
            name=AppearanceName.COIN if collect_type == "item" else AppearanceName.CORE
        ),
    }

    if collect_type == "rewardable":
        rewardable = pmap({collectible_id: Rewardable(amount=10)})
    if collect_type == "required":
        requirable = pmap({collectible_id: Requirable()})

    state = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(pos[eid].x + 1, 0)],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=agent,
        collectible=collectible,
        rewardable=rewardable,
        requirable=requirable,
        inventory=inventory,
        appearance=pmap(appearance),
    )
    return state, agent_id


def test_pickup_normal_item() -> None:
    item_id = new_entity_id()
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "item")
    new_state = collectible_system(state, agent_id)
    # Item should be in inventory
    assert item_id in new_state.inventory[agent_id].item_ids
    # Collectible should be removed from world
    assert item_id not in new_state.collectible
    assert item_id not in new_state.position


def test_pickup_rewardable_increases_score() -> None:
    item_id = new_entity_id()
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "rewardable")
    new_state = collectible_system(state, agent_id)
    # Score should have increased
    assert new_state.score == 10
    # Item should be in inventory
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
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap(
        {
            item_id: Collectible(),
            rewardable_id: Collectible(),
            requirable_id: Collectible(),
        }
    )
    rewardable = pmap({rewardable_id: Rewardable(amount=10)})
    requirable = pmap({requirable_id: Requirable()})
    appearance = {
        agent_id: Appearance(name=AppearanceName.HUMAN),
        item_id: Appearance(name=AppearanceName.COIN),
        rewardable_id: Appearance(name=AppearanceName.CORE),
        requirable_id: Appearance(name=AppearanceName.CORE),
    }

    state = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=agent,
        collectible=collectible,
        rewardable=rewardable,
        requirable=requirable,
        inventory=inventory,
        appearance=pmap(appearance),
    )
    new_state = collectible_system(state, agent_id)
    # All should be out of world maps
    for i in [item_id, rewardable_id, requirable_id]:
        assert i not in new_state.collectible
        assert i not in new_state.position
    # Inventory contains items
    assert item_id in new_state.inventory[agent_id].item_ids
    assert rewardable_id in new_state.inventory[agent_id].item_ids
    assert requirable_id in new_state.inventory[agent_id].item_ids
    # Score increased
    assert new_state.score == 10


def test_pickup_no_inventory_does_nothing() -> None:
    agent_id = new_entity_id()
    item_id = new_entity_id()
    pos = {agent_id: Position(0, 0), item_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    collectible = pmap({item_id: Collectible()})
    appearance = {
        agent_id: Appearance(name=AppearanceName.HUMAN),
        item_id: Appearance(name=AppearanceName.COIN),
    }

    state = State(
        width=2,
        height=1,
        move_fn=lambda s, eid, dir: [],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=agent,
        collectible=collectible,
        appearance=pmap(appearance),
    )
    new_state = collectible_system(state, agent_id)
    # Collectible should be unchanged
    assert item_id in new_state.collectible
    # No crash, inventory still missing
    assert agent_id not in new_state.inventory


def test_pickup_nothing_present_does_nothing() -> None:
    agent_id = new_entity_id()
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    appearance = {agent_id: Appearance(name=AppearanceName.HUMAN)}

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        objective_fn=default_objective_fn,
        position=pmap({agent_id: Position(0, 0)}),
        agent=agent,
        inventory=inventory,
        appearance=pmap(appearance),
    )
    new_state = collectible_system(state, agent_id)
    assert new_state == state  # No change


def test_pickup_required_collectible() -> None:
    agent_id = new_entity_id()
    req_id = new_entity_id()
    pos = {agent_id: Position(0, 0), req_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap({req_id: Collectible()})
    requirable = pmap({req_id: Requirable()})
    appearance = {
        agent_id: Appearance(name=AppearanceName.HUMAN),
        req_id: Appearance(name=AppearanceName.CORE),
    }

    state = State(
        width=2,
        height=1,
        move_fn=lambda s, eid, dir: [],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=agent,
        collectible=collectible,
        requirable=requirable,
        inventory=inventory,
        appearance=pmap(appearance),
    )
    new_state = collectible_system(state, agent_id)
    assert req_id not in new_state.collectible
    assert req_id in new_state.inventory[agent_id].item_ids
    assert req_id not in new_state.position


def test_pickup_after_collectible_already_removed() -> None:
    agent_id = new_entity_id()
    item_id = new_entity_id()
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset([item_id]))})
    appearance = {agent_id: Appearance(name=AppearanceName.HUMAN)}

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        objective_fn=default_objective_fn,
        position=pmap({agent_id: Position(0, 0)}),
        agent=agent,
        inventory=inventory,
        appearance=pmap(appearance),
    )
    new_state = collectible_system(state, agent_id)
    # Should not crash or change the inventory
    assert new_state.inventory[agent_id].item_ids == pset([item_id])
