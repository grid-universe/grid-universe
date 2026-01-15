from dataclasses import replace
from typing import Tuple, List

import pytest
from pyrsistent import pmap

from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import (
    Collidable,
    Position,
    Agent,
    Pushable,
    Portal,
    Appearance,
)
from grid_universe.entity import new_entity_id
from grid_universe.systems.portal import portal_system
from grid_universe.runtime import StepContext


def make_entity_on_portal_state(
    entity_id: EntityID,
    is_agent: bool,
    portal1_id: EntityID,
    portal2_id: EntityID,
    entity_pos: Tuple[int, int],
    portal1_pos: Tuple[int, int],
    portal2_pos: Tuple[int, int],
) -> State:
    position = {
        entity_id: Position(*entity_pos),
        portal1_id: Position(*portal1_pos),
        portal2_id: Position(*portal2_pos),
    }
    portal = {
        portal1_id: Portal(pair_entity=portal2_id),
        portal2_id: Portal(pair_entity=portal1_id),
    }
    collidable = {entity_id: Collidable()}
    appearance = {
        entity_id: Appearance(name=("human" if is_agent else "box")),
        portal1_id: Appearance(name="portal"),
        portal2_id: Appearance(name="portal"),
    }
    agent = {entity_id: Agent()} if is_agent else {}
    pushable = {entity_id: Pushable()} if not is_agent else {}

    return State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        position=pmap(position),
        agent=pmap(agent),
        pushable=pmap(pushable),
        portal=pmap(portal),
        appearance=pmap(appearance),
        collidable=pmap(collidable),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )


ENTITY_TYPES: List[Tuple[str, bool]] = [
    ("agent", True),
    ("pushable", False),
]


@pytest.mark.parametrize("entity_label,is_agent", ENTITY_TYPES)
def test_entity_standing_on_portal_does_not_teleport(
    entity_label: str,
    is_agent: bool,
) -> None:
    entity_id: EntityID = new_entity_id()
    portal1_id: EntityID = new_entity_id()
    portal2_id: EntityID = new_entity_id()
    entity_pos: Tuple[int, int] = (4, 4)
    portal1_pos: Tuple[int, int] = (4, 4)
    portal2_pos: Tuple[int, int] = (7, 7)

    state: State = make_entity_on_portal_state(
        entity_id,
        is_agent,
        portal1_id,
        portal2_id,
        entity_pos,
        portal1_pos,
        portal2_pos,
    )

    ctx = StepContext(prev_position=state.position)
    new_state: State = portal_system(state, ctx)
    assert new_state.position[entity_id] == Position(*portal1_pos)


@pytest.mark.parametrize("entity_label, is_agent", ENTITY_TYPES)
def test_entity_teleported_when_entering_portal(
    entity_label: str,
    is_agent: bool,
) -> None:
    entity_id: EntityID = new_entity_id()
    portal1_id: EntityID = new_entity_id()
    portal2_id: EntityID = new_entity_id()
    start_pos: Tuple[int, int] = (1, 1)
    portal1_pos: Tuple[int, int] = (4, 4)
    portal2_pos: Tuple[int, int] = (7, 7)

    state: State = make_entity_on_portal_state(
        entity_id,
        is_agent,
        portal1_id,
        portal2_id,
        start_pos,
        portal1_pos,
        portal2_pos,
    )
    moved_state: State = replace(
        state,
        position=state.position.set(entity_id, Position(*portal1_pos)),
    )
    ctx = StepContext(prev_position=state.position)
    new_state: State = portal_system(moved_state, ctx)
    assert new_state.position[entity_id] == Position(*portal2_pos)


@pytest.mark.parametrize("entity_label, is_agent", ENTITY_TYPES)
def test_entity_not_teleported_if_not_on_portal(
    entity_label: str,
    is_agent: bool,
) -> None:
    entity_id: EntityID = new_entity_id()
    portal1_id: EntityID = new_entity_id()
    portal2_id: EntityID = new_entity_id()
    entity_pos: Tuple[int, int] = (1, 2)
    portal1_pos: Tuple[int, int] = (3, 5)
    portal2_pos: Tuple[int, int] = (7, 7)

    state: State = make_entity_on_portal_state(
        entity_id,
        is_agent,
        portal1_id,
        portal2_id,
        entity_pos,
        portal1_pos,
        portal2_pos,
    )

    ctx = StepContext(prev_position=state.position)
    new_state: State = portal_system(state, ctx)
    assert new_state.position[entity_id] == Position(*entity_pos)


def test_pushable_teleported_when_pushed_onto_portal() -> None:
    entity_id: EntityID = new_entity_id()
    portal1_id: EntityID = new_entity_id()
    portal2_id: EntityID = new_entity_id()
    start_pos: Tuple[int, int] = (2, 2)
    portal1_pos: Tuple[int, int] = (4, 4)
    portal2_pos: Tuple[int, int] = (8, 8)
    state: State = make_entity_on_portal_state(
        entity_id, False, portal1_id, portal2_id, start_pos, portal1_pos, portal2_pos
    )
    moved_state: State = replace(
        state,
        position=state.position.set(entity_id, Position(*portal1_pos)),
    )
    ctx = StepContext(prev_position=state.position)
    new_state: State = portal_system(moved_state, ctx)
    assert new_state.position[entity_id] == Position(*portal2_pos)


