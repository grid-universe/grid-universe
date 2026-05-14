from dataclasses import replace
from typing import List, Dict, Tuple, Optional, TypedDict, Literal
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.state import State
from grid_universe.components import (
    Status,
    Agent,
    Position,
    Inventory,
    Appearance,
    Immunity,
    Speed,
    Phasing,
    TimeLimit,
    UsageLimit,
)
from grid_universe.entity import new_entity_id
from grid_universe.types import EntityID
from grid_universe.runtime import make_step_context
from grid_universe.systems.status import status_cleanup_system, status_tick_system
from grid_universe.utils.lifetime import remove_entities
from grid_universe.utils.status import use_status_effect


class RequiredEffectSpec(TypedDict):
    type: Literal["immunity", "speed", "phasing"]


class EffectSpec(RequiredEffectSpec, total=False):
    limit: Literal["time", "usage"]
    amount: int
    multiplier: int


def build_agent_with_effects(
    agent_id: Optional[EntityID] = None, effects: Optional[List[EffectSpec]] = None
) -> Tuple[State, EntityID, List[EntityID]]:
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    appearance: Dict[EntityID, Appearance] = {}
    immunity: Dict[EntityID, Immunity] = {}
    speed: Dict[EntityID, Speed] = {}
    phasing: Dict[EntityID, Phasing] = {}
    time_limit: Dict[EntityID, TimeLimit] = {}
    usage_limit: Dict[EntityID, UsageLimit] = {}
    effect_ids: List[EntityID] = []
    status_effect_ids: set[EntityID] = set()
    if agent_id is None:
        agent_id = new_entity_id()
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(set())
    appearance[agent_id] = Appearance(name="human")
    effects = effects or []
    for eff in effects:
        eid: EntityID = new_entity_id()
        eff_type: Literal["immunity", "speed", "phasing"] = eff["type"]
        if eff_type == "immunity":
            immunity[eid] = Immunity()
        elif eff_type == "speed":
            multiplier: int = 2
            if "multiplier" in eff and eff["multiplier"] is not None:
                multiplier = eff["multiplier"]
            speed[eid] = Speed(multiplier=multiplier)
        elif eff_type == "phasing":
            phasing[eid] = Phasing()
        limit = eff.get("limit")
        amount_raw = eff.get("amount")
        if limit == "time" and amount_raw is not None:
            time_limit[eid] = TimeLimit(amount=amount_raw)
        if limit == "usage" and amount_raw is not None:
            usage_limit[eid] = UsageLimit(amount=amount_raw)
        effect_ids.append(eid)
        status_effect_ids.add(eid)
    status: dict[EntityID, Status] = dict(
        {agent_id: Status(effect_ids=status_effect_ids)}
    )
    state: State = State(
        width=3,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict({agent_id: Position(0, 0)}),
        agent=dict(agent),
        inventory=dict(inventory),
        appearance=dict(appearance),
        immunity=dict(immunity),
        speed=dict(speed),
        phasing=dict(phasing),
        time_limit=dict(time_limit),
        usage_limit=dict(usage_limit),
        status=status,
    )
    return (state, agent_id, effect_ids)


def run_status_phases(state: State) -> None:
    ctx = make_step_context(state)
    status_tick_system(state, ctx)
    status_cleanup_system(state, ctx)
    remove_entities(state, ctx, ctx.removed_entity_ids)


def test_time_limited_immunity_ticks_and_expires() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="immunity", limit="time", amount=2)]
    )
    run_status_phases(state)
    state1 = state
    run_status_phases(state1)
    state2 = state1
    assert not state2.status[agent_id].effect_ids


def test_time_limited_speed_ticks_and_expires() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="speed", limit="time", amount=1)]
    )
    run_status_phases(state)
    state1 = state
    assert not state1.status[agent_id].effect_ids


def test_time_limited_phasing_ticks_and_expires() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="phasing", limit="time", amount=2)]
    )
    run_status_phases(state)
    state1 = state
    run_status_phases(state1)
    state2 = state1
    assert not state2.status[agent_id].effect_ids


def test_usage_limited_immunity_does_not_tick() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="immunity", limit="usage", amount=3)]
    )
    run_status_phases(state)
    state2 = state
    assert state2.usage_limit[effect_ids[0]].amount == 3
    assert effect_ids[0] in state2.status[agent_id].effect_ids


def test_usage_limited_speed_does_not_tick() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="speed", limit="usage", amount=2)]
    )
    run_status_phases(state)
    state2 = state
    assert state2.usage_limit[effect_ids[0]].amount == 2
    assert effect_ids[0] in state2.status[agent_id].effect_ids


