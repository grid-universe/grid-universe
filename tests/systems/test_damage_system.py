from dataclasses import replace
from typing import Dict, List, Tuple, Optional
from pyrsistent import pmap, PMap, pset
import pytest

from grid_universe.movements import BaseMovement
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.state import State
from grid_universe.components import (
    Position,
    Agent,
    Health,
    Damage,
    LethalDamage,
    Dead,
    Appearance,
    Collidable,
    Immunity,
    Status,
)
from grid_universe.systems.damage import damage_system
from grid_universe.types import EntityID
from grid_universe.runtime import make_step_context


def step_damage(state: State) -> State:
    next_state, _ = damage_system(state, make_step_context(state))
    return next_state


def build_agent_with_sources(
    *,
    agent_id: EntityID = 1,
    agent_health: int = 10,
    agent_pos: Tuple[int, int] = (0, 0),
    agent_immunity: bool = False,
    agent_dead: bool = False,
    sources: Optional[List[Dict[str, object]]] = None,
) -> Tuple[State, EntityID, List[EntityID]]:
    """
    Build a minimal ECS state with one agent and arbitrary damage/lethal sources at agent's position.
    All IDs are deterministic and all ECS maps are consistent.
    """
    sources = sources or []
    # ECS maps for agent
    position: Dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    health: Dict[EntityID, Health] = {
        agent_id: Health(current_health=agent_health, max_health=agent_health)
    }
    appearance: Dict[EntityID, Appearance] = {agent_id: Appearance(name="human")}
    collidable: Dict[EntityID, Collidable] = {agent_id: Collidable()}
    immunity: Dict[EntityID, Immunity] = {}
    damage_map: Dict[EntityID, Damage] = {}
    lethal_damage_map: Dict[EntityID, LethalDamage] = {}
    dead_map: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()

    status = {}
    if agent_immunity:
        immunity_id = 9999
        immunity = {immunity_id: Immunity()}
        status = {agent_id: Status(effect_ids=pset([immunity_id]))}

    # Add source entities with IDs 2, 3, 4, ...
    source_ids: List[EntityID] = []
    for i, src in enumerate(sources):
        src_id: EntityID = 2 + i
        pos_tuple: Tuple[int, int] = src.get("pos", agent_pos)  # type: ignore
        position[src_id] = Position(*pos_tuple)
        appearance[src_id] = Appearance(name=src.get("appearance", "lava"))  # type: ignore
        collidable[src_id] = Collidable()
        if "damage" in src and src["damage"] is not None:
            damage_map[src_id] = Damage(amount=int(src["damage"]))  # type: ignore
        if src.get("lethal", False):
            lethal_damage_map[src_id] = LethalDamage()
        source_ids.append(src_id)

    state: State = State(
        width=10,
        height=10,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
        position=pmap(position),
        agent=pmap(agent_map),
        health=pmap(health),
        appearance=pmap(appearance),
        dead=dead_map,
        collidable=pmap(collidable),
        damage=pmap(damage_map),
        lethal_damage=pmap(lethal_damage_map),
        immunity=pmap(immunity),
        status=pmap(status),
    )
    return state, agent_id, source_ids


def assert_health(state: State, agent_id: EntityID, expected: int) -> None:
    assert agent_id in state.health, (
        f"agent_id {agent_id} not in health map: {state.health}"
    )
    assert state.health[agent_id].current_health == expected


def test_agent_takes_damage_from_single_source() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"damage": 4, "pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 6)


def test_agent_dies_from_lethal_damage_source() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"lethal": True, "pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert agent_id in state2.dead


def test_agent_survives_zero_damage() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"damage": 0, "pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 10)


def test_negative_damage_raises_error() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"damage": -3, "pos": (0, 0)}],
    )
    with pytest.raises(ValueError):
        step_damage(state)


def test_agent_takes_accumulated_damage_from_multiple_sources() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[
            {"damage": 2, "pos": (0, 0)},
            {"damage": 3, "pos": (0, 0)},
        ],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 5)


def test_lethal_damage_takes_precedence_over_accumulated_damage() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[
            {"damage": 2, "pos": (0, 0)},
            {"damage": 3, "lethal": True, "pos": (0, 0)},
        ],
    )
    state2: State = step_damage(state)
    assert agent_id in state2.dead


