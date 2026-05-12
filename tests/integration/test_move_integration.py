import pytest

from grid_universe.components import (
    Damage,
    Position,
    Health,
    Portal,
    Dead,
    Rewardable,
    Cost,
    Collectible,
    Status,
    Speed,
    Phasing,
)
from grid_universe.movements import BaseMovement
from grid_universe.objectives import CollectAndExitObjective
from grid_universe.step import step
from grid_universe.actions import Action
from pyrsistent import pmap, pset
from grid_universe.types import EntityID
from tests.test_utils import (
    make_agent_box_wall_state,
    make_exit_entity,
    assert_entity_positions,
    replace_state as replace,
)


def test_move_valid() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    action: Action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (1, 0)})


def test_move_blocked_by_wall() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(1, 0)]
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (0, 0), wall_ids[0]: (1, 0)})


@pytest.mark.parametrize("agent_speed_multiplier", [1, 2])
def test_move_pushes_box(agent_speed_multiplier: int) -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    if agent_speed_multiplier > 1:
        speed_effect_id: EntityID = 992
        speed = pmap({speed_effect_id: Speed(multiplier=agent_speed_multiplier)})
        status = pmap({agent_id: Status(effect_ids=pset([speed_effect_id]))})
        state = replace(state, speed=speed, status=status)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    expected_agent_pos = agent_speed_multiplier
    expected_box_pos = agent_speed_multiplier + 1
    assert_entity_positions(
        new_state,
        {agent_id: (expected_agent_pos, 0), box_ids[0]: (expected_box_pos, 0)},
    )


def test_move_push_blocked_by_wall_after_box() -> None:
    state, agent_id, box_ids, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], wall_positions=[(2, 0)]
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(
        new_state,
        {
            agent_id: (0, 0),
            box_ids[0]: (1, 0),
            wall_ids[0]: (2, 0),
        },
    )


def test_move_pushes_box_out_of_bounds() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(3, 0), box_positions=[(4, 0)], width=5, height=1
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (3, 0), box_ids[0]: (4, 0)})


@pytest.mark.parametrize("agent_speed_multiplier", [1, 2])
def test_move_wrapping_enabled(agent_speed_multiplier: int) -> None:
    from grid_universe.movements import WrapAroundMovement

    state, agent_id, _, _ = make_agent_box_wall_state(
        agent_pos=(4, 0), width=5, height=1
    )
    if agent_speed_multiplier > 1:
        speed_effect_id: EntityID = 992
        speed = pmap({speed_effect_id: Speed(multiplier=agent_speed_multiplier)})
        status = pmap({agent_id: Status(effect_ids=pset([speed_effect_id]))})
        state = replace(state, speed=speed, status=status)
    state = replace(state, movement=WrapAroundMovement())
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    expected_agent_pos = (agent_speed_multiplier - 1) % state.width
    assert_entity_positions(new_state, {agent_id: (expected_agent_pos, 0)})


