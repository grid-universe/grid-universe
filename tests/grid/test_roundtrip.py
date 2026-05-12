from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple, Mapping, Sequence, cast


from grid_universe.movements import BaseMovement
from grid_universe.objectives import BaseObjective
from grid_universe.grid.gridstate import GridState
from grid_universe.grid.convert import to_state, from_state
from grid_universe.grid.entity import BaseEntity, Entity, FIELD_TO_COMPONENT
from grid_universe.grid.factories import (
    create_agent,
    create_coin,
    create_core,
    create_key,
    create_door,
    create_portal,
    create_monster,
    create_wall,
    create_speed_effect,
)
from grid_universe.components.properties import PathfindingType


# ---------- Helpers: Canonicalization ----------


def _obj_component_signature(obj: BaseEntity) -> Dict[str, Any]:
    """
    Capture an Entity's components (excluding GridState-only nested lists/refs) as a dict.
    """
    sig: Dict[str, Any] = {}
    for store_name, _ in FIELD_TO_COMPONENT.items():
        comp = getattr(obj, store_name, None)
        if comp is not None:
            sig[store_name] = asdict(comp)
    return sig


def _obj_nested_signature(objs: Sequence[BaseEntity]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for o in objs:
        out.append(_obj_component_signature(o))
    out.sort(key=lambda d: str(sorted(d.items())))
    return out


def canonicalize_grid_state(
    gridstate: GridState,
) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """
    Build a canonical structure for GridState:
      { (x,y): [ {components: {...}, inventory_list: [...], status_list: [...]}, ... ] }
    Entries are sorted deterministically.
    """
    cells: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for x in range(gridstate.width):
        for y in range(gridstate.height):
            entries: List[Dict[str, Any]] = []
            for obj in gridstate.grid[x][y]:
                entries.append(
                    {
                        "components": _obj_component_signature(obj),
                        "inventory_list": _obj_nested_signature(obj.inventory_list),
                        "status_list": _obj_nested_signature(obj.status_list),
                    }
                )
            entries.sort(
                key=lambda e: (
                    str(sorted(e["components"].items())),
                    str(e["inventory_list"]),
                    str(e["status_list"]),
                )
            )
            if entries:
                cells[(x, y)] = entries
    return cells


def _stable_sig(value: Any) -> Any:
    if isinstance(value, Mapping):
        items = cast(Mapping[Any, Any], value).items()
        return tuple((k, _stable_sig(v)) for k, v in sorted(items))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        seq = cast(Sequence[Any], value)
        return tuple(_stable_sig(v) for v in seq)
    return value


def collect_gridstate_entity_id_map(
    gridstate: GridState,
) -> Dict[Tuple[Any, ...], List[int]]:
    """
    Collect entity_id values keyed by a stable signature so we can verify preservation.
    Keys include position, component signature, nested signatures, and reference targets.
    """
    obj_pos: Dict[int, Tuple[int, int]] = {}
    for x in range(gridstate.width):
        for y in range(gridstate.height):
            for obj in gridstate.grid[x][y]:
                obj_pos[id(obj)] = (x, y)

    ids_by_key: Dict[Tuple[Any, ...], List[int]] = {}

    for x in range(gridstate.width):
        for y in range(gridstate.height):
            for obj in gridstate.grid[x][y]:
                ref_target = getattr(obj, "pathfind_target_ref", None)
                ref_portal = getattr(obj, "portal_pair_ref", None)
                tgt_pos = (
                    obj_pos.get(id(ref_target)) if ref_target is not None else None
                )
                portal_pos = (
                    obj_pos.get(id(ref_portal)) if ref_portal is not None else None
                )

                nested_map = {name: items for name, items in obj.iter_nested_objects()}
                inv_list = nested_map.get("inventory_list", [])
                status_list = nested_map.get("status_list", [])

                comp_sig = _stable_sig(_obj_component_signature(obj))
                inv_sig = _stable_sig(_obj_nested_signature(inv_list))
                status_sig = _stable_sig(_obj_nested_signature(status_list))

                key = (
                    "placed",
                    (x, y),
                    comp_sig,
                    inv_sig,
                    status_sig,
                    tgt_pos,
                    portal_pos,
                )
                if obj.entity_id is not None:
                    ids_by_key.setdefault(key, []).append(obj.entity_id)

                for list_name, nested in obj.iter_nested_objects():
                    for child in nested:
                        child_key = (
                            "nested",
                            (x, y),
                            comp_sig,
                            list_name,
                            _stable_sig(_obj_component_signature(child)),
                        )
                        if child.entity_id is not None:
                            ids_by_key.setdefault(child_key, []).append(child.entity_id)

    for key in ids_by_key:
        ids_by_key[key].sort()
    return ids_by_key


def _state_entity_component_signature(state: Any, eid: int) -> Dict[str, Any]:
    """
    Capture non-ID-bearing components of an entity as a plain dict. Excludes Position,
    Inventory, Status. Encodes pathfinding target by target position and portal pair by pair position.
    """
    sig: Dict[str, Any] = {}

    # Basic components
    for store_name, _ in FIELD_TO_COMPONENT.items():
        if store_name in ("inventory", "status", "pathfinding", "portal"):
            continue
        store = getattr(state, store_name)
        comp = store.get(eid)
        if comp is not None:
            sig[store_name] = asdict(comp)

    # Pathfinding: encode type and target by target Position (if positioned)
    pf = state.pathfinding.get(eid)
    if pf is not None:
        tgt_pos: Optional[Tuple[int, int]] = None
        if pf.target is not None and pf.target in state.position:
            p = state.position.get(pf.target)
            if p is not None:
                tgt_pos = (p.x, p.y)
        sig["pathfinding"] = {"type": pf.type.name, "target_pos": tgt_pos}

    # Portal: encode pair by pair position (if positioned)
    pr = state.portal.get(eid)
    if pr is not None:
        pair_pos: Optional[Tuple[int, int]] = None
        if pr.pair_entity in state.position:
            pp = state.position.get(pr.pair_entity)
            if pp is not None:
                pair_pos = (pp.x, pp.y)
        sig["portal"] = {"pair_pos": pair_pos}

    return sig


def _state_nested_signatures(state: Any, ids: List[int]) -> List[Dict[str, Any]]:
    """
    Signature for nested entities (inventory items or status effects), which have no Position.
    """
    out: List[Dict[str, Any]] = []
    for nid in sorted(ids):
        out.append(_state_entity_component_signature(state, nid))
    return out


def canonicalize_state(state: Any) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """
    Build a canonical, comparable structure for State:
      { (x,y): [ {components: {...}, inventory: [...], status: [...]}, ... ] }
    Inventory/status entries are nested component dicts for each referenced entity.
    """
    cells: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

    inv_map: Dict[int, List[int]] = {
        eid: sorted(list(inv.item_ids)) for eid, inv in state.inventory.items()
    }
    st_map: Dict[int, List[int]] = {
        eid: sorted(list(st.effect_ids)) for eid, st in state.status.items()
    }

    for eid, pos in state.position.items():
        key = (pos.x, pos.y)
        comp_sig = _state_entity_component_signature(state, eid)
        inv_sig = _state_nested_signatures(state, inv_map.get(eid, []))
        st_sig = _state_nested_signatures(state, st_map.get(eid, []))
        entry = {"components": comp_sig, "inventory": inv_sig, "status": st_sig}
        cells.setdefault(key, []).append(entry)

    for key in cells:
        cells[key].sort(
            key=lambda e: (
                str(sorted(e["components"].items())),
                str(e["inventory"]),
                str(e["status"]),
            )
        )
    return cells


# ---------- Test fixtures ----------


def build_sample_grid_state() -> GridState:
    """
    Build a GridState that exercises:
    - agent with empty Inventory/Status components and nested lists
    - items/effects in inventory_list/status_list
    - portals paired by reference
    - monster pathfinding to agent by reference
    - some walls
    """
    lvl = GridState(
        width=7,
        height=5,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, e, a: []
        ),
        objective=BaseObjective(
            name="test", description="Test", functions=(lambda s, a, ctx: False,)
        ),
        seed=123,
        step_cost=7,
    )

    # Agent at (1,1) with explicit Inventory/Status components and empty nested lists
    agent = create_agent(health=10)
    # Put a key and a speed effect into nested lists (they'll materialize as entities without Position)
    agent.inventory_list.append(create_key("red"))
    agent.status_list.append(create_speed_effect(2, time=5))
    lvl.add((1, 1), agent)

    # Coin and core on ground
    lvl.add((2, 1), create_coin(3))
    lvl.add((3, 1), create_core(5, required=True))

    # Door keyed to red key
    lvl.add((4, 1), create_door("red"))

    # Portals paired by reference
    p1 = create_portal()
    p2 = create_portal(pair=p1)
    lvl.add((0, 0), p1)
    lvl.add((6, 4), p2)

    # Monster pathfinding to agent (PATH)
    mon = create_monster(
        damage=2, lethal=False, pathfind_target=agent, path_type=PathfindingType.PATH
    )
    lvl.add((6, 1), mon)

    # Some walls
    lvl.add((0, 2), create_wall())
    lvl.add((6, 2), create_wall())

    return lvl


