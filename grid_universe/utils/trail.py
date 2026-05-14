"""Trail (historic position) utilities."""

from collections import defaultdict
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.runtime import StepContext


def get_augmented_trail(
    state: State, ctx: StepContext, entity_ids: set[EntityID]
) -> dict[Position, set[EntityID]]:
    """Return merged mapping of positions to entity sets (current + historic).

    Args:
        state (State): Current world state containing both live entity positions
            and the accumulated historic ``trail`` mapping of prior positions.
        entity_ids: Entity ids whose current position should be merged
            into the historic trail. Entities absent from ``state.position`` are ignored.

    Returns:
        Mapping from grid positions to entity ids that have either previously occupied
        or currently occupy that position among the provided tracked entities.
    """
    pos_to_eids: defaultdict[Position, set[EntityID]] = defaultdict(set)
    for eid in entity_ids:
        if eid not in state.position:
            continue
        pos = state.position[eid]
        pos_to_eids[pos].add(eid)
    for pos, eid_set in ctx.trail.items():
        pos_to_eids[pos].update(eid_set)
    return dict(pos_to_eids)


def add_trail_position(
    ctx: StepContext, entity_id: EntityID, new_pos: Position
) -> None:
    """Record ``entity_id`` as having entered ``new_pos``.

    Idempotent for (entity, position) within an action: repeated additions of
    the same (entity, tile) pair are harmless due to set semantics.
    """
    ctx.trail.setdefault(new_pos, set()).add(entity_id)
