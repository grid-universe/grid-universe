"""Image-based renderer utilities.

Transforms a ``State`` into a composited RGBA image using per-entity
``Appearance`` metadata, property-derived image variants, optional group
recoloring and motion glyph overlays.

Rendering Model
---------------
1. Entities occupying the same cell are grouped into categories:
     * Base floor: rendered under every cell.
     * Background(s): ``appearance.background=True`` (e.g., wall)
     * Main: highest-priority non-background entity
     * Corner Icons: up to four icon entities (``appearance.icon=True``) placed
         in tile corners (NW, NE, SW, SE)
     * Others: additional layered entities (drawn between background and main)
2. A image path is chosen via an object + property signature lookup. If the
     path refers to a directory, a deterministic random selection occurs.
3. Group-based recoloring (e.g., matching keys and locks, portal pairs) applies
     a hue shift while preserving shading (value channel) and saturation rules.
4. Optional movement direction triangles are overlaid for moving entities.

Customization Hooks
-------------------
* Provide a custom ``image_map`` for alternative asset packs.
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
from collections.abc import Callable
from pathlib import Path
import colorsys
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from PIL import Image
from grid_universe.components.properties.appearance import Appearance
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.image import (
    draw_direction_triangles_on_image,
    recolor_image_keep_tone,
)
from grid_universe.utils.ds import HashableDict
import os
import random


DEFAULT_RESOLUTION = 640
DEFAULT_SUBICON_PERCENT = 0.4
DEFAULT_ASSET_ROOT = os.path.join(Path(__file__).parent.parent.resolve(), "assets")

ObjectAsset = tuple[str, tuple[str, ...]]


@dataclass(frozen=True)
class ObjectRendering:
    """Lightweight container capturing render-relevant entity facets.

    Attributes:
        appearance (Appearance): The entity's appearance component (or a default anonymous one).
        properties (Tuple[str, ...]): Property component collection names (e.g. ``('blocking', 'locked')``)
            used to select image variants.
        group (str | None): Deterministic recolor group identifier.
        move_dir (tuple[int, int] | None): (dx, dy) direction for movement glyph overlay.
        move_speed (int): Movement speed (number of direction triangles to draw).
    """

    appearance: Appearance
    properties: tuple[str, ...]
    group: str | None = None
    move_dir: tuple[int, int] | None = None
    move_speed: int = 0

    def asset(self) -> ObjectAsset:
        return (self.appearance.name, self.properties)


ObjectName = str
ObjectProperty = str
ObjectPropertiesImageMap = dict[ObjectName, dict[tuple[ObjectProperty, ...], str]]

TexLookupFn = Callable[[ObjectRendering, int], Image.Image | None]
ImageMap = HashableDict[ObjectAsset, str]
TexCacheKey = tuple[str, int, str | None, tuple[int, int] | None, int]
BaseCacheKey = tuple[int, int, int, str | None, int]

FLOOR_RENDERING = ObjectRendering(
    appearance=Appearance(name="floor", background=True, priority=10),
    properties=tuple(),
)


# --- Built-in Image Maps ---


IMAGEN1_IMAGE_MAP: ImageMap = ImageMap(
    {
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
)


KENNEY_IMAGE_MAP: ImageMap = ImageMap(
    {
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
)

FUTURAMA_IMAGE_MAP: ImageMap = ImageMap(
    {
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
)

DEFAULT_IMAGE_MAP: ImageMap = IMAGEN1_IMAGE_MAP

IMAGE_MAP_REGISTRY: dict[str, ImageMap] = {
    "imagen1": IMAGEN1_IMAGE_MAP,
    "kenney": KENNEY_IMAGE_MAP,
    "futurama": FUTURAMA_IMAGE_MAP,
}


# --- Grouping Rules ---

GroupRule = Callable[[State, EntityID], str | None]


def key_door_group_rule(state: State, eid: EntityID) -> str | None:
    if eid in state.key:
        return f"key:{state.key[eid].key_id}"
    if eid in state.locked:
        return f"key:{state.locked[eid].key_id}"
    return None


def portal_pair_group_rule(state: State, eid: EntityID) -> str | None:
    if eid not in state.portal:
        return None
    pair = state.portal[eid].pair_entity
    a, b = (eid, pair) if eid <= pair else (pair, eid)
    return f"portal:{a}-{b}"


DEFAULT_GROUP_RULES: list[GroupRule] = [
    key_door_group_rule,
    portal_pair_group_rule,
]


def derive_groups(
    state: State, rules: list[GroupRule] = DEFAULT_GROUP_RULES
) -> dict[EntityID, str | None]:
    """Apply grouping rules to each entity.

    Later rendering stages may use groups to recolor related entities with a
    shared hue (e.g., all portals in a pair share the same color while still
    using the original image shading).

    Args:
        state (State): Simulation state.
        rules (List[GroupRule]): Ordered list of functions; first non-None group returned is used.

    Returns:
        Dict[EntityID, str | None]: Mapping of entity id to chosen group id (or ``None`` if ungrouped).
    """
    rule_groups: dict[str, set[str]] = defaultdict(set)
    out: dict[EntityID, str | None] = {}
    for eid, _ in state.position.items():
        group: str | None = None
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
def group_to_color(group_id: str) -> tuple[int, int, int]:
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
    group: str | None,
) -> Image.Image:
    """Recolor wrapper that sets hue to the group's color while preserving tone.

    Delegates to `recolor_image_keep_tone`; if no group is provided the
    image is returned unchanged.
    """
    if group is None:
        return tex
    color = group_to_color(group)
    return recolor_image_keep_tone(tex, color)


@lru_cache(maxsize=4096)
def load_image(path: str, size: int) -> Image.Image | None:
    """Load and resize an image, returning None if inaccessible or invalid."""
    try:
        return Image.open(path).convert("RGBA").resize((size, size))
    except Exception:
        return None


def get_eid_properties_map(state: State) -> dict[EntityID, tuple[str, ...]]:
    """Build a mapping from eid to its component store names efficiently."""
    eid_to_props: dict[EntityID, list[str]] = {}
    # Identify component stores once (avoid scanning __dict__ per eid)
    component_store_names: list[str] = []
    for name, value in state.__dict__.items():
        if isinstance(value, dict) and not name.startswith("_"):
            component_store_names.append(name)

    for store_name in component_store_names:
        store: dict[EntityID, Any] = getattr(state, store_name)
        # Iterate keys once; append store_name to that eid’s props
        for eid in store.keys():
            lst = eid_to_props.get(eid)
            if lst is None:
                eid_to_props[eid] = [store_name]
            else:
                lst.append(store_name)

    # Ensure all positioned eids exist (even if no components beyond position)
    for eid in state.position.keys():
        eid_to_props.setdefault(eid, [])

    return {eid: tuple(props) for eid, props in eid_to_props.items()}


def get_object_renderings(
    state: State,
    eids: list[EntityID],
    groups: dict[EntityID, str | None],
    eid_properties_map: dict[EntityID, tuple[str, ...]],
) -> list[ObjectRendering]:
    """Build rendering descriptors for entity IDs in a single cell.

    Inspects component stores on the ``State`` to infer property labels,
    movement direction and speed, then packages them in ``ObjectRendering``
    objects for subsequent image lookup and layering decisions.
    """
    renderings: list[ObjectRendering] = []
    default_appearance: Appearance = Appearance(name="none")
    for eid in eids:
        appearance = state.appearance.get(eid, default_appearance)
        properties = eid_properties_map[eid]

        move_dir: tuple[int, int] | None = None
        move_speed: int = 0
        if eid in state.moving:
            m = state.moving[eid]
            move_dir = m.vector
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


def choose_background(object_renderings: list[ObjectRendering]) -> ObjectRendering:
    """
    Return the lowest-priority background object, or the implicit floor.
    Higher priority values indicate lower importance.
    """
    items = [
        object_rendering
        for object_rendering in object_renderings
        if object_rendering.appearance.background
    ]
    if len(items) == 0:
        return FLOOR_RENDERING
    return max(items, key=lambda x: x.appearance.priority)  # take the lowest priority


def choose_main(object_renderings: list[ObjectRendering]) -> ObjectRendering | None:
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
    return min(items, key=lambda x: x.appearance.priority)  # take the highest priority


def choose_corner_icons(
    object_renderings: list[ObjectRendering], main: ObjectRendering | None
) -> list[ObjectRendering]:
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


def rendering_sort_key(rendering: ObjectRendering) -> tuple[Any, ...]:
    """Deterministic sort key for composition ordering and cache stability."""
    return (
        rendering.appearance.priority,
        rendering.appearance.name,
        rendering.properties,
        rendering.group or "",
        rendering.move_dir or (0, 0),
        rendering.move_speed,
    )


def get_path(object_asset: ObjectAsset, image_hmap: ObjectPropertiesImageMap) -> str:
    """Resolve an image path for an object asset signature.

    Attempts to find the nearest matching property tuple (maximizing shared
    properties, minimizing unmatched) to allow images that only specify a
    subset of possible property labels.
    """
    object_name, object_properties = object_asset
    if object_name not in image_hmap:
        raise ValueError(f"Object rendering {object_asset} is not found in image map")
    nearest_object_properties = max(
        image_hmap[object_name].keys(),
        key=lambda x: (
            len(set(x).intersection(object_properties))
            - len(set(x) - set(object_properties))
        ),
    )
    return image_hmap[object_name][nearest_object_properties]


def get_cell_key(
    background: ObjectRendering,
    primary_renderings: list[ObjectRendering],
    corner_icons: list[ObjectRendering],
    cell_size: int,
    subicon_size: int,
    resolve_asset_path: Callable[[ObjectRendering], str | None],
) -> tuple[Any, ...]:
    def _get_key(obj: ObjectRendering) -> tuple[Any, ...]:
        return (
            resolve_asset_path(obj),
            cell_size,
            obj.group,
            obj.move_dir,
            obj.move_speed,
        )

    background_key = _get_key(background)
    primary_keys = tuple(_get_key(obj) for obj in primary_renderings)
    corner_keys = tuple(_get_key(obj) for obj in corner_icons[:4])
    return (cell_size, subicon_size, background_key, primary_keys, corner_keys)


def render_cell(
    *,
    background: ObjectRendering,
    primary_renderings: list[ObjectRendering],
    corner_icons: list[ObjectRendering],
    cell_size: int,
    subicon_size: int,
    tex_lookup: TexLookupFn,
) -> Image.Image:
    cell_img = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))

    background_tex = tex_lookup(background, cell_size)
    if background_tex:
        cell_img.paste(background_tex, (0, 0))

    for object_rendering in primary_renderings:
        object_tex = tex_lookup(object_rendering, cell_size)
        if object_tex:
            cell_img.alpha_composite(object_tex, (0, 0))

    for idx, corner_icon in enumerate(corner_icons[:4]):
        dx = cell_size - subicon_size if idx % 2 == 1 else 0
        dy = cell_size - subicon_size if idx // 2 == 1 else 0
        tex = tex_lookup(corner_icon, subicon_size)
        if tex:
            cell_img.alpha_composite(tex, (dx, dy))

    return cell_img


def get_floor_base_image(
    state: State,
    *,
    render_width: int,
    render_height: int,
    cell_size: int,
    floor_asset_path: str | None,
    tex_lookup: TexLookupFn,
    tex_lookup_id: int,
    base_cache: dict[BaseCacheKey, Image.Image],
) -> Image.Image:
    base_key = (
        render_width,
        render_height,
        cell_size,
        floor_asset_path,
        tex_lookup_id,
    )
    base_img = base_cache.get(base_key)
    if base_img is None:
        base_img = Image.new(
            "RGBA", (render_width, render_height), (128, 128, 128, 255)
        )
        floor_tex = tex_lookup(FLOOR_RENDERING, cell_size)
        if floor_tex:
            for y in range(state.height):
                for x in range(state.width):
                    base_img.paste(floor_tex, (x * cell_size, y * cell_size))
        base_cache[base_key] = base_img
    return base_img.copy()


@lru_cache(maxsize=128)
def get_files_in_directory(dir: str) -> list[str]:
    """List image files in a directory."""
    if not os.path.isdir(dir):
        return []
    try:
        entries = os.listdir(dir)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return []

    files = sorted(
        f for f in entries if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
    )
    return files


@lru_cache(maxsize=128)
def select_image_from_directory(
    dir: str,
    seed: int | None,
) -> str | None:
    """Choose a deterministic random image file from a directory."""
    files = get_files_in_directory(dir)
    if not files:
        return None

    rng = random.Random(seed)
    chosen = rng.choice(files)
    return os.path.join(dir, chosen)


def validate_appearance_names(state: State, image_map: ImageMap) -> None:
    """Validate that all appearance names in the state have a corresponding image.

    Raises:
        ValueError: If any appearance name in the state is missing from the image map.
    """
    appearance_names_in_state = set(
        appearance.name for appearance in state.appearance.values()
    )
    appearance_names_in_state.add(FLOOR_RENDERING.appearance.name)
    appearance_names_in_image_map = set(name for (name, _) in image_map.keys())
    missing_names = appearance_names_in_state - appearance_names_in_image_map
    if missing_names:
        raise ValueError(f"Missing appearance names in image map: {missing_names}")


@lru_cache(maxsize=128)
def validate_image_map_files(image_map: ImageMap, asset_root: str) -> None:
    """Validate that all image paths in the image map exist.

    Raises:
        FileNotFoundError: If any image path in the image map does not exist.
    """
    for path in image_map.values():
        full_path = os.path.join(asset_root, path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Image path does not exist: {full_path}")


def render(
    state: State,
    resolution: int = DEFAULT_RESOLUTION,
    subicon_percent: float = DEFAULT_SUBICON_PERCENT,
    image_map: ImageMap | None = None,
    asset_root: str = DEFAULT_ASSET_ROOT,
    tex_lookup_fn: TexLookupFn | None = None,
    cache: dict[TexCacheKey, Image.Image | None] | None = None,
    cell_cache: dict[tuple[Any, ...], Image.Image] | None = None,
    base_cache: dict[BaseCacheKey, Image.Image] | None = None,
) -> Image.Image:
    """Render a ``State`` into a PIL Image.

    Args:
        state (State): Game state to visualize.
        resolution (int): Output image width in pixels (height derived from aspect ratio).
        subicon_percent (float): Relative size of corner icons compared to a cell's size.
        image_map (ImageMap | None): Mapping from ``(appearance name, property tuple)`` to asset path.
        asset_root (str): Root directory containing the asset hierarchy (e.g. ``"assets"``).
        tex_lookup_fn (TexLookupFn | None): Override for image loading/recoloring/overlay logic.
        cache (dict | None): Memoization dict keyed by ``(path, size, group, move_dir, speed)``.
        cell_cache (dict | None): Optional per-cell composition cache (default lookup only).
        base_cache (dict | None): Optional memoization for the floor-filled base image.

    Returns:
        Image.Image: Composited RGBA image of the entire grid.
    """
    cell_size: int = resolution // state.width
    subicon_size: int = int(cell_size * subicon_percent)
    render_width: int = cell_size * state.width
    render_height: int = cell_size * state.height
    target_width: int = resolution
    target_height: int = (resolution * state.height) // state.width

    if image_map is None:
        image_map = DEFAULT_IMAGE_MAP

    validate_appearance_names(state, image_map)
    validate_image_map_files(image_map, asset_root)

    if cache is None:
        cache = {}
    if cell_cache is None:
        cell_cache = {}
    if base_cache is None:
        base_cache = {}

    image_hmap: ObjectPropertiesImageMap = defaultdict(dict)
    for (obj_name, obj_properties), value in image_map.items():
        image_hmap[obj_name][tuple(obj_properties)] = value

    state_rng = random.Random(state.seed)
    object_seeds = [state_rng.randint(0, 2**31) for _ in range(len(image_map))]
    image_map_values = list(image_map.values())
    value_to_first_index = {v: i for i, v in enumerate(image_map_values)}
    groups = derive_groups(state)

    eid_properties_map: dict[EntityID, tuple[str, ...]] = get_eid_properties_map(state)

    def resolve_asset_path(object_rendering: ObjectRendering) -> str | None:
        path = get_path(object_rendering.asset(), image_hmap)
        if not path:
            return None

        asset_path = f"{asset_root}/{path}"
        if os.path.isdir(asset_path):
            asset_index = value_to_first_index[path]
            selected_asset_path = select_image_from_directory(
                asset_path, object_seeds[asset_index]
            )
            if selected_asset_path is None:
                return None
            asset_path = selected_asset_path
        return asset_path

    def default_get_tex(
        object_rendering: ObjectRendering, size: int
    ) -> Image.Image | None:
        asset_path = resolve_asset_path(object_rendering)
        if asset_path is None:
            return None

        key = (
            asset_path,
            size,
            object_rendering.group,
            object_rendering.move_dir,
            object_rendering.move_speed,
        )
        if key in cache:
            return cache[key]

        image = load_image(asset_path, size)
        if image is None:
            return None

        image = apply_recolor_if_group(image, object_rendering.group)
        if object_rendering.move_dir is not None and object_rendering.move_speed > 0:
            dx, dy = object_rendering.move_dir
            image = draw_direction_triangles_on_image(
                image.copy(), size, dx, dy, object_rendering.move_speed
            )

        cache[key] = image
        return image

    tex_lookup = tex_lookup_fn or default_get_tex

    img = get_floor_base_image(
        state,
        render_width=render_width,
        render_height=render_height,
        cell_size=cell_size,
        floor_asset_path=resolve_asset_path(FLOOR_RENDERING),
        tex_lookup=tex_lookup,
        tex_lookup_id=0 if tex_lookup_fn is None else id(tex_lookup_fn),
        base_cache=base_cache,
    )

    grid_entities: dict[tuple[int, int], list[EntityID]] = {}
    for eid, pos in state.position.items():
        grid_entities.setdefault((pos.x, pos.y), []).append(eid)

    for (x, y), eids in grid_entities.items():
        x0, y0 = x * cell_size, y * cell_size

        object_renderings = get_object_renderings(
            state, eids, groups, eid_properties_map
        )

        background = choose_background(object_renderings)
        main = choose_main(object_renderings)
        corner_icons = choose_corner_icons(object_renderings, main)
        others = sorted(
            list(set(object_renderings) - set([main] + corner_icons + [background])),
            key=rendering_sort_key,
        )

        primary_renderings: list[ObjectRendering] = others + (
            [main] if main is not None else []
        )

        cell_key: tuple[Any, ...] = get_cell_key(
            background,
            primary_renderings,
            corner_icons,
            cell_size,
            subicon_size,
            resolve_asset_path,
        )
        cached_cell: Image.Image | None = cell_cache.get(cell_key)

        if cached_cell is None:
            cached_cell = render_cell(
                background=background,
                primary_renderings=primary_renderings,
                corner_icons=corner_icons,
                cell_size=cell_size,
                subicon_size=subicon_size,
                tex_lookup=tex_lookup,
            )
            cell_cache[cell_key] = cached_cell

        img.paste(cached_cell, (x0, y0), cached_cell)

    return render_image(
        img,
        render_width=render_width,
        render_height=render_height,
        target_width=target_width,
        target_height=target_height,
    )


def render_image(
    img: Image.Image,
    *,
    render_width: int,
    render_height: int,
    target_width: int,
    target_height: int,
) -> Image.Image:
    """Finalize the render by resizing if needed."""
    if (render_width, render_height) != (target_width, target_height):
        return img.resize((target_width, target_height), resample=Image.NEAREST)
    return img


class ImageRenderer:
    resolution: int
    subicon_percent: float
    image_map: ImageMap
    asset_root: str
    tex_lookup_fn: TexLookupFn | None
    _tex_cache: dict[TexCacheKey, Image.Image | None]
    _cell_cache: dict[tuple[Any, ...], Image.Image]
    _base_cache: dict[BaseCacheKey, Image.Image]

    def __init__(
        self,
        resolution: int = DEFAULT_RESOLUTION,
        subicon_percent: float = DEFAULT_SUBICON_PERCENT,
        image_map: ImageMap | None = None,
        asset_root: str = DEFAULT_ASSET_ROOT,
        tex_lookup_fn: TexLookupFn | None = None,
    ):
        self.resolution = resolution
        self.subicon_percent = subicon_percent
        self.image_map = image_map or DEFAULT_IMAGE_MAP
        self.asset_root = asset_root
        self.tex_lookup_fn = tex_lookup_fn
        self._tex_cache = {}
        self._cell_cache = {}
        self._base_cache = {}

    def render(self, state: State) -> Image.Image:
        """Render convenience wrapper using stored configuration."""
        return render(
            state,
            resolution=self.resolution,
            subicon_percent=self.subicon_percent,
            image_map=self.image_map,
            asset_root=self.asset_root,
            tex_lookup_fn=self.tex_lookup_fn,
            cache=self._tex_cache,
            cell_cache=self._cell_cache,
            base_cache=self._base_cache,
        )
