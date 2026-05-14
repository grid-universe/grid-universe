from typing import Any, Dict, Tuple
from grid_universe.actions import Action
from grid_universe.components import Position, Moving, Blocking, Collidable
from grid_universe.step import step
from grid_universe.types import EntityID
from tests.test_utils import make_agent_state


def test_two_bouncing_movers_do_not_overlap_on_intersection() -> None:
    """
    Two moving, bouncing blockers start at (0,3) moving right and (3,0) moving down.
    After 3 turns they'd both target (3,3) simultaneously; ensure they don't overlap
    and that exactly one of them bounces (reverses direction).
    """
    agent_id: EntityID = 1
    right_id: EntityID = 2
    down_id: EntityID = 3
    extra = {
        "position": {right_id: Position(0, 3), down_id: Position(3, 0)},
        "moving": {
            right_id: Moving(direction="right", on_collision="bounce"),
            down_id: Moving(direction="down", on_collision="bounce"),
        },
        "blocking": {right_id: Blocking(), down_id: Blocking()},
    }
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=(4, 4), extra_components=extra
    )
    for _ in range(3):
        state = step(state, Action.WAIT, agent_id=agent_id)
    pos_right: Tuple[int, int] = (
        state.position[right_id].x,
        state.position[right_id].y,
    )
    pos_down: Tuple[int, int] = (state.position[down_id].x, state.position[down_id].y)
    assert pos_right != pos_down, f"Movers overlapped at {pos_right}"
    assert not (pos_right == (3, 3) and pos_down == (3, 3)), "Both movers reached (3,3)"
    dir_right = state.moving[right_id].direction
    dir_down = state.moving[down_id].direction
    bounced = (dir_right != "right") + (dir_down != "down")
    assert bounced == 1, (
        f"Expected exactly one bounce; directions were right={dir_right}, down={dir_down}"
    )


def test_moving_blocking_box_bounces_off_collidable_agent() -> None:
    """A blocking mover should treat a collidable agent as an obstacle and bounce."""
    agent_id: EntityID = 1
    box_id: EntityID = 2
    extra: Dict[str, Dict[EntityID, Any]] = {
        "position": {box_id: Position(2, 0)},
        "moving": {box_id: Moving(direction="right", on_collision="bounce")},
        "blocking": {box_id: Blocking()},
        "collidable": {agent_id: Collidable()},
    }
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=(3, 0), extra_components=extra, width=6, height=3
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert (state2.position[box_id].x, state2.position[box_id].y) == (2, 0)
    assert state2.moving[box_id].direction == "left"


def test_moving_collidable_enemy_does_not_bounce_on_collidable_agent() -> None:
    """A collidable-only mover should not treat collidable entities as obstacles.

    Enemy moves right from (2,0) into the agent at (3,0). It should not bounce
    and should end up overlapping the agent.
    """
    agent_id: EntityID = 1
    enemy_id: EntityID = 2
    extra: Dict[str, Dict[EntityID, Any]] = {
        "position": {enemy_id: Position(2, 0)},
        "moving": {enemy_id: Moving(direction="right", on_collision="bounce")},
        "collidable": {agent_id: Collidable(), enemy_id: Collidable()},
    }
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=(3, 0), extra_components=extra, width=6, height=3
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert (state2.position[enemy_id].x, state2.position[enemy_id].y) == (3, 0)
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (3, 0)
    assert state2.moving[enemy_id].direction == "right"
