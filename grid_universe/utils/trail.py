"""
Trail (historic position) utilities.

Provides functions to manage and query the historic trails of entities
within the grid universe, allowing systems to track prior positions for
purposes such as implementing trail-based mechanics.
"""

from collections import defaultdict
from dataclasses import replace
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap, PSet
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.runtime import StepContext


def get_augmented_trail(
    state: State, ctx: StepContext, entity_ids: PSet[EntityID]
) -> PMap[Position, PSet[EntityID]]:
    """Return merged mapping of positions to entity sets (current + historic).

    Args:
        state (State): Current immutable world state containing both live entity positions
            and the accumulated historic ``trail`` mapping of prior positions.
        entity_ids (PSet[EntityID]): Entity ids whose current position should be merged
            into the historic trail. Entities absent from ``state.position`` are ignored.

    Returns:
        PMap[Position, PSet[EntityID]]: Mapping from grid positions to the persistent set of
            entity ids that have either previously occupied (historic) or currently occupy
            that position among the provided tracked entities.
    """
    pos_to_eids: defaultdict[Position, set[EntityID]] = defaultdict(set)
    for eid in entity_ids:
        if eid not in state.position:
            continue
        pos = state.position[eid]
        pos_to_eids[pos].add(eid)
    # Merge with existing trail:
    for pos, eid_set in ctx.trail.items():
        # ``eid_set`` is already a persistent set; its items are EntityID.
        pos_to_eids[pos].update(eid_set)
    # Convert to persistent structures:
    return pmap({pos: pset(eids) for pos, eids in pos_to_eids.items()})


def add_trail_position(
    ctx: StepContext, entity_id: EntityID, new_pos: Position
) -> StepContext:
    """Return new StepContext with ``entity_id`` recorded as having entered ``new_pos``.

    Idempotent for (entity, position) within an action: repeated additions of
    the same (entity, tile) pair are harmless due to set semantics.
    """
    return replace(
        ctx,
        trail=ctx.trail.set(new_pos, ctx.trail.get(new_pos, pset()).add(entity_id)),
    )