def test_portal_pair_missing_does_not_crash() -> None:
    agent_id: EntityID = new_entity_id()
    portal1_id: EntityID = new_entity_id()
    agent_pos: Tuple[int, int] = (2, 2)
    portal1_pos: Tuple[int, int] = (2, 2)
    position = {
        agent_id: Position(*agent_pos),
        portal1_id: Position(*portal1_pos),
    }
    portal = {portal1_id: Portal(pair_entity=999)}
    collidable = {agent_id: Collidable()}
    appearance = {
        agent_id: Appearance(name="human"),
        portal1_id: Appearance(name="portal"),
    }
    state: State = State(
        width=5,
        height=5,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        position=pmap(position),
        agent=pmap({agent_id: Agent()}),
        portal=pmap(portal),
        appearance=pmap(appearance),
        collidable=pmap(collidable),
    )
    ctx = StepContext(prev_position=state.position)
    new_state: State = portal_system(state, ctx)
    assert new_state.position[agent_id] == Position(*agent_pos)


def test_multiple_entities_on_portal_all_blocked() -> None:
    agent_id: EntityID = new_entity_id()
    pushable_id: EntityID = new_entity_id()
    portal1_id: EntityID = new_entity_id()
    portal2_id: EntityID = new_entity_id()
    portal1_pos: Tuple[int, int] = (2, 2)
    portal2_pos: Tuple[int, int] = (7, 7)
    prev_agent_pos: Tuple[int, int] = (1, 2)
    prev_pushable_pos: Tuple[int, int] = (6, 7)
    position = {
        agent_id: Position(*portal1_pos),
        pushable_id: Position(*portal2_pos),
        portal1_id: Position(*portal1_pos),
        portal2_id: Position(*portal2_pos),
    }
    prev_position = {
        agent_id: Position(*prev_agent_pos),
        pushable_id: Position(*prev_pushable_pos),
        portal1_id: Position(*portal1_pos),
        portal2_id: Position(*portal2_pos),
    }
    portal = {
        portal1_id: Portal(pair_entity=portal2_id),
        portal2_id: Portal(pair_entity=portal1_id),
    }
    collidable = {agent_id: Collidable(), pushable_id: Collidable()}
    appearance = {
        agent_id: Appearance(name="human"),
        pushable_id: Appearance(name="box"),
        portal1_id: Appearance(name="portal"),
        portal2_id: Appearance(name="portal"),
    }
    state = State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        position=pmap(position),
        agent=pmap({agent_id: Agent()}),
        pushable=pmap({pushable_id: Pushable()}),
        portal=pmap(portal),
        appearance=pmap(appearance),
        collidable=pmap(collidable),
    )
    ctx = StepContext(prev_position=pmap(prev_position))
    new_state: State = portal_system(state, ctx)
    assert new_state.position[agent_id] == Position(*portal1_pos)
    assert new_state.position[pushable_id] == Position(*portal2_pos)


def test_entity_chained_portals_no_infinite_teleport() -> None:
    from grid_universe.components import (
        Collidable,
        Portal,
        Appearance,
        Agent,
    )

    agent_id: EntityID = new_entity_id()
    portal_a: EntityID = new_entity_id()
    portal_b: EntityID = new_entity_id()
    portal_c: EntityID = new_entity_id()
    pos_a: Tuple[int, int] = (2, 2)
    pos_b: Tuple[int, int] = (4, 4)
    pos_c: Tuple[int, int] = (6, 6)
    prev_agent_pos: Tuple[int, int] = (1, 2)  # Simulate moving onto portal A

    position = {
        agent_id: Position(*pos_a),
        portal_a: Position(*pos_a),
        portal_b: Position(*pos_b),
        portal_c: Position(*pos_c),
    }
    prev_position = {
        agent_id: Position(*prev_agent_pos),
        portal_a: Position(*pos_a),
        portal_b: Position(*pos_b),
        portal_c: Position(*pos_c),
    }
    portal = {
        portal_a: Portal(pair_entity=portal_b),
        portal_b: Portal(pair_entity=portal_c),
        portal_c: Portal(pair_entity=portal_a),
    }
    collidable = {agent_id: Collidable()}
    appearance = {
        agent_id: Appearance(name="human"),
        portal_a: Appearance(name="portal"),
        portal_b: Appearance(name="portal"),
        portal_c: Appearance(name="portal"),
    }
    state: State = State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        position=pmap(position),
        agent=pmap({agent_id: Agent()}),
        portal=pmap(portal),
        appearance=pmap(appearance),
        collidable=pmap(collidable),
    )
    ctx = StepContext(prev_position=pmap(prev_position))
    new_state: State = portal_system(state, ctx)
    # Only one teleport: A→B (not B→C or C→A)
    assert new_state.position[agent_id] == Position(*pos_b)
