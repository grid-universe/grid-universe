"""
Grid utilities.

Provides common functions for grid-based operations, such as boundary checks
and collision detection.

Functions here are used by movement and pathfinding systems to validate
entity positions and movements within the grid world.
"""

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_at


def is_in_bounds(state: State, pos: Position) -> bool:
    """Return True if ``pos`` lies within the level rectangle."""
    return 0 <= pos.x < state.width and 0 <= pos.y < state.height


def wrap_position(x: int, y: int, width: int, height: int) -> Position:
    """Toroidal wrap for coordinates (used by wrap movement)."""
    return Position(x=x % width, y=y % height)


def is_blocked_at(
    state: State,
    pos: Position,
    check_blocking: bool = True,
    check_collidable: bool = True,
    check_pushable: bool = True,
) -> bool:
    """Return True if any blocking entity occupies ``pos``.

    Args:
        state (State): World state.
        pos (Position): Candidate destination.
        check_blocking (bool): If True, treat ``Blocking`` as blocking.
        check_collidable (bool): If True, treat ``Collidable`` as blocking.
        check_pushable (bool): If True, treat ``Pushable`` as blocking.
    """
    ids_at_pos: set[EntityID] = entities_at(state, pos)
    for other_id in ids_at_pos:
        if (
            (check_blocking and other_id in state.blocking)
            or (check_pushable and other_id in state.pushable)
            or (check_collidable and other_id in state.collidable)
        ):
            return True
    return False


def is_entity_blocked_at(
    state: State,
    entity_id: EntityID,
    pos: Position,
) -> bool:
    """Return True if ``entity_id`` would be blocked at ``pos``.

    If the entity is blocking or pushable, collidable entities are also checked.

    Args:
        state (State): World state.
        entity_id (EntityID): Entity.
        pos (Position): Candidate destination.
    """
    return is_blocked_at(
        state,
        pos,
        check_blocking=True,
        check_collidable=(entity_id in state.blocking or entity_id in state.pushable),
        check_pushable=True,
    )
