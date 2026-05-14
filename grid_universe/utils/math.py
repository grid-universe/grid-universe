"""Vector and math utilities used by pathfinding / movement heuristics."""

from collections.abc import Sequence
from typing import Any

from grid_universe.components import Position


def vector_dot_product(vec1: Sequence[int], vec2: Sequence[int]) -> int:
    """Return dot product of two equal-length integer vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length")
    return sum([vec1[i] * vec2[i] for i in range(len(vec1))])


def vector_subtract(vec1: Sequence[int], vec2: Sequence[int]) -> tuple[int, ...]:
    """Return ``vec1 - vec2`` element-wise for equal-length vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length")
    return tuple(vec1[i] - vec2[i] for i in range(len(vec1)))


def position_to_vector(position: Position) -> tuple[int, ...]:
    """Convert a Position dataclass to a vector of its field values."""
    return tuple(getattr(position, field) for field in position.__dataclass_fields__)


def argmax(x: list[Any]) -> int:
    """Return index of maximum value in list ``x`` (first in tie)."""
    return max(range(len(x)), key=lambda i: x[i])
