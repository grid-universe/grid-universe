import pytest
from grid_universe.actions import Action
from grid_universe.grid.convert import to_state
from grid_universe.grid.gridstate import GridState
from grid_universe.grid.step import step
from grid_universe.grid.entity import Entity
from grid_universe.grid.factories import (
    create_agent,
    create_wall,
    create_key,
    create_door,
    create_coin,
    create_core,
    create_exit,
    create_box,
)
from grid_universe.movements import CardinalMovement, WrapAroundMovement
from grid_universe.objectives import CollectAndExitObjective


def find_entity_position(
    gridstate: GridState, entity: Entity
) -> tuple[int, int] | None:
    """Find the position of an entity in the grid, return None if not found."""
    for x in range(gridstate.width):
        for y in range(gridstate.height):
            if entity in gridstate.grid[x][y]:
                return (x, y)
    return None


def has_component_at_pos(
    gridstate: GridState, pos: tuple[int, int], component_name: str
) -> bool:
    """Check if any entity at the given position has the specified component."""
    x, y = pos
    for obj in gridstate.grid[x][y]:
        if getattr(obj, component_name, None) is not None:
            return True
    return False


def test_step_move_right() -> None:
    """Agent should move right when Action.RIGHT is applied."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((1, 1), agent)
    new_grid_state = step(gridstate, Action.RIGHT)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (2, 1)


def test_step_move_left() -> None:
    """Agent should move left when Action.LEFT is applied."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((2, 2), agent)
    new_grid_state = step(gridstate, Action.LEFT)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (1, 2)


def test_step_move_up() -> None:
    """Agent should move up when Action.UP is applied."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((2, 2), agent)
    new_grid_state = step(gridstate, Action.UP)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (2, 1)


def test_step_move_down() -> None:
    """Agent should move down when Action.DOWN is applied."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((2, 2), agent)
    new_grid_state = step(gridstate, Action.DOWN)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (2, 3)


@pytest.mark.parametrize(
    "start_pos, action, expected_pos",
    [
        ((1, 1), Action.UP, (1, 0)),
        ((1, 1), Action.DOWN, (1, 2)),
        ((1, 1), Action.LEFT, (0, 1)),
        ((1, 1), Action.RIGHT, (2, 1)),
        ((2, 2), Action.UP, (2, 1)),
        ((2, 2), Action.DOWN, (2, 3)),
        ((2, 2), Action.LEFT, (1, 2)),
        ((2, 2), Action.RIGHT, (3, 2)),
    ],
)
def test_step_all_directions(
    start_pos: tuple[int, int], action: Action, expected_pos: tuple[int, int]
) -> None:
    """Test all movement directions from various positions."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add(start_pos, agent)
    new_grid_state = step(gridstate, action)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == expected_pos


def test_step_blocked_by_wall() -> None:
    """Agent should not move through a wall."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    wall = create_wall()
    gridstate.add((1, 1), agent)
    gridstate.add((2, 1), wall)
    new_grid_state = step(gridstate, Action.RIGHT)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (1, 1)


@pytest.mark.parametrize(
    "start_pos, action",
    [
        ((0, 0), Action.LEFT),
        ((0, 0), Action.UP),
        ((4, 4), Action.RIGHT),
        ((4, 4), Action.DOWN),
    ],
)
def test_step_blocked_by_edge(start_pos: tuple[int, int], action: Action) -> None:
    """Agent should not move outside grid boundaries with CardinalMovement."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add(start_pos, agent)
    new_grid_state = step(gridstate, action)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == start_pos


def test_step_push_box() -> None:
    """Agent should push a pushable box."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    box = create_box()
    gridstate.add((1, 1), agent)
    gridstate.add((2, 1), box)
    new_grid_state = step(gridstate, Action.RIGHT)
    agent_pos = find_entity_position(new_grid_state, agent)
    box_pos = find_entity_position(new_grid_state, box)
    assert agent_pos == (2, 1)
    assert box_pos == (3, 1)


def test_step_push_box_blocked_by_wall() -> None:
    """Agent should not push a box if blocked by a wall."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    box = create_box()
    wall = create_wall()
    gridstate.add((1, 1), agent)
    gridstate.add((2, 1), box)
    gridstate.add((3, 1), wall)
    new_grid_state = step(gridstate, Action.RIGHT)
    agent_pos = find_entity_position(new_grid_state, agent)
    box_pos = find_entity_position(new_grid_state, box)
    assert agent_pos == (1, 1)
    assert box_pos == (2, 1)


def test_step_pickup_coin() -> None:
    """Agent should pick up a coin at their location."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    coin = create_coin(reward=10)
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), coin)
    new_grid_state = step(gridstate, Action.PICK_UP)
    coin_pos = find_entity_position(new_grid_state, coin)
    assert coin_pos is None
    assert new_grid_state.score == 10


def test_step_pickup_key() -> None:
    """Agent should pick up a key."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    key = create_key(key_id="red")
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), key)
    new_grid_state = step(gridstate, Action.PICK_UP)
    key_pos = find_entity_position(new_grid_state, key)
    assert key_pos is None


def test_step_pickup_core() -> None:
    """Agent should pick up a core (required collectible)."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    core = create_core(reward=50, required=True)
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), core)
    new_grid_state = step(gridstate, Action.PICK_UP)
    core_pos = find_entity_position(new_grid_state, core)
    assert core_pos is None
    assert new_grid_state.score == 50


