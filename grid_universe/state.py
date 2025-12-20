from dataclasses import dataclass
from typing import Any, Optional
from pyrsistent import PMap, PSet, pmap, pset

from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from grid_universe.components.properties import (
    Agent,
    Appearance,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Dead,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Moving,
    Pathfinding,
    Portal,
    Position,
    Pushable,
    Requirable,
    Rewardable,
    Status,
)
from grid_universe.types import EntityID, MoveFn, ObjectiveFn


@dataclass(frozen=True)
class State:
    """Immutable ECS world state.

    Attributes:
        width (int): Grid width in tiles.
        height (int): Grid height in tiles.
        move_fn (MoveFn): Movement function determining entity step paths.
        objective_fn (ObjectiveFn): Objective function determining win condition.
        immunity (PMap[EntityID, Immunity]): Effect component map.
        phasing (PMap[EntityID, Phasing]): Effect component map.
        speed (PMap[EntityID, Speed]): Effect component map.
        time_limit (PMap[EntityID, TimeLimit]): Effect limiter map (remaining steps).
        usage_limit (PMap[EntityID, UsageLimit]): Effect limiter map (remaining uses).
        agent (PMap[EntityID, Agent]): Agent component map.
        appearance (PMap[EntityID, Appearance]): Visual appearance component map.
        blocking (PMap[EntityID, Blocking]): Obstacles that block movement.
        collectible (PMap[EntityID, Collectible]): Entities that can be collected.
        collidable (PMap[EntityID, Collidable]): Entities that can collide (triggering damage, cost, etc.).
        cost (PMap[EntityID, Cost]): Entities that inflict movement cost.
        damage (PMap[EntityID, Damage]): Entities that inflict damage on contact.
        dead (PMap[EntityID, Dead]): Entities that are dead/incapacitated.
        exit (PMap[EntityID, Exit]): Exit tiles/components.
        health (PMap[EntityID, Health]): Entity health component map.
        inventory (PMap[EntityID, Inventory]): Agent inventory component map.
        key (PMap[EntityID, Key]): Keys that can unlock ``Locked`` components.
        lethal_damage (PMap[EntityID, LethalDamage]): Entities that inflict instant death on contact.
        locked (PMap[EntityID, Locked]): Locked entities (doors, etc.).
        moving (PMap[EntityID, Moving]): Entities with autonomous movement behavior.
        pathfinding (PMap[EntityID, Pathfinding]): Entities with pathfinding behavior.
        portal (PMap[EntityID, Portal]): Teleportation portal components.
        position (PMap[EntityID, Position]): Entity position component map.
        pushable (PMap[EntityID, Pushable]): Entities that can be pushed.
        requirable (PMap[EntityID, Requirable]): Entities that must be collected to win if objective requires it.
        rewardable (PMap[EntityID, Rewardable]): Entities that grant rewards when collected.
        status (PMap[EntityID, Status]): Entity status effect component map.
        prev_position (PMap[EntityID, Position]): Snapshot of positions before movement this step (used by system).
        trail (PMap[Position, PSet[EntityID]]): Mapping of positions to entities that have occupied them (for trail effects).
        damage_hits (PSet[tuple[EntityID, EntityID, int]]): Set of damage events this turn (attacker, target, amount).
        turn (int): Current turn number.
        score (int): Cumulative score.
        turn_limit (int | None): Optional maximum number of turns allowed. When
            set, reaching this number triggers a ``lose`` state unless already
            ``win``. ``None`` disables the limit.
        win (bool): True if objective met.
        lose (bool): True if losing condition met.
        message (str | None): Optional status message for display.
        seed (int | None): Base RNG seed for deterministic rendering or procedural systems.
    """

    # Level
    width: int
    height: int
    move_fn: "MoveFn"
    objective_fn: "ObjectiveFn"

    # Components
    ## Effects
    immunity: PMap[EntityID, Immunity] = pmap()
    phasing: PMap[EntityID, Phasing] = pmap()
    speed: PMap[EntityID, Speed] = pmap()
    time_limit: PMap[EntityID, TimeLimit] = pmap()
    usage_limit: PMap[EntityID, UsageLimit] = pmap()
    ## Properties
    agent: PMap[EntityID, Agent] = pmap()
    appearance: PMap[EntityID, Appearance] = pmap()
    blocking: PMap[EntityID, Blocking] = pmap()
    collectible: PMap[EntityID, Collectible] = pmap()
    collidable: PMap[EntityID, Collidable] = pmap()
    cost: PMap[EntityID, Cost] = pmap()
    damage: PMap[EntityID, Damage] = pmap()
    dead: PMap[EntityID, Dead] = pmap()
    exit: PMap[EntityID, Exit] = pmap()
    health: PMap[EntityID, Health] = pmap()
    inventory: PMap[EntityID, Inventory] = pmap()
    key: PMap[EntityID, Key] = pmap()
    lethal_damage: PMap[EntityID, LethalDamage] = pmap()
    locked: PMap[EntityID, Locked] = pmap()
    moving: PMap[EntityID, Moving] = pmap()
    pathfinding: PMap[EntityID, Pathfinding] = pmap()
    portal: PMap[EntityID, Portal] = pmap()
    position: PMap[EntityID, Position] = pmap()
    pushable: PMap[EntityID, Pushable] = pmap()
    requirable: PMap[EntityID, Requirable] = pmap()
    rewardable: PMap[EntityID, Rewardable] = pmap()
    status: PMap[EntityID, Status] = pmap()
    ## Extra
    prev_position: PMap[EntityID, Position] = pmap()
    trail: PMap[Position, PSet[EntityID]] = pmap()
    damage_hits: PSet[tuple[EntityID, EntityID, int]] = pset()

    # Status
    turn: int = 0
    score: int = 0
    win: bool = False
    lose: bool = False
    message: Optional[str] = None
    turn_limit: Optional[int] = None

    # RNG
    seed: Optional[int] = None

    @property
    def description(self) -> PMap[str, Any]:
        """
        Generates a persistent map describing the state's attributes.
        This includes all fields except for empty persistent maps.

        Returns:
            PMap[str, Any]: Persistent map of state attributes and their values.
        """
        description: PMap[str, Any] = pmap()
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            # Skip empty persistent maps to keep output concise. We use a duck
            # type check because mypy cannot infer concrete key/value types for
            # every store here; failing len() should just include the value.
            if isinstance(value, type(pmap())):
                try:  # pragma: no cover - defensive
                    if len(value) == 0:  # pyright: ignore[reportUnknownArgumentType]
                        continue
                except Exception:
                    pass
            description = description.set(field, value)
        return pmap(description)
