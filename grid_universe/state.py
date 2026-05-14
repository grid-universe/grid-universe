from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, TYPE_CHECKING

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
from grid_universe.types import EntityID
from grid_universe.utils.ecs import PositionIndex, build_position_index

if TYPE_CHECKING:
    from grid_universe.objectives import BaseObjective
    from grid_universe.movements import BaseMovement


@dataclass
class State:
    """ECS world state.

    Attributes:
        width (int): Grid width in tiles.
        height (int): Grid height in tiles.
        movement (BaseMovement): Movement function configuration.
        objective (BaseObjective): Objective configuration.
        immunity: Effect component store.
        phasing: Effect component store.
        speed: Effect component store.
        time_limit: Effect limiter store (remaining steps).
        usage_limit: Effect limiter store (remaining uses).
        agent: Agent component store.
        appearance: Visual appearance component store.
        blocking: Obstacles that block movement.
        collectible: Entities that can be collected.
        collidable: Entities that can collide.
        cost: Entities that inflict movement cost.
        damage: Entities that inflict damage on contact.
        dead: Entities that are dead/incapacitated.
        exit: Exit components.
        health: Entity health component store.
        inventory: Agent inventory component store.
        key: Keys that can unlock ``Locked`` components.
        lethal_damage: Entities that inflict instant death on contact.
        locked: Locked entities.
        moving: Entities with autonomous movement behavior.
        pathfinding: Entities with pathfinding behavior.
        portal: Teleportation portal components.
        position: Entity position component store.
        pushable: Entities that can be pushed.
        requirable: Entities that must be collected to win if objective requires it.
        rewardable: Entities that grant rewards when collected.
        status: Entity status effect component store.
        step_cost (int): Base score cost applied once per action step.
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
    movement: BaseMovement
    objective: BaseObjective

    # Components
    ## Effects
    immunity: dict[EntityID, Immunity] = field(default_factory=dict)
    phasing: dict[EntityID, Phasing] = field(default_factory=dict)
    speed: dict[EntityID, Speed] = field(default_factory=dict)
    time_limit: dict[EntityID, TimeLimit] = field(default_factory=dict)
    usage_limit: dict[EntityID, UsageLimit] = field(default_factory=dict)
    ## Properties
    agent: dict[EntityID, Agent] = field(default_factory=dict)
    appearance: dict[EntityID, Appearance] = field(default_factory=dict)
    blocking: dict[EntityID, Blocking] = field(default_factory=dict)
    collectible: dict[EntityID, Collectible] = field(default_factory=dict)
    collidable: dict[EntityID, Collidable] = field(default_factory=dict)
    cost: dict[EntityID, Cost] = field(default_factory=dict)
    damage: dict[EntityID, Damage] = field(default_factory=dict)
    dead: dict[EntityID, Dead] = field(default_factory=dict)
    exit: dict[EntityID, Exit] = field(default_factory=dict)
    health: dict[EntityID, Health] = field(default_factory=dict)
    inventory: dict[EntityID, Inventory] = field(default_factory=dict)
    key: dict[EntityID, Key] = field(default_factory=dict)
    lethal_damage: dict[EntityID, LethalDamage] = field(default_factory=dict)
    locked: dict[EntityID, Locked] = field(default_factory=dict)
    moving: dict[EntityID, Moving] = field(default_factory=dict)
    pathfinding: dict[EntityID, Pathfinding] = field(default_factory=dict)
    portal: dict[EntityID, Portal] = field(default_factory=dict)
    position: dict[EntityID, Position] = field(default_factory=dict)
    pushable: dict[EntityID, Pushable] = field(default_factory=dict)
    requirable: dict[EntityID, Requirable] = field(default_factory=dict)
    rewardable: dict[EntityID, Rewardable] = field(default_factory=dict)
    status: dict[EntityID, Status] = field(default_factory=dict)

    # Status
    step_cost: int = 0
    turn: int = 0
    score: int = 0
    win: bool = False
    lose: bool = False
    message: str | None = None
    turn_limit: int | None = None

    # RNG
    seed: int | None = None
    _position_index: PositionIndex = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self._position_index = build_position_index(self.position)

    def clone(self) -> State:
        cloned_fields: dict[str, Any] = {}
        for state_field in fields(self):
            name = state_field.name
            if name.startswith("_"):
                continue
            value = getattr(self, name)
            if name == "inventory":
                cloned_fields[name] = {
                    entity_id: Inventory(set(inventory.item_ids))
                    for entity_id, inventory in self.inventory.items()
                }
            elif name == "status":
                cloned_fields[name] = {
                    entity_id: Status(set(status.effect_ids))
                    for entity_id, status in self.status.items()
                }
            elif isinstance(value, dict):
                cloned_fields[name] = dict(value)
            else:
                cloned_fields[name] = value
        return State(**cloned_fields)

    @property
    def description(self) -> dict[str, Any]:
        """
        Generates a map describing the state's attributes.
        This includes all fields except empty component stores.

        Returns:
            dict[str, Any]: Map of state attributes and their values.
        """
        description: dict[str, Any] = {}
        for state_field in fields(self):
            name = state_field.name
            if name.startswith("_"):
                continue
            value = getattr(self, name)
            if isinstance(value, dict) and not value:
                continue
            description[name] = value
        return description
