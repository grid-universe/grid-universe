"""Objective predicate functions and registry.

Each objective function answers: *"Has the agent satisfied the win
condition?"* They are pure predicates over a :class:`State` and an ``agent_id``.
The main reducer checks ``state.objective_fn`` after each full action step to
decide whether to set ``state.win``.

Functions here should be fast (O(number of relevant components)).
"""

from typing import Dict
from grid_universe.state import State
from grid_universe.types import EntityID, ObjectiveFn
from grid_universe.utils.ecs import entities_with_components_at


def exit_objective_fn(state: State, agent_id: EntityID) -> bool:
    """Agent stands on any entity possessing an ``Exit`` component."""
    if agent_id not in state.position:
        return False
    return (
        len(entities_with_components_at(state, state.position[agent_id], state.exit))
        > 0
    )


def collect_required_objective_fn(state: State, agent_id: EntityID) -> bool:
    """All entities marked ``Required`` have been collected (no longer collectible)."""
    return all((eid not in state.collectible) for eid in state.required)


def collect_required_and_exit_objective_fn(state: State, agent_id: EntityID) -> bool:
    """Collect all required items and reach an exit tile."""
    return collect_required_objective_fn(state, agent_id) and exit_objective_fn(
        state, agent_id
    )


def all_unlocked_objective_fn(state: State, agent_id: EntityID) -> bool:
    """No remaining locked entities (doors, etc.)."""
    return len(state.locked) == 0


def all_pushable_at_exit_objective_fn(state: State, agent_id: EntityID) -> bool:
    """Every Pushable entity currently occupies an exit tile."""
    for pushable_id in state.pushable:
        if pushable_id not in state.position:
            return False
        if (
            len(
                entities_with_components_at(
                    state, state.position[pushable_id], state.exit
                )
            )
            == 0
        ):
            return False
    return True


default_objective_fn: ObjectiveFn = collect_required_and_exit_objective_fn
"""Default objective function if none is specified in level config."""


OBJECTIVE_FN_REGISTRY: Dict[str, ObjectiveFn] = {
    "default": default_objective_fn,
    "collect": collect_required_objective_fn,
    "exit": exit_objective_fn,
    "collect_exit": collect_required_and_exit_objective_fn,
    "unlock": all_unlocked_objective_fn,
    "push": all_pushable_at_exit_objective_fn,
}
"""Name → objective predicate mapping for level configuration."""
