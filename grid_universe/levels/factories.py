"""Convenience factory functions for building ``Entity`` objects.

Each helper returns a preconfigured `Entity` with a common pattern
(agent, floor, wall, coin, key, door, portal, hazards, effects, etc.). These
are mutable blueprints that can be converted into an immutable ECS
`grid_universe.state.State` via `grid_universe.levels.convert.to_state`.
"""

from __future__ import annotations

from typing import Optional
from pyrsistent import pset

from grid_universe.components.properties import (
    Agent,
    Appearance,
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
    Direction,
)
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from .entity import Entity


def create_agent(health: int = 5) -> Entity:
    """Player-controlled agent with health + inventory + empty status."""
    return Entity(
        agent=Agent(),
        appearance=Appearance(name="human", priority=0),
        health=Health(health=health, max_health=health),
        collidable=Collidable(),
        inventory=Inventory(pset()),
        status=Status(pset()),
    )


def create_floor(cost_amount: int = 1) -> Entity:
    """Background floor tile with movement cost."""
    return Entity(
        appearance=Appearance(name="floor", background=True, priority=10),
        cost=Cost(amount=cost_amount),
    )


def create_wall() -> Entity:
    """Blocking wall tile."""
    return Entity(
        appearance=Appearance(name="wall", background=True, priority=9),
        blocking=Blocking(),
    )


def create_exit() -> Entity:
    """Exit tile used in objectives."""
    return Entity(
        appearance=Appearance(name="exit", priority=9),
        exit=Exit(),
    )


def create_coin(reward: Optional[int] = None) -> Entity:
    """Collectible coin awarding optional score when picked up."""
    return Entity(
        appearance=Appearance(name="coin", icon=True, priority=4),
        collectible=Collectible(),
        rewardable=None if reward is None else Rewardable(amount=reward),
    )


def create_core(reward: Optional[int] = None, required: bool = True) -> Entity:
    """Key objective collectible ("core") optionally giving reward."""
    return Entity(
        appearance=Appearance(name="core", icon=True, priority=4),
        collectible=Collectible(),
        rewardable=None if reward is None else Rewardable(amount=reward),
        requirable=Requirable() if required else None,
    )


def create_key(key_id: str) -> Entity:
    """Key item unlocking doors with matching ``key_id``."""
    return Entity(
        appearance=Appearance(name="key", icon=True, priority=4),
        collectible=Collectible(),
        key=Key(key_id=key_id),
    )


def create_door(key_id: str) -> Entity:
    """Locked door requiring a key with the same id."""
    return Entity(
        appearance=Appearance(name="door", priority=6),
        blocking=Blocking(),
        locked=Locked(key_id=key_id),
    )


def create_portal(*, pair: Optional[Entity] = None) -> Entity:
    """Portal endpoint (optionally auto-paired by reference).

    If ``pair`` is provided we set reciprocal refs so conversion wires the
    pair entities with each other's id.
    """
    obj = Entity(
        appearance=Appearance(name="portal", priority=7),
        portal=Portal(pair_entity=-1),
    )
    if pair is not None:
        obj.portal_pair_ref = pair
        if pair.portal_pair_ref is None:
            pair.portal_pair_ref = obj
    return obj


def create_box(
    pushable: bool = True,
    moving_direction: Optional[Direction] = None,
    moving_bounce: bool = True,
    moving_speed: int = 1,
) -> Entity:
    """Pushable / blocking box (optionally not pushable)."""
    return Entity(
        appearance=Appearance(name="box", priority=2),
        blocking=Blocking(),
        collidable=Collidable(),
        pushable=Pushable() if pushable else None,
        moving=None
        if moving_direction is None
        else Moving(
            direction=moving_direction,
            bounce=moving_bounce,
            speed=moving_speed,
        ),
    )


def create_monster(
    damage: int = 3,
    lethal: bool = False,
    *,
    moving_direction: Optional[Direction] = None,
    moving_bounce: bool = True,
    moving_speed: int = 1,
    pathfind_target: Optional[Entity] = None,
    path_type: PathfindingType = PathfindingType.PATH,
) -> Entity:
    """Basic enemy with damage and optional lethal + pathfinding target."""
    obj = Entity(
        appearance=Appearance(name="monster", priority=1),
        collidable=Collidable(),
        damage=Damage(amount=damage),
        lethal_damage=LethalDamage() if lethal else None,
        moving=None
        if moving_direction is None
        else Moving(
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
    appearance: str,
    damage: int,
    lethal: bool = False,
    priority: int = 7,
) -> Entity:
    """Static damaging (optionally lethal) tile-like hazard."""
    return Entity(
        appearance=Appearance(name=appearance, priority=priority),
        collidable=Collidable(),
        damage=Damage(amount=damage),
        lethal_damage=LethalDamage() if lethal else None,
    )


def create_speed_effect(
    multiplier: int,
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> Entity:
    """Collectible speed effect (optional time / usage limits)."""
    return Entity(
        appearance=Appearance(name="boots", icon=True, priority=4),
        collectible=Collectible(),
        speed=Speed(multiplier=multiplier),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )


def create_immunity_effect(
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> Entity:
    """Collectible immunity effect (optional limits)."""
    return Entity(
        appearance=Appearance(name="shield", icon=True, priority=4),
        collectible=Collectible(),
        immunity=Immunity(),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )


def create_phasing_effect(
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> Entity:
    """Collectible phasing effect (optional limits)."""
    return Entity(
        appearance=Appearance(name="ghost", icon=True, priority=4),
        collectible=Collectible(),
        phasing=Phasing(),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )
