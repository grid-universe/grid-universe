from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import List, Tuple
import streamlit as st

from grid_universe.gym_env import GridUniverseEnv
from grid_universe.examples.maze import (
    generate,
    DEFAULT_BOXES,
    DEFAULT_ENEMIES,
    DEFAULT_HAZARDS,
    DEFAULT_POWERUPS,
    BoxSpec,
    EnemySpec,
    HazardSpec,
    PowerupSpec,
    MovementType,
)
from grid_universe.types import EffectLimit, EffectType, MoveFn, ObjectiveFn
from grid_universe.moves import MOVE_FN_REGISTRY, default_move_fn
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY, default_objective_fn
from grid_universe.renderer.texture import DEFAULT_TEXTURE_MAP, TextureMap

from .base import LevelSource, register_level_source
from ..shared_ui import texture_map_section, seed_section


# -----------------------------
# Config Dataclass
# -----------------------------
@dataclass(frozen=True)
class MazeConfig:
    width: int
    height: int
    turn_limit: int | None
    num_required_items: int
    num_rewardable_items: int
    num_portals: int
    num_doors: int
    health: int
    movement_cost: int
    required_item_reward: int
    rewardable_item_reward: int
    boxes: List[BoxSpec]
    powerups: List[PowerupSpec]
    hazards: List[HazardSpec]
    enemies: List[EnemySpec]
    wall_percentage: float
    move_fn: MoveFn
    objective_fn: ObjectiveFn
    seed: int | None
    render_texture_map: TextureMap


def _default_maze_config() -> MazeConfig:
    return MazeConfig(
        width=10,
        height=10,
        turn_limit=None,
        num_required_items=3,
        num_rewardable_items=3,
        num_portals=1,
        num_doors=1,
        health=5,
        movement_cost=1,
        required_item_reward=10,
        rewardable_item_reward=10,
        boxes=list(DEFAULT_BOXES),
        powerups=list(DEFAULT_POWERUPS),
        hazards=list(DEFAULT_HAZARDS),
        enemies=list(DEFAULT_ENEMIES),
        wall_percentage=0.8,
        move_fn=default_move_fn,
        objective_fn=default_objective_fn,
        seed=None,
        render_texture_map=DEFAULT_TEXTURE_MAP,
    )


# -----------------------------
# UI Helpers
# -----------------------------
def _maze_size_section(cfg: MazeConfig) -> Tuple[int, int, float, int]:
    st.subheader("Maze Size & Structure")
    width = st.slider("Maze width", 6, 30, cfg.width, key="width")
    height = st.slider("Maze height", 6, 30, cfg.height, key="height")
    wall_percentage = st.slider(
        "Wall percentage (0=open, 1=perfect maze)",
        0.0,
        1.0,
        cfg.wall_percentage,
        step=0.01,
        key="wall_percentage",
    )
    movement_cost = st.slider(
        "Floor cost", 0, 10, cfg.movement_cost, key="movement_cost"
    )
    return width, height, wall_percentage, movement_cost


def _run_section(cfg: MazeConfig) -> int | None:
    st.subheader("Run Settings")
    tl = st.number_input(
        "Turn limit (0 = unlimited)",
        min_value=0,
        value=0 if cfg.turn_limit is None else int(cfg.turn_limit),
        key="turn_limit",
    )
    return int(tl) if int(tl) > 0 else None


def _items_section(cfg: MazeConfig) -> Tuple[int, int, int, int]:
    st.subheader("Items & Rewards")
    num_required_items = st.slider(
        "Required Items", 0, 10, cfg.num_required_items, key="num_required_items"
    )
    num_rewardable_items = st.slider(
        "Rewardable Items", 0, 10, cfg.num_rewardable_items, key="num_rewardable_items"
    )
    required_item_reward = st.number_input(
        "Reward per required item",
        min_value=0,
        value=cfg.required_item_reward,
        key="required_item_reward",
    )
    rewardable_item_reward = st.number_input(
        "Reward per rewardable item",
        min_value=0,
        value=cfg.rewardable_item_reward,
        key="rewardable_item_reward",
    )
    return (
        num_required_items,
        num_rewardable_items,
        required_item_reward,
        rewardable_item_reward,
    )


def _agent_section(cfg: MazeConfig) -> int:
    st.subheader("Agent")
    return st.slider("Agent Health", 1, 30, cfg.health, key="health")


