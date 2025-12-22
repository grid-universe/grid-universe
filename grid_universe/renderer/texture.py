"""Texture-based renderer utilities.

Transforms a ``State`` into a composited RGBA image using per-entity
``Appearance`` metadata, property-derived texture variants, optional group
recoloring and motion glyph overlays.

Rendering Model
---------------
1. Entities occupying the same cell are grouped into categories:
     * Background(s): ``appearance.background=True`` (e.g., floor, wall)
     * Main: highest-priority non-background entity
     * Corner Icons: up to four icon entities (``appearance.icon=True``) placed
         in tile corners (NW, NE, SW, SE)
     * Others: additional layered entities (drawn between background and main)
2. A texture path is chosen via an object + property signature lookup. If the
     path refers to a directory, a deterministic random selection occurs.
3. Group-based recoloring (e.g., matching keys and locks, portal pairs) applies
     a hue shift while preserving shading (value channel) and saturation rules.
4. Optional movement direction triangles are overlaid for moving entities.

Customization Hooks
-------------------
* Provide a custom ``texture_map`` for alternative asset packs.
* Replace or extend ``DEFAULT_GROUP_RULES`` to recolor other sets of entities.
* Supply ``tex_lookup_fn`` to implement caching, animation frames, or atlas
    packing.

Performance Notes
-----------------
* A lightweight cache key (path, size, group, movement vector, speed) helps
    reuse generated PIL images across frames.
* ``lru_cache`` on ``group_to_color`` ensures stable, deterministic colors
    without recomputing HSV conversions.
"""

from collections import defaultdict
from pathlib import Path
import colorsys
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Optional, Tuple, List
from PIL import Image
from pyrsistent import pmap
from grid_universe.components.properties.appearance import Appearance, AppearanceName
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.image import (
    draw_direction_triangles_on_image,
    recolor_image_keep_tone,
)
import os
import random


DEFAULT_RESOLUTION = 640
DEFAULT_SUBICON_PERCENT = 0.4
DEFAULT_ASSET_ROOT = os.path.join(Path(__file__).parent.parent.resolve(), "assets")

ObjectAsset = Tuple[AppearanceName, Tuple[str, ...]]


@dataclass(frozen=True)
class ObjectRendering:
    """Lightweight container capturing render-relevant entity facets.

    Attributes:
        appearance (Appearance): The entity's appearance component (or a default anonymous one).
        properties (Tuple[str, ...]): Property component collection names (e.g. ``('blocking', 'locked')``)
            used to select texture variants.
        group (str | None): Deterministic recolor group identifier.
        move_dir (tuple[int, int] | None): (dx, dy) direction for movement glyph overlay.
        move_speed (int): Movement speed (number of direction triangles to draw).
    """

    appearance: Appearance
    properties: Tuple[str, ...]
    group: Optional[str] = None
    move_dir: Optional[Tuple[int, int]] = None
    move_speed: int = 0

    def asset(self) -> ObjectAsset:
        return (self.appearance.name, self.properties)


ObjectName = str
ObjectProperty = str
ObjectPropertiesTextureMap = Dict[ObjectName, Dict[Tuple[ObjectProperty, ...], str]]

TexLookupFn = Callable[[ObjectRendering, int], Image.Image]
TextureMap = Dict[ObjectAsset, str]


# --- Built-in Texture Maps ---


IMAGEN1_TEXTURE_MAP: TextureMap = {
    (
        AppearanceName.HUMAN,
        tuple([]),
    ): "imagen1/human",
    (
        AppearanceName.HUMAN,
        tuple(["dead"]),
    ): "imagen1/sleeping",
    (AppearanceName.COIN, tuple([])): "imagen1/coin",
    (AppearanceName.CORE, tuple(["requirable"])): "imagen1/gem",
    (AppearanceName.BOX, tuple([])): "imagen1/metalbox",
    (AppearanceName.BOX, tuple(["pushable"])): "imagen1/box",
    (AppearanceName.MONSTER, tuple([])): "imagen1/robot",
    (
        AppearanceName.MONSTER,
        tuple(["pathfinding"]),
    ): "imagen1/wolf",
    (AppearanceName.KEY, tuple([])): "imagen1/key",
    (AppearanceName.PORTAL, tuple([])): "imagen1/portal",
    (AppearanceName.DOOR, tuple(["locked"])): "imagen1/locked",
    (AppearanceName.DOOR, tuple([])): "imagen1/opened",
    (AppearanceName.SHIELD, tuple(["immunity"])): "imagen1/shield",
    (AppearanceName.GHOST, tuple(["phasing"])): "imagen1/ghost",
    (AppearanceName.BOOTS, tuple(["speed"])): "imagen1/boots",
    (AppearanceName.SPIKE, tuple([])): "imagen1/spike",
    (AppearanceName.LAVA, tuple([])): "imagen1/lava",
    (AppearanceName.EXIT, tuple([])): "imagen1/exit",
    (AppearanceName.WALL, tuple([])): "imagen1/wall",
    (AppearanceName.FLOOR, tuple([])): "imagen1/floor",
}


