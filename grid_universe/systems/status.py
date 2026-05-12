"""
Status effect management system.

This system manages the lifecycle of status effects applied to entities,
including ticking down time limits, checking usage limits, and cleaning up
expired or orphaned effects.
"""

from dataclasses import replace
from pyrsistent.typing import PMap, PSet
from grid_universe.components import TimeLimit, UsageLimit, Status
from grid_universe.runtime import StepContext, make_step_context
from grid_universe.state import State
from grid_universe.types import EntityID, EffectType
from grid_universe.utils.lifetime import remove_entities


def tick_time_limit(
    state: State,
    status: Status,
    time_limit: PMap[EntityID, TimeLimit],
) -> PMap[EntityID, TimeLimit]:
    """Decrement per-effect time limits present in ``status``."""
    for effect_id in status.effect_ids:
        if effect_id in time_limit:
            time_limit = time_limit.set(
                effect_id, TimeLimit(amount=time_limit[effect_id].amount - 1)
            )
    return time_limit


def cleanup_effect(
    effect_id: EntityID,
    effect_ids: PSet[EntityID],
) -> PSet[EntityID]:
    """Remove ``effect_id`` from status if present."""
    effect_ids = effect_ids.remove(effect_id)
    return effect_ids


def is_effect_expired(
    effect_id: EntityID,
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> bool:
    """Return True if effect's time or usage limit has reached zero."""
    if effect_id in time_limit and time_limit[effect_id].amount <= 0:
        return True
    if effect_id in usage_limit and usage_limit[effect_id].amount <= 0:
        return True
    return False


def cleanup_status_effects(
    state: State,
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
    status: Status,
) -> tuple[Status, set[EntityID]]:
    """Remove orphaned or expired effects from status and entity maps."""
    effect_ids: PSet[EntityID] = status.effect_ids
    removed_effect_ids: set[EntityID] = set()

    # Remove invalid effect_ids by checking all effect component maps using EffectType
    for effect_id in list(effect_ids):
        if all(
            effect_id not in getattr(state, effect_type.name.lower())
            for effect_type in EffectType
        ):
            effect_ids = cleanup_effect(effect_id, effect_ids)
            removed_effect_ids.add(effect_id)

    # Remove expired effect_ids
    for effect_id in list(effect_ids):
        if is_effect_expired(effect_id, time_limit, usage_limit):
            effect_ids = cleanup_effect(effect_id, effect_ids)
            removed_effect_ids.add(effect_id)

    return replace(status, effect_ids=effect_ids), removed_effect_ids


def status_tick_system(state: State, ctx: StepContext) -> State:
    """Phase 1: decrement time limits for effects active at step start.

    When an effect is collected/applied mid-step, it should not immediately lose
    one tick during the same step. We therefore tick using ``ctx.prev_status``
    (a snapshot taken at the beginning of the step), not the possibly-updated
    ``state.status``.
    """
    state_status = state.status
    state_time_limit = state.time_limit

    for _, entity_status in ctx.prev_status.items():
        state_time_limit = tick_time_limit(state, entity_status, state_time_limit)

    return replace(
        state,
        status=state_status,
        time_limit=state_time_limit,
    )


def status_cleanup_system(state: State, ctx: StepContext) -> State:
    """Phase 2: prune orphaned / expired effects from statuses and entities."""
    state_status = state.status
    state_time_limit = state.time_limit
    state_usage_limit = state.usage_limit

    for entity_id, entity_status in state_status.items():
        entity_status, removed_effect_ids = cleanup_status_effects(
            state, state_time_limit, state_usage_limit, entity_status
        )
        ctx.removed_entity_ids.update(removed_effect_ids)
        state_status = state_status.set(entity_id, entity_status)

    return replace(
        state,
        status=state_status,
        time_limit=state_time_limit,
        usage_limit=state_usage_limit,
    )


def status_system(state: State) -> State:
    """Run tick and cleanup phases for all statuses."""
    ctx = make_step_context(state)
    state = status_tick_system(state, ctx)
    state = status_cleanup_system(state, ctx)
    state = remove_entities(state, ctx, ctx.removed_entity_ids)
    return state
