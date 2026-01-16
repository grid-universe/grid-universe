from dataclasses import dataclass


@dataclass(frozen=True)
class Appearance:
    """
    Rendering appearance properties.

    Attributes:
        name: Appearance name. Names supported by the built-in image map:
            none, boots, box, coin, core, door, exit, floor, gem, ghost,
            human, key, lava, lock, monster, portal, shield, spike, wall.
        priority: Integer priority used for layering selection.
        icon: If True this entity may render as a small corner icon.
        background: If True this entity may render as a background tile.
    """

    name: str
    priority: int = 0
    icon: bool = False
    background: bool = False