def _doors_portals_section(cfg: MazeConfig) -> Tuple[int, int]:
    st.subheader("Doors, Portals")
    num_portals = st.slider("Portals (pairs)", 0, 5, cfg.num_portals, key="num_portals")
    num_doors = st.slider("Doors", 0, 4, cfg.num_doors, key="num_doors")
    return num_portals, num_doors


def _boxes_section(cfg: MazeConfig) -> List[BoxSpec]:
    st.subheader("Boxes")
    boxes = list(cfg.boxes) if cfg.boxes else list(DEFAULT_BOXES)
    box_count = st.number_input(
        "Number of boxes", min_value=0, value=len(boxes), key="box_count"
    )
    edited: List[BoxSpec] = []
    for idx in range(box_count):
        pushable_default = boxes[idx][0] if idx < len(boxes) else True
        speed_default = boxes[idx][1] if idx < len(boxes) else 0
        st.markdown(f"**Box #{idx + 1}**")
        c1, c2 = st.columns([1, 1])
        with c1:
            pushable = st.checkbox(
                "Pushable?", value=pushable_default, key=f"box_pushable_{idx}"
            )
        with c2:
            speed = st.number_input(
                "Speed", min_value=0, value=speed_default, key=f"box_speed_{idx}"
            )
        edited.append((bool(pushable), int(speed)))
    return edited


def _hazards_section() -> List[HazardSpec]:
    st.subheader("Hazards")
    hazards: List[HazardSpec] = []
    for hazard_type, hazard_damage, hazard_lethal in DEFAULT_HAZARDS:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            count = st.number_input(
                f"{hazard_type.title()} count",
                min_value=0,
                value=1,
                key=f"hazard_count_{hazard_type}",
            )
        with c2:
            lethal = st.checkbox(
                "Lethal?", value=hazard_lethal, key=f"hazard_lethal_{hazard_type}"
            )
        with c3:
            if not lethal:
                damage = st.number_input(
                    "Damage",
                    min_value=1,
                    value=hazard_damage,
                    key=f"hazard_damage_{hazard_type}",
                )
            else:
                st.markdown("Lethal")
                damage = 0
        hazards.extend([(hazard_type, int(damage), bool(lethal))] * count)
    return hazards


def _powerups_section() -> List[PowerupSpec]:
    st.subheader("Powerups")
    powerups: List[PowerupSpec] = []
    for idx, (
        effect_type,
        limit_type_default,
        limit_amount_default,
        option_default,
    ) in enumerate(DEFAULT_POWERUPS):
        label = effect_type.name.title()
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            count = st.number_input(
                f"{label} count", min_value=0, value=1, key=f"powerup_count_{idx}"
            )
        with c2:
            choice = st.selectbox(
                "Limit Type",
                ["unlimited", "time", "usage"],
                index=0
                if limit_type_default is None
                else (1 if limit_type_default == EffectLimit.TIME else 2),
                key=f"powerup_limit_type_{idx}",
            )
            updated_limit_type = None
            if choice == "time":
                updated_limit_type = EffectLimit.TIME
            elif choice == "usage":
                updated_limit_type = EffectLimit.USAGE
        with c3:
            if updated_limit_type is None:
                st.markdown("Unlimited")
                updated_limit_amount = None
            else:
                default_amt = (
                    limit_amount_default if limit_amount_default is not None else 10
                )
                updated_limit_amount = int(
                    st.number_input(
                        "Limit Amount",
                        min_value=1,
                        value=default_amt,
                        key=f"powerup_limit_amount_{idx}",
                    )
                )
        with c4:
            updated_option = dict(option_default)
            if effect_type == EffectType.SPEED:
                mult_default = int(option_default.get("multiplier", 2))
                updated_option["multiplier"] = int(
                    st.number_input(
                        "Speed x",
                        min_value=2,
                        value=mult_default,
                        key=f"powerup_speed_mult_{idx}",
                    )
                )
            else:
                st.markdown("No extra option")
        if count > 0:
            powerups.extend(
                [
                    (
                        effect_type,
                        updated_limit_type,
                        updated_limit_amount,
                        updated_option,
                    )
                ]
                * count
            )
    return powerups


