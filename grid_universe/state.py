"""Core immutable ECS `State` dataclass.

This module defines the frozen :class:`State` object that represents the
entire game / simulation snapshot at a single turn. All systems are pure
functions that take a previous ``State`` plus inputs (e.g. an ``Action``) and
return a *new* ``State``; no mutation happens in-place. This makes the engine
deterministic, easy to test, and friendly to functional style reducers.

Design notes:

* Component stores are **persistent maps** (``pyrsistent.PMap``) keyed by
    ``EntityID``. Absence of a key means the entity does not currently possess
    that component.
* Effect components (Immunity, Phasing, Speed, TimeLimit, UsageLimit) are
    referenced by :class:`grid_universe.components.properties.Status` which
    holds ordered ``effect_ids``. Several systems (status tick, GC) walk those
    references.
* The ``prev_position`` and ``trail`` auxiliary stores are populated by
    dedicated systems to enable path‑based effects (e.g. trail rendering or
    damage-on-cross mechanics).
* ``win`` / ``lose`` flags are mutually exclusive terminal markers. The
    reducer short‑circuits on terminal states.

Google‑style docstrings throughout the codebase refer back to this structure;
see :mod:`grid_universe.step` for how the reducer orchestrates systems.
"""

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
    Required,
    Rewardable,
    Status,
)
from grid_universe.types import EntityID, MoveFn, ObjectiveFn


@dataclass(frozen=True)
class State:
    """Immutable ECS world state.

    Instances are *value objects*; every transition creates a new ``State``.
    Only include persistent / serializable data here (no open handles or
    caches). Systems should be pure functions that accept and return ``State``.

    Attributes:
        width (int): Grid width in tiles.
        height (int): Grid height in tiles.
        move_fn (MoveFn): Movement candidate function used to resolve move actions.
        objective_fn (ObjectiveFn): Predicate evaluated after each step to set ``win``.
        immunity (PMap[EntityID, Immunity]): Effect component map.
        phasing (PMap[EntityID, Phasing]): Effect component map.
        speed (PMap[EntityID, Speed]): Effect component map.
        time_limit (PMap[EntityID, TimeLimit]): Effect limiter map (remaining steps).
        usage_limit (PMap[EntityID, UsageLimit]): Effect limiter map (remaining uses).
        agent (PMap[EntityID, Agent]): Player / AI controllable entity marker components.
        appearance (PMap[EntityID, Appearance]): Rendering metadata (glyph, layering, groups).
        blocking (PMap[EntityID, Blocking]): Entities that prevent movement into their tile.
        collectible (PMap[EntityID, Collectible]): Items that can be picked up.
        collidable (PMap[EntityID, Collidable]): Entities that can collide (triggering damage, cost, etc.).
        cost (PMap[EntityID, Cost]): Movement or interaction cost applied when entered.
        damage (PMap[EntityID, Damage]): Passive damage applied on collision / contact.
        dead (PMap[EntityID, Dead]): Marker for logically removed entities (awaiting GC).
        exit (PMap[EntityID, Exit]): Tiles that can satisfy the objective when conditions met.
        health (PMap[EntityID, Health]): Health pools for damage / lethal checks.
        inventory (PMap[EntityID, Inventory]): Item/key collections carried by entities.
        key (PMap[EntityID, Key]): Keys that can unlock ``Locked`` components.
        lethal_damage (PMap[EntityID, LethalDamage]): Immediate kill damage sources (pits, hazards).
        locked (PMap[EntityID, Locked]): Lock descriptors requiring matching keys.
        moving (PMap[EntityID, Moving]): Entities currently undergoing movement (inter-step state).
        pathfinding (PMap[EntityID, Pathfinding]): Agents with pathfinding goals and cached paths.
        portal (PMap[EntityID, Portal]): Teleport endpoints / pairs.
        position (PMap[EntityID, Position]): Current grid position of entities.
        pushable (PMap[EntityID, Pushable]): Entities that can be displaced by push actions.
        required (PMap[EntityID, Required]): Items/conditions needed to satisfy collect and default objectives.
        rewardable (PMap[EntityID, Rewardable]): Components conferring score rewards when collected or triggered.
        status (PMap[EntityID, Status]): Ordered list container referencing effect component ids.
        prev_position (PMap[EntityID, Position]): Snapshot of positions before movement this step.
        trail (PMap[Position, PSet[EntityID]]): Positions traversed this step mapped to entity ids.
        turn (int): Turn counter (0-based).
        score (int): Accumulated score.
        turn_limit (int | None): Optional maximum number of turns allowed. When
            set, reaching this number triggers a ``lose`` state unless already
            ``win``. ``None`` disables the limit.
        win (bool): True if objective met.
        lose (bool): True if losing condition met.
        message (str | None): Optional informational / terminal message.
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
    required: PMap[EntityID, Required] = pmap()
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
        """Sparse serialization of non‑empty fields.

        Iterates dataclass fields and returns a persistent map including only
        those that are non‑empty (for component maps) or truthy (for scalars).
        Useful for lightweight diagnostics / debugging without dumping large
        empty maps.

        Returns:
            PMap[str, Any]: Persistent map of field name to value for all
            populated fields.
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
