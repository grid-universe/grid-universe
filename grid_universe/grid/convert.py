"""Conversion utilities between ``GridState`` and ``State``.

GridState and State are complementary representations of game state:

- **GridState**: Mutable, grid-centric, ideal for authoring and editing
- **State**: Immutable, ECS-based, optimized for simulation and stepping

Two primary operations:

* ``to_state``: Build immutable ECS State from a GridState with grid-based entities.
* ``from_state``: Build mutable GridState from an ECS State for editing/inspection.

Handles wiring of portals, pathfinding targets, inventory & status effect
embedding (nested lists -> separate entities), and assigns deterministic
EntityIDs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

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
from grid_universe.grid.gridstate import GridState, Position
from grid_universe.grid.entity import BaseEntity, Entity, FIELD_TO_COMPONENT


def _init_store_maps() -> dict[str, dict[EntityID, Any]]:
    """Initialize mutable component-store maps mirroring State; converted to pmaps later."""
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
        "inventory": {},
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
        "status": {},
    }


def _alloc_from_obj(
    obj: BaseEntity,
    stores: dict[str, dict[EntityID, Any]],
    next_eid_ref: list[int],
    place_pos: Position | None = None,
) -> EntityID:
    """Allocate a new EntityID, copy ECS/effect components from obj, and optionally set Position."""
    eid: EntityID = next_eid_ref[0]
    next_eid_ref[0] += 1

    for store_name, comp in obj.iter_components():
        stores[store_name][eid] = comp

    if place_pos is not None:
        x, y = place_pos
        stores["position"][eid] = PositionComp(x, y)

    return eid


def _build_state(gridstate: GridState, stores: dict[str, dict[EntityID, Any]]) -> State:
    """Convert mutable dict stores to pyrsistent maps and construct immutable State."""
    return State(
        width=gridstate.width,
        height=gridstate.height,
        movement=gridstate.movement,
        objective=gridstate.objective,
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
        # meta
        turn=gridstate.turn,
        score=gridstate.score,
        win=gridstate.win,
        lose=gridstate.lose,
        message=gridstate.message,
        turn_limit=gridstate.turn_limit,
        seed=gridstate.seed,
    )


def to_state(gridstate: GridState) -> State:
    """Convert a GridState (grid of BaseEntity objects) into an immutable State."""
    stores: dict[str, dict[EntityID, Any]] = _init_store_maps()
    next_eid_ref: list[int] = [0]

    # source object -> eid for on-grid objects
    obj_to_eid: dict[int, EntityID] = {}
    placed: list[tuple[BaseEntity, EntityID]] = []

    for y in range(gridstate.height):
        for x in range(gridstate.width):
            for obj in gridstate.grid[y][x]:
                eid = _alloc_from_obj(obj, stores, next_eid_ref, place_pos=(x, y))
                obj_to_eid[id(obj)] = eid
                placed.append((obj, eid))

                # Gather nested lists once
                nested_lists: dict[str, list[BaseEntity]] = {
                    name: items for name, items in obj.iter_nested_objects()
                }

                # Inventory nested items
                if "inventory_list" in nested_lists:
                    base_inv = stores["inventory"].get(eid, Inventory(pset()))
                    item_ids: list[EntityID] = [
                        _alloc_from_obj(item, stores, next_eid_ref, place_pos=None)
                        for item in nested_lists["inventory_list"]
                    ]
                    stores["inventory"][eid] = Inventory(
                        item_ids=base_inv.item_ids.update(item_ids)
                    )

                # Status nested effects
                if "status_list" in nested_lists:
                    base_status = stores["status"].get(eid, Status(pset()))
                    eff_ids: list[EntityID] = [
                        _alloc_from_obj(eff, stores, next_eid_ref, place_pos=None)
                        for eff in nested_lists["status_list"]
                    ]
                    stores["status"][eid] = Status(
                        effect_ids=base_status.effect_ids.update(eff_ids)
                    )

    # Build immutable State before wiring
    state: State = _build_state(gridstate, stores)

    # Wiring: pathfinding target references
    sp = state.pathfinding
    pf_changed = False
    for obj, eid in placed:
        tgt_obj = getattr(obj, "pathfind_target_ref", None)
        if tgt_obj is None:
            continue
        tgt_eid = obj_to_eid.get(id(tgt_obj))
        if tgt_eid is None:
            continue
        desired_type: PathfindingType = (
            getattr(obj, "pathfinding_type", None) or PathfindingType.PATH
        )
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
        mate_obj = getattr(obj, "portal_pair_ref", None)
        if mate_obj is None:
            continue
        mate_eid = obj_to_eid.get(id(mate_obj))
        if mate_eid is None:
            continue
        spr = spr.set(eid, Portal(pair_entity=mate_eid))
        spr = spr.set(mate_eid, Portal(pair_entity=eid))
        portal_changed = True
    if portal_changed:
        state = replace(state, portal=spr)

    return state


def _entity_object_from_state(state: State, eid: EntityID) -> Entity:
    """Reconstruct a generic mutable grid state Entity from a State entity id."""
    kwargs: dict[str, Any] = {}
    for store_name, _ in FIELD_TO_COMPONENT.items():
        store = getattr(state, store_name, None)
        if store is not None and eid in store:
            kwargs[store_name] = store[eid]

    # Rebuild nested lists from Inventory/Status sets
    if (
        eid in state.inventory
        and getattr(state.inventory[eid], "item_ids", None) is not None
    ):
        inventory_list: list[Entity] = [
            _entity_object_from_state(state, item_eid)
            for item_eid in state.inventory[eid].item_ids
        ]
        kwargs["inventory_list"] = inventory_list
        kwargs["inventory"] = Inventory(pset())
    else:
        kwargs["inventory_list"] = []

    if (
        eid in state.status
        and getattr(state.status[eid], "effect_ids", None) is not None
    ):
        status_list: list[Entity] = [
            _entity_object_from_state(state, eff_eid)
            for eff_eid in state.status[eid].effect_ids
        ]
        kwargs["status_list"] = status_list
        kwargs["status"] = Status(pset())
    else:
        kwargs["status_list"] = []

    entity = Entity(**kwargs)
    return entity


def _restore_entity_references(
    state: State,
    eid: EntityID,
    entity: Entity,
    placed_objs: dict[EntityID, Entity],
) -> None:
    """Restore reference fields for a positioned `entity` in-place."""
    pf = state.pathfinding.get(eid)
    if pf is not None and pf.target is not None:
        tgt_obj = placed_objs.get(pf.target)
        if tgt_obj is not None:
            entity.pathfind_target_ref = tgt_obj
            entity.pathfinding_type = pf.type
        entity.pathfinding = None

    pr = state.portal.get(eid)
    if pr is not None:
        mate_obj = placed_objs.get(pr.pair_entity)
        if mate_obj is not None:
            entity.portal_pair_ref = mate_obj
            if mate_obj.portal_pair_ref is None:
                mate_obj.portal_pair_ref = entity
        entity.portal = Portal(pair_entity=-1)


def from_state(state: State) -> GridState:
    """Convert an immutable State back into a mutable GridState (grid of generic Entity objects)."""
    gridstate = GridState(
        width=state.width,
        height=state.height,
        movement=state.movement,
        objective=state.objective,
        seed=state.seed,
        turn=state.turn,
        score=state.score,
        turn_limit=state.turn_limit,
        win=state.win,
        lose=state.lose,
        message=state.message,
    )

    placed_objs: dict[EntityID, Entity] = {}

    for eid in sorted(state.position.keys()):
        pos = state.position.get(eid)
        if pos is None:
            continue
        x, y = pos.x, pos.y
        if not (0 <= x < gridstate.width and 0 <= y < gridstate.height):
            continue
        obj = _entity_object_from_state(state, eid)
        placed_objs[eid] = obj
        gridstate.grid[y][x].append(obj)

    for eid, obj in placed_objs.items():
        _restore_entity_references(state, eid, obj, placed_objs)

    return gridstate


def grid_state_to_initial_state_fn(gridstate: GridState) -> Callable[..., State]:
    """Create the initial State for the given GridState."""

    def initial_state_fn(*args: Any, **kwargs: Any) -> State:
        return to_state(gridstate)

    return initial_state_fn


def grid_state_fn_to_initial_state_fn(
    grid_state_fn: Callable[..., GridState],
) -> Callable[..., State]:
    """Convert a grid-state-building function into an initial state function."""

    def initial_state_fn(*args: Any, **kwargs: Any) -> State:
        gridstate = grid_state_fn(*args, **kwargs)
        return to_state(gridstate)

    return initial_state_fn
