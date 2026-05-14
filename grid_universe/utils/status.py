"""
Status effect utilities.

Provides helper functions for managing status effects on entities,
including adding/removing effects, checking for effect presence, and
consuming effect usages.
"""

from collections.abc import Sequence
from dataclasses import replace
from typing import cast

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    UsageLimit,
    TimeLimit,
)


EffectMap = dict[EntityID, Immunity] | dict[EntityID, Phasing] | dict[EntityID, Speed]


def _normalize_effects(
    effects: EffectMap | Sequence[EffectMap],
) -> list[EffectMap]:
    """Return list form for effect map(s) argument."""
    if isinstance(effects, (list, tuple)):
        return list(cast(Sequence[EffectMap], effects))
    else:
        return [cast(EffectMap, effects)]


def has_effect(state: State, effect_id: EntityID) -> bool:
    """Return True if ``effect_id`` exists in any runtime effect store."""
    effect_maps: list[EffectMap] = [state.immunity, state.phasing, state.speed]
    for effect in effect_maps:
        if effect_id in effect:
            return True
    return False


def valid_effect(state: State, effect_id: EntityID) -> bool:
    """Return True if effect has no expired time/usage limit."""
    # Only add effect if its time or usage limit is positive or unlimited
    if effect_id in state.time_limit and state.time_limit[effect_id].amount <= 0:
        return False
    if effect_id in state.usage_limit and state.usage_limit[effect_id].amount <= 0:
        return False
    return True


def get_status_effect(
    effect_ids: set[EntityID],
    effects: EffectMap | Sequence[EffectMap],
    time_limit: dict[EntityID, TimeLimit],
    usage_limit: dict[EntityID, UsageLimit],
) -> EntityID | None:
    """Select a valid effect from ``effect_ids`` matching any provided store.

    Selection rules:
    1. Filter to effect IDs present in at least one supplied effect map.
    2. Drop expired effects (time or usage limit <= 0).
    3. Prefer effects without usage limits; otherwise lowest EID yields tie.
    """
    effect_maps: list[EffectMap] = _normalize_effects(effects)

    # Effects present in any of the requested effect stores
    relevant = [
        eid for eid in effect_ids if any(eid in eff_map for eff_map in effect_maps)
    ]
    if not relevant:
        return None

    # Filter out expired effects
    valid: list[EntityID] = []
    for eid in relevant:
        # Expired by time
        if eid in time_limit and time_limit[eid].amount <= 0:
            continue
        # Expired by usage
        if eid in usage_limit and usage_limit[eid].amount <= 0:
            continue
        valid.append(eid)

    if not valid:
        return None

    # Deterministic order
    valid.sort()

    # Prefer effects without usage limits (infinite or time-limited)
    for eid in valid:
        if eid not in usage_limit:
            return eid

    # Otherwise, return the first remaining usage-limited effect
    return valid[0]


def use_status_effect(
    effect_id: EntityID, usage_limit: dict[EntityID, UsageLimit]
) -> None:
    """Consume one use from a usage-limited effect if present."""
    if effect_id not in usage_limit:
        return
    usage_limit[effect_id] = replace(
        usage_limit[effect_id], amount=usage_limit[effect_id].amount - 1
    )


def use_status_effect_if_present(
    effect_ids: set[EntityID],
    effects: EffectMap | Sequence[EffectMap],
    time_limit: dict[EntityID, TimeLimit],
    usage_limit: dict[EntityID, UsageLimit],
) -> EntityID | None:
    """Select and consume an effect if one is present."""
    effect_maps: list[EffectMap] = _normalize_effects(effects)
    effect_id = get_status_effect(effect_ids, effect_maps, time_limit, usage_limit)
    if effect_id is not None:
        use_status_effect(effect_id, usage_limit)
    return effect_id