KENNEY_TEXTURE_MAP: TextureMap = {
    (
        AppearanceName.HUMAN,
        tuple([]),
    ): "kenney/animated_characters/male_adventurer/maleAdventurer_idle.png",
    (
        AppearanceName.HUMAN,
        tuple(["dead"]),
    ): "kenney/animated_characters/zombie/zombie_fall.png",
    (AppearanceName.COIN, tuple([])): "kenney/items/coinGold.png",
    (AppearanceName.CORE, tuple(["requirable"])): "kenney/items/gold_1.png",
    (AppearanceName.BOX, tuple([])): "kenney/tiles/boxCrate.png",
    (AppearanceName.BOX, tuple(["pushable"])): "kenney/tiles/boxCrate_double.png",
    (AppearanceName.MONSTER, tuple([])): "kenney/enemies/slimeBlue.png",
    (
        AppearanceName.MONSTER,
        tuple(["pathfinding"]),
    ): "kenney/enemies/slimeBlue_move.png",
    (AppearanceName.KEY, tuple([])): "kenney/items/keyRed.png",
    (AppearanceName.PORTAL, tuple([])): "kenney/items/star.png",
    (AppearanceName.DOOR, tuple(["locked"])): "kenney/tiles/lockRed.png",
    (AppearanceName.DOOR, tuple([])): "kenney/tiles/doorClosed_mid.png",
    (AppearanceName.SHIELD, tuple(["immunity"])): "kenney/items/gemBlue.png",
    (AppearanceName.GHOST, tuple(["phasing"])): "kenney/items/gemGreen.png",
    (AppearanceName.BOOTS, tuple(["speed"])): "kenney/items/gemRed.png",
    (AppearanceName.SPIKE, tuple([])): "kenney/tiles/spikes.png",
    (AppearanceName.LAVA, tuple([])): "kenney/tiles/lava.png",
    (AppearanceName.EXIT, tuple([])): "kenney/tiles/signExit.png",
    (AppearanceName.WALL, tuple([])): "kenney/tiles/brickBrown.png",
    (AppearanceName.FLOOR, tuple([])): "kenney/tiles/brickGrey.png",
}

FUTURAMA_TEXTURE_MAP: TextureMap = {
    (
        AppearanceName.HUMAN,
        tuple([]),
    ): "futurama/character01",
    (
        AppearanceName.HUMAN,
        tuple(["dead"]),
    ): "futurama/character02",
    (AppearanceName.COIN, tuple([])): "futurama/character03",
    (AppearanceName.CORE, tuple(["requirable"])): "futurama/character04",
    (AppearanceName.BOX, tuple([])): "futurama/character06",
    (AppearanceName.BOX, tuple(["pushable"])): "futurama/character07",
    (AppearanceName.MONSTER, tuple([])): "futurama/character08",
    (AppearanceName.MONSTER, tuple(["pathfinding"])): "futurama/character09",
    (AppearanceName.KEY, tuple([])): "futurama/character10",
    (AppearanceName.PORTAL, tuple([])): "futurama/character11",
    (AppearanceName.DOOR, tuple(["locked"])): "futurama/character12",
    (AppearanceName.DOOR, tuple([])): "futurama/character13",
    (AppearanceName.SHIELD, tuple(["immunity"])): "futurama/character14",
    (AppearanceName.GHOST, tuple(["phasing"])): "futurama/character15",
    (AppearanceName.BOOTS, tuple(["speed"])): "futurama/character16",
    (AppearanceName.SPIKE, tuple([])): "futurama/character17",
    (AppearanceName.LAVA, tuple([])): "futurama/character18",
    (AppearanceName.EXIT, tuple([])): "futurama/character19",
    (AppearanceName.WALL, tuple([])): "futurama/character20",
    (AppearanceName.FLOOR, tuple([])): "futurama/blank.png",
}