def test_move_ghost_powerup_ignores_wall_box() -> None:
    state, agent_id, box_ids, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(2, 0)], wall_positions=[(1, 0)]
    )
    effect_id = 99
    # Patch in a phasing effect and status to the state
    state = replace(
        state,
        status=state.status.set(agent_id, Status(effect_ids=pset([effect_id]))),
        phasing=state.phasing.set(effect_id, Phasing()),
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(
        new_state, {agent_id: (1, 0), wall_ids[0]: (1, 0), box_ids[0]: (2, 0)}
    )


@pytest.mark.parametrize("agent_speed_multiplier", [1, 2])
def test_move_onto_portal_teleports_agent(agent_speed_multiplier: int) -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    if agent_speed_multiplier > 1:
        speed_effect_id: EntityID = 992
        speed = pmap({speed_effect_id: Speed(multiplier=agent_speed_multiplier)})
        status = pmap({agent_id: Status(effect_ids=pset([speed_effect_id]))})
        state = replace(state, speed=speed, status=status)
    portal1_id, portal2_id = 999, 1000
    pos = state.position.set(portal1_id, Position(1, 0)).set(portal2_id, Position(3, 0))
    portal = pmap(
        {
            portal1_id: Portal(pair_entity=portal2_id),
            portal2_id: Portal(pair_entity=portal1_id),
        }
    )
    state = replace(state, position=pos, portal=portal)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    shift = agent_speed_multiplier - 1
    assert_entity_positions(new_state, {agent_id: (3 + shift, 0)})


def test_move_onto_hazard_takes_damage() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    hazard_id = 200
    pos = state.position.set(hazard_id, Position(1, 0))
    health = pmap({agent_id: Health(current_health=5, max_health=5)})
    damage = pmap({hazard_id: Damage(amount=1)})
    # No "Hazard" class, just use correct damage
    state = replace(state, position=pos, health=health, damage=damage)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.health[agent_id].current_health == 4


def test_move_onto_enemy_takes_damage() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    enemy_id = 300
    pos = state.position.set(enemy_id, Position(1, 0))
    health = pmap({agent_id: Health(current_health=5, max_health=5)})
    damage = pmap({enemy_id: Damage(amount=2)})
    state = replace(state, position=pos, health=health, damage=damage)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.health[agent_id].current_health == 3


def test_move_onto_reward_cost_collectible_tile() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    reward_id, cost_id, collectible_id = 2, 3, 4
    pos = (
        state.position.set(reward_id, Position(1, 0))
        .set(cost_id, Position(1, 0))
        .set(collectible_id, Position(1, 0))
    )
    rewardable = pmap({reward_id: Rewardable(amount=14)})
    cost = pmap({cost_id: Cost(amount=6)})
    collectible = pmap({collectible_id: Collectible()})
    state = replace(
        state, position=pos, rewardable=rewardable, cost=cost, collectible=collectible
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.score == 8  # 14 - 6


def test_move_double_speed_powerup_moves_twice_and_blocks_at_wall() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(2, 0)], width=4, height=1
    )
    effect_id = 201
    state = replace(
        state,
        status=state.status.set(agent_id, Status(effect_ids=pset([effect_id]))),
        speed=state.speed.set(effect_id, Speed(multiplier=2)),
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (1, 0), wall_ids[0]: (2, 0)})


@pytest.mark.parametrize("agent_speed_multiplier", [1, 2])
def test_move_onto_exit_triggers_win(agent_speed_multiplier: int) -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    if agent_speed_multiplier > 1:
        speed_effect_id: EntityID = 992
        speed = pmap({speed_effect_id: Speed(multiplier=agent_speed_multiplier)})
        status = pmap({agent_id: Status(effect_ids=pset([speed_effect_id]))})
        state = replace(state, speed=speed, status=status)
    exit_id, exit_map, exit_pos = make_exit_entity((1, 0))
    pos = state.position.update(exit_pos)
    state = replace(state, exit=pmap(exit_map), position=pos)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.win


def test_move_dead_agent_does_nothing() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    state = replace(state, dead=pmap({agent_id: Dead()}))
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (0, 0)})


def test_move_after_win_or_lose_does_nothing() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    state_win = replace(state, win=True)
    state_lose = replace(state, lose=True)
    action = Action.RIGHT
    new_state_win = step(state_win, action, agent_id=agent_id)
    new_state_lose = step(state_lose, action, agent_id=agent_id)
    assert_entity_positions(new_state_win, {agent_id: (0, 0)})
    assert_entity_positions(new_state_lose, {agent_id: (0, 0)})


def test_move_chained_portal_no_loop() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    portal_a, portal_b, portal_c = 101, 102, 103
    pos = (
        state.position.set(portal_a, Position(1, 0))
        .set(portal_b, Position(2, 0))
        .set(portal_c, Position(3, 0))
    )
    portal = pmap(
        {
            portal_a: Portal(pair_entity=portal_b),
            portal_b: Portal(pair_entity=portal_c),
            portal_c: Portal(pair_entity=portal_a),
        }
    )
    state = replace(state, position=pos, portal=portal)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.position[agent_id] in [Position(2, 0), Position(3, 0)]


