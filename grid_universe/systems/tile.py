"""
Tile reward and cost systems.

Increases or decreases the agent's score based on non-collectible
rewardable or cost-bearing entities located on the agent's current tile.
"""

from dataclasses import replace

from pyrsistent.typing import PMap
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import Position, Rewardable, Cost
from grid_universe.utils.ecs import entities_at
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def get_noncollectible_entities(
    state: State,
    pos: Position,
    component_map: PMap[EntityID, Rewardable] | PMap[EntityID, Cost],
    ctx: StepContext,
) -> set[EntityID]:
    """Return entity IDs at ``pos`` with a component but not collectible."""
    at_pos = entities_at(state, pos, position_index=ctx.position_index)
    if not at_pos:
        return set()
    collectible_ids = state.collectible
    return {
        eid for eid in at_pos if eid in component_map and eid not in collectible_ids
    }


def tile_reward_system(state: State, eid: EntityID, ctx: StepContext) -> State:
    """Increase score for rewardable non-collectible entities at agent tile."""
    pos = state.position.get(eid)
    if not is_valid_state(state, eid) or is_terminal_state(state, eid) or pos is None:
        return state

    reward_ids = get_noncollectible_entities(state, pos, state.rewardable, ctx)
    if not reward_ids:
        return state

    score = state.score + sum(state.rewardable[rid].amount for rid in reward_ids)
    return replace(state, score=score)


def tile_cost_system(state: State, eid: EntityID, ctx: StepContext) -> State:
    """Decrease score for cost-bearing non-collectible entities at agent tile."""
    pos = state.position.get(eid)
    if not is_valid_state(state, eid) or is_terminal_state(state, eid) or pos is None:
        return state

    cost_ids = get_noncollectible_entities(state, pos, state.cost, ctx)
    if not cost_ids:
        return state

    score = state.score - sum(state.cost[cid].amount for cid in cost_ids)
    return replace(state, score=score)
