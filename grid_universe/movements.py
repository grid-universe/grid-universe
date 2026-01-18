"""Movement functions for entity navigation within the grid universe.

Each movement function defines how an entity moves in response to an action.
They take the current ``State``, the entity ID, and the intended ``Action``,
and return a sequence of ``Position`` instances representing the path taken.
Different movement functions can simulate various terrain types or movement
mechanics (e.g., slippery surfaces, wind effects, gravity).

Users can select from built-in movement classes via the ``MOVEMENT_REGISTRY``
or define custom movements by subclassing ``BaseMovement``.
"""

from dataclasses import dataclass
import random
from collections.abc import Sequence
from grid_universe.components import Position
from grid_universe.actions import Action
from grid_universe.state import State
from grid_universe.types import EntityID, MovementFn
from grid_universe.utils.grid import is_blocked_at


MOVEMENT_MAP = {
    Action.UP: (0, -1),
    Action.DOWN: (0, 1),
    Action.LEFT: (-1, 0),
    Action.RIGHT: (1, 0),
}


# Built-in Movement Functions


def cardinal_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Single-step cardinal movement in the intended direction.
    Returns the adjacent tile in the specified direction.
    """
    pos = state.position[eid]
    dx, dy = MOVEMENT_MAP[action]
    return [Position(pos.x + dx, pos.y + dy)]


def wrap_around_move_fn(
    state: State, eid: EntityID, action: Action
) -> Sequence[Position]:
    """Cardinal step with wrap-around at grid edges.
    Returns the adjacent tile in the direction of ``action``, wrapping around
    the grid if the edge is crossed.
    """
    pos = state.position[eid]
    dx, dy = MOVEMENT_MAP[action]
    width = getattr(state, "width", None)
    height = getattr(state, "height", None)
    if width is None or height is None:
        raise ValueError("State must have width and height for wrap_around_move_fn.")
    new_x = (pos.x + dx) % width
    new_y = (pos.y + dy) % height
    return [Position(new_x, new_y)]


def mirror_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Horizontally mirrored movement (LEFT<->RIGHT)."""
    mirror_map: dict[Action, Action] = {
        Action.LEFT: Action.RIGHT,
        Action.RIGHT: Action.LEFT,
        Action.UP: Action.UP,
        Action.DOWN: Action.DOWN,
    }
    mirrored = mirror_map[action]
    return cardinal_move_fn(state, eid, mirrored)


def slippery_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    """Cardinal step with sliding until blocked.
    The entity continues moving in the chosen direction until blocked, simulating
    a slippery surface. If the first adjacent tile is blocked, no movement occurs.
    """
    pos = state.position[eid]
    dx, dy = MOVEMENT_MAP[action]
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
    The first step is always in the intended direction. Then with 30% chance a
    random wind drift step is applied in a random cardinal direction (which may
    be the same as the original). If the wind step would go out-of-bounds, it is
    skipped.
    """
    pos = state.position[eid]
    dx, dy = MOVEMENT_MAP[action]
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
    dx, dy = MOVEMENT_MAP[action]
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


# Built-in Move Classes


@dataclass(frozen=True)
class BaseMovement:
    """Base class for movement functions."""

    name: str
    description: str
    function: MovementFn

    def __call__(
        self, state: State, eid: EntityID, action: Action
    ) -> Sequence[Position]:
        """Evaluate the movement function."""
        return self.function(state, eid, action)


@dataclass(frozen=True)
class CardinalMovement(BaseMovement):
    """Cardinal movement function."""

    name: str = "cardinal"
    description: str = "Single-step cardinal movement."
    function: MovementFn = cardinal_move_fn


@dataclass(frozen=True)
class WrapAroundMovement(BaseMovement):
    """Wrap-around movement function."""

    name: str = "wrap-around"
    description: str = "Cardinal movement with wrap-around at grid edges."
    function: MovementFn = wrap_around_move_fn


@dataclass(frozen=True)
class MirrorMovement(BaseMovement):
    """Mirror movement function."""

    name: str = "mirror"
    description: str = "Horizontally mirrored movement (LEFT<->RIGHT)."
    function: MovementFn = mirror_move_fn


@dataclass(frozen=True)
class SlipperyMovement(BaseMovement):
    """Slippery movement function."""

    name: str = "slippery"
    description: str = "Cardinal movement with sliding until blocked."
    function: MovementFn = slippery_move_fn


@dataclass(frozen=True)
class WindyMovement(BaseMovement):
    """Windy movement function."""

    name: str = "windy"
    description: str = "Cardinal movement with random wind drift."
    function: MovementFn = windy_move_fn


@dataclass(frozen=True)
class GravityMovement(BaseMovement):
    """Gravity movement function."""

    name: str = "gravity"
    description: str = "Cardinal movement followed by falling downward until blocked."
    function: MovementFn = gravity_move_fn


MOVEMENT_REGISTRY: dict[str, BaseMovement] = {
    "cardinal": CardinalMovement(),
    "wrap-around": WrapAroundMovement(),
    "mirror": MirrorMovement(),
    "slippery": SlipperyMovement(),
    "windy": WindyMovement(),
    "gravity": GravityMovement(),
}
"""Registry of built-in movement objects by name.

Use these movement objects when creating ``State`` instances. Each object
wraps a movement function along with metadata.
"""
