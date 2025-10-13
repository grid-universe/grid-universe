from __future__ import annotations

from typing import Dict, Callable, Any, List, Optional
import streamlit as st
from dataclasses import dataclass

from grid_universe.gym_env import GridUniverseEnv
from grid_universe.state import State
from grid_universe.examples import gameplay_levels
from grid_universe.renderer.texture import DEFAULT_TEXTURE_MAP, TextureMap
from .base import LevelSource, register_level_source
from ..shared_ui import seed_section, texture_map_section


# -----------------------------
# Config Dataclass
# -----------------------------
@dataclass(frozen=True)
class GameplayConfig:
    level_name: str
    seed: Optional[int]
    render_texture_map: TextureMap


# Mapping from UI label to builder function
_NAME_TO_BUILDER: Dict[str, Callable[[int], State]] = {
    "L0 Basic Movement": gameplay_levels.build_level_basic_movement,
    "L1 Maze Turns": gameplay_levels.build_level_maze_turns,
    "L2 Optional Coin Path": gameplay_levels.build_level_optional_coin,
    "L3 One Required Core": gameplay_levels.build_level_required_one,
    "L4 Two Required Cores": gameplay_levels.build_level_required_two,
    "L5 Key & Door": gameplay_levels.build_level_key_door,
    "L6 Hazard Detour": gameplay_levels.build_level_hazard_detour,
    "L7 Portal Shortcut": gameplay_levels.build_level_portal_shortcut,
    "L8 Pushable Box": gameplay_levels.build_level_pushable_box,
    "L9 Enemy Patrol": gameplay_levels.build_level_enemy_patrol,
    "L10 Shield Powerup": gameplay_levels.build_level_power_shield,
    "L11 Ghost Powerup": gameplay_levels.build_level_power_ghost,
    "L12 Boots Powerup": gameplay_levels.build_level_power_boots,
    "L13 Capstone": gameplay_levels.build_level_capstone,
}

_LEVEL_NAMES: List[str] = list(_NAME_TO_BUILDER.keys())


# -----------------------------
# UI Builder
# -----------------------------
def build_gameplay_config(current: object) -> GameplayConfig:
    st.info("Select a curated gameplay progression level.", icon="🎮")
    base_level = (
        current.level_name
        if isinstance(current, GameplayConfig) and current.level_name in _LEVEL_NAMES
        else _LEVEL_NAMES[0]
    )
    level_name = st.selectbox(
        "Gameplay Level",
        _LEVEL_NAMES,
        index=_LEVEL_NAMES.index(base_level),
        key="gameplay_level_select",
    )
    seed = seed_section(key="gameplay_seed")
    texture = texture_map_section(
        current
        if hasattr(current, "render_texture_map")
        else GameplayConfig(level_name, 0, DEFAULT_TEXTURE_MAP)  # type: ignore[arg-type]
    )
    return GameplayConfig(level_name=level_name, seed=seed, render_texture_map=texture)


def _make_env(cfg: GameplayConfig) -> GridUniverseEnv:
    """Construct an env for a curated gameplay level."""
    builder = _NAME_TO_BUILDER.get(cfg.level_name)
    if builder is None:
        raise ValueError(f"Unknown gameplay level: {cfg.level_name}")

    def _initial_state_fn(**_ignored: Any):  # deterministic authored state
        return builder(cfg.seed if cfg.seed is not None else 0)

    sample = _initial_state_fn()
    return GridUniverseEnv(
        render_mode="texture",
        initial_state_fn=_initial_state_fn,
        width=sample.width,
        height=sample.height,
        render_texture_map=cfg.render_texture_map,
    )


def _default_gameplay_config() -> GameplayConfig:
    return GameplayConfig(
        level_name="L0 Basic Movement", seed=0, render_texture_map=DEFAULT_TEXTURE_MAP
    )


register_level_source(
    LevelSource(
        name="Gameplay Example",
        config_type=GameplayConfig,
        initial_config=_default_gameplay_config,
        build_config=build_gameplay_config,
        make_env=_make_env,
    )
)
