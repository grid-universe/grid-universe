from dataclasses import dataclass
from enum import StrEnum, auto

from grid_universe.types import EntityID


class PathfindingType(StrEnum):
    STRAIGHT_LINE = auto()
    PATH = auto()


@dataclass(frozen=True)
class Pathfinding:
    """
    Pathfinding property component.

    Attributes:
        target:
            Optional EntityID of the target entity to path toward. If None, there is no
            active target.
        type:
            Strategy: ``PATH`` for A* pathfinding, ``STRAIGHT_LINE`` for direct movement
            toward the target.
    """

    target: EntityID | None = None
    type: PathfindingType = PathfindingType.PATH
