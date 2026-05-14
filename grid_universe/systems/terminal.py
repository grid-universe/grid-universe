"""
Terminal state management systems.

Handles win/lose conditions based on objective functions, agent death, and turn limits.
"""

from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def win_system(state: State, agent_id: EntityID, ctx: StepContext) -> None:
    """
    Set ``win`` flag if agent meets objective function (idempotent).

    Args:
        state (State): Current state.
        agent_id (EntityID): ID of the agent to check for win condition.

    """
    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return

    if state.objective(state, agent_id, ctx):
        state.win = True


def lose_system(state: State, agent_id: EntityID) -> None:
    """
    Set ``lose`` flag if agent is dead (idempotent).
    Args:
        state (State): Current state.
        agent_id (EntityID): ID of the agent to check for lose condition.

    """
    if agent_id in state.dead and not state.lose:
        state.lose = True


def turn_system(state: State, agent_id: EntityID) -> None:
    """
    Set ``lose`` flag if turn limit is reached.
    Args:
        state (State): Current state.
        agent_id (EntityID): ID of the agent to check for turn limit.

    """
    state.turn += 1
    if (
        state.turn_limit is not None
        and state.turn >= state.turn_limit
        and not state.win
    ):
        state.lose = True
