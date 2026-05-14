from grid_universe.actions import Action
from grid_universe.grid.gridstate import GridState
from grid_universe.step import step as base_step
from grid_universe.grid.convert import to_state, from_state


def step(
    gridstate: GridState, action: Action, agent_id: int | None = None
) -> GridState:
    """
    Execute one step with the given action and return a new GridState.

    Converts this GridState to a State, applies the step function,
    and converts the result back to a GridState.

    Args:
        action: The action to execute
        agent_id: Optional agent entity ID. If None, uses the first agent found.

    Returns:
        New GridState after executing the step
    """
    # Convert to State
    state = to_state(gridstate)

    # Find agent if not provided
    if agent_id is None:
        agent_id = next(iter(state.agent.keys()))

    # Execute step
    new_state = base_step(state, action, agent_id=agent_id)

    # Convert back to GridState
    return from_state(new_state)
