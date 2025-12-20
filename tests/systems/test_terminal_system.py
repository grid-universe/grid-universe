from dataclasses import replace
from typing import Dict, List, Tuple
from pyrsistent import pmap, pset, PMap
from grid_universe.objectives import default_objective_fn
from grid_universe.systems.terminal import win_system, lose_system
from grid_universe.components import (
    Agent,
    Requirable,
    Collectible,
    Exit,
    Inventory,
    Dead,
    Position,
    Appearance,
    AppearanceName,
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
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    requirable: Dict[EntityID, Requirable] = {}
    collectible: Dict[EntityID, Collectible] = {}
    appearance: Dict[EntityID, Appearance] = {
        agent_id: Appearance(name=AppearanceName.HUMAN),
        exit_id: Appearance(name=AppearanceName.EXIT),
    }
    dead: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()

    # Place agent and exit
    pos[agent_id] = Position(1, 1) if agent_on_exit else Position(0, 0)
    pos[exit_id] = Position(1, 1)

    # Place required items (and optionally mark as collected)
    for i, rid in enumerate(requirable_ids):
        requirable[rid] = Requirable()
        if not all_required_collected:
            collectible[rid] = Collectible()
            appearance[rid] = Appearance(name=AppearanceName.CORE)
            pos[rid] = Position(5 + i, 5)
        else:
            # Collected: add to inventory, not to collectible
            inventory[agent_id] = Inventory(
                item_ids=pset(list(inventory[agent_id].item_ids) + [rid])
            )

    state: State = State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        position=pmap(pos),
        agent=pmap(agent),
        exit=pmap({exit_id: Exit()}),
        collectible=pmap(collectible),
        requirable=pmap(requirable),
        inventory=pmap(inventory),
        appearance=pmap(appearance),
        dead=dead,
    )
    return state, agent_id, exit_id, requirable_ids


def test_win_when_on_exit_and_requirable_collected() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True,
        all_required_collected=True,
        agent_dead=False,
    )
    new_state = win_system(state, agent_id)
    assert new_state.win
    assert not new_state.lose


def test_no_win_if_required_not_collected() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True,
        all_required_collected=False,
        agent_dead=False,
    )
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_no_win_if_not_on_exit() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=False,
        all_required_collected=True,
        agent_dead=False,
    )
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_lose_if_agent_dead() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    new_state = lose_system(state, agent_id)
    assert new_state.lose


def test_no_lose_if_agent_alive() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    new_state = lose_system(state, agent_id)
    assert not new_state.lose


def test_win_when_on_exit_no_required_items() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    # Remove all required items from state
    state = replace(state, requirable=pmap())
    new_state = win_system(state, agent_id)
    assert new_state.win


def test_dead_agent_on_exit_no_win() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    win_state = win_system(state, agent_id)
    lose_state = lose_system(state, agent_id)
    assert lose_state.lose
    assert not win_state.win


def test_win_state_is_idempotent() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, win=True)
    new_state = win_system(state, agent_id)
    assert new_state.win


def test_lose_state_is_idempotent() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    state = replace(state, lose=True)
    new_state = lose_system(state, agent_id)
    assert new_state.lose


def test_no_win_if_agent_position_missing() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, position=state.position.remove(agent_id))
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_no_win_if_no_agent_in_state() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, agent=state.agent.remove(agent_id))
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_win_when_on_any_exit() -> None:
    state, agent_id, exit_id, requirable_ids = make_terminal_state(
        agent_on_exit=False, all_required_collected=True, agent_dead=False
    )
    # Add another exit at agent's position
    exit2_id = 77
    pos = state.position.set(exit2_id, state.position[agent_id])
    exits = state.exit.set(exit2_id, Exit())
    state = replace(state, exit=exits, position=pos)
    new_state = win_system(state, agent_id)
    assert new_state.win
