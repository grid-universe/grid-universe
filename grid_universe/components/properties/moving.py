from dataclasses import dataclass
from typing import Literal, cast


Direction = Literal["up", "down", "left", "right"]
CollisionBehavior = Literal["bounce", "stop"]


@dataclass(frozen=True)
class Moving:
    """
    Autonomous movement component.

    Attributes:
        direction: Direction of movement ("up", "down", "left", or "right").
        on_collision: Behavior when a collision occurs ("bounce" or "stop").
        speed: Number of steps to move per tick.
        vector: Computed (dx, dy) movement vector based on direction.
    """

    direction: Direction
    on_collision: CollisionBehavior = "stop"
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
            on_collision=self.on_collision,
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
