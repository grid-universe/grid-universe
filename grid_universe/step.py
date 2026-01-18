from dataclasses import replace
from grid_universe.runtime import StepContext
from grid_universe.actions import Action, MOVE_ACTIONS
from grid_universe.components.properties.position import Position
from grid_universe.systems.damage import damage_system
from grid_universe.systems.pathfinding import pathfinding_system
from grid_universe.systems.status import status_gc_system, status_tick_system
from grid_universe.state import State
from grid_universe.systems.movement import movement_system
from grid_universe.systems.moving import moving_system
from grid_universe.systems.position import position_system
from grid_universe.systems.push import push_system
from grid_universe.systems.portal import portal_system
from grid_universe.systems.collectible import collectible_system
from grid_universe.systems.locked import unlock_system
from grid_universe.systems.terminal import turn_system, win_system, lose_system
from grid_universe.systems.tile import tile_reward_system, tile_cost_system
from grid_universe.types import EntityID
from grid_universe.utils.gc import run_garbage_collector
from grid_universe.utils.status import use_status_effect_if_present
from grid_universe.utils.terminal import is_terminal_state, is_valid_state
from grid_universe.utils.trail import add_trail_position


def step(state: State, action: Action, agent_id: EntityID | None = None) -> State:
    """
    Apply an action to the current state, returning the updated state.

    If `agent_id` is not provided, the first agent in the state will be used.

    Args:
        state (State): The current state of the environment.
        action (Action): The action to be applied.
        agent_id (Optional[EntityID]): The ID of the agent performing the action.
            If None, the first agent in the state will be used.

    Returns:
        State: The updated state after applying the action.

    Raises:
        ValueError: If no agent_id is provided and no agents exist in the state.
    """
    if agent_id is None and (agent_id := next(iter(state.agent.keys()), None)) is None:
        raise ValueError("State contains no agent")

    if agent_id in state.dead:
        return replace(state, lose=True)

    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    ctx: StepContext = StepContext(prev_status=state.status)

    ctx = position_system(state, ctx)  # before movements
    state, ctx = moving_system(state, ctx)
    state = pathfinding_system(state)

    if action in MOVE_ACTIONS:
        state, ctx = _step_move(state, ctx, action, agent_id)
    elif action == Action.USE_KEY:
        state = _step_usekey(state, action, agent_id)
    elif action == Action.PICK_UP:
        state = _step_pickup(state, action, agent_id)
    elif action == Action.WAIT:
        state = _step_wait(state, action, agent_id)
    else:
        raise ValueError("Action is not valid")

    if action not in MOVE_ACTIONS:
        state, ctx = _after_substep(state, ctx, action, agent_id)

    return _after_step(state, ctx, agent_id)


def _step_move(
    state: State, ctx: StepContext, action: Action, agent_id: EntityID
) -> tuple[State, StepContext]:
    """Apply a movement action.

    Handles multi-substep movement, speed effects, and invokes interaction
    systems after each substep.

    Args:
        state (State): Current state prior to movement.
        ctx (StepContext): Current step context.
        action (Action): One of the directional ``Action`` enum members.
        agent_id (EntityID): Controlled agent entity id.

    Returns:
        State: Updated state after applying the movement action.
        StepContext: Updated step context after applying the movement action.
    """
    current_pos = state.position.get(agent_id)
    if not current_pos:
        return state, ctx  # agent has no position, cannot move

    move_count = 1

    if agent_id in state.status:
        usage_limit, effect_id = use_status_effect_if_present(
            state.status[agent_id].effect_ids,
            state.speed,
            state.time_limit,
            state.usage_limit,
        )
        if effect_id is not None:
            move_count = state.speed[effect_id].multiplier * move_count
            state = replace(state, usage_limit=usage_limit)

    for _ in range(move_count):
        positions = state.movement(state, agent_id, action)
        if len(positions) == 0:
            positions = [current_pos]  # no move possible
        for next_pos in positions:
            prev_state = state
            state, ctx = _substep(state, ctx, action, agent_id, next_pos)
            state, ctx = _after_substep(state, ctx, action, agent_id)
            if prev_state == state:
                return state, ctx  # movement blocked, stop processing further sub-moves

    return state, ctx


def _step_usekey(state: State, action: Action, agent_id: EntityID) -> State:
    """
    Apply the use-key action.

    Invokes `grid_universe.systems.locked.unlock_system` to attempt to
    unlock any locked entities at the agent's position or adjacent positions.
    """
    state = unlock_system(state, agent_id)
    return state


def _step_pickup(state: State, action: Action, agent_id: EntityID) -> State:
    """
    Apply the pick-up action.

    Invokes `grid_universe.systems.collectible.collectible_system` to
    collect any collectible entities at the agent's position.
    """
    state = collectible_system(state, agent_id)
    return state


def _step_wait(state: State, action: Action, agent_id: EntityID) -> State:
    """No‑op action.

    This simply consumes a turn.
    """
    return state


def _substep(
    state: State,
    ctx: StepContext,
    action: Action,
    agent_id: EntityID,
    next_pos: Position,
) -> tuple[State, StepContext]:
    """
    Perform a single movement *sub‑step* towards `next_pos`.

    Applies pushing and movement systems to move the agent towards the target
    position.

    Args:
        state (State): Current state before the sub-step.
        ctx (StepContext): Current step context.
        action (Action): Action being processed.
        agent_id (EntityID): Acting agent.
        next_pos (Position): Target position for this sub-step.

    Returns:
        State: Updated state after the sub-step.
    """
    state, ctx = push_system(state, ctx, agent_id, next_pos)
    state = movement_system(state, agent_id, next_pos)
    return state, ctx


def _after_substep(
    state: State, ctx: StepContext, action: Action, agent_id: EntityID
) -> tuple[State, StepContext]:
    """
    Finalize a single movement *sub‑step*.

    Applies portal teleportation, damage processing, tile rewards, position
    updates, and win / lose condition checks.

    Args:
        state (State): State after the sub-step.
        ctx (StepContext): Current step context.
        action (Action): Action being processed.
        agent_id (EntityID): Acting agent.

    Returns:
        State: Updated state after finalizing the sub-step.
        StepContext: Updated step context after finalizing the sub-step.
    """
    ctx = add_trail_position(ctx, agent_id, state.position[agent_id])
    state = portal_system(state, ctx)
    state, ctx = damage_system(state, ctx)
    state = tile_reward_system(state, agent_id)
    ctx = position_system(state, ctx)
    state = win_system(state, agent_id)
    state = lose_system(state, agent_id)
    return state, ctx


def _after_step(state: State, ctx: StepContext, agent_id: EntityID) -> State:
    """
    Finalize the full action step.

    Applies tile cost penalties, turn advancement, status effect garbage
    collection, and overall garbage collection.

    Args:
        state (State): State after all sub-steps of the action.
        ctx (StepContext): Current step context.
        agent_id (EntityID): Acting agent.

    Returns:
        State: Updated state after finalizing the full action step.
    """
    state = status_tick_system(state, ctx)
    state = tile_cost_system(
        state, agent_id
    )  # doesn't penalize faster move (move with submoves)
    state = turn_system(state, agent_id)
    state = status_gc_system(state)
    state = run_garbage_collector(state)
    return state
