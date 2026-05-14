from dataclasses import replace
from typing import Dict, List, Optional, Tuple
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.movements import BaseMovement
from grid_universe.runtime import make_step_context
from grid_universe.state import State
from grid_universe.components import (
    Agent,
    Rewardable,
    Cost,
    Collectible,
    Inventory,
    Dead,
    Position,
    Appearance,
)
from grid_universe.systems.tile import tile_reward_system, tile_cost_system
from grid_universe.types import EntityID


def make_tile_state(
    rewardable_ids: Optional[List[EntityID]] = None,
    cost_ids: Optional[List[EntityID]] = None,
    collectible_ids: Optional[List[EntityID]] = None,
    agent_pos: Tuple[int, int] = (0, 0),
    reward_amount: int = 10,
    cost_amount: int = 2,
    step_cost: int = 0,
    agent_dead: bool = False,
    agent_in_state: bool = True,
) -> Tuple[State, EntityID]:
    agent_id: EntityID = 1
    pos: Dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()} if agent_in_state else {}
    reward_map: Dict[EntityID, Rewardable] = {}
    cost_map: Dict[EntityID, Cost] = {}
    collectible_map: Dict[EntityID, Collectible] = {}
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(set())}
    appearance: Dict[EntityID, Appearance] = {agent_id: Appearance(name="human")}
    dead: dict[EntityID, Dead] = dict({agent_id: Dead()}) if agent_dead else dict()
    rewardable_ids = rewardable_ids or []
    cost_ids = cost_ids or []
    collectible_ids = collectible_ids or []
    for rid in rewardable_ids:
        pos[rid] = Position(*agent_pos)
        reward_map[rid] = Rewardable(amount=reward_amount)
        appearance[rid] = Appearance(name="coin")
    for cid in cost_ids:
        pos[cid] = Position(*agent_pos)
        cost_map[cid] = Cost(amount=cost_amount)
        appearance[cid] = Appearance(name="coin")
    for colid in collectible_ids:
        pos[colid] = Position(*agent_pos)
        collectible_map[colid] = Collectible()
        appearance[colid] = Appearance(name="core")
    state: State = State(
        width=3,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent_map),
        collectible=dict(collectible_map),
        rewardable=dict(reward_map),
        cost=dict(cost_map),
        inventory=dict(inventory),
        appearance=dict(appearance),
        dead=dead,
        step_cost=step_cost,
    )
    return (state, agent_id)


def agent_step_and_score(state: State, agent_id: EntityID) -> int:
    tile_reward_system(state, agent_id, make_step_context(state))
    tile_cost_system(state, agent_id, make_step_context(state))
    return state.score


def test_rewardable_tile_grants_score() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    assert agent_step_and_score(state, agent_id) == 10


def test_cost_tile_removes_score() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    assert agent_step_and_score(state, agent_id) == -2


def test_step_cost_removes_score() -> None:
    state, agent_id = make_tile_state(step_cost=3)
    assert agent_step_and_score(state, agent_id) == -3


def test_step_cost_combines_with_cost_components() -> None:
    state, agent_id = make_tile_state(cost_ids=[3], step_cost=3)
    assert agent_step_and_score(state, agent_id) == -5


def test_rewardable_ignored_if_collectible() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], collectible_ids=[2])
    assert agent_step_and_score(state, agent_id) == 0


def test_cost_ignored_if_collectible() -> None:
    state, agent_id = make_tile_state(cost_ids=[3], collectible_ids=[3])
    assert agent_step_and_score(state, agent_id) == 0


def test_multiple_rewardables_and_costs() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2, 3], cost_ids=[4, 5])
    assert agent_step_and_score(state, agent_id) == 10 + 10 - 2 - 2


def test_reward_and_cost_both_collectible_ignored() -> None:
    state, agent_id = make_tile_state(
        rewardable_ids=[2], cost_ids=[3], collectible_ids=[2, 3]
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_reward_cost_same_tile() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[2])
    assert agent_step_and_score(state, agent_id) == 10 - 2


def test_zero_and_negative_rewards_costs() -> None:
    state, agent_id = make_tile_state(
        rewardable_ids=[2, 3], cost_ids=[4, 5], reward_amount=0, cost_amount=-6
    )
    assert agent_step_and_score(state, agent_id) == 0 + 0 - -6 - -6


def test_rewardable_with_some_collectible() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2, 3], collectible_ids=[3])
    assert agent_step_and_score(state, agent_id) == 10


def test_cost_with_some_collectible() -> None:
    state, agent_id = make_tile_state(cost_ids=[2, 3], collectible_ids=[2])
    assert agent_step_and_score(state, agent_id) == -2


def test_rewardable_at_another_position() -> None:
    state, agent_id = make_tile_state()
    rewardable_id = 99
    reward_map = {**state.rewardable, rewardable_id: Rewardable(amount=11)}
    pos_map = {**state.position, rewardable_id: Position(1, 0)}
    state = replace(state, rewardable=reward_map, position=pos_map)
    assert agent_step_and_score(state, agent_id) == 0


def test_cost_at_another_position() -> None:
    state, agent_id = make_tile_state()
    cost_id = 77
    cost_map = {**state.cost, cost_id: Cost(amount=6)}
    pos_map = {**state.position, cost_id: Position(1, 0)}
    state = replace(state, cost=cost_map, position=pos_map)
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_dead_no_score_change() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3], agent_dead=True)
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_missing_from_state() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3])
    state = replace(
        state,
        agent={key: value for key, value in state.agent.items() if key != agent_id},
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_missing_position() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3])
    state = replace(
        state,
        position={
            key: value for key, value in state.position.items() if key != agent_id
        },
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_multiple_agents_separate_scores() -> None:
    agent1_id = 1
    agent2_id = 2
    pos = {
        agent1_id: Position(0, 0),
        agent2_id: Position(1, 0),
        3: Position(0, 0),
        4: Position(1, 0),
    }
    agent_map: Dict[EntityID, Agent] = {agent1_id: Agent(), agent2_id: Agent()}
    rewardable = {3: Rewardable(amount=12)}
    cost = {4: Cost(amount=7)}
    inventory = {agent1_id: Inventory(set()), agent2_id: Inventory(set())}
    appearance: Dict[EntityID, Appearance] = {
        agent1_id: Appearance(name="human"),
        agent2_id: Appearance(name="human"),
        3: Appearance(name="coin"),
        4: Appearance(name="coin"),
    }
    state = State(
        width=2,
        height=1,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
        position=dict(pos),
        agent=dict(agent_map),
        rewardable=dict(rewardable),
        cost=dict(cost),
        inventory=dict(inventory),
        appearance=dict(appearance),
    )
    score1 = agent_step_and_score(state.clone(), agent1_id)
    score2 = agent_step_and_score(state.clone(), agent2_id)
    assert score1 == 12
    assert score2 == -7
