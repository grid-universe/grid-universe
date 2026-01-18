"""
Defines built-in objectives for determining win conditions in Grid Universe
environments.

Each objective is a ``BaseObjective`` instance containing one or more functions
that accept the current ``State`` and the agent's entity ID, and return a
boolean indicating whether the win condition has been met.

Users can select from built-in objectives via ``OBJECTIVE_REGISTRY`` or define
custom objectives by subclassing ``BaseObjective``.
"""

from dataclasses import dataclass
from grid_universe.state import State
from grid_universe.types import EntityID, ObjectiveFn
from grid_universe.utils.ecs import entities_with_components_at


# Built-in Objective Functions


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


# Built-in Objectives


@dataclass(frozen=True)
class BaseObjective:
    """Base class for objective functions."""

    name: str
    description: str
    functions: tuple[ObjectiveFn, ...]

    def __call__(self, state: State, agent_id: EntityID) -> bool:
        """Evaluate the objective function."""
        return all(fn(state, agent_id) for fn in self.functions)


@dataclass(frozen=True)
class ExitObjective(BaseObjective):
    """Objective function for reaching an exit."""

    name: str = "exit"
    description: str = "Reach an exit tile."
    functions: tuple[ObjectiveFn, ...] = (exit_objective_fn,)


@dataclass(frozen=True)
class CollectObjective(BaseObjective):
    """Objective function for collecting all required items."""

    name: str = "collect"
    description: str = "Collect all required items."
    functions: tuple[ObjectiveFn, ...] = (collect_objective_fn,)


@dataclass(frozen=True)
class CollectAndExitObjective(BaseObjective):
    """Objective function for collecting all required items and reaching an exit."""

    name: str = "collect_exit"
    description: str = "Collect all required items and reach an exit tile."
    functions: tuple[ObjectiveFn, ...] = (
        collect_objective_fn,
        exit_objective_fn,
    )


@dataclass(frozen=True)
class UnlockObjective(BaseObjective):
    """Objective function for unlocking all locked entities."""

    name: str = "unlock"
    description: str = "Unlock all locked entities."
    functions: tuple[ObjectiveFn, ...] = (all_unlocked_objective_fn,)


@dataclass(frozen=True)
class PushObjective(BaseObjective):
    """Objective function for pushing all pushable entities to exit tiles."""

    name: str = "push"
    description: str = "Push all pushable entities to exit tiles."
    functions: tuple[ObjectiveFn, ...] = (all_pushable_at_exit_objective_fn,)


OBJECTIVE_REGISTRY: dict[str, BaseObjective] = {
    "collect": CollectObjective(),
    "exit": ExitObjective(),
    "collect_exit": CollectAndExitObjective(),
    "unlock": UnlockObjective(),
    "push": PushObjective(),
}
"""Registry of built-in objectives by name.

Use these objective objects when creating ``State`` instances. Each objective
encapsulates one or more functions that together define whether the agent
has satisfied the win condition.
"""
