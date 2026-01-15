"""
Damage and lethal interaction system.

Resolves damage and lethal damage interactions between entities based on
their positions and movement trails, applying health reductions and death
status updates as appropriate.

Damage is applied if either of the following conditions are met between a
target entity and a damager entity during the current turn:
- There is an overlap between the target and damager positions.
- There is a swap of positions between the target and damager.
- Their trails intersect.
- The target crosses into the damager's previous position (based on their movement trails).

Damage is NOT applied if:
- The target steps onto the damager's just vacated origin tile without
  any other interaction evidence (no overlap, no swap, no trail intersections).

Damage is only applied once per (target, damager) pair per turn, and
status effects such as immunity or phasing can prevent damage application.
"""

from dataclasses import replace
from typing import Set, Tuple, Dict
from pyrsistent import PMap, PSet
from grid_universe.state import State
from grid_universe.components import Health, Dead, UsageLimit, Position
from grid_universe.types import EntityID
from grid_universe.utils.health import apply_damage_and_check_death
from grid_universe.utils.status import use_status_effect_if_present
from grid_universe.runtime import StepContext


def _build_trail_cache(
    trail: PMap[Position, PSet[EntityID]],
) -> Dict[EntityID, Set[Position]]:
    """Invert trail mapping into entity -> visited positions set."""
    cache: Dict[EntityID, Set[Position]] = {}
    for pos, ids in trail.items():
        for eid in ids:
            cache.setdefault(eid, set()).add(pos)
    return cache


def _is_swap(
    a_prev: Position, a_curr: Position, b_prev: Position, b_curr: Position
) -> bool:
    return a_prev == b_curr and a_curr == b_prev


def _overlap(pos_a: Position, pos_b: Position) -> bool:
    return pos_a == pos_b


def _pure_vacated_origin(
    target_prev: Position,
    target_curr: Position,
    damager_prev: Position,
    damager_curr: Position,
    target_trail: Set[Position],
    damager_trail: Set[Position],
) -> bool:
    """Return True when target steps onto the damager's *just vacated* origin tile.

    We only exclude damage if there is no other interaction evidence:
        * target_curr == damager_prev
        * NOT swap
        * target_prev not in damager_trail (no crossing through damager path)
        * damager_curr not in target_trail (target never visited damager's new tile)
        * trails otherwise disjoint (enforced by caller passing ``trails_intersect == False``)
    """
    if target_curr != damager_prev:
        return False
    if _is_swap(target_prev, target_curr, damager_prev, damager_curr):
        return False
    if target_prev in damager_trail:
        return False
    if damager_curr in target_trail:
        return False
    return True


def _candidate_damagers(state: State) -> Set[EntityID]:
    """Return all entities capable of dealing damage (normal or lethal)."""
    return set(state.damage) | set(state.lethal_damage)


DamageHit = Tuple[EntityID, EntityID, int]  # (target, damager, turn)


def _apply_single_damage(
    state: State,
    target_id: EntityID,
    damager_id: EntityID,
    health: PMap[EntityID, Health],
    dead: PMap[EntityID, Dead],
    usage_limit: PMap[EntityID, UsageLimit],
    damage_hits: PSet[DamageHit],
) -> Tuple[
    PMap[EntityID, Health],
    PMap[EntityID, Dead],
    PMap[EntityID, UsageLimit],
    PSet[DamageHit],
]:
    """Apply damage from damager -> target if not already applied this turn."""
    hit_key: DamageHit = (target_id, damager_id, state.turn)
    if hit_key in damage_hits:
        return health, dead, usage_limit, damage_hits
    # Status-based avoidance (immunity / phasing) consumes effect use.
    if target_id in state.status:
        usage_limit, effect_id = use_status_effect_if_present(
            state.status[target_id].effect_ids,
            [state.immunity, state.phasing],
            state.time_limit,
            usage_limit,
        )
        if effect_id is not None:
            return health, dead, usage_limit, damage_hits
    damage = state.damage[damager_id].amount if damager_id in state.damage else 0
    if damage < 0:
        raise ValueError(f"Damager {damager_id} has negative damage: {damage}")
    health, dead = apply_damage_and_check_death(
        health, dead, target_id, damage, damager_id in state.lethal_damage
    )
    damage_hits = damage_hits.add(hit_key)
    return health, dead, usage_limit, damage_hits


