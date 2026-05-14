"""
Tile reward and cost systems.

Increases or decreases the agent's score based on non-collectible
rewardable or cost-bearing entities located on the agent's current tile.
"""

from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import Position, Rewardable, Cost
from grid_universe.utils.ecs import entities_at
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def get_noncollectible_entities(
    state: State,
    pos: Position,
    component_map: dict[EntityID, Rewardable] | dict[EntityID, Cost],
    ctx: StepContext,
) -> set[EntityID]:
    """Return entity IDs at ``pos`` with a component but not collectible."""
    at_pos = entities_at(state, pos, position_index=ctx.position_index)
    if not at_pos:
        return set()
    return {
        eid for eid in at_pos if eid in component_map and eid not in state.collectible
    }


def tile_reward_system(state: State, eid: EntityID, ctx: StepContext) -> None:
    """Increase score for rewardable non-collectible entities at agent tile."""
    pos = state.position.get(eid)
    if not is_valid_state(state, eid) or is_terminal_state(state, eid) or pos is None:
        return

    reward_ids = get_noncollectible_entities(state, pos, state.rewardable, ctx)
    if not reward_ids:
        return

    state.score += sum(state.rewardable[rid].amount for rid in reward_ids)


def tile_cost_system(state: State, eid: EntityID, ctx: StepContext) -> None:
    """Decrease score for cost-bearing non-collectible entities at agent tile."""
    pos = state.position.get(eid)
    if not is_valid_state(state, eid) or is_terminal_state(state, eid) or pos is None:
        return

    cost_ids = get_noncollectible_entities(state, pos, state.cost, ctx)
    if state.step_cost == 0 and not cost_ids:
        return

    state.score -= state.step_cost + sum(state.cost[cid].amount for cid in cost_ids)
