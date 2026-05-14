from grid_universe.components import Position
from grid_universe.movements import CardinalMovement
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.utils.ecs import build_position_index
from grid_universe.utils.position import (
    remove_position_component,
    set_position_component,
)


def test_set_position_component_updates_store_and_index() -> None:
    positions = dict({1: Position(0, 0), 2: Position(1, 0)})
    state = State(
        width=2,
        height=1,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
        position=positions,
    )
    ctx = StepContext(position_index=build_position_index(state.position))
    set_position_component(state, ctx, 1, Position(1, 0))
    assert state.position[1] == Position(1, 0)
    assert Position(0, 0) not in ctx.position_index
    assert ctx.position_index[Position(1, 0)] == [2, 1]


def test_remove_position_component_updates_store_and_index() -> None:
    positions = dict({1: Position(0, 0), 2: Position(1, 0)})
    state = State(
        width=2,
        height=1,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
        position=positions,
    )
    ctx = StepContext(position_index=build_position_index(state.position))
    remove_position_component(state, ctx, 1)
    assert 1 not in state.position
    assert Position(0, 0) not in ctx.position_index
    assert ctx.position_index[Position(1, 0)] == [2]
