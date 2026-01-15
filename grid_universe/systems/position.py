"""Position snapshot system.

Maintains ``prev_position`` as an immutable snapshot of all entity positions
at the start (or end) of a step. Other systems (e.g. portal teleportation,
trail generation, damage-on-crossing) rely on this historical information to
detect transitions or movement paths.
"""

from dataclasses import replace
from typing import Dict

from pyrsistent import pmap
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.runtime import StepContext


def position_system(state: State, ctx: StepContext) -> StepContext:
    """Snapshot current entity positions.

    Args:
        state (State): Current immutable simulation state.
        ctx (StepContext): Current step context.

    Returns:
        StepContext: Updated step context with snapshot of current positions.
    """
    prev_position: Dict[EntityID, Position] = {}
    for eid, pos in state.position.items():
        prev_position[eid] = pos
    return replace(ctx, prev_position=pmap(prev_position))
