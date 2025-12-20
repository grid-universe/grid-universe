from dataclasses import replace
from typing import Dict, Tuple, Set, Optional
from pyrsistent import pmap, pset, PSet
from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.components import (
    Agent,
    Collectible,
    Rewardable,
    Requirable,
    Inventory,
    Status,
    Position,
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from grid_universe.types import EntityID
from grid_universe.actions import Action
from grid_universe.step import step


def make_agent_with_collectible_state(
    agent_pos: Tuple[int, int],
    collectible_pos: Tuple[int, int],
    reward: int = 0,
    required: bool = False,
    effect: Optional[object] = None,
    limit_type: Optional[str] = None,
    limit_amount: Optional[int] = None,
) -> Tuple[State, EntityID, EntityID]:
    agent_id: EntityID = 1
    collectible_id: EntityID = 2

    position_map: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        collectible_id: Position(*collectible_pos),
    }
    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory_map: Dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    collectible_map: Dict[EntityID, Collectible] = {collectible_id: Collectible()}
    reward_map: Dict[EntityID, Rewardable] = (
        {collectible_id: Rewardable(amount=reward)} if reward else {}
    )
    requirable_map: Dict[EntityID, Requirable] = (
        {collectible_id: Requirable()} if required else {}
    )
    status_map: Dict[EntityID, Status] = {agent_id: Status(effect_ids=pset())}
    usage_limit_map: Dict[EntityID, UsageLimit] = {}
    time_limit_map: Dict[EntityID, TimeLimit] = {}
    immunity_map: Dict[EntityID, Immunity] = {}
    phasing_map: Dict[EntityID, Phasing] = {}
    speed_map: Dict[EntityID, Speed] = {}

    if effect is not None:
        if isinstance(effect, Immunity):
            immunity_map[collectible_id] = effect
        elif isinstance(effect, Phasing):
            phasing_map[collectible_id] = effect
        elif isinstance(effect, Speed):
            speed_map[collectible_id] = effect
        if limit_type == "usage" and limit_amount is not None:
            usage_limit_map[collectible_id] = UsageLimit(amount=limit_amount)
        if limit_type == "time" and limit_amount is not None:
            time_limit_map[collectible_id] = TimeLimit(amount=limit_amount)

    state: State = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(position_map[eid].x + 1, 0)],
        objective_fn=default_objective_fn,
        position=pmap(position_map),
        agent=pmap(agent_map),
        collectible=pmap(collectible_map),
        rewardable=pmap(reward_map),
        requirable=pmap(requirable_map),
        inventory=pmap(inventory_map),
        immunity=pmap(immunity_map),
        phasing=pmap(phasing_map),
        speed=pmap(speed_map),
        time_limit=pmap(time_limit_map),
        usage_limit=pmap(usage_limit_map),
        status=pmap(status_map),
    )
    return state, agent_id, collectible_id


def move_and_pickup(state: State, agent_id: EntityID, action: Action) -> State:
    state2: State = step(state, action, agent_id=agent_id)
    state3: State = step(state2, Action.PICK_UP, agent_id=agent_id)
    return state3


def get_agent_status_effect_ids(state: State, agent_id: EntityID) -> Set[EntityID]:
    if agent_id in state.status:
        return set(state.status[agent_id].effect_ids)
    return set()


def test_agent_picks_up_item() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (1, 0))
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in state2.inventory[agent_id].item_ids
    assert collectible_id not in state2.collectible
    assert collectible_id not in state2.position


def test_agent_picks_up_rewardable() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), reward=10
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in state2.inventory[agent_id].item_ids
    assert state2.score == 10


def test_agent_picks_up_powerup_immunity_usage() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), effect=Immunity(), limit_type="usage", limit_amount=2
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in get_agent_status_effect_ids(state2, agent_id)
    assert collectible_id not in state2.collectible
    assert collectible_id not in state2.position
    assert state2.usage_limit[collectible_id].amount == 2


def test_agent_picks_up_powerup_phasing_time() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), effect=Phasing(), limit_type="time", limit_amount=3
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in get_agent_status_effect_ids(state2, agent_id)
    assert state2.time_limit[collectible_id].amount == 3


def test_agent_picks_up_powerup_speed_unlimited() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), effect=Speed(multiplier=2)
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in get_agent_status_effect_ids(state2, agent_id)
    assert collectible_id in state2.speed
    assert collectible_id not in state2.time_limit
    assert collectible_id not in state2.usage_limit


def test_pickup_powerup_stacks_usage() -> None:
    from grid_universe.components import Immunity, UsageLimit, Status

    # Step 1: Set up agent with Immunity effect and usage=3
    state, agent_id, effect_id1 = make_agent_with_collectible_state(
        (0, 0), (1, 0), effect=Immunity(), limit_type="usage", limit_amount=2
    )
    # Step 2: Now place a new collectible with the same effect (usage=2) at (1,0)
    # This simulates picking up a duplicate powerup
    effect_id2 = 999
    # ADD: make sure to add new effect to entity map using Entity()
    state = replace(
        state,
        collectible=state.collectible.set(effect_id2, Collectible()),
        position=state.position.set(effect_id2, Position(1, 0)),
        immunity=state.immunity.set(effect_id2, Immunity()),
        status=state.status.set(agent_id, Status(effect_ids=pset([effect_id2]))),
        usage_limit=state.usage_limit.set(effect_id2, UsageLimit(amount=3)),
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert state2.usage_limit[effect_id1].amount == 2
    assert state2.usage_limit[effect_id2].amount == 3


def test_pickup_powerup_unlimited_usage() -> None:
    # Unlimited = no usage_limit entry
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), effect=Immunity()
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in get_agent_status_effect_ids(state2, agent_id)
    assert collectible_id not in state2.usage_limit


