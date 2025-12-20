from typing import Dict, Tuple, List, Optional, Type, TypeVar, TypedDict
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap
from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.components import (
    Position,
    Agent,
    Inventory,
    Key,
    Collectible,
    Locked,
    Blocking,
    Collidable,
    Exit,
    Pushable,
    Cost,
    Damage,
    Dead,
    Health,
    LethalDamage,
    Moving,
    Portal,
    Requirable,
    Rewardable,
    Appearance,
    AppearanceName,
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
    Status,
)
from grid_universe.entity import new_entity_id
from grid_universe.types import EntityID, MoveFn, ObjectiveFn
from grid_universe.moves import default_move_fn


class MinimalEntities(TypedDict):
    agent_id: EntityID
    key_id: EntityID
    door_id: EntityID


def make_minimal_key_door_state() -> Tuple[State, MinimalEntities]:
    """Standard key-door ECS state for integration tests."""
    pos: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    key: Dict[EntityID, Key] = {}
    collectible: Dict[EntityID, Collectible] = {}
    locked: Dict[EntityID, Locked] = {}
    blocking: Dict[EntityID, Blocking] = {}
    collidable: Dict[EntityID, Collidable] = {}
    appearance: Dict[EntityID, Appearance] = {}

    agent_id = new_entity_id()
    key_id = new_entity_id()
    door_id = new_entity_id()
    positions = {
        "agent": (0, 0),
        "key": (0, 1),
        "door": (0, 2),
    }
    pos[agent_id] = Position(*positions["agent"])
    pos[key_id] = Position(*positions["key"])
    pos[door_id] = Position(*positions["door"])
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    key[key_id] = Key(key_id="red")
    collectible[key_id] = Collectible()
    locked[door_id] = Locked(key_id="red")
    blocking[door_id] = Blocking()
    collidable[agent_id] = Collidable()
    collidable[door_id] = Collidable()
    appearance[agent_id] = Appearance(name=AppearanceName.HUMAN)
    appearance[key_id] = Appearance(name=AppearanceName.KEY)
    appearance[door_id] = Appearance(name=AppearanceName.DOOR)

    state = State(
        width=3,
        height=3,
        move_fn=default_move_fn,
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=pmap(agent),
        locked=pmap(locked),
        key=pmap(key),
        collectible=pmap(collectible),
        inventory=pmap(inventory),
        appearance=pmap(appearance),
        blocking=pmap(blocking),
        collidable=pmap(collidable),
    )
    return state, MinimalEntities(agent_id=agent_id, key_id=key_id, door_id=door_id)


def make_exit_entity(
    position: Tuple[int, int],
) -> Tuple[EntityID, Dict[EntityID, Exit], Dict[EntityID, Position]]:
    """Utility to add a single Exit entity at a given position."""
    exit_id = new_entity_id()
    return (
        exit_id,
        {exit_id: Exit()},
        {exit_id: Position(*position)},
    )


def make_agent_box_wall_state(
    agent_pos: Tuple[int, int],
    box_positions: Optional[List[Tuple[int, int]]] = None,
    wall_positions: Optional[List[Tuple[int, int]]] = None,
    width: int = 5,
    height: int = 5,
) -> Tuple[State, EntityID, List[EntityID], List[EntityID]]:
    """
    Utility for integration: agent + any number of boxes and walls.
    Returns state, agent_id, [box_ids], [wall_ids].
    """
    pos: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    pushable: Dict[EntityID, Pushable] = {}
    blocking: Dict[EntityID, Blocking] = {}
    collidable: Dict[EntityID, Collidable] = {}
    appearance: Dict[EntityID, Appearance] = {}

    agent_id = new_entity_id()
    pos[agent_id] = Position(*agent_pos)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    collidable[agent_id] = Collidable()
    appearance[agent_id] = Appearance(name=AppearanceName.HUMAN)

    box_ids: List[EntityID] = []
    if box_positions:
        for bpos in box_positions:
            bid = new_entity_id()
            pos[bid] = Position(*bpos)
            pushable[bid] = Pushable()
            collidable[bid] = Collidable()
            appearance[bid] = Appearance(name=AppearanceName.BOX)
            box_ids.append(bid)

    wall_ids: List[EntityID] = []
    if wall_positions:
        for wpos in wall_positions:
            wid = new_entity_id()
            pos[wid] = Position(*wpos)
            blocking[wid] = Blocking()
            collidable[wid] = Collidable()
            appearance[wid] = Appearance(name=AppearanceName.WALL)
            wall_ids.append(wid)

    state = State(
        width=width,
        height=height,
        move_fn=default_move_fn,
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=pmap(agent),
        pushable=pmap(pushable),
        inventory=pmap(inventory),
        appearance=pmap(appearance),
        blocking=pmap(blocking),
        collidable=pmap(collidable),
    )
    return state, agent_id, box_ids, wall_ids