def _apply_damage_for_target(
    state: State,
    ctx: StepContext,
    target_id: EntityID,
    health: PMap[EntityID, Health],
    dead: PMap[EntityID, Dead],
    usage_limit: PMap[EntityID, UsageLimit],
    damage_hits: PSet[DamageHit],
    damager_ids: Set[EntityID],
    trail_cache: Dict[EntityID, Set[Position]],
) -> Tuple[
    PMap[EntityID, Health],
    PMap[EntityID, Dead],
    PMap[EntityID, UsageLimit],
    PSet[DamageHit],
]:
    """Evaluate all damagers against a single target and apply damage if predicates pass."""
    target_pos = state.position.get(target_id)
    if target_pos is None or target_id in dead:
        return health, dead, usage_limit, damage_hits

    target_prev = ctx.prev_position.get(target_id)
    target_trail = trail_cache.get(target_id, set())

    for damager_id in damager_ids:
        if damager_id == target_id:
            continue  # skip self
        damager_pos = state.position.get(damager_id)
        if damager_pos is None:
            continue

        damager_prev = ctx.prev_position.get(damager_id)

        # If either lacks prev position, only overlap is reliable.
        if target_prev is None or damager_prev is None:
            if _overlap(target_pos, damager_pos):
                health, dead, usage_limit, damage_hits = _apply_single_damage(
                    state,
                    target_id,
                    damager_id,
                    health,
                    dead,
                    usage_limit,
                    damage_hits,
                )
            continue

        damager_trail = trail_cache.get(damager_id, set())

        overlap = _overlap(target_pos, damager_pos)
        swap = _is_swap(target_prev, target_pos, damager_prev, damager_pos)
        trails_intersect = bool(target_trail & damager_trail)

        # Pure vacated origin exclusion
        if not overlap and not trails_intersect:
            if _pure_vacated_origin(
                target_prev,
                target_pos,
                damager_prev,
                damager_pos,
                target_trail,
                damager_trail,
            ):
                continue

        endpoint_cross = target_pos == damager_prev and (
            target_prev in damager_trail or damager_prev in target_trail
        )

        if overlap or swap or trails_intersect or endpoint_cross:
            health, dead, usage_limit, damage_hits = _apply_single_damage(
                state,
                target_id,
                damager_id,
                health,
                dead,
                usage_limit,
                damage_hits,
            )

    return health, dead, usage_limit, damage_hits


def damage_system(state: State, ctx: StepContext) -> tuple[State, StepContext]:
    """Resolve damage / lethal interactions for this turn.

    Complexity: O(H * D + T) where
        H = # entities with health
        D = # entities with damage/lethal components
        T = total trail entries this action
    """
    health: PMap[EntityID, Health] = state.health
    dead: PMap[EntityID, Dead] = state.dead
    usage_limit: PMap[EntityID, UsageLimit] = state.usage_limit
    damage_hits: PSet[DamageHit] = ctx.damage_hits

    damager_ids = _candidate_damagers(state)
    trail_cache = _build_trail_cache(ctx.trail)

    # Iterate over snapshot list to avoid issues if component maps structurally change.
    for target_id in list(state.health.keys()):
        health, dead, usage_limit, damage_hits = _apply_damage_for_target(
            state,
            ctx,
            target_id,
            health,
            dead,
            usage_limit,
            damage_hits,
            damager_ids,
            trail_cache,
        )

    state = replace(
        state,
        health=health,
        dead=dead,
        usage_limit=usage_limit,
    )
    ctx = replace(ctx, damage_hits=damage_hits)
    return state, ctx
