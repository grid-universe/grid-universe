from pyrsistent import pmap

from grid_universe.components import Position
from grid_universe.runtime import StepContext
from grid_universe.utils.ecs import build_mutable_position_index
from grid_universe.utils.position import (
    remove_position_component,
    set_position_component,
)


def test_set_position_component_updates_store_and_index() -> None:
    positions = pmap({1: Position(0, 0), 2: Position(1, 0)})
    ctx = StepContext(position_index=build_mutable_position_index(positions))

    positions = set_position_component(positions, ctx, 1, Position(1, 0))

    assert positions[1] == Position(1, 0)
    assert Position(0, 0) not in ctx.position_index
    assert ctx.position_index[Position(1, 0)] == [2, 1]


def test_remove_position_component_updates_store_and_index() -> None:
    positions = pmap({1: Position(0, 0), 2: Position(1, 0)})
    ctx = StepContext(position_index=build_mutable_position_index(positions))

    positions = remove_position_component(positions, ctx, 1)

    assert 1 not in positions
    assert Position(0, 0) not in ctx.position_index
    assert ctx.position_index[Position(1, 0)] == [2]
