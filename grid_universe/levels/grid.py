"""Mutable grid/level representation.

The `grid_universe.levels.grid.Level` dataclass is an alternative,
mutable representation of a `grid_universe.state.State`. It provides a
simple grid editing API (add/remove/move) and stores the configuration needed
to build a runtime state.

Use `grid_universe.levels.factories` to create `grid_universe.levels.entity.Entity`
objects conveniently, and `grid_universe.levels.convert` to convert between
this representation and the immutable runtime `grid_universe.state.State`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from grid_universe.types import MoveFn, ObjectiveFn
from .entity import Entity

# Grid coordinate alias (x, y)
Position = Tuple[int, int]


@dataclass
class Level:
    """
    Grid-centric, mutable level representation.

    - ``grid[y][x]`` is a list of `grid_universe.levels.entity.Entity` instances at that cell.
    - The level stores configuration such as ``move_fn``, ``objective_fn``, ``seed``, and simple
        meta (turn/score/etc.).
    - Use `grid_universe.levels.convert.to_state` / `grid_universe.levels.convert.from_state`
        to convert between ``Level`` and the immutable ECS `grid_universe.state.State`.
    """

    width: int
    height: int
    move_fn: MoveFn
    objective_fn: ObjectiveFn
    seed: Optional[int] = None

    # 2D array of cells: each cell holds a list of EntityObject
    grid: List[List[List[Entity]]] = field(init=False)

    # Optional meta (carried through conversion)
    turn: int = 0
    score: int = 0
    win: bool = False
    lose: bool = False
    message: Optional[str] = None
    turn_limit: Optional[int] = None

    def __post_init__(self) -> None:
        # Initialize empty grid
        self.grid = [[[] for _ in range(self.width)] for _ in range(self.height)]

    # -------- Grid editing API --------

    def add(self, pos: Position, obj: Entity) -> None:
        """
        Place an `grid_universe.levels.entity.Entity` into the cell at pos (x, y).
        """
        x, y = pos
        self._check_bounds(x, y)
        self.grid[y][x].append(obj)

    def add_many(self, items: List[Tuple[Position, Entity]]) -> None:
        """
        Place multiple entities. Each entry is ``(pos, obj)``.
        """
        for pos, obj in items:
            self.add(pos, obj)

    def remove(self, pos: Position, obj: Entity) -> bool:
        """
        Remove a specific entity (by identity) from the cell at pos.
        Returns True if the object was found and removed, False otherwise.
        """
        x, y = pos
        self._check_bounds(x, y)
        cell = self.grid[y][x]
        for i, o in enumerate(cell):
            if o is obj:
                del cell[i]
                return True
        return False

    def remove_if(self, pos: Position, predicate: Callable[[Entity], bool]) -> int:
        """
        Remove all objects in the cell at pos for which predicate(obj) is True.
        Returns the number of removed objects.
        """
        x, y = pos
        self._check_bounds(x, y)
        cell = self.grid[y][x]
        keep = [o for o in cell if not predicate(o)]
        removed = len(cell) - len(keep)
        self.grid[y][x] = keep
        return removed

    def move_obj(self, from_pos: Position, obj: Entity, to_pos: Position) -> bool:
        """
        Move a specific entity (by identity) from one cell to another.
        Returns True if moved (i.e., it was found in the source cell), False otherwise.
        """
        if not self.remove(from_pos, obj):
            return False
        self.add(to_pos, obj)
        return True

    def clear_cell(self, pos: Position) -> int:
        """
        Remove all objects from the cell at pos. Returns the number of removed objects.
        """
        x, y = pos
        self._check_bounds(x, y)
        n = len(self.grid[y][x])
        self.grid[y][x] = []
        return n

    def objects_at(self, pos: Position) -> List[Entity]:
        """
        Return a shallow copy of the list of objects at pos.
        """
        x, y = pos
        self._check_bounds(x, y)
        return list(self.grid[y][x])

    # -------- Internal helpers --------

    def _check_bounds(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"Out of bounds: {(x, y)} for grid {self.width}x{self.height}"
            )
