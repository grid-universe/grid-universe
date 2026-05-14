from grid_universe.runtime import StepContext, make_step_context, snapshot_positions
from grid_universe.actions import Action, MOVE_ACTIONS
from grid_universe.components.properties.position import Position
from grid_universe.systems.damage import damage_system
from grid_universe.systems.pathfinding import pathfinding_system
from grid_universe.systems.status import status_cleanup_system, status_tick_system
from grid_universe.state import State
from grid_universe.systems.movement import movement_system
from grid_universe.systems.moving import moving_system
from grid_universe.systems.push import push_system
from grid_universe.systems.portal import portal_system
from grid_universe.systems.collectible import collectible_system
from grid_universe.systems.locked import unlock_system
from grid_universe.systems.terminal import turn_system, win_system, lose_system
from grid_universe.systems.tile import tile_reward_system, tile_cost_system
from grid_universe.types import EntityID
from grid_universe.utils.lifetime import remove_entities
from grid_universe.utils.status import use_status_effect_if_present
from grid_universe.utils.terminal import is_terminal_state, is_valid_state
from grid_universe.utils.trail import add_trail_position


def step(
    state: State,
    action: Action,
    agent_id: EntityID | None = None,
    *,
    in_place: bool = False,
) -> State:
    """
    Apply an action and return the updated state.

    By default this works on a clone of ``state``. With ``in_place=True``, it
    updates and returns the input ``state`` directly.
    If ``agent_id`` is not provided, the first agent in the state is used.

    Args:
        state (State): The current state of the environment.
        action (Action): The action to be applied.
        agent_id (EntityID | None): The ID of the agent performing the action.
            If ``None``, the first agent in the state is used.
        in_place (bool): If true, update ``state`` directly. If false, clone first.

    Returns:
        State: The updated state.

    Raises:
        ValueError: If no agent_id is provided and no agents exist in the state.
    """
    if not in_place:
        state = state.clone()

    if agent_id is None and (agent_id := next(iter(state.agent.keys()), None)) is None:
        raise ValueError("State contains no agent")

    if agent_id in state.dead:
        state.lose = True
        return state

    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    ctx: StepContext = make_step_context(state)

    snapshot_positions(ctx, state)
    moving_system(state, ctx)
    pathfinding_system(state, ctx)

    if action in MOVE_ACTIONS:
        _step_move(state, ctx, action, agent_id)
    elif action == Action.USE_KEY:
        _step_usekey(state, ctx, agent_id)
    elif action == Action.PICK_UP:
        _step_pickup(state, ctx, agent_id)
    elif action == Action.WAIT:
        pass
    else:
        raise ValueError("Action is not valid")

    if action not in MOVE_ACTIONS:
        _after_substep(state, ctx, agent_id)

    _after_step(state, ctx, agent_id)
    return state


def _step_move(
    state: State, ctx: StepContext, action: Action, agent_id: EntityID
) -> None:
    """Apply a movement action.

    Handles multi-substep movement, speed effects, and invokes interaction
    systems after each substep.

    Args:
        state (State): Current state prior to movement.
        ctx (StepContext): Current step context.
        action (Action): One of the directional ``Action`` enum members.
        agent_id (EntityID): Controlled agent entity id.

    """
    current_pos = state.position.get(agent_id)
    if not current_pos:
        return

    move_count = 1

    if agent_id in state.status:
        effect_id = use_status_effect_if_present(
            state.status[agent_id].effect_ids,
            state.speed,
            state.time_limit,
            state.usage_limit,
        )
        if effect_id is not None:
            move_count = state.speed[effect_id].multiplier * move_count

    for _ in range(move_count):
        positions = state.movement(state, agent_id, action)
        if len(positions) == 0:
            positions = [current_pos]  # no move possible
        for next_pos in positions:
            prev_pos = state.position.get(agent_id)
            _substep(state, ctx, agent_id, next_pos)
            _after_substep(state, ctx, agent_id)
            if state.position.get(agent_id) == prev_pos:
                return


def _step_usekey(state: State, ctx: StepContext, agent_id: EntityID) -> None:
    """
    Apply the use-key action.

    Invokes `grid_universe.systems.locked.unlock_system` to attempt to
    unlock any locked entities at the agent's position or adjacent positions.
    """
    unlock_system(state, agent_id, ctx)


def _step_pickup(state: State, ctx: StepContext, agent_id: EntityID) -> None:
    """
    Apply the pick-up action.

    Invokes `grid_universe.systems.collectible.collectible_system` to
    collect any collectible entities at the agent's position.
    """
    collectible_system(state, agent_id, ctx)


def _substep(
    state: State,
    ctx: StepContext,
    agent_id: EntityID,
    next_pos: Position,
) -> None:
    """
    Perform a single movement *sub‑step* towards `next_pos`.

    Applies pushing and movement systems to move the agent towards the target
    position.

    Args:
        state (State): Current state before the sub-step.
        ctx (StepContext): Current step context.
        agent_id (EntityID): Acting agent.
        next_pos (Position): Target position for this sub-step.
    """
    push_system(state, ctx, agent_id, next_pos)
    movement_system(state, agent_id, next_pos, ctx)


def _after_substep(state: State, ctx: StepContext, agent_id: EntityID) -> None:
    """
    Finalize a single movement *sub‑step*.

    Applies portal teleportation, damage processing, tile rewards, position
    updates, and win / lose condition checks.

    Args:
        state (State): State after the sub-step.
        ctx (StepContext): Current step context.
        agent_id (EntityID): Acting agent.
    """
    add_trail_position(ctx, agent_id, state.position[agent_id])
    portal_system(state, ctx)
    damage_system(state, ctx)
    tile_reward_system(state, agent_id, ctx)
    snapshot_positions(ctx, state)
    win_system(state, agent_id, ctx)
    lose_system(state, agent_id)


def _after_step(state: State, ctx: StepContext, agent_id: EntityID) -> None:
    """
    Finalize the full action step.

    Applies tile cost penalties, turn advancement, status effect cleanup,
    and component cleanup for entities removed during the step.

    Args:
        state (State): State after all sub-steps of the action.
        ctx (StepContext): Current step context.
        agent_id (EntityID): Acting agent.

    """
    status_tick_system(state, ctx)
    tile_cost_system(state, agent_id, ctx)  # doesn't penalize faster move
    turn_system(state, agent_id)
    status_cleanup_system(state, ctx)
    remove_entities(state, ctx, ctx.removed_entity_ids)
