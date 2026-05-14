from dataclasses import replace
from typing import Dict, Set, Tuple, Optional
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.state import State
from grid_universe.components import (
    Agent,
    Inventory,
    Collectible,
    Position,
    Status,
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
    Health,
    Blocking,
    Damage,
)
from grid_universe.types import EntityID
from grid_universe.actions import Action
from grid_universe.step import step
from ..test_utils import make_agent_state


def agent_has_effect(state: State, agent_id: EntityID, effect_id: EntityID) -> bool:
    status: Optional[Status] = state.status.get(agent_id)
    return status is not None and effect_id in status.effect_ids


def tick_turns(state: State, agent_id: EntityID, turns: int) -> State:
    for _ in range(turns):
        state = step(state, Action.WAIT, agent_id=agent_id)
    return state


def get_agent_status_effects(state: State, agent_id: EntityID) -> Set[EntityID]:
    status: Optional[Status] = state.status.get(agent_id)
    if status:
        return set(status.effect_ids)
    return set()


def make_agent_and_powerup_state(
    *,
    agent_pos: Tuple[int, int],
    powerup_pos: Tuple[int, int],
    effect_type: str,
    time_limit: Optional[int] = None,
    usage_limit: Optional[int] = None,
    speed_multiplier: Optional[int] = None,
    powerup_id: EntityID = 2,
    agent_id: EntityID = 1,
    agent_health: int = 10,
) -> Tuple[State, EntityID, EntityID]:
    pos: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        powerup_id: Position(*powerup_pos),
    }
    agent: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(set())}
    collectible: Dict[EntityID, Collectible] = {powerup_id: Collectible()}
    status: Dict[EntityID, Status] = {agent_id: Status(effect_ids=set())}
    health: Dict[EntityID, Health] = {
        agent_id: Health(current_health=agent_health, max_health=agent_health)
    }
    immunity: Dict[EntityID, Immunity] = {}
    phasing: Dict[EntityID, Phasing] = {}
    speed: Dict[EntityID, Speed] = {}
    time_limits: Dict[EntityID, TimeLimit] = {}
    usage_limits: Dict[EntityID, UsageLimit] = {}
    if effect_type == "immunity":
        immunity[powerup_id] = Immunity()
    elif effect_type == "phasing":
        phasing[powerup_id] = Phasing()
    elif effect_type == "speed":
        mul = speed_multiplier if speed_multiplier is not None else 2
        speed[powerup_id] = Speed(multiplier=mul)
    else:
        raise ValueError("Unsupported effect_type")
    if time_limit is not None:
        time_limits[powerup_id] = TimeLimit(amount=time_limit)
    if usage_limit is not None:
        usage_limits[powerup_id] = UsageLimit(amount=usage_limit)
    state: State = State(
        width=4,
        height=2,
        movement=BaseMovement(
            name="test",
            description="Test",
            function=lambda s, eid, d: [
                Position(
                    s.position[eid].x
                    + (1 if d == Action.RIGHT else -1 if d == Action.LEFT else 0),
                    s.position[eid].y
                    + (1 if d == Action.DOWN else -1 if d == Action.UP else 0),
                )
            ],
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent),
        collectible=dict(collectible),
        inventory=dict(inventory),
        health=dict(health),
        immunity=dict(immunity),
        phasing=dict(phasing),
        speed=dict(speed),
        time_limit=dict(time_limits),
        usage_limit=dict(usage_limits),
        status=dict(status),
    )
    return (state, agent_id, powerup_id)


def move_and_pickup(state: State, agent_id: EntityID, action: Action) -> State:
    state = step(state, action, agent_id=agent_id)
    state = step(state, Action.PICK_UP, agent_id=agent_id)
    return state


def test_agent_picks_up_usage_limited_powerup() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity", usage_limit=2
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    assert agent_has_effect(state, agent_id, powerup_id)
    assert state.usage_limit[powerup_id].amount == 2
    assert powerup_id not in state.collectible
    assert powerup_id not in state.position


def test_agent_picks_up_time_limited_powerup() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=3
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    assert agent_has_effect(state, agent_id, powerup_id)
    assert state.time_limit[powerup_id].amount == 3


def test_agent_picks_up_unlimited_powerup() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="speed", speed_multiplier=2
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    assert agent_has_effect(state, agent_id, powerup_id)
    assert powerup_id in state.speed
    assert powerup_id not in state.time_limit
    assert powerup_id not in state.usage_limit