def _enemies_section(cfg: MazeConfig) -> List[EnemySpec]:
    st.subheader("Enemies")
    enemies = list(cfg.enemies) if cfg.enemies else list(DEFAULT_ENEMIES)
    enemy_count = st.number_input(
        "Number of enemies", min_value=0, value=len(enemies), key="enemy_count"
    )
    edited: List[EnemySpec] = []
    for idx in range(enemy_count):
        dmg_default = enemies[idx][0] if idx < len(enemies) else 3
        lethal_default = enemies[idx][1] if idx < len(enemies) else False
        move_type_default = (
            enemies[idx][2] if idx < len(enemies) else MovementType.STATIC
        )
        speed_default = enemies[idx][3] if idx < len(enemies) else 1
        st.markdown(f"**Enemy #{idx + 1}**")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            lethal = st.checkbox(
                "Lethal?", value=lethal_default, key=f"enemy_lethal_{idx}"
            )
        with c2:
            damage = (
                0
                if lethal
                else int(
                    st.number_input(
                        "Damage",
                        min_value=1,
                        value=dmg_default,
                        key=f"enemy_damage_{idx}",
                    )
                )
            )
        with c3:
            movement_type = st.selectbox(
                "Movement Type",
                list(MovementType),
                index=list(MovementType).index(move_type_default),
                key=f"enemy_movement_type_{idx}",
            )
        with c4:
            if movement_type == MovementType.STATIC:
                st.markdown("Static")
                speed = 0
            else:
                speed = int(
                    st.number_input(
                        "Movement Speed",
                        min_value=1,
                        value=max(1, speed_default),
                        key=f"enemy_movement_speed_{idx}",
                    )
                )
        edited.append((int(damage), bool(lethal), movement_type, int(speed)))
    return edited


def _movement_section(cfg: MazeConfig) -> MoveFn:
    st.subheader("Gameplay Movement")
    names = list(MOVE_FN_REGISTRY.keys())
    label = st.selectbox(
        "Movement rule",
        names,
        index=names.index(
            next(k for k, v in MOVE_FN_REGISTRY.items() if v is cfg.move_fn)
        ),
        key="move_fn",
    )
    return MOVE_FN_REGISTRY[label]


def _objective_section(cfg: MazeConfig) -> ObjectiveFn:
    st.subheader("Gameplay Objective")
    names = list(OBJECTIVE_FN_REGISTRY.keys())
    label = st.selectbox(
        "Objective",
        names,
        index=names.index(
            next(k for k, v in OBJECTIVE_FN_REGISTRY.items() if v is cfg.objective_fn)
        ),
        key="objective_fn",
    )
    return OBJECTIVE_FN_REGISTRY[label]


def build_maze_config(current: object) -> MazeConfig:
    base = current if isinstance(current, MazeConfig) else _default_maze_config()
    st.info("Procedural maze generator.", icon="🛠️")
    width, height, wall_pct, move_cost = _maze_size_section(base)
    num_req, num_reward, reward_req, reward_reward = _items_section(base)
    health = _agent_section(base)
    num_portals, num_doors = _doors_portals_section(base)
    boxes = _boxes_section(base)
    hazards = _hazards_section()
    powerups = _powerups_section()
    enemies = _enemies_section(base)
    move_fn = _movement_section(base)
    objective_fn = _objective_section(base)
    turn_limit = _run_section(base)
    seed = seed_section(key="maze_seed")
    texture = texture_map_section(base)  # type: ignore[arg-type]
    return MazeConfig(
        width=width,
        height=height,
        turn_limit=turn_limit,
        num_required_items=num_req,
        num_rewardable_items=num_reward,
        num_portals=num_portals,
        num_doors=num_doors,
        health=health,
        movement_cost=move_cost,
        required_item_reward=reward_req,
        rewardable_item_reward=reward_reward,
        boxes=boxes,
        powerups=powerups,
        hazards=hazards,
        enemies=enemies,
        wall_percentage=wall_pct,
        move_fn=move_fn,
        objective_fn=objective_fn,
        seed=seed,
        render_texture_map=texture,
    )


def _make_env(cfg: MazeConfig) -> GridUniverseEnv:
    return GridUniverseEnv(
        render_mode="texture",
        initial_state_fn=generate,
        **dataclasses.asdict(cfg),
    )


register_level_source(
    LevelSource(
        name="Procedural Maze",
        config_type=MazeConfig,
        initial_config=_default_maze_config,
        build_config=build_maze_config,
        make_env=_make_env,
    )
)
