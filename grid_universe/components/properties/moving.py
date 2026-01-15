from dataclasses import dataclass
from enum import StrEnum, auto


class MovingAxis(StrEnum):
    """
    Axis of autonomous movement.
    """

    HORIZONTAL = auto()
    VERTICAL = auto()


@dataclass(frozen=True)
class Moving:
    """
    Autonomous movement component.

    Attributes:
        axis: Axis of autonomous movement (horizontal or vertical).
        direction: +1 or -1 indicating step direction along the axis. +1 is right/down, -1 is left/up.
        bounce: Reverse direction upon hitting an obstacle if True; stop moving if False.
        speed: Number of steps to move per tick.
    """

    axis: MovingAxis
    direction: int  # 1 or -1
    bounce: bool = True
    speed: int = 1
