from collections.abc import Mapping
from typing import Any
from grid_universe.actions import Action
from grid_universe.components import Position
from grid_universe.examples.maze import generate
from grid_universe.step import step
from grid_universe.types import EntityID
from grid_universe.utils.ecs import PositionIndex


def test_step_reuses_single_position_index(monkeypatch: Any) -> None:
    state = generate(width=15, height=15, seed=0)
    import grid_universe.state as state_module
    import grid_universe.utils.ecs as ecs_module

    original_build = ecs_module.build_position_index
    call_count = 0

    def counted_build(position_store: Mapping[EntityID, Position]) -> PositionIndex:
        nonlocal call_count
        call_count += 1
        return original_build(position_store)

    monkeypatch.setattr(ecs_module, "build_position_index", counted_build)
    monkeypatch.setattr(state_module, "build_position_index", counted_build)
    step(state, Action.WAIT, in_place=True)
    assert call_count == 0
