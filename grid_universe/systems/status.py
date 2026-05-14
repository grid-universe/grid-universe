"""
Status effect management system.

This system manages the lifecycle of status effects applied to entities,
including ticking down time limits, checking usage limits, and cleaning up
expired or orphaned effects.
"""

from grid_universe.components import TimeLimit, UsageLimit, Status
from grid_universe.runtime import StepContext
from grid_universe.state import State
from grid_universe.types import EntityID, EffectType


def tick_time_limit(
    status: Status,
    time_limit: dict[EntityID, TimeLimit],
) -> None:
    """Decrement per-effect time limits present in ``status``."""
    for effect_id in status.effect_ids:
        if effect_id in time_limit:
            time_limit[effect_id] = TimeLimit(amount=time_limit[effect_id].amount - 1)


def is_effect_expired(
    effect_id: EntityID,
    time_limit: dict[EntityID, TimeLimit],
    usage_limit: dict[EntityID, UsageLimit],
) -> bool:
    """Return True if effect's time or usage limit has reached zero."""
    if effect_id in time_limit and time_limit[effect_id].amount <= 0:
        return True
    if effect_id in usage_limit and usage_limit[effect_id].amount <= 0:
        return True
    return False


def cleanup_status_effects(
    state: State,
    time_limit: dict[EntityID, TimeLimit],
    usage_limit: dict[EntityID, UsageLimit],
    status: Status,
) -> tuple[Status, set[EntityID]]:
    """Remove orphaned or expired effects from status and entity maps."""
    effect_ids = status.effect_ids
    removed_effect_ids: set[EntityID] = set()

    # Remove invalid effect_ids by checking all effect component maps using EffectType
    for effect_id in list(effect_ids):
        if all(
            effect_id not in getattr(state, effect_type.name.lower())
            for effect_type in EffectType
        ):
            effect_ids = effect_ids - {effect_id}
            removed_effect_ids.add(effect_id)

    # Remove expired effect_ids
    for effect_id in list(effect_ids):
        if is_effect_expired(effect_id, time_limit, usage_limit):
            effect_ids = effect_ids - {effect_id}
            removed_effect_ids.add(effect_id)

    return Status(effect_ids=effect_ids), removed_effect_ids


def status_tick_system(state: State, ctx: StepContext) -> None:
    """Phase 1: decrement time limits for effects active at step start.

    When an effect is collected/applied mid-step, it should not immediately lose
    one tick during the same step. We therefore tick using ``ctx.prev_status``
    (a snapshot taken at the beginning of the step), not the possibly-updated
    ``state.status``.
    """
    for _, entity_status in ctx.prev_status.items():
        tick_time_limit(entity_status, state.time_limit)


def status_cleanup_system(state: State, ctx: StepContext) -> None:
    """Phase 2: prune orphaned / expired effects from statuses and entities."""
    for entity_id, entity_status in list(state.status.items()):
        entity_status, removed_effect_ids = cleanup_status_effects(
            state, state.time_limit, state.usage_limit, entity_status
        )
        ctx.removed_entity_ids.update(removed_effect_ids)
        state.status[entity_id] = entity_status
