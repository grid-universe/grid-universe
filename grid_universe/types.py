from enum import StrEnum, auto
from typing import Callable, Sequence, TYPE_CHECKING


# Forward declaration for MoveFn typing to avoid circular imports:
if TYPE_CHECKING:
    from grid_universe.state import State
    from grid_universe.actions import Action
    from grid_universe.components import Position

EntityID = int
"""Type alias for entity identifiers."""

MoveFn = Callable[["State", "EntityID", "Action"], Sequence["Position"]]
"""Function type for computing possible moves for an entity."""

ObjectiveFn = Callable[["State", "EntityID"], bool]
"""Function type for evaluating whether an entity has met an objective."""


class EffectType(StrEnum):
    """Types of effects that can be applied to entities."""

    IMMUNITY = auto()
    PHASING = auto()
    SPEED = auto()


class EffectLimit(StrEnum):
    """Types of limits for effect application."""

    TIME = auto()
    USAGE = auto()


EffectLimitAmount = int
