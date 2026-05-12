from collections.abc import Callable, Sequence
from enum import StrEnum, auto
from typing import TYPE_CHECKING


# Forward declaration for MovementFn typing to avoid circular imports:
if TYPE_CHECKING:
    from grid_universe.state import State
    from grid_universe.actions import Action
    from grid_universe.components import Position
    from grid_universe.runtime import StepContext

EntityID = int
"""Type alias for entity identifiers."""

MovementFn = Callable[["State", "EntityID", "Action"], Sequence["Position"]]
"""Function type for computing possible moves for an entity."""

ObjectiveFn = Callable[["State", "EntityID", "StepContext"], bool]
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
