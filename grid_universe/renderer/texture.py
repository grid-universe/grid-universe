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
from grid_universe.components.properties.appearance import Appearance
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

ObjectAsset = Tuple[str, Tuple[str, ...]]


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
    ("human", tuple([])): "imagen1/human",
    ("human", tuple(["dead"])): "imagen1/sleeping",
    ("coin", tuple([])): "imagen1/coin",
    ("core", tuple(["requirable"])): "imagen1/gem",
    ("box", tuple([])): "imagen1/metalbox",
    ("box", tuple(["pushable"])): "imagen1/box",
    ("monster", tuple([])): "imagen1/robot",
    ("monster", tuple(["pathfinding"])): "imagen1/wolf",
    ("key", tuple([])): "imagen1/key",
    ("portal", tuple([])): "imagen1/portal",
    ("door", tuple(["locked"])): "imagen1/locked",
    ("door", tuple([])): "imagen1/opened",
    ("shield", tuple(["immunity"])): "imagen1/shield",
    ("ghost", tuple(["phasing"])): "imagen1/ghost",
    ("boots", tuple(["speed"])): "imagen1/boots",
    ("spike", tuple([])): "imagen1/spike",
    ("lava", tuple([])): "imagen1/lava",
    ("exit", tuple([])): "imagen1/exit",
    ("wall", tuple([])): "imagen1/wall",
    ("floor", tuple([])): "imagen1/floor",
}


KENNEY_TEXTURE_MAP: TextureMap = {
    (
        "human",
        tuple([]),
    ): "kenney/animated_characters/male_adventurer/maleAdventurer_idle.png",
    ("human", tuple(["dead"])): "kenney/animated_characters/zombie/zombie_fall.png",
    ("coin", tuple([])): "kenney/items/coinGold.png",
    ("core", tuple(["requirable"])): "kenney/items/gold_1.png",
    ("box", tuple([])): "kenney/tiles/boxCrate.png",
    ("box", tuple(["pushable"])): "kenney/tiles/boxCrate_double.png",
    ("monster", tuple([])): "kenney/enemies/slimeBlue.png",
    ("monster", tuple(["pathfinding"])): "kenney/enemies/slimeBlue_move.png",
    ("key", tuple([])): "kenney/items/keyRed.png",
    ("portal", tuple([])): "kenney/items/star.png",
    ("door", tuple(["locked"])): "kenney/tiles/lockRed.png",
    ("door", tuple([])): "kenney/tiles/doorClosed_mid.png",
    ("shield", tuple(["immunity"])): "kenney/items/gemBlue.png",
    ("ghost", tuple(["phasing"])): "kenney/items/gemGreen.png",
    ("boots", tuple(["speed"])): "kenney/items/gemRed.png",
    ("spike", tuple([])): "kenney/tiles/spikes.png",
    ("lava", tuple([])): "kenney/tiles/lava.png",
    ("exit", tuple([])): "kenney/tiles/signExit.png",
    ("wall", tuple([])): "kenney/tiles/brickBrown.png",
    ("floor", tuple([])): "kenney/tiles/brickGrey.png",
}

FUTURAMA_TEXTURE_MAP: TextureMap = {
    ("human", tuple([])): "futurama/character01",
    ("human", tuple(["dead"])): "futurama/character02",
    ("coin", tuple([])): "futurama/character03",
    ("core", tuple(["requirable"])): "futurama/character04",
    ("box", tuple([])): "futurama/character06",
    ("box", tuple(["pushable"])): "futurama/character07",
    ("monster", tuple([])): "futurama/character08",
    ("monster", tuple(["pathfinding"])): "futurama/character09",
    ("key", tuple([])): "futurama/character10",
    ("portal", tuple([])): "futurama/character11",
    ("door", tuple(["locked"])): "futurama/character12",
    ("door", tuple([])): "futurama/character13",
    ("shield", tuple(["immunity"])): "futurama/character14",
    ("ghost", tuple(["phasing"])): "futurama/character15",
    ("boots", tuple(["speed"])): "futurama/character16",
    ("spike", tuple([])): "futurama/character17",
    ("lava", tuple([])): "futurama/character18",
    ("exit", tuple([])): "futurama/character19",
    ("wall", tuple([])): "futurama/character20",
    ("floor", tuple([])): "futurama/blank.png",
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
    default_appearance: Appearance = Appearance(name="none")
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


def validate_appearance_names(state: State, texture_map: TextureMap) -> None:
    """Validate that all appearance names in the state have a corresponding texture.

    Raises:
        ValueError: If any appearance name in the state is missing from the texture map.
    """
    appearance_names_in_state = set(
        appearance.name for appearance in state.appearance.values()
    )
    appearance_names_in_texture_map = set(name for (name, _) in texture_map.keys())
    missing_names = appearance_names_in_state - appearance_names_in_texture_map
    if missing_names:
        raise ValueError(f"Missing appearance names in texture map: {missing_names}")


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
    render_width: int = cell_size * state.width
    render_height: int = cell_size * state.height
    target_width: int = resolution
    target_height: int = (resolution * state.height) // state.width

    if texture_map is None:
        texture_map = DEFAULT_TEXTURE_MAP

    validate_appearance_names(state, texture_map)

    if cache is None:
        cache = {}

    texture_hmap: ObjectPropertiesTextureMap = defaultdict(dict)
    for (obj_name, obj_properties), value in texture_map.items():
        texture_hmap[obj_name][tuple(obj_properties)] = value

    img = Image.new("RGBA", (render_width, render_height), (128, 128, 128, 255))

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

    # Resize to target resolution if needed
    if (render_width, render_height) != (target_width, target_height):
        img = img.resize((target_width, target_height), resample=Image.NEAREST)

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
