from dataclasses import dataclass

from grid_universe.types import EntityID


@dataclass(frozen=True)
class Status:
    """
    Status effect component.

    Attributes:
        effect_ids: Set of EntityIDs representing status effects applied to the entity.
    """

    effect_ids: set[EntityID]