def test_usage_limited_phasing_does_not_tick() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="phasing", limit="usage", amount=2)]
    )
    run_status_phases(state)
    state2 = state
    assert state2.usage_limit[effect_ids[0]].amount == 2
    assert effect_ids[0] in state2.status[agent_id].effect_ids


def test_unlimited_time_immunity_does_not_expire() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="immunity")]
    )
    run_status_phases(state)
    state2 = state
    assert state2.status[agent_id].effect_ids


def test_unlimited_time_speed_does_not_expire() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="speed")]
    )
    run_status_phases(state)
    state2 = state
    assert state2.status[agent_id].effect_ids


def test_unlimited_time_phasing_does_not_expire() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="phasing")]
    )
    run_status_phases(state)
    state2 = state
    assert state2.status[agent_id].effect_ids


def test_multiple_effects_tick_independently() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[
            EffectSpec(type="immunity", limit="time", amount=1),
            EffectSpec(type="speed", limit="usage", amount=2),
            EffectSpec(type="phasing", limit="time", amount=2),
        ]
    )
    run_status_phases(state)
    state1 = state
    remaining = state1.status[agent_id].effect_ids
    assert (
        effect_ids[0] not in remaining
        and effect_ids[1] in remaining
        and (effect_ids[2] in remaining)
    )
    run_status_phases(state1)
    state2 = state1
    remaining2 = state2.status[agent_id].effect_ids
    assert effect_ids[1] in remaining2 and effect_ids[2] not in remaining2


def test_multi_agent_effects_are_isolated() -> None:
    state1, agent1, eff1 = build_agent_with_effects(
        agent_id=1, effects=[EffectSpec(type="immunity", limit="time", amount=1)]
    )
    state2, agent2, eff2 = build_agent_with_effects(
        agent_id=2, effects=[EffectSpec(type="speed", limit="usage", amount=2)]
    )
    state = replace(
        state1,
        position={**state1.position, **state2.position},
        agent={**state1.agent, **state2.agent},
        inventory={**state1.inventory, **state2.inventory},
        appearance={**state1.appearance, **state2.appearance},
        immunity={**state1.immunity, **state2.immunity},
        speed={**state1.speed, **state2.speed},
        status={**state1.status, **state2.status},
        time_limit={**state1.time_limit, **state2.time_limit},
        usage_limit={**state1.usage_limit, **state2.usage_limit},
    )
    run_status_phases(state)
    state2 = state
    assert not state2.status[agent1].effect_ids
    assert eff2[0] in state2.status[agent2].effect_ids


def test_status_effects_empty_is_robust() -> None:
    state, agent_id, effect_ids = build_agent_with_effects()
    run_status_phases(state)
    state2 = state
    assert agent_id in state2.status
    assert not state2.status[agent_id].effect_ids


def test_status_phases_no_agents() -> None:
    state = State(
        width=1,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
    )
    run_status_phases(state)
    state2 = state
    assert state2.status == dict()


def test_multiple_same_type_time_limited_effects_tick_independently() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[
            EffectSpec(type="speed", limit="time", amount=1),
            EffectSpec(type="speed", limit="time", amount=3),
        ]
    )
    run_status_phases(state)
    state1 = state
    assert effect_ids[0] not in state1.status[agent_id].effect_ids
    assert effect_ids[1] in state1.status[agent_id].effect_ids
    run_status_phases(state1)
    state2 = state1
    assert effect_ids[1] in state2.status[agent_id].effect_ids
    run_status_phases(state2)
    state3 = state2
    assert not state3.status[agent_id].effect_ids


def test_multiple_usage_limited_effects_are_used_one_at_a_time() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[
            EffectSpec(type="speed", limit="usage", amount=1),
            EffectSpec(type="speed", limit="usage", amount=2),
        ]
    )
    use_status_effect(effect_ids[0], state.usage_limit)
    assert state.usage_limit[effect_ids[0]].amount == 0
    use_status_effect(effect_ids[1], state.usage_limit)
    assert state.usage_limit[effect_ids[1]].amount == 1
    use_status_effect(effect_ids[1], state.usage_limit)
    assert state.usage_limit[effect_ids[1]].amount == 0


def test_status_cleanup_for_missing_effect() -> None:
    agent_id: EntityID = new_entity_id()
    ghost_effect: EntityID = new_entity_id()
    state = State(
        width=1,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=dict({agent_id: Position(0, 0)}),
        agent=dict({agent_id: Agent()}),
        status=dict({agent_id: Status(effect_ids=set([ghost_effect]))}),
        appearance=dict({agent_id: Appearance(name="human")}),
    )
    run_status_phases(state)
    state2 = state
    assert not state2.status[agent_id].effect_ids
