from collections.abc import Mapping
from typing import Dict, Tuple, List, Optional, Type, TypeVar, TypedDict
from grid_universe.movements import CardinalMovement, BaseMovement
from grid_universe.objectives import CollectAndExitObjective, BaseObjective
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
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
    Status,
)
from grid_universe.entity import new_entity_id
from grid_universe.types import EntityID


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
    positions = {"agent": (0, 0), "key": (0, 1), "door": (0, 2)}
    pos[agent_id] = Position(*positions["agent"])
    pos[key_id] = Position(*positions["key"])
    pos[door_id] = Position(*positions["door"])
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(set())
    key[key_id] = Key(key_id="red")
    collectible[key_id] = Collectible()
    locked[door_id] = Locked(key_id="red")
    blocking[door_id] = Blocking()
    collidable[agent_id] = Collidable()
    collidable[door_id] = Collidable()
    appearance[agent_id] = Appearance(name="human")
    appearance[key_id] = Appearance(name="key")
    appearance[door_id] = Appearance(name="door")
    state = State(
        width=3,
        height=3,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent),
        locked=dict(locked),
        key=dict(key),
        collectible=dict(collectible),
        inventory=dict(inventory),
        appearance=dict(appearance),
        blocking=dict(blocking),
        collidable=dict(collidable),
    )
    return (state, MinimalEntities(agent_id=agent_id, key_id=key_id, door_id=door_id))


def make_exit_entity(
    position: Tuple[int, int],
) -> Tuple[EntityID, Dict[EntityID, Exit], Dict[EntityID, Position]]:
    """Utility to add a single Exit entity at a given position."""
    exit_id = new_entity_id()
    return (exit_id, {exit_id: Exit()}, {exit_id: Position(*position)})


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
    inventory[agent_id] = Inventory(set())
    collidable[agent_id] = Collidable()
    appearance[agent_id] = Appearance(name="human")
    box_ids: List[EntityID] = []
    if box_positions:
        for bpos in box_positions:
            bid = new_entity_id()
            pos[bid] = Position(*bpos)
            pushable[bid] = Pushable()
            collidable[bid] = Collidable()
            appearance[bid] = Appearance(name="box")
            box_ids.append(bid)
    wall_ids: List[EntityID] = []
    if wall_positions:
        for wpos in wall_positions:
            wid = new_entity_id()
            pos[wid] = Position(*wpos)
            blocking[wid] = Blocking()
            collidable[wid] = Collidable()
            appearance[wid] = Appearance(name="wall")
            wall_ids.append(wid)
    state = State(
        width=width,
        height=height,
        movement=CardinalMovement(),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent),
        pushable=dict(pushable),
        inventory=dict(inventory),
        appearance=dict(appearance),
        blocking=dict(blocking),
        collidable=dict(collidable),
    )
    return (state, agent_id, box_ids, wall_ids)


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
    extra_components: Mapping[str, object] | None,
    key: str,
    typ: Type[T],
) -> Dict[EntityID, T]:
    result: Dict[EntityID, T] = {}
    if not extra_components:
        return result
    store = extra_components.get(key)
    if not isinstance(store, Mapping):
        return result
    for entity_id, component in store.items():
        if isinstance(entity_id, int) and isinstance(component, typ):
            result[entity_id] = component
    return result


def make_agent_state(
    *,
    agent_pos: Tuple[int, int],
    movement: Optional[BaseMovement] = None,
    objective: Optional[BaseObjective] = None,
    extra_components: Mapping[str, object] | None = None,
    width: int = 5,
    height: int = 5,
    agent_dead: bool = False,
    agent_id: EntityID = 1,
) -> Tuple[State, EntityID]:
    positions: Dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    positions.update(filter_component_map(extra_components, "position", Position))
    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(set())}
    dead_map: dict[EntityID, Dead] = dict({agent_id: Dead()}) if agent_dead else dict()
    movement_obj = movement if movement is not None else CardinalMovement()
    objective_obj = objective if objective is not None else CollectAndExitObjective()
    state: State = State(
        width=width,
        height=height,
        movement=movement_obj,
        objective=objective_obj,
        position=dict(positions),
        agent=dict(agent_map),
        pushable=dict(filter_component_map(extra_components, "pushable", Pushable)),
        locked=dict(filter_component_map(extra_components, "locked", Locked)),
        portal=dict(filter_component_map(extra_components, "portal", Portal)),
        exit=dict(filter_component_map(extra_components, "exit", Exit)),
        key=dict(filter_component_map(extra_components, "key", Key)),
        collectible=dict(
            filter_component_map(extra_components, "collectible", Collectible)
        ),
        rewardable=dict(
            filter_component_map(extra_components, "rewardable", Rewardable)
        ),
        cost=dict(filter_component_map(extra_components, "cost", Cost)),
        requirable=dict(
            filter_component_map(extra_components, "requirable", Requirable)
        ),
        inventory=dict(inventory),
        health=dict(filter_component_map(extra_components, "health", Health)),
        appearance=dict(
            filter_component_map(extra_components, "appearance", Appearance)
        ),
        blocking=dict(filter_component_map(extra_components, "blocking", Blocking)),
        dead=dead_map,
        moving=dict(filter_component_map(extra_components, "moving", Moving)),
        collidable=dict(
            filter_component_map(extra_components, "collidable", Collidable)
        ),
        damage=dict(filter_component_map(extra_components, "damage", Damage)),
        lethal_damage=dict(
            filter_component_map(extra_components, "lethal_damage", LethalDamage)
        ),
        immunity=dict(filter_component_map(extra_components, "immunity", Immunity)),
        phasing=dict(filter_component_map(extra_components, "phasing", Phasing)),
        speed=dict(filter_component_map(extra_components, "speed", Speed)),
        time_limit=dict(
            filter_component_map(extra_components, "time_limit", TimeLimit)
        ),
        usage_limit=dict(
            filter_component_map(extra_components, "usage_limit", UsageLimit)
        ),
        status=dict(filter_component_map(extra_components, "status", Status)),
    )
    return (state, agent_id)
