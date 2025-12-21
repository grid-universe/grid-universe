"""Pathfinding systems.

Provides pathfinding logic for entities with the Pathfinding property.
Entities can use either A* pathfinding or a simple straight-line approach
to move toward their targets.
"""

from dataclasses import replace
from typing import Dict, List, Tuple

from pyrsistent import pvector
from pyrsistent.typing import PMap
from grid_universe.components import PathfindingType, Position, UsageLimit
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_blocked_at, is_in_bounds
from grid_universe.utils.math import (
    argmax,
    position_to_vector,
    vector_dot_product,
    vector_subtract,
)
from grid_universe.utils.status import use_status_effect_if_present

from queue import PriorityQueue
from itertools import count


def get_astar_next_position(
    state: State, entity_id: EntityID, target_id: EntityID
) -> Position:
    """Compute next step toward target using A* with Manhattan distance heuristic.

    Args:
        state (State): Current world state.
        entity_id (EntityID): ID of the entity to move.
        target_id (EntityID): ID of the target entity.

    Returns:
        Position: Next position toward the target, or current position if no path found.
    """
    start = state.position[entity_id]
    goal = state.position[target_id]

    if start == goal:
        return start

    def in_bounds(pos: Position) -> bool:
        return is_in_bounds(state, pos)

    def is_blocked(pos: Position) -> bool:
        return is_blocked_at(state, pos, check_collidable=False)

    def heuristic(a: Position, b: Position) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def get_valid_next_positions(position: Position) -> List[Position]:
        neighbor_positions = [
            Position(position.x + dx, position.y + dy) for dx, dy in neighbors
        ]
        return [
            pos for pos in neighbor_positions if in_bounds(pos) and not is_blocked(pos)
        ]

    frontier: PriorityQueue[Tuple[int, int, Position]] = PriorityQueue()
    prev_pos: Dict[Position, Position] = {}
    cost_so_far: Dict[Position, int] = {start: 0}

    tiebreaker = count()  # Unique sequence count
    frontier.put((0, next(tiebreaker), start))

    while not frontier.empty():
        _, __, current = frontier.get()
        if current == goal:
            break
        for next_pos in get_valid_next_positions(current):
            new_cost = cost_so_far[current] + 1
            if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                cost_so_far[next_pos] = new_cost
                priority = new_cost + heuristic(next_pos, goal)
                frontier.put((priority, next(tiebreaker), next_pos))
                prev_pos[next_pos] = current

    # Reconstruct path
    if goal not in prev_pos:
        return start  # No path found

    # Walk backwards to get the path
    path: List[Position] = []
    current = goal
    while current != start:
        path.append(current)
        current = prev_pos[current]
    path.reverse()

    if not path:
        return start
    return path[0]


def get_straight_line_next_position(
    state: State, entity_id: EntityID, target_id: EntityID
) -> Position:
    """Compute next step toward target using straight-line heuristic.

    Args:
        state (State): Current world state.
        entity_id (EntityID): ID of the entity to move.
        target_id (EntityID): ID of the target entity.

    Returns:
        Position: Next position toward the target.
    """
    target_vec = position_to_vector(state.position[target_id])
    entity_vec = position_to_vector(state.position[entity_id])
    dvec = vector_subtract(target_vec, entity_vec)
    actions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    values = [vector_dot_product(pvector(action), dvec) for action in actions]
    best_action = actions[argmax(values)]
    return Position(
        state.position[entity_id].x + best_action[0],
        state.position[entity_id].y + best_action[1],
    )


def entity_pathfinding(
    state: State, usage_limit: PMap[EntityID, UsageLimit], entity_id: EntityID
) -> State:
    """Apply pathfinding for a single entity (straight-line or A*)."""
    if entity_id not in state.position or entity_id not in state.pathfinding:
        return state

    pathfinding_type = state.pathfinding[entity_id].type
    pathfinding_target = state.pathfinding[entity_id].target

    if pathfinding_target is None:
        return state

    if pathfinding_target in state.status:
        usage_limit, effect_id = use_status_effect_if_present(
            state.status[pathfinding_target].effect_ids,
            state.phasing,
            state.time_limit,
            usage_limit,
        )
        state = replace(state, usage_limit=usage_limit)
        if effect_id is not None:
            return state

    if pathfinding_type == PathfindingType.STRAIGHT_LINE:
        next_pos = get_straight_line_next_position(state, entity_id, pathfinding_target)
    elif pathfinding_type == PathfindingType.PATH:
        next_pos = get_astar_next_position(state, entity_id, pathfinding_target)
    else:
        raise NotImplementedError

    if is_blocked_at(state, next_pos, check_collidable=False) or not is_in_bounds(
        state, next_pos
    ):
        return state

    return replace(state, position=state.position.set(entity_id, next_pos))


def pathfinding_system(state: State) -> State:
    """Advance all pathfinding-enabled entities by one tile if possible."""
    for entity_id in state.pathfinding:
        state = entity_pathfinding(state, state.usage_limit, entity_id)
    return state
