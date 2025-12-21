"""Gymnasium environment wrapper for Grid Universe.

Provides a structured observation that pairs a rendered RGBA image with rich
info dictionaries (agent status / inventory / active effects, environment
config). Reward is the delta of ``state.score`` per step. ``terminated`` is
``True`` on win, ``truncated`` on lose.

Observation schema (see docs for full details):

```python
{
    "image": np.ndarray(H,W,4),
    "info": {
            "agent": {...},
            "status": {...},
            "config": {...},
            "message": str  # empty string if None
    }
}
```

or

```python
Level  # if observation_type="level"
```

Usage:

```python
from grid_universe.gym_env import GridUniverseEnv
from grid_universe.examples.maze import generate as maze_generate

env = GridUniverseEnv(initial_state_fn=maze_generate, width=9, height=9, seed=123)
```

Customization hooks:
    * ``initial_state_fn``: Provide a callable that returns a fully built ``State``.
    * ``render_texture_map`` / resolution let you swap assets or resolution.

The environment is purposely *not* vectorized; wrap externally if needed.
"""

import string
import gymnasium as gym
from gymnasium import spaces

import numpy as np
from typing import Callable, Optional, Dict, Tuple, Any, List, TypedDict, cast, Union
from numpy.typing import NDArray

from PIL.Image import Image as PILImage

from grid_universe.state import State
from grid_universe.levels.convert import from_state  # for Level observation type
from grid_universe.levels.grid import (
    Level,
)
from grid_universe.actions import Action as Action
from grid_universe.renderer.texture import (
    DEFAULT_ASSET_ROOT,
    DEFAULT_RESOLUTION,
    DEFAULT_TEXTURE_MAP,
    TextureRenderer,
    TextureMap,
)
from grid_universe.step import step
from grid_universe.types import EffectLimit, EffectType, EntityID


class EffectEntry(TypedDict):
    """Single active effect entry.

    Fields use sentinel defaults in the runtime observation:
      * Empty string ("") for absent text fields.
      * -1 for numeric fields that are logically None / not applicable.
    """

    id: int  # Unique effect entity id
    type: str  # "" | "IMMUNITY" | "PHASING" | "SPEED"
    limit_type: str  # "" | "TIME" | "USAGE"
    limit_amount: int  # -1 if no limit
    multiplier: int  # Speed multiplier (or -1 if not SPEED)


class InventoryItem(TypedDict):
    """Inventory item entry (key / core / coin / generic item)."""

    id: int
    type: str  # "key" | "core" | "coin" | "item"
    key_id: str  # "" if not a key
    appearance_name: str  # "" if not known / provided


class HealthInfo(TypedDict):
    """Health block; -1 indicates missing (agent has no health component)."""

    health: int
    max_health: int


class AgentInfo(TypedDict):
    """Agent sub‑observation grouping health, effects and inventory."""

    health: HealthInfo
    effects: List[EffectEntry]
    inventory: List[InventoryItem]


class StatusInfo(TypedDict):
    """Environment status (score, phase, current turn)."""

    score: int
    phase: str  # "win" | "lose" | "ongoing"
    turn: int


class ConfigInfo(TypedDict):
    """Static / semi‑static config describing the active level & functions."""

    move_fn: str
    objective_fn: str
    seed: int  # -1 if None
    width: int
    height: int
    turn_limit: int  # -1 if unlimited


class InfoDict(TypedDict):
    """Full structured info payload accompanying every observation."""

    agent: AgentInfo
    status: StatusInfo
    config: ConfigInfo
    message: str  # Narrative / status message ("" if none)


ImageArray = NDArray[np.uint8]


class Observation(TypedDict):
    """Top‑level observation returned by the environment.

    image: RGBA image array (H x W x 4, dtype=uint8)
    info:  Rich structured dictionaries (see :class:`InfoDict`).
    """

    image: ImageArray
    info: InfoDict


def _serialize_effect(state: State, effect_id: EntityID) -> Dict[str, Any]:
    """Serialize an effect entity.

    Args:
        state (State): Current state snapshot.
        effect_id (EntityID): Entity id for the effect object.

    Returns:
        Dict[str, Any]: JSON‑friendly payload with id, type, limit metadata and
            speed multiplier if applicable.
    """
    # Start with sentinel defaults to guarantee presence of every field
    effect_type: str = ""
    limit_type: str = ""  # TIME | USAGE | ""
    limit_amount: int = -1
    multiplier: int = -1

    if effect_id in state.immunity:
        effect_type = EffectType.IMMUNITY.name
    elif effect_id in state.phasing:
        effect_type = EffectType.PHASING.name
    elif effect_id in state.speed:
        effect_type = EffectType.SPEED.name
        try:
            multiplier = int(state.speed[effect_id].multiplier)
        except Exception:
            multiplier = -1

    # Limits: usage takes precedence if both present
    if effect_id in state.time_limit:
        limit_type = EffectLimit.TIME.name
        try:
            limit_amount = int(state.time_limit[effect_id].amount)
        except Exception:
            limit_amount = -1
    if effect_id in state.usage_limit:
        limit_type = EffectLimit.USAGE.name
        try:
            limit_amount = int(state.usage_limit[effect_id].amount)
        except Exception:
            limit_amount = -1

    return {
        "id": int(effect_id),
        "type": effect_type,
        "limit_type": limit_type,
        "limit_amount": limit_amount,
        "multiplier": multiplier,
    }


