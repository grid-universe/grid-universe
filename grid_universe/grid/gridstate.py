"""Grid-based state representation.

The `grid_universe.grid.gridstate.GridState` dataclass is a first-class,
grid-centric representation for building and editing game states. It provides
a simple grid editing API (add/remove/move) and stores the configuration
needed for simulation.

GridState and `grid_universe.state.State` are complementary
representations optimized for different use cases:

- **GridState**: Grid-centric, ideal for authoring and editing
- **State**: ECS representation optimized for simulation and stepping

Use `grid_universe.grid.factories` to create `grid_universe.grid.entity.BaseEntity`
objects conveniently, and `grid_universe.grid.convert` to convert between
representations as needed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from grid_universe.movements import BaseMovement
from grid_universe.objectives import BaseObjective
from .entity import BaseEntity

# Grid coordinate alias (x, y)
Position = tuple[int, int]


@dataclass
class GridState:
    """
    Grid-centric state representation.

    GridState is a first-class representation for building, editing, and reasoning
    about game states in a spatial, grid-based manner. It stores entities in a 2D grid
    structure alongside game configuration and metadata.

    - ``grid[x][y]`` is a list of `grid_universe.grid.entity.BaseEntity` instances at that cell.
    - Stores configuration such as ``movement``, ``objective``, ``seed``, and metadata
        (turn/score/win/lose/etc.).
    - Convert to/from the ECS `grid_universe.state.State` using
        `grid_universe.grid.convert.to_state` / `grid_universe.grid.convert.from_state`
        when needed for simulation.
    """

    width: int
    height: int
    movement: BaseMovement
    objective: BaseObjective
    seed: int | None = None

    # 2D array of cells: each cell holds a list of EntityObject
    grid: list[list[list[BaseEntity]]] = field(init=False)

    # Optional meta (carried through conversion)
    turn: int = 0
    score: int = 0
    step_cost: int = 0
    win: bool = False
    lose: bool = False
    message: str | None = None
    turn_limit: int | None = None

    def __post_init__(self) -> None:
        # Initialize empty grid
        self.grid = [[[] for _ in range(self.height)] for _ in range(self.width)]

    # -------- Grid editing API --------

    def add(self, pos: Position, obj: BaseEntity) -> None:
        """
        Place an `grid_universe.grid.entity.BaseEntity` into the cell at pos (x, y).
        """
        x, y = pos
        self._check_bounds(x, y)
        self.grid[x][y].append(obj)

    def add_many(self, items: list[tuple[Position, BaseEntity]]) -> None:
        """
        Place multiple entities. Each entry is ``(pos, obj)``.
        """
        for pos, obj in items:
            self.add(pos, obj)

    def remove(self, pos: Position, obj: BaseEntity) -> bool:
        """
        Remove a specific entity (by identity) from the cell at pos.
        Returns True if the object was found and removed, False otherwise.
        """
        x, y = pos
        self._check_bounds(x, y)
        cell = self.grid[x][y]
        for i, o in enumerate(cell):
            if o is obj:
                del cell[i]
                return True
        return False

    def remove_if(self, pos: Position, predicate: Callable[[BaseEntity], bool]) -> int:
        """
        Remove all objects in the cell at pos for which predicate(obj) is True.
        Returns the number of removed objects.
        """
        x, y = pos
        self._check_bounds(x, y)
        cell = self.grid[x][y]
        keep = [o for o in cell if not predicate(o)]
        removed = len(cell) - len(keep)
        self.grid[x][y] = keep
        return removed

    def move_obj(self, from_pos: Position, obj: BaseEntity, to_pos: Position) -> bool:
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
        n = len(self.grid[x][y])
        self.grid[x][y] = []
        return n

    def objects_at(self, pos: Position) -> list[BaseEntity]:
        """
        Return a shallow copy of the list of objects at pos.
        """
        x, y = pos
        self._check_bounds(x, y)
        return list(self.grid[x][y])

    # -------- Internal helpers --------

    def _check_bounds(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"Out of bounds: {(x, y)} for grid {self.width}x{self.height}"
            )
