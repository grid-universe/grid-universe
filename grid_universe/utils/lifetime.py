"""Entity lifetime cleanup utilities."""

from collections.abc import Iterable
from dataclasses import fields

from grid_universe.runtime import StepContext
from grid_universe.types import EntityID
from grid_universe.state import State
from grid_universe.utils.position import remove_position_component

POSITION_FIELD = "position"


def remove_entities(
    state: State, ctx: StepContext, entity_ids: Iterable[EntityID]
) -> None:
    """Remove known-dead entities from all component stores."""
    ids = frozenset(entity_ids)
    if not ids:
        return

    for entity_id in ids:
        if entity_id not in state.position:
            continue
        remove_position_component(state, ctx, entity_id)

    for state_field in fields(state):
        if state_field.name == POSITION_FIELD or state_field.name.startswith("_"):
            continue
        store = getattr(state, state_field.name)
        if not isinstance(store, dict):
            continue
        if ids.isdisjoint(store):
            continue
        for entity_id in ids:
            store.pop(entity_id, None)
