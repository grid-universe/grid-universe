"""Conversion utilities between mutable ``Level``/``Entity`` and runtime ``State``.

Two primary operations:

* ``to_state``: Materialize immutable ECS world from a grid of ``Entity``.
* ``from_state``: Reconstruct a mutable ``Level``/``Entity`` representation from a runtime state.

Handles wiring of portals, pathfinding targets, inventory & status effect
embedding (nested lists -> separate entities), and assigns deterministic
EntityIDs.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

from pyrsistent import pmap, pset

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components.properties import (
    Position as PositionComp,
    Inventory,
    Status,
    Pathfinding,
    PathfindingType,
    Portal,
)
from grid_universe.levels.grid import Level, Position
from grid_universe.levels.entity import Entity, COMPONENT_TO_FIELD


def _init_store_maps() -> Dict[str, Dict[EntityID, Any]]:
    """
    Initialize mutable component-store maps mirroring State; converted to pmaps later.
    """
    return {
        # effects
        "immunity": {},
        "phasing": {},
        "speed": {},
        "time_limit": {},
        "usage_limit": {},
        # properties
        "agent": {},
        "appearance": {},
        "blocking": {},
        "collectible": {},
        "collidable": {},
        "cost": {},
        "damage": {},
        "dead": {},
        "exit": {},
        "health": {},
        "inventory": {},  # Inventory component map
        "key": {},
        "lethal_damage": {},
        "locked": {},
        "moving": {},
        "pathfinding": {},
        "portal": {},
        "position": {},
        "pushable": {},
        "requirable": {},
        "rewardable": {},
        "status": {},  # Status component map
    }


def _alloc_from_obj(
    obj: Entity,
    stores: Dict[str, Dict[EntityID, Any]],
    next_eid_ref: List[int],
    place_pos: Optional[Position] = None,
) -> EntityID:
    """
    Allocate a new EntityID, create Entity(), copy present components from obj, and optionally set Position.

    - obj: mutable level Entity
    - stores: store_name -> {eid: component}
    - next_eid_ref: single-item list acting as a mutable counter
    - place_pos: (x, y) to create a Position component; None for off-grid entities
    """
    eid: EntityID = next_eid_ref[0]
    next_eid_ref[0] += 1

    # Copy ECS components present on the object (includes Inventory/Status if provided)
    for store_name, comp in obj.iter_components():
        stores[store_name][eid] = comp

    if place_pos is not None:
        x, y = place_pos
        stores["position"][eid] = PositionComp(x, y)

    return eid


def _build_state(level: Level, stores: Dict[str, Dict[EntityID, Any]]) -> State:
    """
    Convert mutable dict stores to pyrsistent maps and construct immutable State.
    """
    return State(
        width=level.width,
        height=level.height,
        move_fn=level.move_fn,
        objective_fn=level.objective_fn,
        # effects
        immunity=pmap(stores["immunity"]),
        phasing=pmap(stores["phasing"]),
        speed=pmap(stores["speed"]),
        time_limit=pmap(stores["time_limit"]),
        usage_limit=pmap(stores["usage_limit"]),
        # properties
        agent=pmap(stores["agent"]),
        appearance=pmap(stores["appearance"]),
        blocking=pmap(stores["blocking"]),
        collectible=pmap(stores["collectible"]),
        collidable=pmap(stores["collidable"]),
        cost=pmap(stores["cost"]),
        damage=pmap(stores["damage"]),
        dead=pmap(stores["dead"]),
        exit=pmap(stores["exit"]),
        health=pmap(stores["health"]),
        inventory=pmap(stores["inventory"]),
        key=pmap(stores["key"]),
        lethal_damage=pmap(stores["lethal_damage"]),
        locked=pmap(stores["locked"]),
        moving=pmap(stores["moving"]),
        pathfinding=pmap(stores["pathfinding"]),
        portal=pmap(stores["portal"]),
        position=pmap(stores["position"]),
        pushable=pmap(stores["pushable"]),
        requirable=pmap(stores["requirable"]),
        rewardable=pmap(stores["rewardable"]),
        status=pmap(stores["status"]),
        # extras
        prev_position=pmap({}),
        trail=pmap({}),
        # meta
        turn=level.turn,
        score=level.score,
        win=level.win,
        lose=level.lose,
        message=level.message,
        turn_limit=level.turn_limit,
        seed=level.seed,
    )


def to_state(level: Level) -> State:
    """
    Convert a Level (grid of Entity objects) into an immutable State.

    Semantics:
        - Copies all present ECS components from each Entity (including Inventory, Status) onto a new entity id.
    - Assigns Position for on-grid entities; nested inventory/effect entities have no Position.
        - Materializes nested lists:
                * inventory_list: each item Entity becomes a new entity; its id is added to holder's Inventory.item_ids.
          If holder lacks an Inventory component, an empty one is created.
                * status_list: each effect Entity becomes a new entity; its id is added to holder's Status.effect_ids.
          If holder lacks a Status component, an empty one is created.
    - Wiring:
        * pathfind_target_ref: if set and the referenced object is placed, sets Pathfinding.target to that eid,
          creating a Pathfinding component if missing (type defaults to PathfindingType.PATH or uses obj.pathfinding_type).
        * portal_pair_ref: if set (on-grid for both ends), sets reciprocal Portal.pair_entity.
    """
    stores: Dict[str, Dict[EntityID, Any]] = _init_store_maps()
    next_eid_ref: List[int] = [0]

    # source object -> eid for on-grid objects
    obj_to_eid: Dict[int, EntityID] = {}
    placed: List[Tuple[Entity, EntityID]] = []

    for y in range(level.height):
        for x in range(level.width):
            for obj in level.grid[y][x]:
                eid = _alloc_from_obj(obj, stores, next_eid_ref, place_pos=(x, y))
                obj_to_eid[id(obj)] = eid
                placed.append((obj, eid))

                # Merge/ensure Inventory from component and/or nested list
                if obj.inventory_list:
                    base_inv: Inventory = stores["inventory"].get(
                        eid,
                        obj.inventory
                        if obj.inventory is not None
                        else Inventory(pset()),
                    )
                    item_ids: List[EntityID] = [
                        _alloc_from_obj(item, stores, next_eid_ref, place_pos=None)
                        for item in obj.inventory_list
                    ]
                    stores["inventory"][eid] = Inventory(
                        item_ids=base_inv.item_ids.update(item_ids)
                    )
                elif obj.inventory is not None and eid not in stores["inventory"]:
                    stores["inventory"][eid] = obj.inventory

                # Merge/ensure Status from component and/or nested list
                if obj.status_list:
                    base_status: Status = stores["status"].get(
                        eid, obj.status if obj.status is not None else Status(pset())
                    )
                    eff_ids: List[EntityID] = [
                        _alloc_from_obj(eff, stores, next_eid_ref, place_pos=None)
                        for eff in obj.status_list
                    ]
                    stores["status"][eid] = Status(
                        effect_ids=base_status.effect_ids.update(eff_ids)
                    )
                elif obj.status is not None and eid not in stores["status"]:
                    stores["status"][eid] = obj.status

    # Build immutable State before wiring
    state: State = _build_state(level, stores)

    # Wiring: pathfinding target references
    sp = state.pathfinding
    pf_changed = False
    for obj, eid in placed:
        tgt = obj.pathfind_target_ref
        if tgt is None:
            continue
        tgt_eid = obj_to_eid.get(id(tgt))
        if tgt_eid is None:
            continue
        desired_type: PathfindingType = obj.pathfinding_type or PathfindingType.PATH
        current = sp.get(eid)
        if current is None:
            sp = sp.set(eid, Pathfinding(target=tgt_eid, type=desired_type))
            pf_changed = True
        elif current.target is None:
            sp = sp.set(eid, Pathfinding(target=tgt_eid, type=current.type))
            pf_changed = True
    if pf_changed:
        state = replace(state, pathfinding=sp)

    # Wiring: portal pair references (bidirectional)
    spr = state.portal
    portal_changed = False
    for obj, eid in placed:
        mate = obj.portal_pair_ref
        if mate is None:
            continue
        mate_eid = obj_to_eid.get(id(mate))
        if mate_eid is None:
            continue
        spr = spr.set(eid, Portal(pair_entity=mate_eid))
        spr = spr.set(mate_eid, Portal(pair_entity=eid))
        portal_changed = True
    if portal_changed:
        state = replace(state, portal=spr)

    return state


def _entity_object_from_state(state: State, eid: EntityID) -> Entity:
    """
    Reconstruct a mutable level `grid_universe.levels.entity.Entity` from a State entity id.

    Inventory and Status components (if present) are copied. Nested collections
    (``inventory_list`` / ``status_list``) are initialized empty here.
    """
    kwargs: Dict[str, Any] = {}
    for _, store_name in COMPONENT_TO_FIELD.items():
        store = getattr(state, store_name)
        kwargs[store_name] = store.get(eid)
    # Nested lists start empty; caller may populate from Inventory/Status sets.
    kwargs["inventory_list"] = []
    kwargs["status_list"] = []
    return Entity(**kwargs)


def from_state(state: State) -> Level:
    """
    Convert an immutable State back into a mutable Level (grid of Entity objects).

    Behavior:
    - Positioned entities are placed into `Level.grid[y][x]` in ascending eid order (deterministic).
        - Entity components (including Inventory/Status) are reconstructed for positioned entities.
    - Holder inventory_list/status_list are rebuilt from Inventory.item_ids / Status.effect_ids
            by reconstructing item/effect entities (not placed on the grid).
        - Reference fields (pathfind_target_ref, portal_pair_ref) are restored for positioned entities
            when their targets/pairs are themselves positioned.
    """
    level = Level(
        width=state.width,
        height=state.height,
        move_fn=state.move_fn,
        objective_fn=state.objective_fn,
        seed=state.seed,
        turn=state.turn,
        score=state.score,
        turn_limit=state.turn_limit,
        win=state.win,
        lose=state.lose,
        message=state.message,
    )

    # eid -> positioned Entity
    placed_objs: Dict[EntityID, Entity] = {}

    # Place entities on the grid
    for eid in sorted(state.position.keys()):
        pos = state.position.get(eid)
        if pos is None:
            continue
        x, y = pos.x, pos.y
        if not (0 <= x < level.width and 0 <= y < level.height):
            continue
        obj = _entity_object_from_state(state, eid)
        placed_objs[eid] = obj
        level.grid[y][x].append(obj)

    # Rebuild nested lists from Inventory/Status sets
    for holder_eid, holder_obj in placed_objs.items():
        inv = state.inventory.get(holder_eid)
        if inv is not None and getattr(inv, "item_ids", None) is not None:
            for item_eid in inv.item_ids:
                holder_obj.inventory_list.append(
                    _entity_object_from_state(state, item_eid)
                )
            holder_obj.inventory = Inventory(pset())

        st = state.status.get(holder_eid)
        if st is not None and getattr(st, "effect_ids", None) is not None:
            for eff_eid in st.effect_ids:
                holder_obj.status_list.append(_entity_object_from_state(state, eff_eid))
            holder_obj.status = Status(pset())

    # Restore reference fields for positioned entities
    for eid, obj in placed_objs.items():
        # Pathfinding ref
        pf = state.pathfinding.get(eid)
        if pf is not None and pf.target is not None:
            tgt_obj = placed_objs.get(pf.target)
            if tgt_obj is not None:
                obj.pathfind_target_ref = tgt_obj
                obj.pathfinding_type = pf.type
            obj.pathfinding = None

        # Portal pair ref (bidirectional)
        pr = state.portal.get(eid)
        if pr is not None:
            mate_obj = placed_objs.get(pr.pair_entity)
            if mate_obj is not None:
                obj.portal_pair_ref = mate_obj
                # Set reciprocal if not already set
                if mate_obj.portal_pair_ref is None:
                    mate_obj.portal_pair_ref = obj
            obj.portal = Portal(pair_entity=-1)

    return level
