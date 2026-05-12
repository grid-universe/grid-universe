"""Entity lifetime cleanup utilities."""

from dataclasses import replace
from collections.abc import Iterable

from pyrsistent import pmap
from typing import Any, Final, cast

from pyrsistent.typing import PMap
from grid_universe.runtime import StepContext
from grid_universe.types import EntityID
from grid_universe.state import State
from grid_universe.utils.position import remove_position_component

POSITION_FIELD: Final = "position"
PMAP_TYPE: Final[type[Any]] = type(pmap())


def remove_entities(
    state: State, ctx: StepContext, entity_ids: Iterable[EntityID]
) -> State:
    """Remove known-dead entities from all component stores."""
    ids = frozenset(entity_ids)
    if not ids:
        return state

    new_fields: dict[str, Any] = {}
    position = state.position
    for entity_id in ids:
        if entity_id not in position:
            continue
        position = remove_position_component(position, ctx, entity_id)
    if position is not state.position:
        new_fields[POSITION_FIELD] = position

    for field in state.__dataclass_fields__:
        if field == POSITION_FIELD:
            continue
        value = getattr(state, field)
        if not isinstance(value, PMAP_TYPE):
            continue
        value_map = cast(PMap[EntityID, Any], value)
        if ids.isdisjoint(value_map):
            continue

        updated = value_map
        for entity_id in ids:
            if entity_id not in updated:
                continue
            updated = updated.remove(entity_id)
        new_fields[field] = updated

    if not new_fields:
        return state

    return replace(state, **new_fields)