def _serialize_inventory_item(state: State, item_id: EntityID) -> Dict[str, Any]:
    """Serialize an inventory item (key / collectible / generic).

    Returns type categorization plus optional appearance hint.
    """
    item: Dict[str, Any] = {
        "id": int(item_id),
        "type": "item",  # default
        "key_id": "",  # sentinel empty string
        "appearance_name": "",  # sentinel empty string
    }
    # Key?
    if item_id in state.key:
        item["type"] = "key"
        try:
            item["key_id"] = str(state.key[item_id].key_id)
        except Exception:
            item["key_id"] = ""
    # Collectibles (categorize core vs coin if we can)
    elif item_id in state.collectible:
        if item_id in state.requirable:
            item["type"] = "core"
        else:
            item["type"] = "coin"
    # Appearance (optional extra metadata)
    if item_id in state.appearance:
        try:
            item["appearance_name"] = state.appearance[item_id].name.name
        except Exception:
            item["appearance_name"] = ""
    return item


def agent_observation_dict(state: State, agent_id: EntityID) -> AgentInfo:
    """Compose structured agent sub‑observation.

    Includes health, list of active effect entries, and inventory items.
    Missing health is represented by ``None`` values which are later converted
    to sentinel numbers in the space definition (-1) when serialized to numpy
    arrays (Gym leaves them as ints here).
    """
    # Health
    hp = state.health.get(agent_id)
    health_dict: Dict[str, Any] = {
        "health": int(hp.health) if hp else -1,
        "max_health": int(hp.max_health) if hp else -1,
    }

    # Active effects (status)
    effects: List[Dict[str, Any]] = []
    status = state.status.get(agent_id)
    if status is not None:
        for eff_id in status.effect_ids:
            effects.append(_serialize_effect(state, eff_id))

    # Inventory items
    inv_items: List[Dict[str, Any]] = []
    inv = state.inventory.get(agent_id)
    if inv:
        for item_eid in inv.item_ids:
            inv_items.append(_serialize_inventory_item(state, item_eid))

    return cast(
        AgentInfo,
        {
            "health": health_dict,
            "effects": tuple(effects),
            "inventory": tuple(inv_items),
        },
    )


def env_status_observation_dict(state: State) -> StatusInfo:
    """Status portion of observation (score, phase, turn)."""
    # Derive phase for clarity
    phase = "ongoing"
    if state.win:
        phase = "win"
    elif state.lose:
        phase = "lose"
    return cast(
        StatusInfo,
        {
            "score": int(state.score),
            "phase": phase,
            "turn": int(state.turn),
        },
    )


def env_config_observation_dict(state: State) -> ConfigInfo:
    """Config portion of observation (function names, seed, dimensions)."""
    move_fn_name = getattr(state.move_fn, "__name__", str(state.move_fn))
    objective_fn_name = getattr(state.objective_fn, "__name__", str(state.objective_fn))
    return cast(
        ConfigInfo,
        {
            "move_fn": move_fn_name,
            "objective_fn": objective_fn_name,
            "seed": state.seed if state.seed is not None else -1,
            "width": state.width,
            "height": state.height,
            "turn_limit": state.turn_limit if state.turn_limit is not None else -1,
        },
    )


