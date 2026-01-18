from dataclasses import replace
from typing import Tuple, List, Dict
from pyrsistent import pmap, pset

from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import (
    Agent,
    Inventory,
    Pushable,
    Collidable,
    Blocking,
    Position,
    Collectible,
    Exit,
    Appearance,
)
from grid_universe.actions import Action
from grid_universe.step import step


def make_push_state(
    agent_pos: Tuple[int, int],
    box_positions: List[Tuple[int, int]] = [],
    wall_positions: List[Tuple[int, int]] = [],
    width: int = 5,
    height: int = 5,
) -> Tuple[State, EntityID, List[EntityID], List[EntityID]]:
    pos: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    pushable: Dict[EntityID, Pushable] = {}
    blocking: Dict[EntityID, Blocking] = {}
    collidable: Dict[EntityID, Collidable] = {}
    appearance: Dict[EntityID, Appearance] = {}

    agent_id: EntityID = 1
    pos[agent_id] = Position(*agent_pos)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    collidable[agent_id] = Collidable()
    appearance[agent_id] = Appearance(name="human")

    box_ids: List[EntityID] = []
    for bpos in box_positions:
        bid: EntityID = len(pos) + 1
        pos[bid] = Position(*bpos)
        pushable[bid] = Pushable()
        collidable[bid] = Collidable()
        appearance[bid] = Appearance(name="box")
        box_ids.append(bid)

    wall_ids: List[EntityID] = []
    for wpos in wall_positions:
        wid: EntityID = len(pos) + 1
        pos[wid] = Position(*wpos)
        blocking[wid] = Blocking()
        collidable[wid] = Collidable()
        appearance[wid] = Appearance(name="wall")
        wall_ids.append(wid)

    state: State = State(
        width=width,
        height=height,
        movement=BaseMovement(
            name="test",
            description="Test movement",
            function=lambda s, eid, dir: [
                Position(
                    s.position[eid].x
                    + (1 if dir == Action.RIGHT else -1 if dir == Action.LEFT else 0),
                    s.position[eid].y
                    + (1 if dir == Action.DOWN else -1 if dir == Action.UP else 0),
                )
            ],
        ),
        objective=CollectAndExitObjective(),
        position=pmap(pos),
        agent=pmap(agent),
        pushable=pmap(pushable),
        blocking=pmap(blocking),
        collidable=pmap(collidable),
        appearance=pmap(appearance),
        inventory=pmap(inventory),
    )
    return state, agent_id, box_ids, wall_ids


def check_positions(state: State, expected: Dict[EntityID, Position]) -> None:
    for eid, pos in expected.items():
        assert state.position[eid] == pos


def test_agent_pushes_box_successfully() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
        },
    )


def test_push_blocked_by_wall() -> None:
    state, agent_id, box_ids, wall_ids = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], wall_positions=[(2, 0)]
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            wall_ids[0]: Position(2, 0),
        },
    )


def test_push_blocked_by_another_box() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)]
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            box_ids[1]: Position(2, 0),
        },
    )


def test_push_box_out_of_bounds() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(3, 0), box_positions=[(4, 0)], width=5, height=1
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(3, 0),
            box_ids[0]: Position(4, 0),
        },
    )


def test_push_box_onto_collectible() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    collectible_id: EntityID = 100
    state = replace(
        state,
        collectible=state.collectible.set(collectible_id, Collectible()),
        position=state.position.set(collectible_id, Position(2, 0)),
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            collectible_id: Position(2, 0),
        },
    )


def test_push_box_onto_exit() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    exit_id: EntityID = 101
    state = replace(
        state,
        exit=state.exit.set(exit_id, Exit()),
        position=state.position.set(exit_id, Position(2, 0)),
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            exit_id: Position(2, 0),
        },
    )


def test_push_box_left_right_up_down() -> None:
    for action, agent_pos, box_pos, dest_pos in [
        (Action.RIGHT, (0, 0), (1, 0), (2, 0)),
        (Action.LEFT, (2, 0), (1, 0), (0, 0)),
        (Action.DOWN, (0, 0), (0, 1), (0, 2)),
        (Action.UP, (0, 2), (0, 1), (0, 0)),
    ]:
        state, agent_id, box_ids, _ = make_push_state(
            agent_pos=agent_pos, box_positions=[box_pos], width=3, height=3
        )
        state = step(
            state,
            action,
            agent_id=agent_id,
        )
        check_positions(
            state,
            {
                agent_id: Position(*box_pos),
                box_ids[0]: Position(*dest_pos),
            },
        )


def test_push_box_on_narrow_grid_edge() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(0, 1)], width=1, height=2
    )
    state = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(0, 1),
        },
    )


def test_push_chain_of_boxes_blocked() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)]
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            box_ids[1]: Position(2, 0),
        },
    )


def test_push_not_adjacent() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(2, 0)]
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert state.position[agent_id] == Position(1, 0)
    assert state.position[box_ids[0]] == Position(2, 0)


def test_push_no_pushable_at_destination() -> None:
    state, agent_id, _, _ = make_push_state(agent_pos=(0, 0))
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
        },
    )


def test_push_box_blocked_by_agent() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    agent2_id: EntityID = 99
    state = replace(
        state,
        agent=state.agent.set(agent2_id, Agent()),
        collidable=state.collidable.set(agent2_id, Collidable()),
        position=state.position.set(agent2_id, Position(2, 0)),
        inventory=state.inventory.set(agent2_id, Inventory(pset())),
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            agent2_id: Position(2, 0),
        },
    )


def test_push_box_missing_position_component() -> None:
    state, agent_id, box_ids, _ = make_push_state(agent_pos=(0, 0))
    missing_box_id: EntityID = 42
    state = replace(
        state,
        pushable=state.pushable.set(missing_box_id, Pushable()),
        collidable=state.collidable.set(missing_box_id, Collidable()),
        appearance=state.appearance.set(missing_box_id, Appearance(name="box")),
        # No position for box 42
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert missing_box_id not in state.position


def test_push_missing_agent_position() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    state = replace(state, position=state.position.remove(agent_id))
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert box_ids[0] in state.position
    assert agent_id not in state.position


def test_push_box_at_narrow_grid_edge() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    state = replace(state, width=1, height=2)
    state = replace(
        state,
        position=state.position.set(agent_id, Position(0, 0)).set(
            box_ids[0], Position(0, 1)
        ),
    )
    state = step(
        state,
        Action.DOWN,
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(0, 1),
        },
    )


def test_push_after_agent_moves_multiple_times() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    state = step(
        state,
        Action.LEFT,
        agent_id=agent_id,
    )
    state = step(
        state,
        Action.RIGHT,
        agent_id=agent_id,
    )
    assert state.position[agent_id] == Position(1, 0)
    assert state.position[box_ids[0]] == Position(2, 0)
