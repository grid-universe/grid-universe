from grid_universe.components import Inventory, Key
from grid_universe.utils.inventory import has_key_with_id, all_keys_with_id
from grid_universe.types import EntityID


def test_add_and_remove_item() -> None:
    inv = Inventory(item_ids=set())
    key_id: EntityID = 101
    inv2 = Inventory(item_ids=inv.item_ids | {key_id})
    assert key_id in inv2.item_ids
    inv3 = Inventory(item_ids=inv2.item_ids - {key_id})
    assert key_id not in inv3.item_ids


def test_has_key_with_id() -> None:
    k1: EntityID = 1
    k2: EntityID = 2
    k3: EntityID = 3
    key_store = {k1: Key(key_id="red"), k2: Key(key_id="blue"), k3: Key(key_id="red")}
    inv = Inventory(item_ids=set([k1, k2]))
    assert has_key_with_id(inv, key_store, "red") == k1
    assert has_key_with_id(inv, key_store, "blue") == k2
    assert has_key_with_id(inv, key_store, "green") is None


def test_all_keys_with_id() -> None:
    k1: EntityID = 1
    k2: EntityID = 2
    k3: EntityID = 3
    key_store = {k1: Key(key_id="red"), k2: Key(key_id="red"), k3: Key(key_id="blue")}
    inv = Inventory(item_ids=set([k1, k2, k3]))
    red_keys = all_keys_with_id(inv, key_store, "red")
    blue_keys = all_keys_with_id(inv, key_store, "blue")
    assert red_keys == set([k1, k2])
    assert blue_keys == set([k3])
    assert all_keys_with_id(inv, key_store, "green") == set()
