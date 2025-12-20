"""
Defines built-in objective functions for determining win conditions in Grid
Universe environments.

Each function adheres to the ``ObjectiveFn`` signature, accepting the current
``State`` and the agent's entity ID, and returning a boolean indicating whether
the win condition has been met.
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


def collect_objective_fn(state: State, agent_id: EntityID) -> bool:
    """All entities marked ``Requirable`` have been collected."""
    return all((eid not in state.collectible) for eid in state.requirable)


def collect_and_exit_objective_fn(state: State, agent_id: EntityID) -> bool:
    """Collect all requirable items and reach an exit tile."""
    return collect_objective_fn(state, agent_id) and exit_objective_fn(
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


default_objective_fn: ObjectiveFn = collect_and_exit_objective_fn
"""Default objective function if none is specified in level config."""


OBJECTIVE_FN_REGISTRY: Dict[str, ObjectiveFn] = {
    "default": default_objective_fn,
    "collect": collect_objective_fn,
    "exit": exit_objective_fn,
    "collect_exit": collect_and_exit_objective_fn,
    "unlock": all_unlocked_objective_fn,
    "push": all_pushable_at_exit_objective_fn,
}
"""Registry of built-in objective functions by name.

Each function answers whether the agent has satisfied the win condition.
"""
