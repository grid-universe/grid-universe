from dataclasses import dataclass
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap, PSet
from grid_universe.components import Position
from grid_universe.components.properties.status import Status
from grid_universe.types import EntityID


@dataclass(frozen=True)
class StepContext:
    """Contextual data for the current step.

    Attributes:
        prev_position (PMap[EntityID, Position]): Snapshot of positions before movement this step.
        prev_status (PMap[EntityID, Status]): Snapshot of statuses at the beginning of the step.
        trail (PMap[Position, PSet[EntityID]]): Mapping of positions to entities that have occupied them (for trail effects).
        damage_hits (PSet[tuple[EntityID, EntityID, int]]): Set of damage events this turn (target, damager, turn).
    """

    prev_position: PMap[EntityID, Position] = pmap()
    prev_status: PMap[EntityID, Status] = pmap()
    trail: PMap[Position, PSet[EntityID]] = pmap()
    damage_hits: PSet[tuple[EntityID, EntityID, int]] = pset()