def test_step_pickup_nothing() -> None:
    """PICK_UP with nothing to pick up should not error."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((1, 1), agent)
    new_grid_state = step(gridstate, Action.PICK_UP)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (1, 1)


def test_step_use_key_unlock_door() -> None:
    """Agent with a key should unlock adjacent door."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    key = create_key(key_id="red")
    door = create_door(key_id="red")
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), key)
    gridstate.add((2, 1), door)
    gridstate = step(gridstate, Action.PICK_UP)
    new_grid_state = step(gridstate, Action.USE_KEY)
    has_locked = has_component_at_pos(new_grid_state, (2, 1), "locked")
    assert has_locked is False
    final_state = step(new_grid_state, Action.RIGHT)
    agent_in_final = None
    for obj in final_state.grid[2][1]:
        if getattr(obj, "agent", None) is not None:
            agent_in_final = obj
            break
    assert agent_in_final is not None


def test_step_use_key_no_key() -> None:
    """USE_KEY without a key should not crash."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    door = create_door(key_id="red")
    gridstate.add((1, 1), agent)
    gridstate.add((2, 1), door)
    new_grid_state = step(gridstate, Action.USE_KEY)
    door_pos = find_entity_position(new_grid_state, door)
    assert door_pos == (2, 1)


def test_step_use_key_wrong_key() -> None:
    """USE_KEY with wrong key should not unlock door."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    key = create_key(key_id="blue")
    door = create_door(key_id="red")
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), key)
    gridstate.add((2, 1), door)
    gridstate = step(gridstate, Action.PICK_UP)
    new_grid_state = step(gridstate, Action.USE_KEY)
    has_locked = has_component_at_pos(new_grid_state, (2, 1), "locked")
    assert has_locked is True
    final_state = step(new_grid_state, Action.RIGHT)
    agent_in_final = None
    for obj in final_state.grid[1][1]:
        if getattr(obj, "agent", None) is not None:
            agent_in_final = obj
            break
    assert agent_in_final is not None


def test_step_wait() -> None:
    """WAIT action should not move agent but advance turn."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((2, 2), agent)
    initial_turn = gridstate.turn
    new_grid_state = step(gridstate, Action.WAIT)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (2, 2)
    assert new_grid_state.turn == initial_turn + 1


def test_step_with_explicit_agent_id() -> None:
    """Step should work with explicit agent_id parameter."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((1, 1), agent)
    state = to_state(gridstate)
    agent_id = next(iter(state.agent.keys()))
    new_grid_state = step(gridstate, Action.RIGHT, agent_id=agent_id)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (2, 1)


def test_step_no_agent_raises() -> None:
    """Step should raise StopIteration when no agent exists."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    with pytest.raises(StopIteration):
        step(gridstate, Action.RIGHT)


def test_step_win_condition() -> None:
    """Agent reaching exit with all cores should trigger win."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    core = create_core(reward=10, required=True)
    exit_tile = create_exit()
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), core)
    gridstate.add((2, 1), exit_tile)
    gridstate = step(gridstate, Action.PICK_UP)
    new_grid_state = step(gridstate, Action.RIGHT)
    assert new_grid_state.win is True


def test_step_terminal_state_no_further_steps() -> None:
    """Once in terminal state (win), further steps should not change state."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    core = create_core(reward=10, required=True)
    exit_tile = create_exit()
    gridstate.add((1, 1), agent)
    gridstate.add((1, 1), core)
    gridstate.add((2, 1), exit_tile)
    gridstate = step(gridstate, Action.PICK_UP)
    gridstate = step(gridstate, Action.RIGHT)
    assert gridstate.win is True
    agent_found = False
    for obj in gridstate.grid[2][1]:
        if getattr(obj, "agent", None) is not None:
            agent_found = True
            break
    assert agent_found
    new_grid_state = step(gridstate, Action.LEFT)
    agent_still_there = False
    for obj in new_grid_state.grid[2][1]:
        if getattr(obj, "agent", None) is not None:
            agent_still_there = True
            break
    assert agent_still_there


def test_step_wraparound_movement() -> None:
    """Agent with WrapAroundMovement should wrap around grid edges."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=WrapAroundMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((0, 2), agent)
    new_grid_state = step(gridstate, Action.LEFT)
    agent_pos = find_entity_position(new_grid_state, agent)
    assert agent_pos == (4, 2)


def test_step_preserves_original_grid_state() -> None:
    """Step should not change the original GridState."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((1, 1), agent)
    original_pos = find_entity_position(gridstate, agent)
    assert original_pos == (1, 1)
    new_grid_state = step(gridstate, Action.RIGHT)
    assert find_entity_position(gridstate, agent) == (1, 1)
    agent_found_at_new_pos = False
    for obj in new_grid_state.grid[2][1]:
        if getattr(obj, "agent", None) is not None:
            agent_found_at_new_pos = True
            break
    assert agent_found_at_new_pos


def test_step_turn_increments() -> None:
    """Each step should increment the turn counter."""
    gridstate = GridState(
        width=5,
        height=5,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
    )
    agent = create_agent()
    gridstate.add((1, 1), agent)
    initial_turn = gridstate.turn
    gridstate = step(gridstate, Action.RIGHT)
    assert gridstate.turn == initial_turn + 1
    gridstate = step(gridstate, Action.DOWN)
    assert gridstate.turn == initial_turn + 2
    gridstate = step(gridstate, Action.LEFT)
    assert gridstate.turn == initial_turn + 3
