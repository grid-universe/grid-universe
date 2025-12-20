"""Built-in movement generator functions.

Each *move function* maps (state, entity id, action) -> sequence of
``Position`` objects representing the path the entity will attempt for a single
directional action. Systems consume these candidate positions in order,
stopping early if blocked. This indirection allows custom movement behaviors
to be plugged per level (e.g. wrapping, sliding, wind drift).

Contract (``MoveFn``):

* Must return at least one ``Position`` (often just the immediate neighbor).
* Should not mutate ``State``.
* May return multiple positions to simulate chained micro‑steps (sliding,
  gravity fall, wind, etc.).

Performance: The functions here use straightforward iteration over the
``state.position`` map for collision checks; this is acceptable for small
grids. For very large maps a spatial index could be introduced.
"""

import random
from typing import Sequence, Dict
from grid_universe.components import Position
from grid_universe.actions import Action
from grid_universe.state import State
from grid_universe.types import EntityID, MoveFn
from grid_universe.utils.grid import is_blocked_at


def cardinal_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Single-tile cardinal step.

    Returns the adjacent tile in the direction of ``action`` without bounds
    wrapping. Caller handles blocking and validity.
    """
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    return [Position(pos.x + dx, pos.y + dy)]


def wrap_around_move_fn(
    state: State, eid: EntityID, action: Action
) -> Sequence[Position]:
    """Cardinal step with toroidal wrapping.

    Requires ``state.width`` & ``state.height``. Moving off an edge re-enters
    on the opposite side.
    """
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width = getattr(state, "width", None)
    height = getattr(state, "height", None)
    if width is None or height is None:
        raise ValueError("State must have width and height for wrap_around_move_fn.")
    new_x = (pos.x + dx) % width
    new_y = (pos.y + dy) % height
    return [Position(new_x, new_y)]


def mirror_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Horizontally mirrored movement (LEFT<->RIGHT)."""
    mirror_map: Dict[Action, Action] = {
        Action.LEFT: Action.RIGHT,
        Action.RIGHT: Action.LEFT,
        Action.UP: Action.UP,
        Action.DOWN: Action.DOWN,
    }
    mirrored = mirror_map[action]
    return default_move_fn(state, eid, mirrored)


def slippery_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Slide in direction until blocked or edge.

    Returns the whole path of intermediate positions; if the first tile is
    blocked returns the current position (no movement).
    """
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width, height = state.width, state.height
    nx, ny = pos.x + dx, pos.y + dy
    path: list[Position] = []
    while 0 <= nx < width and 0 <= ny < height:  # Prevents infinite loop at grid edge
        test_pos = Position(nx, ny)
        if is_blocked_at(state, test_pos, check_collidable=False, check_pushable=False):
            break
        path.append(test_pos)
        nx += dx
        ny += dy
    return path if path else [pos]


def windy_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Primary cardinal step plus optional wind drift.

    With 30%% probability (per deterministic RNG seeded by ``state.seed`` and
    turn) a perpendicular single-tile drift is appended.
    """
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width, height = state.width, state.height
    path: list[Position] = []

    # Deterministic RNG
    base_seed = hash((state.seed if state.seed is not None else 0, state.turn))
    rng = random.Random(base_seed)

    # First move
    nx1, ny1 = pos.x + dx, pos.y + dy
    if 0 <= nx1 < width and 0 <= ny1 < height:
        path.append(Position(nx1, ny1))
        # Wind effect
        if rng.random() < 0.3:
            wind_dx, wind_dy = rng.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
            nx2, ny2 = nx1 + wind_dx, ny1 + wind_dy
            if 0 <= nx2 < width and 0 <= ny2 < height:
                path.append(Position(nx2, ny2))
    # If the first move is out of bounds, wind does not apply.
    return path if path else [pos]


def gravity_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Cardinal step then fall straight downward until blocked.

    If the initial adjacent tile is blocked or out-of-bounds, no movement is
    produced. Otherwise the path includes the first step plus each subsequent
    unobstructed downward tile.
    """
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width, height = state.width, state.height
    nx, ny = pos.x + dx, pos.y + dy

    def can_move(px: int, py: int) -> bool:
        # Out-of-bounds check
        if not (0 <= px < width and 0 <= py < height):
            return False
        test_pos = Position(px, py)
        if is_blocked_at(state, test_pos, check_collidable=True, check_pushable=True):
            return False
        return True

    if not can_move(nx, ny):
        return [pos]

    path: list[Position] = [Position(nx, ny)]
    while True:
        next_x, next_y = nx, path[-1].y + 1
        if not can_move(next_x, next_y):
            break
        path.append(Position(next_x, next_y))
    return path


default_move_fn: MoveFn = cardinal_move_fn
"""Alias for the default single-step movement function."""


# Move function registry for per-level assignment
MOVE_FN_REGISTRY: Dict[str, MoveFn] = {
    "default": default_move_fn,
    "cardinal": cardinal_move_fn,
    "wrap": wrap_around_move_fn,
    "mirror": mirror_move_fn,
    "slippery": slippery_move_fn,
    "windy": windy_move_fn,
    "gravity": gravity_move_fn,
}
"""Registry of built-in movement function names to callables.

Users may supply a custom function directly in a ``State`` or extend this
registry before level generation.
"""
