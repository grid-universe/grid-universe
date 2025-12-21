"""Entity ID management utilities."""

from typing import Iterator, List

from grid_universe.types import EntityID


def entity_id_generator() -> Iterator[EntityID]:
    """Yield an infinite sequence of monotonically increasing entity IDs."""
    eid = 0
    while True:
        yield eid
        eid += 1


_entity_id_gen = entity_id_generator()


def new_entity_id() -> EntityID:
    """Return a newly allocated unique entity ID."""
    return next(_entity_id_gen)


def new_entity_ids(n: int) -> List[EntityID]:
    """Return ``n`` fresh entity IDs as a list."""
    return [new_entity_id() for _ in range(n)]
