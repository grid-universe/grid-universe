import warnings

from grid_universe.actions import Action
from grid_universe.env import GridUniverseEnv
from grid_universe.examples.gameplay_levels import build_level_basic_movement
from grid_universe.examples.maze import generate
from grid_universe.state import State


def _layout_signature(state: State) -> tuple[tuple[int, int, str], ...]:
    return tuple(
        sorted(
            (
                position.x,
                position.y,
                state.appearance[entity_id].name
                if entity_id in state.appearance
                else "",
            )
            for entity_id, position in state.position.items()
        )
    )


def _assert_observation_matches_space(env: GridUniverseEnv, obs: object) -> None:
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        assert env.observation_space.contains(obs)

    assert records == []


def test_image_env_reset_and_step_observations_match_space() -> None:
    env = GridUniverseEnv(
        initial_state_fn=generate,
        width=9,
        height=9,
        seed=7,
        render_resolution=72,
    )

    obs, _ = env.reset()
    _assert_observation_matches_space(env, obs)

    obs, _, _, _, _ = env.step(Action.RIGHT)
    _assert_observation_matches_space(env, obs)


def test_image_env_space_uses_actual_reset_state_shape() -> None:
    env = GridUniverseEnv(
        initial_state_fn=build_level_basic_movement,
        render_resolution=70,
    )

    obs, _ = env.reset()

    assert isinstance(obs, dict)
    assert obs["image"].shape == (50, 70, 4)
    _assert_observation_matches_space(env, obs)


def test_env_reset_seed_overrides_initial_state_seed() -> None:
    env = GridUniverseEnv(
        initial_state_fn=generate,
        width=9,
        height=9,
        observation_type="gridstate",
    )

    env.reset(seed=1)
    assert env.state is not None
    first = _layout_signature(env.state)
    env.reset(seed=1)
    assert env.state is not None
    second = _layout_signature(env.state)
    env.reset(seed=2)
    assert env.state is not None
    third = _layout_signature(env.state)

    assert first == second
    assert first != third