DEFAULT_TEXTURE_MAP: TextureMap = IMAGEN1_TEXTURE_MAP

TEXTURE_MAP_REGISTRY: Dict[str, TextureMap] = {
    "imagen1": IMAGEN1_TEXTURE_MAP,
    "kenney": KENNEY_TEXTURE_MAP,
    "futurama": FUTURAMA_TEXTURE_MAP,
}


# --- Grouping Rules ---

GroupRule = Callable[[State, EntityID], Optional[str]]


def key_door_group_rule(state: State, eid: EntityID) -> Optional[str]:
    if eid in state.key:
        return f"key:{state.key[eid].key_id}"
    if eid in state.locked:
        return f"key:{state.locked[eid].key_id}"
    return None


def portal_pair_group_rule(state: State, eid: EntityID) -> Optional[str]:
    if eid not in state.portal:
        return None
    pair = state.portal[eid].pair_entity
    a, b = (eid, pair) if eid <= pair else (pair, eid)
    return f"portal:{a}-{b}"


DEFAULT_GROUP_RULES: List[GroupRule] = [
    key_door_group_rule,
    portal_pair_group_rule,
]


def derive_groups(
    state: State, rules: List[GroupRule] = DEFAULT_GROUP_RULES
) -> Dict[EntityID, Optional[str]]:
    """Apply grouping rules to each entity.

    Later rendering stages may use groups to recolor related entities with a
    shared hue (e.g., all portals in a pair share the same color while still
    using the original texture shading).

    Args:
        state (State): Immutable simulation state.
        rules (List[GroupRule]): Ordered list of functions; first non-None group returned is used.

    Returns:
        Dict[EntityID, str | None]: Mapping of entity id to chosen group id (or ``None`` if ungrouped).
    """
    rule_groups: dict[str, set[str]] = defaultdict(set)
    out: Dict[EntityID, Optional[str]] = {}
    for eid, _ in state.position.items():
        group: Optional[str] = None
        for rule in rules:
            group = rule(state, eid)
            if group is not None:
                rule_groups[rule.__name__].add(group)
                break
        out[eid] = group
    for groups in rule_groups.values():
        if len(groups) > 1:
            continue
        # remove singleton groups to avoid unnecessary recoloring
        for eid, group in out.items():
            if group in groups:
                out[eid] = None
    return out


@lru_cache(maxsize=2048)
def group_to_color(group_id: str) -> Tuple[int, int, int]:
    """Deterministically map a group string to an RGB color.

    Uses the group id as a seed to generate stable but visually distinct HSV
    values, then converts them to RGB.
    """
    rng = random.Random(group_id)
    h = rng.random()
    s = 0.6 + 0.3 * rng.random()
    v = 0.7 + 0.25 * rng.random()
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def apply_recolor_if_group(
    tex: Image.Image,
    group: Optional[str],
) -> Image.Image:
    """Recolor wrapper that sets hue to the group's color while preserving tone.

    Delegates to `recolor_image_keep_tone`; if no group is provided the
    texture is returned unchanged.
    """
    if group is None:
        return tex
    color = group_to_color(group)
    return recolor_image_keep_tone(tex, color)


@lru_cache(maxsize=4096)
def load_texture(path: str, size: int) -> Optional[Image.Image]:
    """Load and resize a texture, returning None if inaccessible or invalid."""
    try:
        return Image.open(path).convert("RGBA").resize((size, size))
    except Exception:
        return None


def get_object_renderings(
    state: State, eids: List[EntityID], groups: Dict[EntityID, Optional[str]]
) -> List[ObjectRendering]:
    """Build rendering descriptors for entity IDs in a single cell.

    Inspects component PMaps on the ``State`` to infer property labels,
    movement direction and speed, then packages them in ``ObjectRendering``
    objects for subsequent texture lookup and layering decisions.
    """
    renderings: List[ObjectRendering] = []
    default_appearance: Appearance = Appearance(name=AppearanceName.NONE)
    for eid in eids:
        appearance = state.appearance.get(eid, default_appearance)
        properties = tuple(
            [
                component
                for component, value in state.__dict__.items()
                if isinstance(value, type(pmap())) and eid in value
            ]
        )

        move_dir: Optional[Tuple[int, int]] = None
        move_speed: int = 0
        if eid in state.moving:
            m = state.moving[eid]
            if m.axis.name == "HORIZONTAL":
                move_dir = (1 if m.direction > 0 else -1, 0)
            else:
                move_dir = (0, 1 if m.direction > 0 else -1)
            move_speed = m.speed

        renderings.append(
            ObjectRendering(
                appearance=appearance,
                properties=properties,
                group=groups.get(eid),
                move_dir=move_dir,
                move_speed=move_speed,
            )
        )
    return renderings


