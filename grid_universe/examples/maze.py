"""Procedural maze level generator example.

This module demonstrates building a parameterized maze-based level using the
``GridState`` editing API and factory helpers, then converting to a ``State``
suitable for simulation or Gym-style environments.

Design Goals
------------
* Showcase composition of factories (agent, walls, doors, portals, hazards,
    power-ups, enemies) with reference wiring (e.g., portal pairing,
  enemy pathfinding target reference to the agent) that are resolved during
  ``to_state`` conversion.
* Provide tunable difficulty levers: wall density, counts of required
  objectives, rewards, hazards, enemies, doors, portals and power-ups.
* Illustrate how movement styles (static, directional patrol, straight-line
  pathfinding, full pathfinding) can be expressed via component choices.

Usage Example
-------------
    from grid_universe.examples import maze
    state = maze.generate(width=20, height=20, seed=123)

    # Render / step the state using the engine's systems or gym wrapper.

Key Concepts Illustrated
------------------------
Required Items:
    Use cores flagged as ``required=True`` which the default objective logic
    expects to be collected before reaching the exit.
Power-Ups:
    Effects created with optional time or usage limits (speed, immunity,
    phasing) acting as pickups.
Enemies:
    Configurable movement style and lethality; pathfinding enemies reference
    the agent to resolve target entity IDs later.
Essential Path:
    Minimal union of shortest paths that touch required items and exit. Other
    entities (hazards, enemies, boxes) prefer non-essential cells.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum, auto
from typing import Any

import random

from grid_universe.state import State
from grid_universe.types import (
    EffectLimit,
    EffectLimitAmount,
    EffectType,
)
from grid_universe.movements import BaseMovement, CardinalMovement
from grid_universe.objectives import BaseObjective, CollectAndExitObjective
from grid_universe.components.properties import (
    PathfindingType,
    Direction,
)
from grid_universe.grid.gridstate import GridState, Position
from grid_universe.grid.convert import to_state
from grid_universe.grid.entity import Entity
from grid_universe.grid.factories import (
    create_agent,
    create_wall,
    create_exit,
    create_coin,
    create_core,
    create_key,
    create_door,
    create_portal,
    create_box,
    create_monster,
    create_hazard,
    create_speed_effect,
    create_immunity_effect,
    create_phasing_effect,
)
from grid_universe.utils.maze import (
    generate_perfect_maze,
    adjust_maze_wall_percentage,
    all_required_path_positions,
)


# -------------------------
# Specs and defaults
# -------------------------

EffectOption = dict[str, Any]
PowerupSpec = tuple[
    EffectType, EffectLimit | None, EffectLimitAmount | None, EffectOption
]
DamageAmount = int
IsLethal = bool
HazardSpec = tuple[str, DamageAmount, IsLethal]

DEFAULT_POWERUPS: list[PowerupSpec] = [
    (EffectType.SPEED, EffectLimit.TIME, 10, {"multiplier": 2}),
    (EffectType.PHASING, EffectLimit.TIME, 10, {}),
    (EffectType.IMMUNITY, EffectLimit.USAGE, 5, {}),
]

DEFAULT_HAZARDS: list[HazardSpec] = [
    ("lava", 5, True),
    ("spike", 3, False),
]


class MovementType(StrEnum):
    STATIC = auto()
    DIRECTIONAL = auto()
    PATHFINDING_LINE = auto()
    PATHFINDING_PATH = auto()


EnemySpec = tuple[DamageAmount, IsLethal, MovementType, int]
BoxSpec = tuple[bool, int]

DEFAULT_ENEMIES: list[EnemySpec] = [
    (5, True, MovementType.DIRECTIONAL, 2),
    (3, False, MovementType.PATHFINDING_LINE, 1),
]

DEFAULT_BOXES: list[BoxSpec] = [
    (True, 0),
    (False, 1),
    (False, 2),
]


# -------------------------
# Internal helpers
# -------------------------


def _random_direction(rng: random.Random) -> Direction:
    """Choose a random cardinal movement direction.

    Parameters
    ----------
    rng:
        Random source.

    Returns
    -------
    str
        One of: "up", "down", "left", "right".
    """
    return rng.choice(["up", "down", "left", "right"])


def _pop_or_fallback(positions: list[Position], fallback: Position) -> Position:
    """Pop a position if available else return a fallback.

    Useful when the parameterization may request more placements than there
    are open tiles.
    """
    return positions.pop() if positions else fallback


# -------------------------
# Main generator
# -------------------------


def generate(
    width: int,
    height: int,
    num_required_items: int = 1,
    num_rewardable_items: int = 1,
    num_portals: int = 1,
    num_doors: int = 1,
    health: int = 5,
    movement_cost: int = 1,
    required_item_reward: int = 10,
    rewardable_item_reward: int = 10,
    boxes: list[BoxSpec] = DEFAULT_BOXES,
    powerups: list[PowerupSpec] = DEFAULT_POWERUPS,
    hazards: list[HazardSpec] = DEFAULT_HAZARDS,
    enemies: list[EnemySpec] = DEFAULT_ENEMIES,
    wall_percentage: float = 0.8,
    movement: BaseMovement = CardinalMovement(),
    objective: BaseObjective = CollectAndExitObjective(),
    seed: int | None = None,
    turn_limit: int | None = None,
) -> State:
    """Generate a randomized maze game state.

    This function orchestrates maze carving, tile classification, entity
    placement and reference wiring before producing the simulation ``State``.

    Args:
        width (int): Width of the maze grid.
        height (int): Height of the maze grid.
        num_required_items (int): Number of required cores that must be collected before exit.
        num_rewardable_items (int): Number of optional reward coins.
        num_portals (int): Number of portal pairs to place (each pair consumes two open cells).
        num_doors (int): Number of door/key pairs; each door is locked by its matching key.
        health (int): Initial agent health points.
        movement_cost (int): Base score cost applied once per action step.
        required_item_reward (int): Reward granted for collecting each required item.
        rewardable_item_reward (int): Reward granted for each optional reward item (coin).
        boxes (List[BoxSpec]): List defining ``(pushable?, speed)`` for box entities; speed > 0 creates moving boxes.
        powerups (List[PowerupSpec]): Effect specifications converted into pickup entities.
        hazards (List[HazardSpec]): Hazard specifications ``(appearance, damage, lethal)``.
        enemies (List[EnemySpec]): Enemy specifications ``(damage, lethal, movement type, speed)``.
        wall_percentage (float): Fraction of original maze walls to retain (``0.0`` => open field, ``1.0`` => perfect maze).
        movement (BaseMovement): Movement system configuration for the level.
        objective (BaseObjective): Win condition configuration for the level.
        seed (int | None): RNG seed for deterministic generation.

    Returns:
        State: Fully wired state ready for simulation.
    """
    rng = random.Random(seed)

    # 1) Base maze -> adjust walls
    maze_grid = generate_perfect_maze(width, height, rng)
    maze_grid = adjust_maze_wall_percentage(maze_grid, wall_percentage, rng)

    # 2) GridState
    gridstate = GridState(
        width=width,
        height=height,
        movement=movement,
        objective=objective,
        seed=seed,
        turn_limit=turn_limit,
        step_cost=movement_cost,
    )

    # 3) Collect positions
    open_positions: list[Position] = [
        pos for pos, is_open in maze_grid.items() if is_open
    ]
    wall_positions: list[Position] = [
        pos for pos, is_open in maze_grid.items() if not is_open
    ]
    rng.shuffle(open_positions)  # randomize for placement variety

    # 4) Agent and exit
    start_pos: Position = _pop_or_fallback(open_positions, (0, 0))
    agent = create_agent(health=health)
    gridstate.add(start_pos, agent)

    goal_pos: Position = _pop_or_fallback(open_positions, (width - 1, height - 1))
    gridstate.add(goal_pos, create_exit())

    # 5) Required cores
    required_positions: list[Position] = []
    for _ in range(num_required_items):
        if not open_positions:
            break
        pos = open_positions.pop()
        gridstate.add(pos, create_core(reward=required_item_reward, required=True))
        required_positions.append(pos)

    # Compute essential path set
    essential_path: set[Position] = all_required_path_positions(
        maze_grid, start_pos, required_positions, goal_pos
    )

    # 6) Rewardable coins
    for _ in range(num_rewardable_items):
        if not open_positions:
            break
        gridstate.add(open_positions.pop(), create_coin(reward=rewardable_item_reward))

    # 7) Portals (explicit pairing by reference)
    for _ in range(num_portals):
        if len(open_positions) < 2:
            break
        p1 = create_portal()
        p2 = create_portal(pair=p1)  # reciprocal reference
        gridstate.add(open_positions.pop(), p1)
        gridstate.add(open_positions.pop(), p2)

    # 8) Doors/keys
    for i in range(num_doors):
        if len(open_positions) < 2:
            break
        key_pos = open_positions.pop()
        door_pos = open_positions.pop()
        key_id_str = f"key{i}"
        gridstate.add(key_pos, create_key(key_id=key_id_str))
        gridstate.add(door_pos, create_door(key_id=key_id_str))

    # 9) Powerups (as pickups)
    create_effect_fn_map: dict[EffectType, Callable[..., Entity]] = {
        EffectType.SPEED: create_speed_effect,
        EffectType.IMMUNITY: create_immunity_effect,
        EffectType.PHASING: create_phasing_effect,
    }
    for type_, lim_type, lim_amount, extra in powerups:
        if not open_positions:
            break
        pos = open_positions.pop()
        create_effect_fn = create_effect_fn_map[type_]
        kwargs = {
            "time": lim_amount if lim_type == EffectLimit.TIME else None,
            "usage": lim_amount if lim_type == EffectLimit.USAGE else None,
        }
        gridstate.add(pos, create_effect_fn(**extra, **kwargs))

    # 10) Non-essential positions (for enemies, hazards, moving boxes)
    open_non_essential: list[Position] = [
        p for p in open_positions if p not in essential_path
    ]
    rng.shuffle(open_non_essential)

    # 11) Boxes
    for pushable, speed in boxes:
        if not open_non_essential:
            break
        pos = open_non_essential.pop()
        direction = _random_direction(rng) if speed > 0 else None
        box = create_box(
            pushable=pushable,
            moving_direction=direction,
            moving_speed=speed,
        )
        gridstate.add(pos, box)

    # 12) Enemies (wire pathfinding to agent by reference if requested)
    for dmg, lethal, mtype, mspeed in enemies:
        if not open_non_essential:
            break
        pos = open_non_essential.pop()

        # Explicit pathfinding via reference to the agent
        path_type: PathfindingType | None = None
        if mtype == MovementType.PATHFINDING_LINE:
            path_type = PathfindingType.STRAIGHT_LINE
        elif mtype == MovementType.PATHFINDING_PATH:
            path_type = PathfindingType.PATH

        # If path_type is set, wire target to agent; otherwise directional/static
        if path_type is not None:
            enemy = create_monster(
                damage=dmg, lethal=lethal, pathfind_target=agent, path_type=path_type
            )
        else:
            mdirection = _random_direction(rng) if mspeed > 0 else None
            enemy = create_monster(
                damage=dmg,
                lethal=lethal,
                moving_direction=mdirection,
                moving_speed=mspeed,
            )

        gridstate.add(pos, enemy)

    # 13) Hazards
    for app_name, dmg, lethal in hazards:
        if not open_non_essential:
            break
        gridstate.add(
            open_non_essential.pop(),
            create_hazard(app_name, damage=dmg, lethal=lethal, priority=7),
        )

    # 14) Walls
    for pos in wall_positions:
        gridstate.add(pos, create_wall())

    # Convert to State (wiring is resolved inside to_state)
    return to_state(gridstate)