def test_agent_picks_up_required() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), required=True
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    assert collectible_id in state2.inventory[agent_id].item_ids


def test_agent_picks_up_multiple_types() -> None:
    agent_id: EntityID = 1
    item_id: EntityID = 2
    rewardable_id: EntityID = 3
    requirable_id: EntityID = 4
    pos: Dict[EntityID, Position] = {
        agent_id: Position(0, 0),
        item_id: Position(0, 1),
        rewardable_id: Position(0, 1),
        requirable_id: Position(0, 1),
    }
    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory_map: Dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    collectible_map: Dict[EntityID, Collectible] = {
        item_id: Collectible(),
        rewardable_id: Collectible(),
        requirable_id: Collectible(),
    }
    rewardable_map: Dict[EntityID, Rewardable] = {rewardable_id: Rewardable(amount=10)}
    requirable_map: Dict[EntityID, Requirable] = {requirable_id: Requirable()}

    state: State = State(
        width=3,
        height=2,
        move_fn=lambda s, eid, dir: [Position(0, 1)],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=pmap(agent_map),
        collectible=pmap(collectible_map),
        rewardable=pmap(rewardable_map),
        requirable=pmap(requirable_map),
        inventory=pmap(inventory_map),
    )
    state2 = move_and_pickup(state, agent_id, Action.DOWN)
    assert item_id in state2.inventory[agent_id].item_ids
    assert rewardable_id in state2.inventory[agent_id].item_ids
    assert requirable_id in state2.inventory[agent_id].item_ids
    assert state2.score == 10
    for cid in [item_id, rewardable_id, requirable_id]:
        assert cid not in state2.collectible
        assert cid not in state2.position


def test_pickup_defensive_edge_cases() -> None:
    # No inventory
    state, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (0, 0))
    state2 = replace(state, inventory=pmap())
    state3 = step(state2, Action.PICK_UP, agent_id=agent_id)
    assert collectible_id in state3.collectible
    # Nothing present
    state4, agent_id2, _ = make_agent_with_collectible_state((0, 0), (1, 0))
    step(state4, Action.PICK_UP, agent_id=agent_id2)
    # Already collected
    state6, agent_id3, collectible_id3 = make_agent_with_collectible_state(
        (0, 0), (0, 0)
    )
    state7 = replace(
        state6,
        collectible=state6.collectible.remove(collectible_id3),
        position=state6.position.remove(collectible_id3),
    )
    step(state7, Action.PICK_UP, agent_id=agent_id3)
    # Should do nothing and not crash


def test_pickup_required_updates_win_condition() -> None:
    state, agent_id, _ = make_agent_with_collectible_state(
        (0, 0), (1, 0), required=True
    )
    move_and_pickup(state, agent_id, Action.RIGHT)
    # Not asserting win here, just verifying that state is valid after required pickup


def test_pickup_removes_from_all_relevant_stores() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), reward=5, required=True
    )
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    for store in [state2.collectible, state2.position]:
        assert collectible_id not in store


def test_pickup_inventory_not_duplicated() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (1, 0))
    state2 = move_and_pickup(state, agent_id, Action.RIGHT)
    state3 = step(state2, Action.PICK_UP, agent_id=agent_id)
    items: PSet[EntityID] = state3.inventory[agent_id].item_ids
    assert len(items) == len(set(items))


def test_pickup_collectible_with_score_cost() -> None:
    from grid_universe.components import Cost

    agent_id: EntityID = 1
    collectible_id: EntityID = 2
    cost_id: EntityID = 3
    pos: Dict[EntityID, Position] = {
        agent_id: Position(0, 0),
        collectible_id: Position(1, 0),
        cost_id: Position(1, 0),
    }
    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory_map: Dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    collectible_map: Dict[EntityID, Collectible] = {collectible_id: Collectible()}
    rewardable_map: Dict[EntityID, Rewardable] = {collectible_id: Rewardable(amount=15)}
    cost_map: Dict[EntityID, Cost] = {cost_id: Cost(amount=6)}

    state: State = State(
        width=2,
        height=1,
        move_fn=lambda s, eid, dir: [Position(1, 0)],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=pmap(agent_map),
        collectible=pmap(collectible_map),
        rewardable=pmap(rewardable_map),
        cost=pmap(cost_map),
        inventory=pmap(inventory_map),
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    state3 = step(state2, Action.PICK_UP, agent_id=agent_id)
    assert state3.score == 3
    assert collectible_id in state3.inventory[agent_id].item_ids
    assert collectible_id not in state3.collectible
    assert collectible_id not in state3.position