def assert_entity_positions(
    state: State, expected: Dict[EntityID, Tuple[int, int]]
) -> None:
    """Check that expected entities are at the right positions."""
    for eid, (x, y) in expected.items():
        actual = state.position.get(eid)
        assert actual == Position(x, y), (
            f"Entity {eid} expected at {(x, y)}, got {actual}"
        )


T = TypeVar("T")


def filter_component_map(
    extra_components: Optional[Dict[str, Dict[EntityID, object]]],
    key: str,
    typ: Type[T],
) -> Dict[EntityID, T]:
    result: Dict[EntityID, T] = {}
    if extra_components and key in extra_components:
        for k, v in extra_components[key].items():
            if isinstance(v, typ):
                result[k] = v
    return result


def make_agent_state(
    *,
    agent_pos: Tuple[int, int],
    move_fn: Optional[MoveFn] = None,
    objective_fn: Optional[ObjectiveFn] = None,
    extra_components: Optional[Dict[str, Dict[EntityID, object]]] = None,
    width: int = 5,
    height: int = 5,
    agent_dead: bool = False,
    agent_id: EntityID = 1,
) -> Tuple[State, EntityID]:
    positions: Dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    positions.update(filter_component_map(extra_components, "position", Position))

    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    dead_map: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()

    state: State = State(
        width=width,
        height=height,
        move_fn=move_fn if move_fn is not None else default_move_fn,
        objective_fn=(
            objective_fn if objective_fn is not None else default_objective_fn
        ),
        position=pmap(positions),
        agent=pmap(agent_map),
        pushable=pmap(filter_component_map(extra_components, "pushable", Pushable)),
        locked=pmap(filter_component_map(extra_components, "locked", Locked)),
        portal=pmap(filter_component_map(extra_components, "portal", Portal)),
        exit=pmap(filter_component_map(extra_components, "exit", Exit)),
        key=pmap(filter_component_map(extra_components, "key", Key)),
        collectible=pmap(
            filter_component_map(extra_components, "collectible", Collectible)
        ),
        rewardable=pmap(
            filter_component_map(extra_components, "rewardable", Rewardable)
        ),
        cost=pmap(filter_component_map(extra_components, "cost", Cost)),
        requirable=pmap(
            filter_component_map(extra_components, "requirable", Requirable)
        ),
        inventory=pmap(inventory),
        health=pmap(filter_component_map(extra_components, "health", Health)),
        appearance=pmap(
            filter_component_map(extra_components, "appearance", Appearance)
        ),
        blocking=pmap(filter_component_map(extra_components, "blocking", Blocking)),
        dead=dead_map,
        moving=pmap(filter_component_map(extra_components, "moving", Moving)),
        collidable=pmap(
            filter_component_map(extra_components, "collidable", Collidable)
        ),
        damage=pmap(filter_component_map(extra_components, "damage", Damage)),
        lethal_damage=pmap(
            filter_component_map(extra_components, "lethal_damage", LethalDamage)
        ),
        immunity=pmap(filter_component_map(extra_components, "immunity", Immunity)),
        phasing=pmap(filter_component_map(extra_components, "phasing", Phasing)),
        speed=pmap(filter_component_map(extra_components, "speed", Speed)),
        time_limit=pmap(
            filter_component_map(extra_components, "time_limit", TimeLimit)
        ),
        usage_limit=pmap(
            filter_component_map(extra_components, "usage_limit", UsageLimit)
        ),
        status=pmap(filter_component_map(extra_components, "status", Status)),
    )
    return state, agent_id