class GridUniverseEnv(gym.Env[Union[Observation, Level], np.integer]):
    """Gymnasium ``Env`` implementation for the Grid Universe.

    Parameters mirror the procedural level generator plus rendering knobs. The
    action space is ``Discrete(len(Action))``; see :mod:`grid_universe.actions`.
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        initial_state_fn: Callable[..., State],
        render_mode: str = "rgb_array",
        render_resolution: int = DEFAULT_RESOLUTION,
        render_texture_map: TextureMap = DEFAULT_TEXTURE_MAP,
        render_asset_root: str = DEFAULT_ASSET_ROOT,
        observation_type: str = "image",
        **kwargs: Any,
    ):
        """Create a new environment instance.

        Args:
            render_mode (str): "rgb_array" to return PIL image frames, "human" to open a window.
            render_resolution (int): Width (pixels) of rendered image (height derived).
            render_texture_map (TextureMap): Mapping of ``(AppearanceName, properties)`` to asset paths.
            initial_state_fn (Callable[..., State]): Callable returning an initial ``State``.
            **kwargs: Forwarded to ``initial_state_fn`` (e.g., size, densities, seed).
        """
        # Observation type: "image" (default behavior) or "level" (returns Level dataclass)
        if observation_type not in {"image", "level"}:
            raise ValueError(
                f"Unsupported observation_type '{observation_type}'. Expected 'image' or 'level'."
            )
        self._observation_type = observation_type

        # Generator/config kwargs for level creation
        self._initial_state_fn = initial_state_fn
        self._initial_state_kwargs = kwargs

        # Runtime state
        self.state: Optional[State] = None
        self.agent_id: Optional[EntityID] = None

        # Basic config
        self.width: int = int(kwargs.get("width", 9))
        self.height: int = int(kwargs.get("height", 9))
        self._render_resolution = render_resolution
        self._render_texture_map = render_texture_map
        self._render_asset_root = render_asset_root
        self._render_mode = render_mode

        # Rendering setup
        render_width: int = render_resolution
        render_height: int = int(self.height / self.width * render_width)
        self._texture_renderer: Optional[TextureRenderer] = None

        # Observation space helpers (Gymnasium has no Integer/Optional)
        base_chars = (
            string.ascii_lowercase + string.ascii_uppercase + string.digits + "_"
        )
        text_space_short = spaces.Text(
            max_length=32, min_length=0, charset=base_chars
        )  # enums
        text_space_medium = spaces.Text(
            max_length=128, min_length=0, charset=base_chars
        )  # fn names
        text_space_long = spaces.Text(
            max_length=512, min_length=0, charset=string.printable
        )

        def int_box(low: int, high: int) -> spaces.Box:
            return spaces.Box(
                low=np.array(low, dtype=np.int64),
                high=np.array(high, dtype=np.int64),
                shape=(),
                dtype=np.int64,
            )

        # Effect entry: use "" for absent strings, -1 for absent numbers
        effect_space = spaces.Dict(
            {
                "id": int_box(0, 1_000_000_000),
                "type": text_space_short,  # "", "IMMUNITY", "PHASING", "SPEED"
                "limit_type": text_space_short,  # "", "TIME", "USAGE"
                "limit_amount": int_box(-1, 1_000_000_000),  # -1 if none
                "multiplier": int_box(-1, 1_000_000),  # -1 if N/A (only SPEED)
            }
        )

        # Inventory item: type in {"key","core","coin","item"}; empty strings for optional text
        item_space = spaces.Dict(
            {
                "id": int_box(0, 1_000_000_000),
                "type": text_space_short,
                "key_id": text_space_medium,  # "" if not a key
                "appearance_name": text_space_short,  # "" if unknown
            }
        )

        # Health: -1 to indicate missing
        health_space = spaces.Dict(
            {
                "health": int_box(-1, 1_000_000),
                "max_health": int_box(-1, 1_000_000),
            }
        )

        if self._observation_type == "image":
            # Full observation space: image + structured info dict
            self.observation_space = cast(
                gym.Space[Observation],
                spaces.Dict(
                    {
                        "image": spaces.Box(
                            low=0,
                            high=255,
                            shape=(render_height, render_width, 4),
                            dtype=np.uint8,
                        ),
                        "info": spaces.Dict(
                            {
                                "agent": spaces.Dict(
                                    {
                                        "health": health_space,
                                        "effects": spaces.Sequence(effect_space),
                                        "inventory": spaces.Sequence(item_space),
                                    }
                                ),
                                "status": spaces.Dict(
                                    {
                                        "score": int_box(-1_000_000_000, 1_000_000_000),
                                        "phase": text_space_short,  # "win" / "lose" / "ongoing"
                                        "turn": int_box(0, 1_000_000_000),
                                    }
                                ),
                                "config": spaces.Dict(
                                    {
                                        "move_fn": text_space_medium,
                                        "objective_fn": text_space_medium,
                                        "seed": int_box(
                                            -1_000_000_000, 1_000_000_000
                                        ),  # use -1 to represent None if needed
                                        "width": int_box(1, 10_000),
                                        "height": int_box(1, 10_000),
                                        "turn_limit": int_box(-1, 1_000_000_000),
                                    }
                                ),
                                "message": text_space_long,
                            }
                        ),
                    }
                ),
            )
        else:
            # For Level observations we cannot define a strict Gym space (arbitrary Python object).
            # Provide a placeholder space (Discrete(1)) with documented contract that observations are Level.
            # Users leveraging RL libraries should stick to observation_type="image".
            self.observation_space = spaces.Discrete(1)

        # Actions
        self.action_space = spaces.Discrete(len(Action))

        # Initialize first episode
        self.reset()

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict[str, object]] = None
    ) -> Tuple[Union[Observation, Level], Dict[str, object]]:
        """Start a new episode.

        Args:
            seed (int | None): Currently unused (procedural seed is passed via kwargs on construction).
            options (dict | None): Gymnasium options (unused).

        Returns:
            Tuple[Observation, dict]: Observation dict and empty info dict per Gymnasium API.
        """
        self.state = self._initial_state_fn(**self._initial_state_kwargs)
        self.agent_id = next(iter(self.state.agent.keys()))
        if self._observation_type == "image":
            self._setup_renderer()
        obs = self._get_obs()
        return obs, self._get_info()

    def step(
        self, action: np.integer | int | Action
    ) -> Tuple[Union[Observation, Level], float, bool, bool, Dict[str, object]]:
        """Apply one environment step.

        Args:
            action (int | np.integer | Action): Integer index (or ``Action`` enum
                member) selecting an action from the discrete action space.

        Returns:
            Tuple[Observation, float, bool, bool, dict]: ``(observation, reward, terminated, truncated, info)``.
        """
        assert self.state is not None and self.agent_id is not None

        step_action: Action = Action.WAIT  # default fallback

        if isinstance(action, Action):
            step_action = action
        else:
            # Try coercing to int (covers plain int and numpy integer). If this fails, raise.
            try:
                action_index = int(action)
            except Exception as exc:
                raise TypeError(
                    f"Action must be int-compatible or Action; got {type(action)!r}"
                ) from exc

            if not 0 <= action_index < len(Action):
                raise ValueError(
                    f"Invalid action index {action_index}; expected 0..{len(Action) - 1}"
                )

            step_action = list(Action)[action_index]

        prev_score = self.state.score
        self.state = step(self.state, step_action, agent_id=self.agent_id)
        reward = float(self.state.score - prev_score)
        obs = self._get_obs()
        terminated = self.state.win
        truncated = self.state.lose
        info = self._get_info()
        return obs, reward, terminated, truncated, info

    def render(self, mode: Optional[str] = None) -> Optional[PILImage]:  # type: ignore
        """Render the current state.

        Args:
            mode (str | None): "human" to display, "rgb_array" to return PIL image. Defaults to
                the instance's configured render mode.
        """
        render_mode = mode or self._render_mode
        assert self.state is not None
        self._setup_renderer()
        assert self._texture_renderer is not None
        img = self._texture_renderer.render(self.state)
        if render_mode == "human":
            img.show()
            return None
        elif render_mode == "rgb_array":
            return img
        else:
            raise NotImplementedError(f"Render mode '{render_mode}' not supported.")

    def state_info(self) -> InfoDict:
        """Return structured ``info`` sub-dict used in observations."""
        assert self.state is not None and self.agent_id is not None
        info_dict: InfoDict = {
            "agent": agent_observation_dict(self.state, self.agent_id),
            "status": env_status_observation_dict(self.state),
            "config": env_config_observation_dict(self.state),
            "message": self.state.message or "",
        }
        return info_dict

    def _get_obs(self) -> Union[Observation, Level]:
        """Internal helper constructing the observation per observation_type.

        observation_type="image": returns Observation (dict with image + info)
        observation_type="level": returns a mutable ``Level`` object produced
            via levels.convert.from_state(state). This allows algorithms to
            reason over symbolic grid/entity structures directly.
        """
        assert self.state is not None and self.agent_id is not None
        if self._observation_type == "level":
            # Return mutable Level view
            return from_state(self.state)

        # Default image observation path
        self._setup_renderer()
        assert self._texture_renderer is not None
        img = self._texture_renderer.render(self.state)
        img_np: ImageArray = np.array(img)
        info_dict: InfoDict = self.state_info()
        return cast(Observation, {"image": img_np, "info": info_dict})

    def _get_info(self) -> Dict[str, object]:
        """Return the step info (empty placeholder for compatibility)."""
        return {}

    def _setup_renderer(self) -> None:
        """(Re)initialize the texture renderer if needed."""
        if self._texture_renderer is None:
            self._texture_renderer = TextureRenderer(
                resolution=self._render_resolution,
                texture_map=self._render_texture_map,
                asset_root=self._render_asset_root,
            )

    def close(self) -> None:
        """Release any renderer resources (no-op placeholder)."""
        pass