# ---------- Tests ----------


def test_level_roundtrip_lossless() -> None:
    """
    GridState -> State -> GridState preserves component structure and nested lists.
    Also verifies wiring refs are restored (pathfinding target, portal pair).
    """
    grid_state1 = build_sample_grid_state()
    state = to_state(grid_state1)
    grid_state2 = from_state(state)

    # Canonical compare
    assert state.step_cost == grid_state1.step_cost
    assert grid_state2.step_cost == grid_state1.step_cost
    can1 = canonicalize_grid_state(grid_state1)
    can2 = canonicalize_grid_state(grid_state2)
    assert can1 == can2, (
        f"GridState roundtrip mismatch.\nOriginal: {can1}\nRoundtrip: {can2}"
    )

    # Entity IDs preserved (by signature)
    id_map1 = collect_gridstate_entity_id_map(grid_state1)
    id_map2 = collect_gridstate_entity_id_map(grid_state2)
    assert id_map1 == id_map2, (
        f"GridState entity_id roundtrip mismatch.\nOriginal: {id_map1}\nRoundtrip: {id_map2}"
    )

    # Wiring refs: find agent and monster, ensure monster.target_ref is agent
    # Also ensure portals are paired by portal_pair_ref bidirectionally
    agent_obj = None
    monster_obj = None
    portal_objs: List[Entity] = []
    for x in range(grid_state2.width):
        for y in range(grid_state2.height):
            for obj in grid_state2.grid[x][y]:
                if obj.agent is not None:
                    agent_obj = obj
                if (
                    obj.damage is not None
                    and obj.appearance
                    and obj.appearance.name == "monster"
                ):
                    monster_obj = obj
                if obj.portal is not None:
                    portal_objs.append(obj)
    assert agent_obj is not None and monster_obj is not None
    assert monster_obj.pathfind_target_ref is agent_obj
    # portals should be paired
    assert len(portal_objs) == 2
    a, b = portal_objs
    assert a.portal_pair_ref is b and b.portal_pair_ref is a


def test_state_roundtrip_lossless() -> None:
    """
    State -> GridState -> State preserves positioned entities, nested inventory/status entities,
    and pathfinding/portal semantics (compared canonically by positions).
    """
    gridstate = build_sample_grid_state()
    state1 = to_state(gridstate)
    grid_state2 = from_state(state1)
    state2 = to_state(grid_state2)

    can1 = canonicalize_state(state1)
    can2 = canonicalize_state(state2)
    assert can1 == can2, (
        f"State roundtrip mismatch.\nOriginal: {can1}\nRoundtrip: {can2}"
    )

    # Entity IDs preserved through State -> GridState -> State (by signature)
    id_map1 = collect_gridstate_entity_id_map(from_state(state1))
    id_map2 = collect_gridstate_entity_id_map(from_state(state2))
    assert id_map1 == id_map2, (
        f"State entity_id roundtrip mismatch.\nOriginal: {id_map1}\nRoundtrip: {id_map2}"
    )
