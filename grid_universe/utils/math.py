"""Vector and math utilities used by pathfinding / movement heuristics."""

from typing import Any
from pyrsistent import pvector
from pyrsistent.typing import PVector

from grid_universe.components import Position


def vector_dot_product(vec1: PVector[int], vec2: PVector[int]) -> int:
    """Return dot product of two equal-length integer vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length")
    return sum([vec1[i] * vec2[i] for i in range(len(vec1))])


def vector_subtract(vec1: PVector[int], vec2: PVector[int]) -> PVector[int]:
    """Return ``vec1 - vec2`` element-wise for equal-length vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length")
    return pvector([vec1[i] - vec2[i] for i in range(len(vec1))])


def position_to_vector(position: Position) -> PVector[int]:
    """Convert a Position dataclass to a vector of its field values."""
    return pvector(
        [getattr(position, field) for field in position.__dataclass_fields__]
    )


def argmax(x: list[Any]) -> int:
    """Return index of maximum value in list ``x`` (first in tie)."""
    return max(range(len(x)), key=lambda i: x[i])
