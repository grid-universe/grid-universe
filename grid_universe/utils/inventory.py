"""Inventory manipulation helpers."""

from collections.abc import Mapping
from grid_universe.components import Inventory, Key
from grid_universe.types import EntityID


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
) -> set[EntityID]:
    """Return all key IDs matching ``key_id``."""
    return {
        item_id
        for item_id in inventory.item_ids
        if (k := key_store.get(item_id)) and k.key_id == key_id
    }
