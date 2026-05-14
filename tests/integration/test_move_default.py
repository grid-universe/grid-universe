from typing import Tuple
import pytest
from grid_universe.actions import Action
from grid_universe.components import (
    Exit,
    Pushable,
    Position,
    LethalDamage,
    Blocking,
    Health,
    Speed,
    Status,
    Phasing,
)
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.types import EntityID
from grid_universe.step import step
from grid_universe.movements import CardinalMovement, BaseMovement
from tests.test_utils import make_agent_state


def test_agent_moves_right() -> None:
    agent_id: EntityID = 1
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=(1, 1), movement=CardinalMovement()
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)


@pytest.mark.parametrize(
    "start, action, expected",
    [
        ((1, 1), Action.UP, (1, 0)),
        ((1, 1), Action.DOWN, (1, 2)),
        ((1, 1), Action.LEFT, (0, 1)),
        ((1, 1), Action.RIGHT, (2, 1)),
    ],
)
def test_agent_moves_in_all_actions(
    start: Tuple[int, int], action: Action, expected: Tuple[int, int]
) -> None:
    agent_id: EntityID = 1
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=start, movement=CardinalMovement()
    )
    state2 = step(state, action, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == expected


@pytest.mark.parametrize(
    "start, action",
    [
        ((0, 0), Action.LEFT),
        ((0, 0), Action.UP),
        ((4, 4), Action.RIGHT),
        ((4, 4), Action.DOWN),
    ],
)
def test_agent_blocked_by_edge(start: Tuple[int, int], action: Action) -> None:
    agent_id: EntityID = 1
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=start, movement=CardinalMovement()
    )
    state2 = step(state, action, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == start


def test_agent_blocked_by_wall() -> None:
    agent_id: EntityID = 1
    wall_id: EntityID = 2
    extra = {"position": {wall_id: Position(2, 1)}, "blocking": {wall_id: Blocking()}}
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 1)


def test_agent_pushes_single_box() -> None:
    agent_id: EntityID = 1
    box_id: EntityID = 2
    extra = {"position": {box_id: Position(2, 1)}, "pushable": {box_id: Pushable()}}
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)
    assert (state2.position[box_id].x, state2.position[box_id].y) == (3, 1)


def test_agent_blocked_by_chain_of_boxes() -> None:
    agent_id: EntityID = 1
    box1: EntityID = 2
    box2: EntityID = 3
    extra = {
        "position": {box1: Position(2, 1), box2: Position(3, 1)},
        "pushable": {box1: Pushable(), box2: Pushable()},
    }
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 1)
    assert (state2.position[box1].x, state2.position[box1].y) == (2, 1)
    assert (state2.position[box2].x, state2.position[box2].y) == (3, 1)


def test_agent_with_ghost_moves_through_wall() -> None:
    agent_id: EntityID = 1
    wall_id: EntityID = 2
    effect_id: EntityID = 200
    extra = {
        "position": {wall_id: Position(2, 1)},
        "blocking": {wall_id: Blocking()},
        "status": {agent_id: Status(effect_ids=set([effect_id]))},
        "phasing": {effect_id: Phasing()},
    }
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)


def test_agent_with_double_speed_moves_two_steps() -> None:
    agent_id: EntityID = 1
    effect_id: EntityID = 201
    extra = {
        "status": {agent_id: Status(effect_ids=set([effect_id]))},
        "speed": {effect_id: Speed(multiplier=2)},
    }
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (3, 1)


def test_agent_wins_on_exit() -> None:
    agent_id: EntityID = 1
    exit_id: EntityID = 5
    extra = {"position": {exit_id: Position(2, 1)}, "exit": {exit_id: Exit()}}
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)
    assert state2.win


def test_agent_loses_on_hazard() -> None:
    agent_id: EntityID = 1
    hazard_id: EntityID = 20
    extra = {
        "position": {hazard_id: Position(2, 1)},
        "lethal_damage": {hazard_id: LethalDamage()},
        "health": {agent_id: Health(current_health=1, max_health=1)},
    }
    state, _ = make_agent_state(
        agent_id=agent_id,
        agent_pos=(1, 1),
        extra_components=extra,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)
    assert agent_id in state2.dead


def test_agent_move_fn_returns_empty_list() -> None:
    agent_id: EntityID = 1
    empty_movement = BaseMovement(
        name="empty",
        description="Movement that returns empty list",
        function=lambda state, eid, action: [],
    )
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=(1, 1), movement=empty_movement
    )
    state2 = step(state, Action.RIGHT, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 1)
