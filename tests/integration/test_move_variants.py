from typing import Tuple
import pytest
from grid_universe.actions import Action
from grid_universe.components import (
    Exit,
    Position,
    Pushable,
    Blocking,
    LethalDamage,
    Health,
)
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.types import EntityID
from grid_universe.movements import (
    WrapAroundMovement,
    SlipperyMovement,
    WindyMovement,
    GravityMovement,
)
from grid_universe.step import step
from tests.test_utils import make_agent_state

# --- WRAP-AROUND UNIQUE TESTS ---


@pytest.mark.parametrize(
    "start, action, expected",
    [
        ((0, 2), Action.LEFT, (4, 2)),
        ((4, 2), Action.RIGHT, (0, 2)),
        ((3, 0), Action.UP, (3, 4)),
        ((3, 4), Action.DOWN, (3, 0)),
    ],
)
def test_wrap_around_at_edges(
    start: Tuple[int, int], action: Action, expected: Tuple[int, int]
) -> None:
    state, agent_id = make_agent_state(
        agent_pos=start, movement=WrapAroundMovement(), width=5, height=5
    )
    state2 = step(state, action, agent_id=agent_id)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == expected


def test_wrap_around_blocked_destination() -> None:
    wall_id: EntityID = 2
    extra = {"position": {wall_id: Position(0, 2)}, "blocking": {wall_id: Blocking()}}
    state, agent_id = make_agent_state(
        agent_pos=(4, 2), extra_components=extra, movement=WrapAroundMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    # Should not move; destination is blocked
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (4, 2)


def test_wrap_around_push_box() -> None:
    box_id: EntityID = 2
    extra = {
        "position": {box_id: Position(0, 2)},
        "pushable": {box_id: Pushable()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(4, 2), extra_components=extra, movement=WrapAroundMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    # Agent wraps to (0,2), box moves to (1,2)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (0, 2)
    assert (state2.position[box_id].x, state2.position[box_id].y) == (1, 2)


def test_wrap_around_push_box_from_edge():
    box_id: EntityID = 2
    extra = {
        "position": {box_id: Position(0, 2)},
        "pushable": {box_id: Pushable()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(4, 2), extra_components=extra, movement=WrapAroundMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (0, 2)
    assert (state2.position[box_id].x, state2.position[box_id].y) == (1, 2)


def test_wrap_around_win_on_exit() -> None:
    exit_id: EntityID = 5
    extra = {
        "position": {exit_id: Position(0, 2)},
        "exit": {exit_id: Exit()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(4, 2), extra_components=extra, movement=WrapAroundMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (0, 2)
    assert state2.win


def test_wrap_around_lose_on_hazard() -> None:
    agent_id: EntityID = 1
    hazard_id: EntityID = 20
    extra = {
        "health": {agent_id: Health(current_health=1, max_health=1)},
        "position": {hazard_id: Position(0, 2)},
        "lethal_damage": {hazard_id: LethalDamage()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(4, 2),
        extra_components=extra,
        movement=WrapAroundMovement(),
        objective=CollectAndExitObjective(),
        width=5,
        agent_id=agent_id,
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (0, 2)
    assert agent_id in state2.dead


# --- SLIPPERY UNIQUE TESTS ---


def test_slippery_slides_until_blocked() -> None:
    wall_id: EntityID = 2
    extra = {"position": {wall_id: Position(4, 2)}, "blocking": {wall_id: Blocking()}}
    state, agent_id = make_agent_state(
        agent_pos=(1, 2), extra_components=extra, movement=SlipperyMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    # Should stop before wall at (4,2): lands at (3,2)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (3, 2)


def test_slippery_slides_to_edge() -> None:
    state, agent_id = make_agent_state(
        agent_pos=(1, 2), movement=SlipperyMovement(), width=5
    )
    state2 = step(
        state,
        Action.LEFT,
        agent_id=agent_id,
    )
    # Should slide to (0,2)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (0, 2)


def test_slippery_push_box_and_slide() -> None:
    box_id: EntityID = 2
    extra = {
        "position": {box_id: Position(2, 2)},
        "pushable": {box_id: Pushable()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 2), extra_components=extra, movement=SlipperyMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    # With no blocker, agent should end at (3,2), box at (4,2)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (3, 2)
    assert (state2.position[box_id].x, state2.position[box_id].y) == (4, 2)


def test_slippery_slide_win_on_exit() -> None:
    exit_id: EntityID = 5
    extra = {
        "position": {exit_id: Position(4, 2)},
        "exit": {exit_id: Exit()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 2), extra_components=extra, movement=SlipperyMovement(), width=5
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (4, 2)
    assert state2.win


def test_slippery_slide_lose_on_hazard() -> None:
    agent_id: EntityID = 1
    hazard_id: EntityID = 20
    extra = {
        "health": {agent_id: Health(current_health=1, max_health=1)},
        "position": {hazard_id: Position(4, 2)},
        "lethal_damage": {hazard_id: LethalDamage()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 2),
        extra_components=extra,
        movement=SlipperyMovement(),
        objective=CollectAndExitObjective(),
        width=5,
        agent_id=agent_id,
    )
    state2 = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (4, 2)
    assert agent_id in state2.dead


# --- WINDY UNIQUE TESTS ---


class DummyRng:
    def random(self) -> float:
        return 0.1  # < 0.3, so wind triggers

    def choice(self, *_) -> Tuple[int, int]:
        return (1, 0)  # wind to the right


def test_windy_random_move(monkeypatch) -> None:
    # Monkeypatch random to always trigger wind to the right
    import grid_universe.movements as moves_mod

    monkeypatch.setattr(moves_mod.random, "Random", lambda *_args, **_kw: DummyRng())
    state, agent_id = make_agent_state(agent_pos=(1, 1), movement=WindyMovement())
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    # Moves down, then right due to wind
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 2)


def test_windy_blocked_by_wall(monkeypatch) -> None:
    wall_id: EntityID = 2
    import grid_universe.movements as moves_mod

    monkeypatch.setattr(moves_mod.random, "Random", lambda *_args, **_kw: DummyRng())
    extra = {"position": {wall_id: Position(2, 2)}, "blocking": {wall_id: Blocking()}}
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, movement=WindyMovement()
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    # Moves down to (1,2), then wind tries right to (2,2) but blocked, so stays at (1,2)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 2)


def test_windy_win_on_exit(monkeypatch) -> None:
    exit_id: EntityID = 5
    import grid_universe.movements as moves_mod

    monkeypatch.setattr(moves_mod.random, "Random", lambda *_args, **_kw: DummyRng())
    extra = {
        "position": {exit_id: Position(2, 2)},
        "exit": {exit_id: Exit()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, movement=WindyMovement()
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 2)
    assert state2.win


def test_windy_lose_on_hazard(monkeypatch) -> None:
    agent_id: EntityID = 1
    hazard_id: EntityID = 20
    import grid_universe.movements as moves_mod

    monkeypatch.setattr(moves_mod.random, "Random", lambda *_args, **_kw: DummyRng())
    extra = {
        "health": {agent_id: Health(current_health=1, max_health=1)},
        "position": {hazard_id: Position(2, 2)},
        "lethal_damage": {hazard_id: LethalDamage()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1),
        extra_components=extra,
        movement=WindyMovement(),
        objective=CollectAndExitObjective(),
        agent_id=agent_id,
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 2)
    assert agent_id in state2.dead


# --- GRAVITY UNIQUE TESTS ---


def test_gravity_falls_until_blocked() -> None:
    wall_id: EntityID = 2
    extra = {"position": {wall_id: Position(1, 4)}, "blocking": {wall_id: Blocking()}}
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, movement=GravityMovement(), height=5
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    # Should fall to (1,3), stopped before wall at (1,4)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 3)


def test_gravity_stops_at_bottom() -> None:
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), movement=GravityMovement(), height=5
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    # Should fall to (1,4)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 4)


def test_gravity_win_by_falling_on_exit() -> None:
    exit_id: EntityID = 5
    extra = {
        "position": {exit_id: Position(1, 4)},
        "exit": {exit_id: Exit()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, movement=GravityMovement(), height=5
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 4)
    assert state2.win


def test_gravity_lose_by_falling_on_hazard() -> None:
    agent_id: EntityID = 1
    hazard_id: EntityID = 20
    extra = {
        "health": {agent_id: Health(current_health=1, max_health=1)},
        "position": {hazard_id: Position(1, 4)},
        "lethal_damage": {hazard_id: LethalDamage()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1),
        extra_components=extra,
        movement=GravityMovement(),
        objective=CollectAndExitObjective(),
        height=5,
        agent_id=agent_id,
    )
    state2 = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 4)
    assert agent_id in state2.dead