def choose_background(object_renderings: List[ObjectRendering]) -> ObjectRendering:
    """
    Return the lowest-priority background object.
    Higher priority values indicate lower importance.

    Raises
    ------
    ValueError
        If no candidate background exists in the cell.
    """
    items = [
        object_rendering
        for object_rendering in object_renderings
        if object_rendering.appearance.background
    ]
    if len(items) == 0:
        raise ValueError(f"No matching background: {object_renderings}")
    return sorted(items, key=lambda x: x.appearance.priority)[
        -1
    ]  # take the lowest priority


def choose_main(object_renderings: List[ObjectRendering]) -> Optional[ObjectRendering]:
    """
    Return the highest-priority non-background object.
    Lower priority values indicate higher importance.

    Returns ``None`` if no non-background objects exist.
    """
    items = [
        object_rendering
        for object_rendering in object_renderings
        if not object_rendering.appearance.background
    ]
    if len(items) == 0:
        return None
    return sorted(items, key=lambda x: x.appearance.priority)[
        0
    ]  # take the highest priority


def choose_corner_icons(
    object_renderings: List[ObjectRendering], main: Optional[ObjectRendering]
) -> List[ObjectRendering]:
    """Return up to four icon objects (excluding main) sorted by priority."""
    items = set(
        [
            object_rendering
            for object_rendering in object_renderings
            if object_rendering.appearance.icon
        ]
    ) - set([main])
    return sorted(items, key=lambda x: x.appearance.priority)[
        :4
    ]  # take the highest priority


def get_path(
    object_asset: ObjectAsset, texture_hmap: ObjectPropertiesTextureMap
) -> str:
    """Resolve a texture path for an object asset signature.

    Attempts to find the nearest matching property tuple (maximizing shared
    properties, minimizing unmatched) to allow textures that only specify a
    subset of possible property labels.
    """
    object_name, object_properties = object_asset
    if object_name not in texture_hmap:
        raise ValueError(f"Object rendering {object_asset} is not found in texture map")
    nearest_object_properties = sorted(
        texture_hmap[object_name].keys(),
        key=lambda x: len(set(x).intersection(object_properties))
        - len(set(x) - set(object_properties)),
        reverse=True,
    )[0]
    return texture_hmap[object_name][nearest_object_properties]


def select_texture_from_directory(
    dir: str,
    seed: Optional[int],
) -> Optional[str]:
    """Choose a deterministic random texture file from a directory."""
    if not os.path.isdir(dir):
        return None

    try:
        entries = os.listdir(dir)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return None

    files = sorted(
        f for f in entries if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
    )
    if not files:
        return None

    rng = random.Random(seed)
    chosen = rng.choice(files)
    return os.path.join(dir, chosen)


