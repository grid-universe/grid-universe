# tests/unit/test_moves.py

import pytest
import random
from typing import List, Sequence, Tuple, Dict
from dataclasses import replace

from grid_universe.movements import (
    CardinalMovement,
    WrapAroundMovement,
    MirrorMovement,
    SlipperyMovement,
    GravityMovement,
    WindyMovement,
    BaseMovement,
    slippery_move_fn,
    windy_move_fn,
    gravity_move_fn,
)
from grid_universe.actions import Action
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.components import Position, Blocking
from grid_universe.types import EntityID
from tests.test_utils import make_agent_state


@pytest.mark.parametrize(
    "movement, start, Action, expected",
    [
        # CardinalMovement, all Actions
        (CardinalMovement(), (2, 2), Action.UP, (2, 1)),
        (CardinalMovement(), (2, 2), Action.DOWN, (2, 3)),
        (CardinalMovement(), (2, 2), Action.LEFT, (1, 2)),
        (CardinalMovement(), (2, 2), Action.RIGHT, (3, 2)),
        # CardinalMovement, out-of-bounds
        (CardinalMovement(), (0, 0), Action.LEFT, (-1, 0)),
        (CardinalMovement(), (0, 0), Action.UP, (0, -1)),
        (CardinalMovement(), (4, 4), Action.DOWN, (4, 5)),
        (CardinalMovement(), (4, 4), Action.RIGHT, (5, 4)),
        # WrapAroundMovement, edge wrap
        (WrapAroundMovement(), (0, 1), Action.LEFT, (4, 1)),
        (WrapAroundMovement(), (4, 1), Action.RIGHT, (0, 1)),
        (WrapAroundMovement(), (2, 0), Action.UP, (2, 4)),
        (WrapAroundMovement(), (2, 4), Action.DOWN, (2, 0)),
        # WrapAroundMovement, not at edge (should not wrap)
        (WrapAroundMovement(), (2, 2), Action.UP, (2, 1)),
        (WrapAroundMovement(), (2, 2), Action.LEFT, (1, 2)),
        # MirrorMovement
        (MirrorMovement(), (2, 2), Action.UP, (2, 1)),  # UP mirrored to UP
        (MirrorMovement(), (2, 2), Action.DOWN, (2, 3)),  # DOWN mirrored to DOWN
        (MirrorMovement(), (2, 2), Action.LEFT, (3, 2)),  # LEFT mirrored to RIGHT
        (MirrorMovement(), (2, 2), Action.RIGHT, (1, 2)),  # RIGHT mirrored to LEFT
        # MirrorMovement, out-of-bounds mirror
        (MirrorMovement(), (0, 0), Action.LEFT, (1, 0)),  # mirrors to right
        (
            MirrorMovement(),
            (0, 0),
            Action.RIGHT,
            (-1, 0),
        ),  # mirrors to left (out of grid)
    ],
)
def test_simple_moves(
    movement: BaseMovement,
    start: Tuple[int, int],
    Action: Action,
    expected: Tuple[int, int],
) -> None:
    width: int = 5
    height: int = 5
    state, agent_id = make_agent_state(
        agent_pos=start,
        movement=movement,
        width=width,
        height=height,
    )
    positions: Sequence[Position] = movement(state, agent_id, Action)
    assert positions and positions[0] == Position(*expected)


@pytest.mark.parametrize(
    "movement",
    [
        CardinalMovement(),
        WrapAroundMovement(),
        MirrorMovement(),
        SlipperyMovement(),
        WindyMovement(),
        GravityMovement(),
    ],
)
def test_move_fn_missing_position_raises(
    movement: BaseMovement,
) -> None:
    width: int = 3
    height: int = 3
    state, agent_id = make_agent_state(
        agent_pos=(1, 1),
        movement=movement,
        width=width,
        height=height,
    )
    state = replace(state, position=state.position.remove(agent_id))
    with pytest.raises(KeyError):
        movement(state, agent_id, Action.UP)


def test_wrap_around_move_fn_raises_on_missing_size() -> None:
    state, agent_id = make_agent_state(agent_pos=(1, 1), movement=WrapAroundMovement())
    # Remove width/height using dataclasses.replace (frozen dataclass)
    state = replace(state, width=None, height=None)  # type: ignore
    with pytest.raises(ValueError):
        state.movement(state, agent_id, Action.UP)


