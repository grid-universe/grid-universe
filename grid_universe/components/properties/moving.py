from dataclasses import dataclass
from typing import Literal, cast


Direction = Literal["up", "down", "left", "right"]


@dataclass(frozen=True)
class Moving:
    """
    Autonomous movement component.

    Attributes:
        direction: Direction of movement ("up", "down", "left", or "right").
        bounce: Reverse direction upon hitting an obstacle if True; stop moving if False.
        speed: Number of steps to move per tick.
        vector: Computed (dx, dy) movement vector based on direction.
    """

    direction: Direction
    bounce: bool = True
    speed: int = 1

    def reversed(self) -> "Moving":
        """Return a new Moving instance with the direction reversed."""
        reverse_map = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left",
        }
        return Moving(
            direction=cast(Direction, reverse_map[self.direction]),
            bounce=self.bounce,
            speed=self.speed,
        )

    @property
    def vector(self) -> tuple[int, int]:
        """Get the (dx, dy) movement vector based on the direction."""
        direction_map = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        return direction_map[self.direction]
