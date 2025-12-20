"""Convenience factory functions for authoring ``EntitySpec`` objects.

Each helper returns a preconfigured :class:`EntitySpec` with a common pattern
(agent, floor, wall, coin, key, door, portal, hazards, effects, etc.). These
are mutable authoring-time blueprints converted into immutable ECS entities by
``levels.convert.to_state``.
"""

from __future__ import annotations

from typing import Optional
from pyrsistent import pset

from grid_universe.components.properties import (
    Agent,
    Appearance,
    AppearanceName,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Portal,
    Pushable,
    Requirable,
    Rewardable,
    PathfindingType,
    Status,
    Moving,
    MovingAxis,
)
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from .entity_spec import EntitySpec


def create_agent(health: int = 5) -> EntitySpec:
    """Player-controlled agent with health + inventory + empty status."""
    return EntitySpec(
        agent=Agent(),
        appearance=Appearance(name=AppearanceName.HUMAN, priority=0),
        health=Health(health=health, max_health=health),
        collidable=Collidable(),
        inventory=Inventory(pset()),
        status=Status(pset()),
    )


def create_floor(cost_amount: int = 1) -> EntitySpec:
    """Background floor tile with movement cost."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.FLOOR, background=True, priority=10),
        cost=Cost(amount=cost_amount),
    )


def create_wall() -> EntitySpec:
    """Blocking wall tile."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.WALL, background=True, priority=9),
        blocking=Blocking(),
    )


def create_exit() -> EntitySpec:
    """Exit tile used in objectives."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.EXIT, priority=9),
        exit=Exit(),
    )


def create_coin(reward: Optional[int] = None) -> EntitySpec:
    """Collectible coin awarding optional score when picked up."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.COIN, icon=True, priority=4),
        collectible=Collectible(),
        rewardable=None if reward is None else Rewardable(amount=reward),
    )


def create_core(reward: Optional[int] = None, required: bool = True) -> EntitySpec:
    """Key objective collectible ("core") optionally giving reward."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.CORE, icon=True, priority=4),
        collectible=Collectible(),
        rewardable=None if reward is None else Rewardable(amount=reward),
        requirable=Requirable() if required else None,
    )


def create_key(key_id: str) -> EntitySpec:
    """Key item unlocking doors with matching ``key_id``."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.KEY, icon=True, priority=4),
        collectible=Collectible(),
        key=Key(key_id=key_id),
    )


def create_door(key_id: str) -> EntitySpec:
    """Locked door requiring a key with the same id."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.DOOR, priority=6),
        blocking=Blocking(),
        locked=Locked(key_id=key_id),
    )


def create_portal(*, pair: Optional[EntitySpec] = None) -> EntitySpec:
    """Portal endpoint (optionally auto-paired during authoring).

    If ``pair`` is provided we set reciprocal refs so conversion wires the
    pair entities with each other's id.
    """
    obj = EntitySpec(
        appearance=Appearance(name=AppearanceName.PORTAL, priority=7),
        portal=Portal(pair_entity=-1),
    )
    if pair is not None:
        obj.portal_pair_ref = pair
        if pair.portal_pair_ref is None:
            pair.portal_pair_ref = obj
    return obj


def create_box(
    pushable: bool = True,
    moving_axis: Optional[MovingAxis] = None,
    moving_direction: Optional[int] = None,
    moving_bounce: bool = True,
    moving_speed: int = 1,
) -> EntitySpec:
    """Pushable / blocking box (optionally not pushable)."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.BOX, priority=2),
        blocking=Blocking(),
        collidable=Collidable(),
        pushable=Pushable() if pushable else None,
        moving=None
        if moving_axis is None or moving_direction is None
        else Moving(
            axis=moving_axis,
            direction=moving_direction,
            bounce=moving_bounce,
            speed=moving_speed,
        ),
    )


def create_monster(
    damage: int = 3,
    lethal: bool = False,
    *,
    moving_axis: Optional[MovingAxis] = None,
    moving_direction: Optional[int] = None,
    moving_bounce: bool = True,
    moving_speed: int = 1,
    pathfind_target: Optional[EntitySpec] = None,
    path_type: PathfindingType = PathfindingType.PATH,
) -> EntitySpec:
    """Basic enemy with damage and optional lethal + pathfinding target."""
    obj = EntitySpec(
        appearance=Appearance(name=AppearanceName.MONSTER, priority=1),
        collidable=Collidable(),
        damage=Damage(amount=damage),
        lethal_damage=LethalDamage() if lethal else None,
        moving=None
        if moving_axis is None or moving_direction is None
        else Moving(
            axis=moving_axis,
            direction=moving_direction,
            bounce=moving_bounce,
            speed=moving_speed,
        ),
    )
    if pathfind_target is not None:
        obj.pathfind_target_ref = pathfind_target
        obj.pathfinding_type = path_type
    return obj


def create_hazard(
    appearance: AppearanceName,
    damage: int,
    lethal: bool = False,
    priority: int = 7,
) -> EntitySpec:
    """Static damaging (optionally lethal) tile-like hazard."""
    return EntitySpec(
        appearance=Appearance(name=appearance, priority=priority),
        collidable=Collidable(),
        damage=Damage(amount=damage),
        lethal_damage=LethalDamage() if lethal else None,
    )


def create_speed_effect(
    multiplier: int,
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> EntitySpec:
    """Collectible speed effect (optional time / usage limits)."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.BOOTS, icon=True, priority=4),
        collectible=Collectible(),
        speed=Speed(multiplier=multiplier),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )


def create_immunity_effect(
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> EntitySpec:
    """Collectible immunity effect (optional limits)."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.SHIELD, icon=True, priority=4),
        collectible=Collectible(),
        immunity=Immunity(),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )


def create_phasing_effect(
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> EntitySpec:
    """Collectible phasing effect (optional limits)."""
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.GHOST, icon=True, priority=4),
        collectible=Collectible(),
        phasing=Phasing(),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )
