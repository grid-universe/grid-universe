from dataclasses import dataclass

from grid_universe.types import EntityID


@dataclass(frozen=True)
class Inventory:
    """
    Inventory component.

    Attributes:
        item_ids: Set of EntityIDs representing items in the inventory.
    """

    item_ids: set[EntityID]