def test_agent_stacks_same_type_powerup() -> None:
    state, agent_id, powerup1 = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity", usage_limit=2
    )
    powerup2: EntityID = 99
    state = replace(
        state,
        collectible={**state.collectible, powerup2: Collectible()},
        position={**state.position, powerup2: Position(2, 0)},
        immunity={**state.immunity, powerup2: Immunity()},
        usage_limit={**state.usage_limit, powerup2: UsageLimit(amount=3)},
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    effect_ids: Set[EntityID] = get_agent_status_effects(state, agent_id)
    assert powerup1 in effect_ids
    assert powerup2 in effect_ids
    assert state.usage_limit[powerup1].amount == 2
    assert state.usage_limit[powerup2].amount == 3


def test_agent_collects_different_effect_powerups() -> None:
    state, agent_id, powerup1 = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity", usage_limit=1
    )
    powerup2: EntityID = 42
    state = replace(
        state,
        collectible={**state.collectible, powerup2: Collectible()},
        position={**state.position, powerup2: Position(2, 0)},
        phasing={**state.phasing, powerup2: Phasing()},
        time_limit={**state.time_limit, powerup2: TimeLimit(amount=4)},
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    effect_ids: Set[EntityID] = get_agent_status_effects(state, agent_id)
    assert powerup1 in effect_ids
    assert powerup2 in effect_ids
    assert state.usage_limit[powerup1].amount == 1
    assert state.time_limit[powerup2].amount == 4


def test_powerup_entity_removed_on_pickup() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="speed", speed_multiplier=2
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    assert powerup_id not in state.collectible
    assert powerup_id not in state.position


def test_time_limited_powerup_expires() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=2
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 2)
    assert not agent_has_effect(state, agent_id, powerup_id)
    assert powerup_id not in state.phasing


def test_unlimited_powerup_does_not_expire() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity"
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 5)
    assert agent_has_effect(state, agent_id, powerup_id)


def test_expired_powerup_is_cleaned_from_state() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=1
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 1)
    assert powerup_id not in get_agent_status_effects(state, agent_id)
    assert powerup_id not in state.phasing
    assert powerup_id not in state.time_limit


def test_multiple_powerups_tick_independently() -> None:
    state, agent_id, p1 = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity", time_limit=1
    )
    p2: EntityID = 51
    state = replace(
        state,
        collectible={**state.collectible, p2: Collectible()},
        position={**state.position, p2: Position(2, 0)},
        phasing={**state.phasing, p2: Phasing()},
        time_limit={**state.time_limit, p2: TimeLimit(amount=3)},
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 1)
    effect_ids: Set[EntityID] = get_agent_status_effects(state, agent_id)
    assert p1 not in effect_ids
    assert p2 in effect_ids
    state = tick_turns(state, agent_id, 2)
    assert not agent_has_effect(state, agent_id, p2)


def test_powerup_not_added_if_limit_zero_or_negative() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=0
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    assert not agent_has_effect(state, agent_id, powerup_id)
    state2, agent_id2, powerup_id2 = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity", usage_limit=-2
    )
    state2 = move_and_pickup(state2, agent_id2, Action.RIGHT)
    assert not agent_has_effect(state2, agent_id2, powerup_id2)


def test_powerup_effect_applies_on_pickup_turn() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=2
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    assert agent_has_effect(state, agent_id, powerup_id)


def test_powerup_effect_removed_after_expiry() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0),
        powerup_pos=(1, 0),
        effect_type="speed",
        time_limit=1,
        speed_multiplier=2,
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 1)
    assert not agent_has_effect(state, agent_id, powerup_id)


def test_powerup_entity_not_collectible_not_picked_up() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity"
    )
    state = replace(
        state,
        collectible={
            key: value for key, value in state.collectible.items() if key != powerup_id
        },
    )
    state = step(state, Action.PICK_UP, agent_id=agent_id)
    assert not agent_has_effect(state, agent_id, powerup_id)
    assert powerup_id in state.immunity


def test_usage_limited_powerup_consumed_on_damage() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity", usage_limit=1
    )
    damage_id: EntityID = 88
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = replace(
        state,
        position={
            **{**state.position, agent_id: Position(2, 0)},
            damage_id: Position(2, 0),
        },
        damage={**state.damage, damage_id: Damage(amount=5)},
    )
    state = step(state, Action.WAIT, agent_id=agent_id)
    assert powerup_id not in state.usage_limit
    assert not agent_has_effect(state, agent_id, powerup_id)


def test_immunity_blocks_hazard_functionally() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0),
        powerup_pos=(1, 0),
        effect_type="immunity",
        usage_limit=1,
        agent_health=7,
    )
    damage_id: EntityID = 101
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = replace(
        state,
        position={
            **{**state.position, agent_id: Position(2, 0)},
            damage_id: Position(2, 0),
        },
        damage={**state.damage, damage_id: Damage(amount=5)},
    )
    state = step(state, Action.WAIT, agent_id=agent_id)
    assert state.health[agent_id].current_health == 7
    state = step(state, Action.WAIT, agent_id=agent_id)
    assert state.health[agent_id].current_health == 2