@pytest.mark.parametrize(
    "start, blockers, Action, expected",
    [
        ((1, 1), [(3, 1)], Action.RIGHT, [(2, 1)]),  # slides until before wall
        ((1, 1), [], Action.RIGHT, [(2, 1), (3, 1), (4, 1)]),  # slides to edge
        ((1, 1), [(2, 1)], Action.RIGHT, [(1, 1)]),  # blocked immediately
        (
            (1, 1),
            [(1, 4)],
            Action.DOWN,
            [(1, 2), (1, 3)],
        ),  # slides till before wall at bottom
        ((1, 4), [], Action.DOWN, [(1, 4)]),  # stuck at edge, can't slide
        ((0, 0), [], Action.LEFT, [(0, 0)]),  # stuck at edge, can't slide
    ],
)
def test_slippery_move_fn(
    start: Tuple[int, int],
    blockers: List[Tuple[int, int]],
    Action: Action,
    expected: List[Tuple[int, int]],
) -> None:
    width: int = 5
    height: int = 5
    blocking_entities: Dict[EntityID, Blocking] = {}
    pos_map: Dict[EntityID, Position] = {}
    for idx, blocker_pos in enumerate(blockers):
        wid: EntityID = 100 + idx
        blocking_entities[wid] = Blocking()
        pos_map[wid] = Position(*blocker_pos)
    extra = {
        "blocking": blocking_entities,
        "position": pos_map,
    }
    state, agent_id = make_agent_state(
        agent_pos=start,
        movement=SlipperyMovement(),
        objective=CollectAndExitObjective(),
        width=width,
        height=height,
        extra_components=extra,
    )
    positions: Sequence[Position] = slippery_move_fn(state, agent_id, Action)
    assert [p for p in positions] == [Position(*xy) for xy in expected]


@pytest.mark.parametrize(
    "start, blockers, Action, expected",
    [
        ((1, 1), [(1, 3)], Action.DOWN, [(1, 2)]),  # falls to just before wall
        ((1, 1), [], Action.DOWN, [(1, 2), (1, 3), (1, 4)]),  # falls to bottom
        ((1, 1), [(1, 2)], Action.DOWN, [(1, 1)]),  # blocked immediately
        ((1, 4), [], Action.DOWN, [(1, 4)]),  # at bottom: can't move
    ],
)
def test_gravity_move_fn(
    start: Tuple[int, int],
    blockers: List[Tuple[int, int]],
    Action: Action,
    expected: List[Tuple[int, int]],
) -> None:
    width: int = 5
    height: int = 5
    blocking_entities: Dict[EntityID, Blocking] = {}
    pos_map: Dict[EntityID, Position] = {}
    for idx, blocker_pos in enumerate(blockers):
        wid: EntityID = 200 + idx
        blocking_entities[wid] = Blocking()
        pos_map[wid] = Position(*blocker_pos)
    extra = {
        "blocking": blocking_entities,
        "position": pos_map,
    }
    state, agent_id = make_agent_state(
        agent_pos=start,
        movement=GravityMovement(),
        objective=CollectAndExitObjective(),
        width=width,
        height=height,
        extra_components=extra,
    )
    positions: Sequence[Position] = gravity_move_fn(state, agent_id, Action)
    assert [p for p in positions] == [Position(*xy) for xy in expected]


@pytest.mark.parametrize(
    "wind_first, wind_dir, start, Action, blockers, expected",
    [
        # No wind, just first move
        (0.5, (0, 1), (1, 1), Action.UP, [], [(1, 0)]),
        # Wind triggers, wind right, not blocked
        (0.1, (1, 0), (1, 1), Action.UP, [], [(1, 0), (2, 0)]),
        # Wind triggers, wind left, not blocked
        (0.1, (-1, 0), (1, 1), Action.UP, [], [(1, 0), (0, 0)]),
        # Wind triggers, wind up, but first move out of bounds—should just return current pos
        (0.1, (0, -1), (0, 0), Action.UP, [], [(0, 0)]),
        # Wind triggers, wind right, but right is blocked (move fn does not check blockers)
        (0.1, (1, 0), (1, 1), Action.UP, [(2, 0)], [(1, 0), (2, 0)]),
    ],
)
def test_windy_move_fn(
    monkeypatch: pytest.MonkeyPatch,
    wind_first: float,
    wind_dir: Tuple[int, int],
    start: Tuple[int, int],
    Action: Action,
    blockers: List[Tuple[int, int]],
    expected: List[Tuple[int, int]],
) -> None:
    class DummyRng:
        def random(self) -> float:
            return wind_first

        def choice(self, *_) -> Tuple[int, int]:
            return wind_dir

    monkeypatch.setattr(random, "Random", lambda *_args, **_kw: DummyRng())
    width: int = 5
    height: int = 5
    blocking_entities: Dict[EntityID, Blocking] = {}
    pos_map: Dict[EntityID, Position] = {}
    for idx, blocker_pos in enumerate(blockers):
        wid: EntityID = 300 + idx
        blocking_entities[wid] = Blocking()
        pos_map[wid] = Position(*blocker_pos)
    extra = {
        "blocking": blocking_entities,
        "position": pos_map,
    }
    state, agent_id = make_agent_state(
        agent_pos=start,
        movement=WindyMovement(),
        objective=CollectAndExitObjective(),
        width=width,
        height=height,
        extra_components=extra,
    )
    positions: Sequence[Position] = windy_move_fn(state, agent_id, Action)
    assert [p for p in positions] == [Position(*xy) for xy in expected]
