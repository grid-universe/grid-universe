"""Inventory manipulation helpers."""

from collections.abc import Mapping
from pyrsistent import PSet, pset
from grid_universe.components import Inventory, Key
from grid_universe.types import EntityID


def add_item(inventory: Inventory, item_id: EntityID) -> Inventory:
    """Return a new inventory with ``item_id`` added."""
    return Inventory(item_ids=inventory.item_ids.add(item_id))


def remove_item(inventory: Inventory, item_id: EntityID) -> Inventory:
    """Return a new inventory with ``item_id`` removed."""
    return Inventory(item_ids=inventory.item_ids.remove(item_id))


def has_key_with_id(
    inventory: Inventory, key_store: Mapping[EntityID, Key], key_id: str
) -> EntityID | None:
    """Return ID of a key with ``key_id`` if present in inventory else None."""
    for item_id in inventory.item_ids:
        key = key_store.get(item_id)
        if key and key.key_id == key_id:
            return item_id
    return None


def all_keys_with_id(
    inventory: Inventory, key_store: Mapping[EntityID, Key], key_id: str
) -> PSet[EntityID]:
    """Return persistent set of all key IDs matching ``key_id``."""
    return pset(
        item_id
        for item_id in inventory.item_ids
        if (k := key_store.get(item_id)) and k.key_id == key_id
    )
