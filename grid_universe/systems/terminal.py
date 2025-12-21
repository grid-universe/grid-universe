"""
Terminal state management systems.

Handles win/lose conditions based on objective functions, agent death, and turn limits.
"""

from dataclasses import replace
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def win_system(state: State, agent_id: EntityID) -> State:
    """
    Set ``win`` flag if agent meets objective function (idempotent).

    Args:
        state (State): Current immutable state.
        agent_id (EntityID): ID of the agent to check for win condition.

    Returns:
        State: Updated state with ``win`` flag set if objective met.
    """
    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    if state.objective_fn(state, agent_id):
        return replace(state, win=True)
    return state


def lose_system(state: State, agent_id: EntityID) -> State:
    """
    Set ``lose`` flag if agent is dead (idempotent).
    Args:
        state (State): Current immutable state.
        agent_id (EntityID): ID of the agent to check for lose condition.

    Returns:
        State: Updated state with ``lose`` flag set if agent is dead.
    """
    if agent_id in state.dead and not state.lose:
        return replace(state, lose=True)
    return state


def turn_system(state: State, agent_id: EntityID) -> State:
    """
    Set ``lose`` flag if turn limit is reached.
    Args:
        state (State): Current immutable state.
        agent_id (EntityID): ID of the agent to check for turn limit.

    Returns:
        State: Updated state with ``lose`` flag set if turn limit reached.
    """
    state = replace(state, turn=state.turn + 1)
    if (
        state.turn_limit is not None
        and state.turn >= state.turn_limit
        and not state.win
    ):
        state = replace(state, lose=True)
    return state