def test_phasing_allows_movement_through_blocking_functionally() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=2
    )
    block_id: EntityID = 202
    state = replace(
        state,
        blocking={**state.blocking, block_id: Blocking()},
        position={**state.position, block_id: Position(2, 0)},
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = step(state, Action.RIGHT, agent_id=agent_id)
    assert state.position[agent_id] == Position(2, 0)


def test_speed_powerup_moves_twice_functionally() -> None:
    state, agent_id, powerup_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="speed", speed_multiplier=2
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = step(state, Action.RIGHT, agent_id=agent_id)
    assert state.speed[powerup_id].multiplier == 2
    assert state.position[agent_id].x >= 1


def test_stack_unlimited_and_limited_powerups() -> None:
    state, agent_id, unlimited_id = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity"
    )
    limited_id: EntityID = 888
    state = replace(
        state,
        collectible={**state.collectible, limited_id: Collectible()},
        position={**state.position, limited_id: Position(2, 0)},
        immunity={**state.immunity, limited_id: Immunity()},
        usage_limit={**state.usage_limit, limited_id: UsageLimit(amount=2)},
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    effect_ids = get_agent_status_effects(state, agent_id)
    assert unlimited_id in effect_ids
    assert limited_id in effect_ids
    state = tick_turns(state, agent_id, 3)
    assert unlimited_id in get_agent_status_effects(state, agent_id)
    assert unlimited_id in state.immunity


def test_effect_cleanup_removes_all_components() -> None:
    state, agent_id, eid = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="phasing", time_limit=1
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 1)
    effect_ids = get_agent_status_effects(state, agent_id)
    assert eid not in effect_ids
    assert eid not in state.phasing
    assert eid not in state.time_limit


def test_multi_agent_powerup_isolation() -> None:
    state1, agent1, eid1 = make_agent_and_powerup_state(
        agent_pos=(0, 0),
        powerup_pos=(1, 0),
        effect_type="immunity",
        usage_limit=2,
        agent_id=10,
    )
    state2, agent2, eid2 = make_agent_and_powerup_state(
        agent_pos=(2, 0),
        powerup_pos=(3, 0),
        effect_type="phasing",
        time_limit=2,
        agent_id=20,
        powerup_id=30,
    )
    state = replace(
        state1,
        position={**state1.position, **state2.position},
        agent={**state1.agent, **state2.agent},
        inventory={**state1.inventory, **state2.inventory},
        collectible={**state1.collectible, **state2.collectible},
        status={**state1.status, **state2.status},
        health={**state1.health, **state2.health},
        immunity={**state1.immunity, **state2.immunity},
        phasing={**state1.phasing, **state2.phasing},
        usage_limit={**state1.usage_limit, **state2.usage_limit},
        time_limit={**state1.time_limit, **state2.time_limit},
    )
    state = move_and_pickup(state, agent1, Action.RIGHT)
    state = move_and_pickup(state, agent2, Action.RIGHT)
    assert agent_has_effect(state, agent1, eid1)
    assert agent_has_effect(state, agent2, eid2)
    state = tick_turns(state, agent1, 2)
    state = tick_turns(state, agent2, 2)
    assert agent_has_effect(state, agent1, eid1)
    assert not agent_has_effect(state, agent2, eid2)


def test_effect_priority_with_multiple_powerups() -> None:
    unlimited_id: EntityID = 900
    limited_id: EntityID = 901
    state, agent_id, _ = make_agent_and_powerup_state(
        agent_pos=(0, 0), powerup_pos=(1, 0), effect_type="immunity"
    )
    state = replace(
        state,
        collectible={
            **{**state.collectible, unlimited_id: Collectible()},
            limited_id: Collectible(),
        },
        position={
            **{**state.position, unlimited_id: Position(2, 0)},
            limited_id: Position(3, 0),
        },
        immunity={
            **{**state.immunity, unlimited_id: Immunity()},
            limited_id: Immunity(),
        },
        time_limit={**state.time_limit, limited_id: TimeLimit(amount=1)},
    )
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = move_and_pickup(state, agent_id, Action.RIGHT)
    state = tick_turns(state, agent_id, 2)
    effect_ids = get_agent_status_effects(state, agent_id)
    assert unlimited_id in effect_ids
    assert limited_id not in effect_ids


def test_speed_time_limit_pickup_then_three_moves_is_2_2_2() -> None:
    state, agent_id = make_agent_state(agent_pos=(0, 0), width=20, height=1)
    effect_id: EntityID = 6001
    state = replace(
        state,
        position={**state.position, effect_id: Position(0, 0)},
        collectible={**state.collectible, effect_id: Collectible()},
        speed={**state.speed, effect_id: Speed(multiplier=2)},
        time_limit={**state.time_limit, effect_id: TimeLimit(amount=3)},
        status={**state.status, agent_id: Status(effect_ids=set())},
    )
    state = step(state, Action.PICK_UP, agent_id=agent_id)
    state = step(state, Action.RIGHT, agent_id=agent_id)
    state = step(state, Action.RIGHT, agent_id=agent_id)
    state = step(state, Action.RIGHT, agent_id=agent_id)
    assert state.position[agent_id] == Position(6, 0)