def test_multiple_sources_mixed_damage_and_lethal() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[
            {"damage": 1, "pos": (0, 0)},
            {"damage": 2, "lethal": True, "pos": (0, 0)},
            {"damage": 7, "pos": (0, 0)},
        ],
    )
    state2: State = step_damage(state)
    assert agent_id in state2.dead


def test_damage_does_not_underflow_below_zero() -> None:
    state, agent_id, _ = build_agent_with_sources(
        agent_health=3,
        sources=[{"damage": 10, "pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 0)


def test_no_damage_when_agent_not_on_source() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"damage": 7, "pos": (2, 2)}],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 10)


def test_no_damage_or_lethal_component_present() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 10)


def test_damage_sources_with_zero_and_positive_damage() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[
            {"damage": 0, "pos": (0, 0)},
            {"damage": 5, "pos": (0, 0)},
        ],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 5)


def test_already_dead_agent_not_affected() -> None:
    state, agent_id, _ = build_agent_with_sources(
        agent_dead=True,
        sources=[{"damage": 3, "pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert agent_id in state2.dead
    assert agent_id in state2.health
    assert state2.health[agent_id].current_health == 10


def test_agent_with_no_health_component() -> None:
    state, agent_id, _ = build_agent_with_sources(
        sources=[{"damage": 6, "pos": (0, 0)}],
    )
    state = replace(state, health=pmap())
    state2: State = step_damage(state)
    assert agent_id not in state2.health


def test_damage_component_negative_amount_is_robust() -> None:
    state, agent_id, source_ids = build_agent_with_sources(
        sources=[{"damage": 3, "pos": (0, 0)}],
    )
    src_id: EntityID = source_ids[0]
    state = replace(state, damage=state.damage.set(src_id, Damage(amount=-999)))
    with pytest.raises(ValueError):
        step_damage(state)


def test_multiple_agents_each_take_appropriate_damage() -> None:
    agent1: EntityID = 1
    agent2: EntityID = 2
    position: Dict[EntityID, Position] = {
        agent1: Position(1, 1),
        agent2: Position(2, 2),
        3: Position(1, 1),
        4: Position(2, 2),
    }
    agent_map: Dict[EntityID, Agent] = {agent1: Agent(), agent2: Agent()}
    health: Dict[EntityID, Health] = {
        agent1: Health(current_health=10, max_health=10),
        agent2: Health(current_health=10, max_health=10),
    }
    appearance: Dict[EntityID, Appearance] = {
        agent1: Appearance(name="human"),
        agent2: Appearance(name="human"),
        3: Appearance(name="lava"),
    }
    collidable: Dict[EntityID, Collidable] = {
        agent1: Collidable(),
        agent2: Collidable(),
        3: Collidable(),
        4: Collidable(),
    }
    damage_map: Dict[EntityID, Damage] = {3: Damage(amount=2), 4: Damage(amount=3)}

    state: State = State(
        width=10,
        height=10,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
        position=pmap(position),
        agent=pmap(agent_map),
        health=pmap(health),
        appearance=pmap(appearance),
        collidable=pmap(collidable),
        damage=pmap(damage_map),
    )
    state2: State = step_damage(state)
    assert agent1 in state2.health and state2.health[agent1].current_health == 8
    assert agent2 in state2.health and state2.health[agent2].current_health == 7


def test_agent_with_immunity_component_blocks_damage() -> None:
    state, agent_id, _ = build_agent_with_sources(
        agent_immunity=True,
        sources=[{"damage": 5, "pos": (0, 0)}],
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 10)
    assert agent_id not in state2.dead


def test_damage_and_unrelated_components_do_not_interfere() -> None:
    state, agent_id, source_ids = build_agent_with_sources(
        sources=[{"damage": 4, "pos": (0, 0)}],
    )
    unrelated_id: EntityID = 99
    state = replace(
        state,
        position=state.position.set(unrelated_id, Position(0, 0)),
        rewardable=state.rewardable.set(unrelated_id, object()),  # type: ignore
        appearance=state.appearance.set(unrelated_id, Appearance(name="coin")),
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 6)


def test_agent_with_multiple_health_entries_is_robust() -> None:
    state, agent_id, source_ids = build_agent_with_sources(
        sources=[{"damage": 2, "pos": (0, 0)}],
    )
    state = replace(
        state,
        health=state.health.set(agent_id, Health(current_health=5, max_health=10)),
    )
    state2: State = step_damage(state)
    assert_health(state2, agent_id, 3)