@pytest.mark.parametrize("agent_speed_multiplier", [1, 2])
def test_move_push_box_onto_portal_box_teleported(agent_speed_multiplier: int) -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    if agent_speed_multiplier > 1:
        speed_effect_id: EntityID = 992
        speed = pmap({speed_effect_id: Speed(multiplier=agent_speed_multiplier)})
        status = pmap({agent_id: Status(effect_ids=pset([speed_effect_id]))})
        state = replace(state, speed=speed, status=status)
    portal_a, portal_b = 110, 111
    pos = state.position.set(portal_a, Position(2, 0)).set(portal_b, Position(4, 0))
    portal = pmap(
        {portal_a: Portal(pair_entity=portal_b), portal_b: Portal(pair_entity=portal_a)}
    )
    state = replace(state, position=pos, portal=portal)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    box_pos = new_state.position[box_ids[0]]
    assert (
        new_state.position[agent_id] == Position(1, 0)
        if agent_speed_multiplier == 1
        else Position(2, 0)
    )
    assert box_pos == Position(4, 0)


def test_move_box_chain_blocked() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)]
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(
        new_state, {agent_id: (0, 0), box_ids[0]: (1, 0), box_ids[1]: (2, 0)}
    )


def test_move_on_hazard_and_enemy_both_damage() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    hazard_id, enemy_id = 201, 202
    pos = state.position.set(hazard_id, Position(1, 0)).set(enemy_id, Position(1, 0))
    health = pmap({agent_id: Health(current_health=10, max_health=10)})
    damage = pmap({hazard_id: Damage(amount=2), enemy_id: Damage(amount=3)})
    state = replace(state, position=pos, health=health, damage=damage)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.health[agent_id].current_health == 5


def test_move_out_of_bounds_action_negative_index() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), width=1, height=1
    )
    action = Action.LEFT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (0, 0)})


def test_move_agent_not_in_agent_map() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    state = replace(state, agent=state.agent.remove(agent_id))
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert agent_id in new_state.position
    assert new_state.position[agent_id] == Position(0, 0)
    assert agent_id not in new_state.agent


def test_move_with_minimal_state() -> None:
    from grid_universe.state import State

    state = State(
        width=2,
        height=2,
        movement=BaseMovement(
            name="test", description="Test", function=lambda s, eid, d: []
        ),
        objective=CollectAndExitObjective(),
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=9999)
    assert isinstance(new_state, State)
    assert len(new_state.position) == 0


def test_move_double_speed_powerup_both_steps_blocked() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(1, 0), (2, 0)], width=4, height=1
    )
    effect_id = 301
    state = replace(
        state,
        status=state.status.set(agent_id, Status(effect_ids=pset([effect_id]))),
        speed=state.speed.set(effect_id, Speed(multiplier=2)),
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(
        new_state, {agent_id: (0, 0), wall_ids[0]: (1, 0), wall_ids[1]: (2, 0)}
    )


def test_move_ghost_and_double_speed_combo() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(1, 0), (2, 0)], width=4, height=1
    )
    effect_ghost = 401
    effect_speed = 402
    state = replace(
        state,
        status=state.status.set(
            agent_id, Status(effect_ids=pset([effect_ghost, effect_speed]))
        ),
        phasing=state.phasing.set(effect_ghost, Phasing()),
        speed=state.speed.set(effect_speed, Speed(multiplier=2)),
    )
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.position[agent_id] == Position(2, 0)


def test_push_box_onto_exit_agent_doesnt_win() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], width=5, height=1
    )
    exit_id, exit_map, exit_pos = make_exit_entity((2, 0))
    pos = state.position.update(exit_pos)
    state = replace(state, exit=pmap(exit_map), position=pos)
    action = Action.RIGHT
    new_state = step(state, action, agent_id=agent_id)
    # Agent should not win
    assert not new_state.win
    assert_entity_positions(new_state, {agent_id: (1, 0), box_ids[0]: (2, 0)})
