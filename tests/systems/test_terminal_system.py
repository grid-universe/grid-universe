from dataclasses import replace
from typing import Dict, List, Tuple
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.systems.terminal import win_system, lose_system
from grid_universe.runtime import make_step_context
from grid_universe.components import (
    Agent,
    Requirable,
    Collectible,
    Exit,
    Inventory,
    Dead,
    Position,
    Appearance,
)
from grid_universe.state import State
from grid_universe.types import EntityID


def make_terminal_state(
    agent_on_exit: bool, all_required_collected: bool, agent_dead: bool
) -> Tuple[State, EntityID, EntityID, List[EntityID]]:
    agent_id: EntityID = 1
    exit_id: EntityID = 2
    requirable_ids: List[EntityID] = [3, 4]
    agent: Dict[EntityID, Agent] = {agent_id: Agent()}
    pos: Dict[EntityID, Position] = {}
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(set())}
    requirable: Dict[EntityID, Requirable] = {}
    collectible: Dict[EntityID, Collectible] = {}
    appearance: Dict[EntityID, Appearance] = {
        agent_id: Appearance(name="human"),
        exit_id: Appearance(name="exit"),
    }
    dead: dict[EntityID, Dead] = dict({agent_id: Dead()}) if agent_dead else dict()
    pos[agent_id] = Position(1, 1) if agent_on_exit else Position(0, 0)
    pos[exit_id] = Position(1, 1)
    for i, rid in enumerate(requirable_ids):
        requirable[rid] = Requirable()
        if not all_required_collected:
            collectible[rid] = Collectible()
            appearance[rid] = Appearance(name="core")
            pos[rid] = Position(5 + i, 5)
        else:
            inventory[agent_id] = Inventory(
                item_ids=set(list(inventory[agent_id].item_ids) + [rid])
            )
    state: State = State(
        width=10,
        height=10,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent),
        exit=dict({exit_id: Exit()}),
        collectible=dict(collectible),
        requirable=dict(requirable),
        inventory=dict(inventory),
        appearance=dict(appearance),
        dead=dead,
    )
    return (state, agent_id, exit_id, requirable_ids)


def test_win_when_on_exit_and_requirable_collected() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    win_system(state, agent_id, make_step_context(state))
    assert state.win
    assert not state.lose


def test_no_win_if_required_not_collected() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=False, agent_dead=False
    )
    win_system(state, agent_id, make_step_context(state))
    assert not state.win


def test_no_win_if_not_on_exit() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=False, all_required_collected=True, agent_dead=False
    )
    win_system(state, agent_id, make_step_context(state))
    assert not state.win


def test_lose_if_agent_dead() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    lose_system(state, agent_id)
    assert state.lose


def test_no_lose_if_agent_alive() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    lose_system(state, agent_id)
    assert not state.lose


def test_win_when_on_exit_no_required_items() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, requirable=dict())
    win_system(state, agent_id, make_step_context(state))
    assert state.win


def test_dead_agent_on_exit_no_win() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    win_system(state, agent_id, make_step_context(state))
    assert not state.win
    lose_system(state, agent_id)
    assert state.lose


def test_win_state_is_idempotent() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, win=True)
    win_system(state, agent_id, make_step_context(state))
    assert state.win


def test_lose_state_is_idempotent() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    state = replace(state, lose=True)
    lose_system(state, agent_id)
    assert state.lose


def test_no_win_if_agent_position_missing() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(
        state,
        position={
            key: value for key, value in state.position.items() if key != agent_id
        },
    )
    win_system(state, agent_id, make_step_context(state))
    assert not state.win


def test_no_win_if_no_agent_in_state() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(
        state,
        agent={key: value for key, value in state.agent.items() if key != agent_id},
    )
    win_system(state, agent_id, make_step_context(state))
    assert not state.win


def test_win_when_on_any_exit() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=False, all_required_collected=True, agent_dead=False
    )
    exit2_id = 77
    pos = {**state.position, exit2_id: state.position[agent_id]}
    exits = {**state.exit, exit2_id: Exit()}
    state = replace(state, exit=exits, position=pos)
    win_system(state, agent_id, make_step_context(state))
    assert state.win
