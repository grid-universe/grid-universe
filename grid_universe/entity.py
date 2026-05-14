"""Entity ID management utilities."""

from collections.abc import Iterator

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
