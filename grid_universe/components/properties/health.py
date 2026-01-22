from dataclasses import dataclass


@dataclass(frozen=True)
class Health:
    """
    Health component.

    Attributes:
        current_health: Current health points.
        max_health: Maximum health points.
    """

    current_health: int
    max_health: int