def render(
    state: State,
    resolution: int = DEFAULT_RESOLUTION,
    subicon_percent: float = DEFAULT_SUBICON_PERCENT,
    texture_map: Optional[TextureMap] = None,
    asset_root: str = DEFAULT_ASSET_ROOT,
    tex_lookup_fn: Optional[TexLookupFn] = None,
    cache: Optional[
        Dict[
            Tuple[str, int, Optional[str], Optional[Tuple[int, int]], int],
            Optional[Image.Image],
        ]
    ] = None,
) -> Image.Image:
    """Render a ``State`` into a PIL Image.

    Args:
        state (State): Immutable game state to visualize.
        resolution (int): Output image width in pixels (height derived from aspect ratio).
        subicon_percent (float): Relative size of corner icons compared to a cell's size.
        texture_map (TextureMap | None): Mapping from ``(appearance name, property tuple)`` to asset path.
        asset_root (str): Root directory containing the asset hierarchy (e.g. ``"assets"``).
        tex_lookup_fn (TexLookupFn | None): Override for texture loading/recoloring/overlay logic.
        cache (dict | None): Mutable memoization dict keyed by ``(path, size, group, move_dir, speed)``.

    Returns:
        Image.Image: Composited RGBA image of the entire grid.
    """
    cell_size: int = resolution // state.width
    subicon_size: int = int(cell_size * subicon_percent)

    if texture_map is None:
        texture_map = DEFAULT_TEXTURE_MAP

    if cache is None:
        cache = {}

    texture_hmap: ObjectPropertiesTextureMap = defaultdict(dict)
    for (obj_name, obj_properties), value in texture_map.items():
        texture_hmap[obj_name][tuple(obj_properties)] = value

    width, height = state.width, state.height
    img = Image.new(
        "RGBA", (width * cell_size, height * cell_size), (128, 128, 128, 255)
    )

    state_rng = random.Random(state.seed)
    object_seeds = [state_rng.randint(0, 2**31) for _ in range(len(texture_map))]
    texture_map_values = list(texture_map.values())
    value_to_first_index = {v: i for i, v in enumerate(texture_map_values)}
    groups = derive_groups(state)

    def default_get_tex(
        object_rendering: ObjectRendering, size: int
    ) -> Optional[Image.Image]:
        path = get_path(object_rendering.asset(), texture_hmap)
        if not path:
            return None

        asset_path = f"{asset_root}/{path}"
        if os.path.isdir(asset_path):
            asset_index = value_to_first_index[path]
            selected_asset_path = select_texture_from_directory(
                asset_path, object_seeds[asset_index]
            )
            if selected_asset_path is None:
                return None
            asset_path = selected_asset_path

        key = (
            asset_path,
            size,
            object_rendering.group,
            object_rendering.move_dir,
            object_rendering.move_speed,
        )
        if key in cache:
            return cache[key]

        texture = load_texture(asset_path, size)
        if texture is None:
            return None

        texture = apply_recolor_if_group(texture, object_rendering.group)
        if object_rendering.move_dir is not None and object_rendering.move_speed > 0:
            dx, dy = object_rendering.move_dir
            texture = draw_direction_triangles_on_image(
                texture.copy(), size, dx, dy, object_rendering.move_speed
            )

        cache[key] = texture
        return texture

    tex_lookup = tex_lookup_fn or default_get_tex

    grid_entities: Dict[Tuple[int, int], List[EntityID]] = {}
    for eid, pos in state.position.items():
        grid_entities.setdefault((pos.x, pos.y), []).append(eid)

    for (x, y), eids in grid_entities.items():
        x0, y0 = x * cell_size, y * cell_size

        object_renderings = get_object_renderings(state, eids, groups)

        background = choose_background(object_renderings)
        main = choose_main(object_renderings)
        corner_icons = choose_corner_icons(object_renderings, main)
        others = list(
            set(object_renderings) - set([main] + corner_icons + [background])
        )

        primary_renderings: List[ObjectRendering] = (
            [background] + others + ([main] if main is not None else [])
        )

        for object_rendering in primary_renderings:
            object_tex = tex_lookup(object_rendering, cell_size)
            if object_tex:
                img.alpha_composite(object_tex, (x0, y0))

        for idx, corner_icon in enumerate(corner_icons[:4]):
            dx = x0 + (cell_size - subicon_size if idx % 2 == 1 else 0)
            dy = y0 + (cell_size - subicon_size if idx // 2 == 1 else 0)
            tex = tex_lookup(corner_icon, subicon_size)
            if tex:
                img.alpha_composite(tex, (dx, dy))

    return img


class TextureRenderer:
    resolution: int
    subicon_percent: float
    texture_map: TextureMap
    asset_root: str
    tex_lookup_fn: Optional[TexLookupFn]

    def __init__(
        self,
        resolution: int = DEFAULT_RESOLUTION,
        subicon_percent: float = DEFAULT_SUBICON_PERCENT,
        texture_map: Optional[TextureMap] = None,
        asset_root: str = DEFAULT_ASSET_ROOT,
        tex_lookup_fn: Optional[TexLookupFn] = None,
    ):
        self.resolution = resolution
        self.subicon_percent = subicon_percent
        self.texture_map = texture_map or DEFAULT_TEXTURE_MAP
        self.asset_root = asset_root
        self.tex_lookup_fn = tex_lookup_fn

    def render(self, state: State) -> Image.Image:
        """Render convenience wrapper using stored configuration."""
        return render(
            state,
            resolution=self.resolution,
            subicon_percent=self.subicon_percent,
            texture_map=self.texture_map,
            asset_root=self.asset_root,
            tex_lookup_fn=self.tex_lookup_fn,
        )
