from dataclasses import replace
from typing import List, Dict, Tuple, Optional, TypedDict, Literal
from pyrsistent import pmap, pset, PMap, PSet
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
from grid_universe.systems.status import status_system
from grid_universe.utils.status import use_status_effect


class RequiredEffectSpec(TypedDict):
    type: Literal["immunity", "speed", "phasing"]


class EffectSpec(RequiredEffectSpec, total=False):
    limit: Literal["time", "usage"]
    amount: int
    multiplier: int


def build_agent_with_effects(
    agent_id: Optional[EntityID] = None,
    effects: Optional[List[EffectSpec]] = None,
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
    status_effect_ids: PSet[EntityID] = pset()

    if agent_id is None:
        agent_id = new_entity_id()
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
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
        status_effect_ids = status_effect_ids.add(eid)

    status: PMap[EntityID, Status] = pmap(
        {agent_id: Status(effect_ids=status_effect_ids)}
    )

    state: State = State(
        width=3,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
        position=pmap({agent_id: Position(0, 0)}),
        agent=pmap(agent),
        inventory=pmap(inventory),
        appearance=pmap(appearance),
        immunity=pmap(immunity),
        speed=pmap(speed),
        phasing=pmap(phasing),
        time_limit=pmap(time_limit),
        usage_limit=pmap(usage_limit),
        status=status,
    )
    return state, agent_id, effect_ids


# --- TESTS ---


def test_time_limited_immunity_ticks_and_expires() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="immunity", limit="time", amount=2)]
    )
    state1 = status_system(state)
    state2 = status_system(state1)
    assert not state2.status[agent_id].effect_ids


def test_time_limited_speed_ticks_and_expires() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="speed", limit="time", amount=1)]
    )
    state1 = status_system(state)
    assert not state1.status[agent_id].effect_ids


def test_time_limited_phasing_ticks_and_expires() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="phasing", limit="time", amount=2)]
    )
    state1 = status_system(state)
    state2 = status_system(state1)
    assert not state2.status[agent_id].effect_ids


def test_usage_limited_immunity_does_not_tick() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="immunity", limit="usage", amount=3)]
    )
    state2 = status_system(state)
    assert state2.usage_limit[effect_ids[0]].amount == 3
    assert effect_ids[0] in state2.status[agent_id].effect_ids


def test_usage_limited_speed_does_not_tick() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="speed", limit="usage", amount=2)]
    )
    state2 = status_system(state)
    assert state2.usage_limit[effect_ids[0]].amount == 2
    assert effect_ids[0] in state2.status[agent_id].effect_ids


def test_usage_limited_phasing_does_not_tick() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="phasing", limit="usage", amount=2)]
    )
    state2 = status_system(state)
    assert state2.usage_limit[effect_ids[0]].amount == 2
    assert effect_ids[0] in state2.status[agent_id].effect_ids


def test_unlimited_time_immunity_does_not_expire() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="immunity")]
    )
    state2 = status_system(state)
    assert state2.status[agent_id].effect_ids


def test_unlimited_time_speed_does_not_expire() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="speed")]
    )
    state2 = status_system(state)
    assert state2.status[agent_id].effect_ids


def test_unlimited_time_phasing_does_not_expire() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[EffectSpec(type="phasing")]
    )
    state2 = status_system(state)
    assert state2.status[agent_id].effect_ids


def test_multiple_effects_tick_independently() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[
            EffectSpec(type="immunity", limit="time", amount=1),
            EffectSpec(type="speed", limit="usage", amount=2),
            EffectSpec(type="phasing", limit="time", amount=2),
        ]
    )
    state1 = status_system(state)
    remaining = state1.status[agent_id].effect_ids
    assert (
        effect_ids[0] not in remaining
        and effect_ids[1] in remaining
        and effect_ids[2] in remaining
    )
    state2 = status_system(state1)
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
        position=state1.position.update(state2.position),
        agent=state1.agent.update(state2.agent),
        inventory=state1.inventory.update(state2.inventory),
        appearance=state1.appearance.update(state2.appearance),
        immunity=state1.immunity.update(state2.immunity),
        speed=state1.speed.update(state2.speed),
        status=state1.status.update(state2.status),
        time_limit=state1.time_limit.update(state2.time_limit),
        usage_limit=state1.usage_limit.update(state2.usage_limit),
    )
    state2 = status_system(state)
    assert not state2.status[agent1].effect_ids
    assert eff2[0] in state2.status[agent2].effect_ids


def test_status_effects_empty_is_robust() -> None:
    state, agent_id, effect_ids = build_agent_with_effects()
    state2 = status_system(state)
    assert agent_id in state2.status
    assert not state2.status[agent_id].effect_ids


def test_status_system_no_agents() -> None:
    state = State(
        width=1,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, dir: []
        ),
        objective=CollectAndExitObjective(),
    )
    state2 = status_system(state)
    assert state2.status == pmap()


def test_multiple_same_type_time_limited_effects_tick_independently() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[
            EffectSpec(type="speed", limit="time", amount=1),
            EffectSpec(type="speed", limit="time", amount=3),
        ]
    )
    state1 = status_system(state)
    assert effect_ids[0] not in state1.status[agent_id].effect_ids
    assert effect_ids[1] in state1.status[agent_id].effect_ids
    state2 = status_system(state1)
    assert effect_ids[1] in state2.status[agent_id].effect_ids
    state3 = status_system(state2)
    assert not state3.status[agent_id].effect_ids


def test_multiple_usage_limited_effects_are_used_one_at_a_time() -> None:
    state, agent_id, effect_ids = build_agent_with_effects(
        effects=[
            EffectSpec(type="speed", limit="usage", amount=1),
            EffectSpec(type="speed", limit="usage", amount=2),
        ]
    )
    use1 = use_status_effect(effect_ids[0], state.usage_limit)
    assert use1[effect_ids[0]].amount == 0
    use2 = use_status_effect(effect_ids[1], use1)
    assert use2[effect_ids[1]].amount == 1
    use3 = use_status_effect(effect_ids[1], use2)
    assert use3[effect_ids[1]].amount == 0


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
        position=pmap({agent_id: Position(0, 0)}),
        agent=pmap({agent_id: Agent()}),
        status=pmap({agent_id: Status(effect_ids=pset([ghost_effect]))}),
        appearance=pmap({agent_id: Appearance(name="human")}),
    )
    state2 = status_system(state)
    assert not state2.status[agent_id].effect_ids
